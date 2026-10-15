"""A complete key set does not prove unchanged English was translated."""
import json
from pathlib import Path
import shutil
import unittest
import uuid
from unittest.mock import patch
from aion2_global_translator.codec import FString, L10NDocument, L10NTable, locale_seed
from aion2_global_translator.service import TranslatorService


class BuildWorkflow(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / "build/test-fixtures" / str(uuid.uuid4())
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.service = TranslatorService(data_dir=self.root / "private")
        table = L10NTable(FString("SYNTHETIC"), [(FString("label"), FString("Settings")), (FString("name"), FString("Alice"))])
        self.doc = L10NDocument(table, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)
        self.manifest = {locale_seed("en-US"): b"k" * 32}
        self.source = self.root / "map.json"
        self.source.write_text(json.dumps({"label": "Ayarlar", "name": "Alice"}), encoding="utf-8")

    def test_unchanged_names_need_explicit_review_and_build_never_installs(self):
        config = {"provider": "offline-json", "json_path": str(self.source)}
        with patch.object(self.service, "_extract", return_value=(self.doc, self.manifest)), patch.object(self.service, "install_stage") as install:
            with self.assertRaisesRegex(ValueError, "need review"):
                self.service.build_translation("unused", "tr", config)
            report = self.service.data / "stages/tr/unchanged-review.json"
            self.assertEqual(json.loads(report.read_text("utf-8")), {"name": "Alice"})
            self.assertFalse((report.parent / "L10NString.dat").exists())
            config["review_unchanged"] = True
            result = self.service.build_translation("unused", "tr", config)
            self.assertEqual(result["status"], "prepared")
            install.assert_not_called()
            meta = json.loads((report.parent / "patch-meta.json").read_text("utf-8"))
            self.assertEqual(meta["unchanged_linguistic_entry_count"], 1)
            self.assertFalse(meta["human_reviewed"])

    def test_partial_maps_never_create_installable_stage(self):
        self.source.write_text('{"label":"Ayarlar"}', encoding="utf-8")
        with patch.object(self.service, "_extract", return_value=(self.doc, self.manifest)):
            with self.assertRaisesRegex(ValueError, "complete source key set"):
                self.service.build_translation("unused", "tr", {"provider": "offline-json", "json_path": str(self.source)})
        self.assertFalse((self.service.data / "stages/tr/patch-meta.json").exists())


if __name__ == "__main__":
    unittest.main()
