"""Context terminology and legacy repair tests using synthetic data only."""
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid

from aion2_global_translator import service as s
from aion2_global_translator.codec import FString, L10NDocument, L10NTable, locale_seed
from aion2_global_translator.protection import validate
from aion2_global_translator.terminology import apply_turkish_context_terms


class ContextTerms(unittest.TestCase):
    def test_commands_are_imperative_but_noun_fields_and_sentences_stay(self):
        source = {
            "String_UI_HUD_KEYGUIDE_DESC_TALK_body": "Talk",
            "PcSocialAction_15_action_name": "Talk",
            "InputKeyMapping_BattleUse_desc": "Use",
            "String_UI_WORKSHOP_BUTTON_CRAFT_body": "Craft",
            "String_UI_CONTEXT_MENU_CLAIMALL_body": "Claim All",
            "String_UI_PARTY_BTN_INVITE_body": "Invite",
            "String_UI_CHAT_MENU_TALK_body": "Talk",
            "String_UI_TALK_TITLE_body": "Talk",
            "String_UI_TALK_TITLE2_body": "Talk",
            "String_STR_ITEM_TALK_body": "Talk",
            "String_UI_HELP_TEXT_body": "Talk to the guard.",
        }
        current = {k: "Konuşmak" for k in source}
        current["String_UI_HELP_TEXT_body"] = "Muhafızla konuş."
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output["String_UI_HUD_KEYGUIDE_DESC_TALK_body"], "Konuş")
        self.assertEqual(output["PcSocialAction_15_action_name"], "Konuş")
        self.assertEqual(output["InputKeyMapping_BattleUse_desc"], "Kullan")
        self.assertEqual(output["String_UI_WORKSHOP_BUTTON_CRAFT_body"], "Üret")
        self.assertEqual(output["String_UI_CONTEXT_MENU_CLAIMALL_body"], "Tümünü al")
        self.assertEqual(output["String_UI_PARTY_BTN_INVITE_body"], "Davet et")
        self.assertEqual(report["changed_entries"], 6)
        for key in ["String_UI_CHAT_MENU_TALK_body", "String_UI_TALK_TITLE_body",
                    "String_UI_TALK_TITLE2_body", "String_STR_ITEM_TALK_body", "String_UI_HELP_TEXT_body"]:
            self.assertEqual(output[key], current[key])
        self.assertEqual(current["PcSocialAction_15_action_name"], "Konuşmak")

    def test_class_aliases_require_verified_label_context(self):
        source = {
            "String_STR_CLASS_GLADIATOR_body": "Gladiator",
            "String_STR_CLASS_TEMPLAR_body": "Templar",
            "String_STR_CLASS_RANGER_body": "Ranger",
            "String_UI_ITEM_TOOLTIP_MOUSEOVER_TEXT_ASSASSIN_body": "Assassin",
            "String_STR_CLASS_ELEMENTALIST_body": "Spiritmaster",
            "String_UI_SHOP_ENUM_CATEGORY_Abyss_Stigma_EL_body": "Elementalist",
            "String_UI_ITEM_TOOLTIP_MOUSEOVER_TEXT_SORCERER_body": "Sorcerer",
            "String_UI_CLASS_LABEL_CLERIC_body": "Cleric",
            "String_UI_SHOP_ENUM_CATEGORY_Abyss_SpecializedSkill_CH_body": "Chanter",
            "String_STR_NPC_ELEMENTALIST_body": "Elementalist",
            "SkillAbnormalString_NPC_ASSASSIN_desc_name": "Assassin",
        }
        output, report = apply_turkish_context_terms(source, source)
        self.assertEqual(list(output.values())[:9], ["Gladyatör", "Tapınakçı", "Avcı", "Suikastçı",
                         "Ruh Çağırıcı", "Ruh Çağırıcı", "Sihirbaz", "Ruhban", "Kantor"])
        self.assertEqual(output["String_STR_NPC_ELEMENTALIST_body"], "Elementalist")
        self.assertEqual(output["SkillAbnormalString_NPC_ASSASSIN_desc_name"], "Assassin")
        self.assertEqual(report["rule_counts"]["class_label"], 9)

    def test_exact_values_and_skill_context_do_not_rewrite_prose(self):
        source = {"SkillString_RANGER_10_skill_name": "Snipe", "NoteData_1_text": "Snipe",
                  "String_UI_BUTTON_TALK_body": "Talk {0}", "String_UI_ACTION_ATTACK_body": "Attack!"}
        current = {"SkillString_RANGER_10_skill_name": "Su çulluğu", "NoteData_1_text": "Çulluk",
                   "String_UI_BUTTON_TALK_body": "Konuşmak {0}", "String_UI_ACTION_ATTACK_body": "Saldır!"}
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output, dict(current, SkillString_RANGER_10_skill_name="Keskin Atış"))
        again, second = apply_turkish_context_terms(source, output)
        self.assertEqual(again, output)
        self.assertEqual(second["changed_entries"], 0)
        self.assertEqual(report["rule_keys"]["skill_snipe"], ["SkillString_RANGER_10_skill_name"])

    def test_partial_or_invalid_maps_are_rejected(self):
        with self.assertRaises(ValueError):
            apply_turkish_context_terms({"a": "Talk"}, {})
        with self.assertRaises(TypeError):
            apply_turkish_context_terms({"a": 1}, {"a": "Konuş"})

    def test_weapon_staff_compounds_preserve_protected_literals(self):
        source = {"Skin_WP_0009_T04_ST_desc_dark": "Guardian Staff (Staff)",
                  "String_STR_ITEM_EQUIP_WP_STAFF_TEST_body": '<QK>Guardian Staff</> {Personeli} +5 %s'}
        current = {"Skin_WP_0009_T04_ST_desc_dark": "Muhafız Personeli (Personel)",
                   "String_STR_ITEM_EQUIP_WP_STAFF_TEST_body": '<QK>Muhafız Personeli</> {Personeli} +5 %s'}
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output["Skin_WP_0009_T04_ST_desc_dark"], "Muhafız Asası (Asa)")
        self.assertEqual(output["String_STR_ITEM_EQUIP_WP_STAFF_TEST_body"], '<QK>Muhafız Asası</> {Personeli} +5 %s')
        self.assertEqual(report["rule_counts"]["staff_weapon_polysemy"], 2)
        validate(source["String_STR_ITEM_EQUIP_WP_STAFF_TEST_body"], output["String_STR_ITEM_EQUIP_WP_STAFF_TEST_body"])

    def test_tavern_employees_and_unverified_staff_context_are_not_weapons(self):
        source = {"String_STR_NPC_TAVERN_STAFF_body": "Tavern Staff",
                  "EnvObjData_DROPPED_STAFF_desc": "Dropped Staff",
                  "String_STR_ITEM_EQUIP_WP_STAFF_DESC_body": "The Staff employs a guard.",
                  "String_UI_STAFF_LIST_TITLE_body": "Staff"}
        current = {k: "Han Personeli" for k in source}
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output, current)
        self.assertEqual(report["changed_entries"], 0)

    def test_cast_duration_is_fixed_only_for_the_verified_casting_stat(self):
        source = {"String_StatName_CastingTime_body": "Cast duration", "NoteData_CASTING_TITLE": "Cast duration"}
        current = {k: "Oyuncu kadrosunun süresi" for k in source}
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output["String_StatName_CastingTime_body"], "Beceri hazırlık süresi")
        self.assertEqual(output["NoteData_CASTING_TITLE"], "Oyuncu kadrosunun süresi")
        self.assertEqual(report["rule_counts"]["casting_time_stat"], 1)

    def test_bound_flag_is_corrected_without_changing_book_binding_or_literals(self):
        source = {"String_STR_ITEM_BOOK_body": 'Leather-bound Book (Bound) <tag note="(Ciltli)">{flag:(Ciltli)} +5 %s</tag>',
                  "String_STR_ITEM_HARDBOUND_body": "Hardbound Balaur Scale (Bound)"}
        current = {"String_STR_ITEM_BOOK_body": 'Deri Ciltli Kitap (Ciltli) <tag note="(Ciltli)">{flag:(Ciltli)} +5 %s</tag>',
                   "String_STR_ITEM_HARDBOUND_body": "Sert Ciltli Balaur Pulu (Bağlı)"}
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output["String_STR_ITEM_BOOK_body"], 'Deri Ciltli Kitap (Bağlı) <tag note="(Ciltli)">{flag:(Ciltli)} +5 %s</tag>')
        self.assertEqual(output["String_STR_ITEM_HARDBOUND_body"], current["String_STR_ITEM_HARDBOUND_body"])
        self.assertEqual(report["rule_counts"]["bound_item_flag"], 1)
        validate(source["String_STR_ITEM_BOOK_body"], output["String_STR_ITEM_BOOK_body"])

    def test_book_binding_and_protected_bound_text_are_not_item_flags(self):
        source = {"String_STR_ITEM_BOOK_body": "Hardbound Book",
                  "String_STR_ITEM_BOOK_TITLE_body": '<tag example="(Bound)">Book</tag> {name:(Bound)}'}
        current = {"String_STR_ITEM_BOOK_body": "Ciltli Kitap",
                   "String_STR_ITEM_BOOK_TITLE_body": '<tag example="(Bound)">Kitap (Ciltli)</tag> {name:(Bound)}'}
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output, current)
        self.assertEqual(report["changed_entries"], 0)

    def test_bound_flag_and_staff_rules_compose_and_are_idempotent(self):
        key = "String_STR_ITEM_EQUIP_WP_STAFF_TEST_body"
        source, current = {key: "Guardian Staff (Bound)"}, {key: "Muhafız Personeli (Ciltli)"}
        output, report = apply_turkish_context_terms(source, current)
        self.assertEqual(output[key], "Muhafız Asası (Bağlı)")
        self.assertEqual(report["changed_entries"], 1)
        self.assertEqual(report["rule_counts"]["staff_weapon_polysemy"], 1)
        self.assertEqual(report["rule_counts"]["bound_item_flag"], 1)
        again, second = apply_turkish_context_terms(source, output)
        self.assertEqual(again, output)
        self.assertEqual(second["changed_entries"], 0)


