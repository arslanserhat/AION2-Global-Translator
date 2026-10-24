"""Synthetic heading repair/build tests; no real game or network is accessed."""
from pathlib import Path
import json
import shutil
import unittest
from unittest.mock import patch
import uuid

from aion2_global_translator import service as s
from aion2_global_translator.codec import FString, L10NDocument, L10NTable, locale_seed


class TurkishHeadingRepair(unittest.TestCase):
    def setUp(self):
        parent = (Path.cwd() / "build/test-fixtures").resolve()
        parent.mkdir(parents=True, exist_ok=True)
        self.root = parent / ("display-repair-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.assertTrue(self.root.resolve().is_relative_to(parent))
        self.addCleanup(shutil.rmtree, self.root)
        self.game = self.root / "synthetic-game"
        self.game.mkdir()
        self.pakdir = self.game / "paks"
        self.pakdir.mkdir()
        self.loose = self.game / "L10NString.dat"
        self.backup = self.root / "private/backups"
        self.backup.mkdir(parents=True)
        self.source = {
            "SkillString_DEMO_Snipe_skill_name": "Snipe",
            "SkillAbnormalString_DEMO_desc_name": "Strong recovery",
            "String_UI_PANEL_TITLE_body": "Inventory {0}",
            "String_UI_HELP_TEXT_body": "Return to the city.",
            "String_STR_ITEM_DEMO_SWORD_body": "Sword",
        }
        self.current = {
            "SkillString_DEMO_Snipe_skill_name": "Çulluk",
            "SkillAbnormalString_DEMO_desc_name": "Güçlü İyileştirme",
            "String_UI_PANEL_TITLE_body": "Çanta {0}",
            "String_UI_HELP_TEXT_body": "Şehre dön.",
            "String_STR_ITEM_DEMO_SWORD_body": "Gümüş Kılıç",
        }
        table = L10NTable(FString("AION2"), [(FString(key), FString(value)) for key, value in self.source.items()], trailing=b"\0" * 4)
        doc = L10NDocument(table, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)
        self.manifest = {locale_seed("en-US"): b"k" * 32}
        self.original = L10NDocument.decode(doc.encode(), "en-US", self.manifest)
        self.installed_dat = self.original.encode(self.original.table.translated(self.current))
        self.loose.write_bytes(self.installed_dat)
        self.state = dict(steam_build=s.BUILD, dat_sha256=s.sha(self.installed_dat),
                          target_language="tr", entries=len(self.source))
        (self.backup / "state.json").write_text(json.dumps(self.state), encoding="utf-8")
        self.service = s.TranslatorService(data_dir=self.root / "private")
        self.patchers = [
            patch.object(s, "DISPLAY_ENTRY_COUNT", len(self.source)),
            patch.object(s, "game_running", return_value=False),
            patch.object(self.service, "paths", return_value=(self.game, self.pakdir, self.loose, self.backup)),
            patch.object(self.service, "_state", side_effect=lambda *args: dict(self.state)),
            patch.object(self.service, "_extract", return_value=(self.original, self.manifest)),
            patch.object(self.service, "install_stage", return_value=dict(status="installed", installed_language="tr")),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.before_game = self.snapshot(self.game)

    @staticmethod
    def snapshot(path):
        return {str(file.relative_to(path)): file.read_bytes()
                for file in path.rglob("*") if file.is_file()}

    def decode(self, stage):
        return L10NDocument.decode((stage / "L10NString.dat").read_bytes(), "en-US", self.manifest).table.as_dict()

    def test_repair_preserves_unicode_body_and_delegates_to_normal_install(self):
        result = self.service.repair_turkish_headings(self.game)
        stage = Path(result["stage"])
        output = self.decode(stage)
        self.assertEqual(output["SkillString_DEMO_Snipe_skill_name"], "Keskin Atis")
        self.assertEqual(output["SkillAbnormalString_DEMO_desc_name"], "Guclu Iyilestirme")
        self.assertEqual(output["String_UI_PANEL_TITLE_body"], "Canta {0}")
        self.assertEqual(output["String_UI_HELP_TEXT_body"], "Şehre dön.")
        self.assertEqual(output["String_STR_ITEM_DEMO_SWORD_body"], "Gumus Kilic")
        self.assertEqual(set(output), set(self.source))
        self.service.install_stage.assert_called_once_with(self.game, stage)
        self.assertEqual(self.snapshot(self.game), self.before_game)
        prior = Path(result["prior_stage"])
        self.assertEqual((prior / "L10NString.dat").read_bytes(), self.installed_dat)
        self.assertEqual(json.loads((prior / "installed-state.json").read_text("utf-8")), self.state)
        meta = json.loads((stage / "patch-meta.json").read_text("utf-8"))
        self.assertEqual(meta["display_profile"], "turkish-heading-font-safe-v2")
        self.assertEqual(meta["dat_sha256"], s.sha((stage / "L10NString.dat").read_bytes()))
        self.assertEqual(meta["display_report"]["canonical_skill_name_fixes"], ["SkillString_DEMO_Snipe_skill_name"])

    def test_existing_first_restore_point_is_not_overwritten(self):
        first = self.service.repair_turkish_headings(self.game)
        prior = Path(first["prior_stage"])
        before = self.snapshot(prior)
        # A later verified install can differ, while the initial restore point stays.
        changed = dict(self.current, String_UI_PANEL_TITLE_body="Eşyalar {0}")
        self.loose.write_bytes(self.original.encode(self.original.table.translated(changed)))
        self.state["dat_sha256"] = s.sha(self.loose.read_bytes())
        (self.backup / "state.json").write_text(json.dumps(self.state), encoding="utf-8")
        self.service.repair_turkish_headings(self.game)
        self.assertEqual(self.snapshot(prior), before)

    def test_running_game_or_non_turkish_state_refuses_without_stages(self):
        with patch.object(s, "game_running", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "Close AION 2"):
                self.service.repair_turkish_headings(self.game)
        self.state["target_language"] = "de"
        (self.backup / "state.json").write_text(json.dumps(self.state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "installed Turkish"):
            self.service.repair_turkish_headings(self.game)
        self.assertFalse((self.service.data / "stages").exists())
        self.service.install_stage.assert_not_called()
        self.assertEqual(self.snapshot(self.game), self.before_game)

    def test_changed_installed_hash_is_rejected(self):
        self.loose.write_bytes(b"external edit after verified state")
        before = self.snapshot(self.game)
        with self.assertRaisesRegex(ValueError, "Installed translation changed"):
            self.service.repair_turkish_headings(self.game)
        self.assertEqual(self.snapshot(self.game), before)
        self.service.install_stage.assert_not_called()

    def test_incomplete_key_set_is_rejected(self):
        smaller = L10NTable(FString("AION2"), [(FString("different"), FString("Başlık"))])
        doc = L10NDocument(smaller, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)
        self.loose.write_bytes(doc.encode())
        self.state["dat_sha256"] = s.sha(self.loose.read_bytes())
        (self.backup / "state.json").write_text(json.dumps(self.state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "complete original source key set"):
            self.service.repair_turkish_headings(self.game)
        self.service.install_stage.assert_not_called()

    def test_invalid_existing_restore_point_is_preserved_and_blocks_install(self):
        prior = self.service.data / "stages/tr-before-font-fix"
        prior.mkdir(parents=True)
        (prior / "patch-meta.json").write_text("{}", encoding="utf-8")
        (prior / "L10NString.dat").write_bytes(b"unverified pre-existing backup")
        before = self.snapshot(prior)
        with self.assertRaisesRegex(ValueError, "pre-repair pack is invalid"):
            self.service.repair_turkish_headings(self.game)
        self.assertEqual(self.snapshot(prior), before)
        self.assertEqual(self.snapshot(self.game), self.before_game)
        self.service.install_stage.assert_not_called()

    def test_new_turkish_build_defaults_to_font_profile_without_installing(self):
        translation = self.root / "translated.json"
        translation.write_text(json.dumps(self.current, ensure_ascii=False), encoding="utf-8")
        result = self.service.build_translation(self.game, "tr", {"provider": "offline-json", "json_path": str(translation)})
        output = self.decode(Path(result["stage"]))
        self.assertEqual(output["SkillString_DEMO_Snipe_skill_name"], "Keskin Atis")
        self.assertEqual(output["String_UI_HELP_TEXT_body"], "Şehre dön.")
        meta = json.loads((Path(result["stage"]) / "patch-meta.json").read_text("utf-8"))
        self.assertTrue(meta["font_compatible_titles"])
        self.assertTrue(meta["display_report"]["protected_literals_preserved"])
        self.service.install_stage.assert_not_called()
        self.assertEqual(self.snapshot(self.game), self.before_game)

    def test_new_turkish_build_can_keep_unicode_headings(self):
        translation = self.root / "translated.json"
        translation.write_text(json.dumps(self.current, ensure_ascii=False), encoding="utf-8")
        result = self.service.build_translation(self.game, "tr", {"provider": "offline-json", "json_path": str(translation),
                                                                  "font_compatible_titles": False})
        output = self.decode(Path(result["stage"]))
        self.assertEqual(output["SkillString_DEMO_Snipe_skill_name"], "Keskin Atış")
        self.assertEqual(output["String_UI_PANEL_TITLE_body"], "Çanta {0}")
        self.assertEqual(output["String_UI_HELP_TEXT_body"], "Şehre dön.")
        self.service.install_stage.assert_not_called()

    def test_external_change_before_install_is_preserved(self):
        closed_calls = []
        external = b"external change while a repair pack was prepared"
        def check_closed():
            closed_calls.append(True)
            if len(closed_calls) == 2:
                self.loose.write_bytes(external)
        with patch.object(self.service, "_closed", side_effect=check_closed):
            with self.assertRaisesRegex(ValueError, "changed while preparing heading repair"):
                self.service.repair_turkish_headings(self.game)
        self.assertEqual(self.loose.read_bytes(), external)
        self.service.install_stage.assert_not_called()

    def test_disabling_profile_removes_stale_display_report(self):
        translation = self.root / "translated.json"
        translation.write_text(json.dumps(self.current, ensure_ascii=False), encoding="utf-8")
        config = {"provider": "offline-json", "json_path": str(translation)}
        result = self.service.build_translation(self.game, "tr", config)
        report = Path(result["stage"]) / "display-report.json"
        self.assertTrue(report.is_file())
        self.service.build_translation(self.game, "tr", dict(config, font_compatible_titles=False))
        self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
