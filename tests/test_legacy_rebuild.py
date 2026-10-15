"""Verified, unchanged legacy Turkish cells may survive an offline JSON edit."""
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid

from aion2_global_translator import service as s
from aion2_global_translator.codec import FString, L10NDocument, L10NTable, locale_seed
from aion2_global_translator.display import apply_turkish_heading_compatibility
from aion2_global_translator.multilingual import apply_target_context_terms


class LegacyOfflineRebuild(unittest.TestCase):
    def setUp(self):
        parent = (Path.cwd() / "build/test-fixtures").resolve()
        parent.mkdir(parents=True, exist_ok=True)
        self.root = parent / ("legacy-rebuild-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.assertTrue(self.root.is_relative_to(parent))
        self.addCleanup(shutil.rmtree, self.root)
        self.service = s.TranslatorService(data_dir=self.root / "private")
        self.source = {
            "SkillString_DEMO_desc_name": "HP recovery 10 %s",
            "String_UI_HELP_TEXT_body": "Restores MP <QK>{0}</>\n5",
            "String_UI_GREETING_body": "Welcome",
            "String_UI_DAMAGE_body": "Damage 20",
        }
        self.legacy = {
            "SkillString_DEMO_desc_name": "Can İyileştirme 10 %s",
            "String_UI_HELP_TEXT_body": "Mana yeniler <QK>{0}</>\n5",
            "String_UI_GREETING_body": "Merhaba",
            "String_UI_DAMAGE_body": "Hasar 20",
        }
        self.doc = self.make_doc(self.source)
        self.manifest = {locale_seed("en-US"): b"k" * 32}
        self.stage = self.service.data / "stages/tr"
        self.input = self.root / "edited.json"
        self.config = dict(provider="offline-json", json_path=str(self.input))
        self.write_reference()
        self.write_input(dict(self.legacy, String_UI_GREETING_body="Hoş geldin"))
        for patcher in [patch.object(self.service, "_extract", return_value=(self.doc, self.manifest)),
                        patch.object(self.service, "install_stage")]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_doc(self, values, namespace="AION2"):
        table = L10NTable(FString(namespace), [(FString(k), FString(v)) for k, v in values.items()])
        return L10NDocument(table, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)

    def write_input(self, values):
        self.input.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")

    def write_reference(self, values=None, *, namespace="AION2", metadata=None):
        values, _ = apply_turkish_heading_compatibility(values or self.legacy)
        data = self.make_doc(values, namespace).encode()
        self.stage.mkdir(parents=True, exist_ok=True)
        (self.stage / "L10NString.dat").write_bytes(data)
        meta = dict(steam_build=s.BUILD, original_pak_sha256=s.ORIGINAL_SHA, target_language="tr",
                    source_entry_count=len(self.source), dat_sha256=s.sha(data), quality_gate_passed=True,
                    remaining_untranslated_candidate_entries=0)
        meta.update(metadata or {})
        (self.stage / "patch-meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return data

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.stage.iterdir() if p.is_file()}

    def build(self, config=None):
        return self.service.build_translation("synthetic-game", "tr", config or self.config)

    def output(self):
        return L10NDocument.decode((self.stage / "L10NString.dat").read_bytes(), "en-US", self.manifest).table.as_dict()

    def test_untouched_legacy_cells_and_one_other_edit_rebuild_with_auditable_scope(self):
        previous = (self.stage / "L10NString.dat").read_bytes()
        self.build()
        values = self.output()
        self.assertEqual(values["SkillString_DEMO_desc_name"], "Can Iyilestirme 10 %s")
        self.assertEqual(values["String_UI_HELP_TEXT_body"], self.legacy["String_UI_HELP_TEXT_body"])
        self.assertEqual(values["String_UI_GREETING_body"], "Hoş geldin")
        meta = json.loads((self.stage / "patch-meta.json").read_text("utf-8"))
        self.assertEqual(meta["carry_forward_legacy_keys"], ["SkillString_DEMO_desc_name", "String_UI_HELP_TEXT_body"])
        self.assertEqual(meta["carry_forward_legacy_count"], 2)
        self.assertEqual(meta["carry_forward_legacy_reference"]["dat_sha256"], s.sha(previous))
        self.assertFalse(meta["human_reviewed"])
        self.assertIn("unchanged verified legacy Turkish cells", meta["validation_scope"])
        canonical = json.loads((self.stage / "entries.translated.json").read_text("utf-8"))
        self.assertEqual(canonical["SkillString_DEMO_desc_name"], self.legacy["SkillString_DEMO_desc_name"])
        self.service.install_stage.assert_not_called()

    def test_changed_legacy_alias_is_not_granted_an_exception(self):
        self.write_input(dict(self.legacy, String_UI_HELP_TEXT_body="Milletvekili yeniler <QK>{0}</>\n5"))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Changed legacy cell"):
            self.build()
        self.assertEqual(self.snapshot(), before)

    def test_original_numbers_tags_macros_and_controls_still_have_to_match(self):
        for bad in ["Mana yeniler <QK>{0}</>\n6", "Mana yeniler <other>{0}</>\n5",
                    "Mana yeniler <QK>{1}</>\n5", "Mana yeniler <QK>{0}</> 5"]:
            # Even if a hash-consistent legacy DAT contains this same corruption,
            # original English structural validation must reject the exception.
            values = dict(self.legacy, String_UI_HELP_TEXT_body=bad)
            self.write_reference(values)
            self.write_input(values)
            before = self.snapshot()
            with self.subTest(value=bad), self.assertRaises(ValueError):
                self.build()
            self.assertEqual(self.snapshot(), before)

    def test_brand_new_offline_map_cannot_introduce_legacy_aliases(self):
        (self.stage / "L10NString.dat").unlink()
        (self.stage / "patch-meta.json").unlink()
        with self.assertRaisesRegex(ValueError, "existing verified"):
            self.build()
        self.assertEqual(self.snapshot(), {})

    def test_online_provider_remains_strict_even_with_a_legacy_reference(self):
        before = self.snapshot()
        with patch("aion2_global_translator.providers.LibreTranslateProvider") as provider, \
                patch.object(self.service, "_verified_legacy_reference") as reference:
            provider.return_value.languages.return_value = [{"code": "en", "targets": ["tr"]}, {"code": "tr"}]
            provider.return_value.translate_batch.return_value = ["Can İyileştirme 10 %s"]
            with self.assertRaises(ValueError):
                self.build(dict(provider="libretranslate", url="https://synthetic.invalid"))
            reference.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_tampered_reference_hash_or_identity_is_rejected_without_stage_writes(self):
        cases = [{"dat_sha256": "0" * 64}, {"steam_build": "other"},
                 {"original_pak_sha256": "0" * 64}, {"target_language": "de"},
                 {"source_entry_count": 3}, {"quality_gate_passed": False},
                 {"remaining_untranslated_candidate_entries": 1}]
        for metadata in cases:
            self.write_reference(metadata=metadata)
            before = self.snapshot()
            with self.subTest(metadata=metadata), self.assertRaisesRegex(ValueError, "existing verified"):
                self.build()
            self.assertEqual(self.snapshot(), before)

    def test_reference_namespace_and_complete_key_set_are_verified(self):
        for namespace, values in [("OTHER", self.legacy), ("AION2", dict(self.legacy, unexpected="Extra"))]:
            self.write_reference(values, namespace=namespace)
            before = self.snapshot()
            with self.subTest(namespace=namespace), self.assertRaises(ValueError):
                self.build()
            self.assertEqual(self.snapshot(), before)

    def test_new_strict_map_never_needs_or_trusts_a_legacy_reference(self):
        proper = dict(self.legacy, SkillString_DEMO_desc_name="HP İyileştirme 10 %s",
                      String_UI_HELP_TEXT_body="MP yeniler <QK>{0}</>\n5")
        self.write_input(proper)
        self.write_reference(metadata={"dat_sha256": "0" * 64})
        with patch.object(self.service, "_verified_legacy_reference", side_effect=AssertionError("must stay lazy")):
            self.build()
        meta = json.loads((self.stage / "patch-meta.json").read_text("utf-8"))
        self.assertEqual(meta["carry_forward_legacy_keys"], [])
        self.assertEqual(self.output()["String_UI_HELP_TEXT_body"], proper["String_UI_HELP_TEXT_body"])

    def test_fixing_a_legacy_cell_to_the_current_identifier_is_allowed_normally(self):
        proper = dict(self.legacy, String_UI_HELP_TEXT_body="MP yeniler <QK>{0}</>\n5")
        self.write_input(proper)
        self.build()
        meta = json.loads((self.stage / "patch-meta.json").read_text("utf-8"))
        self.assertEqual(meta["carry_forward_legacy_keys"], ["SkillString_DEMO_desc_name"])
        self.assertEqual(self.output()["String_UI_HELP_TEXT_body"], proper["String_UI_HELP_TEXT_body"])

    def test_after_context_changes_cannot_modify_inherited_alias_text(self):
        def changed_context(source, values, language):
            output, report = apply_target_context_terms(source, values, language)
            output["String_UI_HELP_TEXT_body"] = "Milletvekili yeniler <QK>{0}</>\n5"
            return output, report
        before = self.snapshot()
        with patch("aion2_global_translator.multilingual.apply_target_context_terms", side_effect=changed_context):
            with self.assertRaisesRegex(ValueError, "Legacy cell changed"):
                self.build()
        self.assertEqual(self.snapshot(), before)

    def test_reference_change_during_context_processing_is_preserved(self):
        def external_change(source, values, language):
            result = apply_target_context_terms(source, values, language)
            (self.stage / "L10NString.dat").write_bytes(b"external change")
            return result
        with patch("aion2_global_translator.multilingual.apply_target_context_terms", side_effect=external_change):
            with self.assertRaisesRegex(ValueError, "changed while rebuilding"):
                self.build()
        self.assertEqual((self.stage / "L10NString.dat").read_bytes(), b"external change")
        self.assertFalse((self.stage / "entries.translated.json").exists())

    def test_font_option_can_keep_canonical_unicode_equivalent_to_the_verified_dat(self):
        self.build(dict(self.config, font_compatible_titles=False))
        self.assertEqual(self.output()["SkillString_DEMO_desc_name"], "Can İyileştirme 10 %s")
        meta = json.loads((self.stage / "patch-meta.json").read_text("utf-8"))
        self.assertEqual(meta["carry_forward_legacy_count"], 2)


if __name__ == "__main__":
    unittest.main()