class LegacyLiteralValidation(unittest.TestCase):
    def test_legacy_can_mana_are_diagnostic_while_new_provider_stays_strict(self):
        source = "Recover 10 HP and 5 MP %s\n{0}<QK>Now</>"
        target = "10 Can ve 5 Mana %s yenile\n{0}<QK>Şimdi</>"
        diagnostic = s._legacy_structure_and_abbreviations(source, target)
        self.assertEqual(diagnostic, {"source": {"HP": 1, "MP": 1}, "installed": {}})
        with self.assertRaises(ValueError):
            validate(source, target)
        validate(target, target.replace("Şimdi", "Simdi"))

    def test_relaxation_cannot_hide_numeric_printf_macro_or_newline_loss(self):
        source = "HP 10 %s %d\n{0}<QK>Now</>"
        valid = "Can 10 %s %d\n{0}<QK>Şimdi</>"
        for bad in [valid.replace("10", "11"), valid.replace("%s %d", "%d %s"),
                    valid.replace("{0}", ""), valid.replace("\n", " "),
                    valid.replace("<QK>Şimdi</>", "</>Şimdi<QK>")]:
            with self.subTest(target=bad), self.assertRaises(ValueError):
                s._legacy_structure_and_abbreviations(source, bad)
        with self.assertRaises(ValueError):
            s._legacy_structure_and_abbreviations("HP", "")


class TerminologyServiceIntegration(unittest.TestCase):
    def setUp(self):
        parent = (Path.cwd() / "build/test-fixtures").resolve()
        parent.mkdir(parents=True, exist_ok=True)
        self.root = parent / ("terminology-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.assertTrue(self.root.is_relative_to(parent))
        self.addCleanup(shutil.rmtree, self.root)
        self.game = self.root / "synthetic-game"
        self.game.mkdir()
        self.pakdir = self.game / "paks"
        self.pakdir.mkdir()
        self.loose = self.game / "L10NString.dat"
        self.backup = self.root / "private/backups"
        self.backup.mkdir(parents=True)
        self.source = {"SkillString_DEMO_desc_name": "HP recovery 10 %s",
                       "String_UI_HUD_KEYGUIDE_DESC_TALK_body": "Talk",
                       "String_STR_CLASS_TEMPLAR_body": "Templar",
                       "SkillString_DEMO_Snipe_skill_name": "Snipe"}
        self.current = {"SkillString_DEMO_desc_name": "Can İyileştirme 10 %s",
                        "String_UI_HUD_KEYGUIDE_DESC_TALK_body": "Konuşmak",
                        "String_STR_CLASS_TEMPLAR_body": "Tapınak Şövalyesi",
                        "SkillString_DEMO_Snipe_skill_name": "Çulluk"}
        table = L10NTable(FString("AION2"), [(FString(k), FString(v)) for k, v in self.source.items()])
        doc = L10NDocument(table, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)
        self.manifest = {locale_seed("en-US"): b"k" * 32}
        self.original = L10NDocument.decode(doc.encode(), "en-US", self.manifest)
        self.service = s.TranslatorService(data_dir=self.root / "private")
        self.state = dict(steam_build=s.BUILD, target_language="tr", entries=len(self.source))
        self.install_current(self.current)
        for patcher in [patch.object(s, "DISPLAY_ENTRY_COUNT", len(self.source)),
                        patch.object(s, "game_running", return_value=False),
                        patch.object(self.service, "paths", return_value=(self.game, self.pakdir, self.loose, self.backup)),
                        patch.object(self.service, "_state", side_effect=lambda *args: dict(self.state)),
                        patch.object(self.service, "_extract", return_value=(self.original, self.manifest)),
                        patch.object(self.service, "install_stage", return_value={"status": "installed"})]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def install_current(self, values):
        dat = self.original.encode(self.original.table.translated(values))
        self.loose.write_bytes(dat)
        self.state["dat_sha256"] = s.sha(dat)
        (self.backup / "state.json").write_text(json.dumps(self.state), encoding="utf-8")

    def decode(self, stage):
        return L10NDocument.decode((stage / "L10NString.dat").read_bytes(), "en-US", self.manifest).table.as_dict()

    def test_legacy_font_repair_keeps_can_alias_and_applies_context_before_folding(self):
        installed = self.loose.read_bytes()
        result = self.service.repair_turkish_headings(self.game)
        stage = Path(result["stage"])
        output = self.decode(stage)
        self.assertEqual(output["SkillString_DEMO_desc_name"], "Can Iyilestirme 10 %s")
        self.assertEqual(output["String_UI_HUD_KEYGUIDE_DESC_TALK_body"], "Konuş")
        self.assertEqual(output["String_STR_CLASS_TEMPLAR_body"], "Tapınakçı")
        self.assertEqual(output["SkillString_DEMO_Snipe_skill_name"], "Keskin Atis")
        self.assertEqual(self.loose.read_bytes(), installed)
        self.service.install_stage.assert_called_once_with(self.game, stage)
        diagnostic = json.loads((stage / "legacy-abbreviation-report.json").read_text("utf-8"))
        self.assertEqual(diagnostic, {"SkillString_DEMO_desc_name": {"source": {"HP": 1}, "installed": {}}})
        meta = json.loads((stage / "patch-meta.json").read_text("utf-8"))
        self.assertEqual(meta["context_terms_report"]["changed_entries"], 3)
        self.assertIn("not a full semantic review", meta["validation_scope"])

    def test_bad_legacy_source_numbers_are_blocked_before_staging_or_install(self):
        self.install_current(dict(self.current, SkillString_DEMO_desc_name="Can İyileştirme 11 %s"))
        installed = self.loose.read_bytes()
        with self.assertRaisesRegex(ValueError, "invalid structural literals"):
            self.service.repair_turkish_headings(self.game)
        self.assertEqual(self.loose.read_bytes(), installed)
        self.assertFalse((self.service.data / "stages").exists())
        self.service.install_stage.assert_not_called()

    def test_new_build_keeps_strict_abbreviations_and_canonical_context_terms(self):
        path = self.root / "translated.json"
        path.write_text(json.dumps(self.current), encoding="utf-8")
        config = dict(provider="offline-json", json_path=str(path), font_compatible_titles=False)
        with self.assertRaises(ValueError):
            self.service.build_translation(self.game, "tr", config)
        proper = dict(self.current, SkillString_DEMO_desc_name="HP İyileştirme 10 %s")
        path.write_text(json.dumps(proper), encoding="utf-8")
        result = self.service.build_translation(self.game, "tr", config)
        stage = Path(result["stage"])
        output = self.decode(stage)
        self.assertEqual(output["SkillString_DEMO_desc_name"], "HP İyileştirme 10 %s")
        self.assertEqual(output["String_UI_HUD_KEYGUIDE_DESC_TALK_body"], "Konuş")
        self.assertEqual(output["String_STR_CLASS_TEMPLAR_body"], "Tapınakçı")
        self.assertEqual(output["SkillString_DEMO_Snipe_skill_name"], "Keskin Atış")
        self.assertEqual(json.loads((stage / "context-terms-report.json").read_text("utf-8"))["changed_entries"], 3)
        self.service.install_stage.assert_not_called()


if __name__ == "__main__":
    unittest.main()
