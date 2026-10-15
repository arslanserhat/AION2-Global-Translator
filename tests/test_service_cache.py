"""Protection-revision cache behavior with synthetic text and a mocked provider."""
import json
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import unittest
from unittest.mock import patch
import uuid

from aion2_global_translator.codec import FString, L10NDocument, L10NTable, locale_seed
from aion2_global_translator.protection import PROTECTION_PROFILE
from aion2_global_translator.service import TranslatorService


class ProtectedProviderCache(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / "build/test-fixtures" / ("provider-cache-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.service = TranslatorService(data_dir=self.root / "private")
        self.service.data.mkdir()
        self.source = "Restores 10 HP and 5 MP."
        table = L10NTable(FString("AION2"), [(FString("SkillString_TEST_desc_summary"), FString(self.source))])
        self.doc = L10NDocument(table, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)
        self.manifest = {locale_seed("en-US"): b"k" * 32}
        self.database = self.service.data / "provider-cache.sqlite"
        self.url = "https://provider.example.invalid"
        self.config = dict(provider="libretranslate", url=self.url)
        extract = patch.object(self.service, "_extract", return_value=(self.doc, self.manifest))
        extract.start()
        self.addCleanup(extract.stop)
        provider = patch("aion2_global_translator.providers.LibreTranslateProvider")
        self.provider = provider.start().return_value
        self.addCleanup(provider.stop)
        self.provider.languages.return_value = [{"code": "en", "targets": ["tr"]}, {"code": "tr"}]
        self.provider.translate_batch.side_effect = lambda texts: [texts[0].replace("Restores", "Yeniler").replace("and", "ve")]

    def seed(self, translated, *, legacy=False, profile=PROTECTION_PROFILE):
        with closing(sqlite3.connect(self.database)) as db:
            if legacy:
                db.execute("CREATE TABLE cache (server TEXT, lang TEXT, source TEXT, translated TEXT, PRIMARY KEY(server,lang,source))")
                db.execute("INSERT INTO cache VALUES (?,?,?,?)", (self.url, "tr", self.source, translated))
            else:
                db.execute("CREATE TABLE IF NOT EXISTS cache_v2 (profile TEXT, server TEXT, lang TEXT, source TEXT, translated TEXT, PRIMARY KEY(profile,server,lang,source))")
                db.execute("INSERT INTO cache_v2 VALUES (?,?,?,?,?)", (profile, self.url, "tr", self.source, translated))
            db.commit()

    def cached(self, *, legacy=False):
        with closing(sqlite3.connect(self.database)) as db:
            if legacy:
                return db.execute("SELECT translated FROM cache").fetchone()[0]
            return db.execute("SELECT translated FROM cache_v2 WHERE profile=?", (PROTECTION_PROFILE,)).fetchone()[0]

    def test_legacy_cache_is_preserved_but_never_reused(self):
        wrong = "10 beygir gücü ve 5 milletvekili yeniler."
        self.seed(wrong, legacy=True)
        result = self.service.build_translation("synthetic", "tr", self.config)
        self.provider.translate_batch.assert_called_once()
        self.assertEqual(self.cached(legacy=True), wrong)
        self.assertEqual(self.cached(), "Yeniler 10 HP ve 5 MP.")
        meta = json.loads((Path(result["stage"]) / "patch-meta.json").read_text("utf-8"))
        self.assertEqual(meta["protection_profile"], PROTECTION_PROFILE)

    def test_invalid_current_cache_is_retranslated_before_replacing_its_row(self):
        self.seed("10 HP ve 5 milletvekili yeniler.")
        self.service.build_translation("synthetic", "tr", self.config)
        self.provider.translate_batch.assert_called_once()
        self.assertEqual(self.cached(), "Yeniler 10 HP ve 5 MP.")
        sent_html = self.provider.translate_batch.call_args.args[0][0]
        self.assertNotIn("HP", sent_html)
        self.assertNotIn("MP", sent_html)

    def test_failed_retranslation_keeps_the_previous_cache_row(self):
        wrong = "10 HP ve 5 milletvekili yeniler."
        self.seed(wrong)
        self.provider.translate_batch.side_effect = None
        self.provider.translate_batch.return_value = ["10 HP yeniler."]
        with self.assertRaises(ValueError):
            self.service.build_translation("synthetic", "tr", self.config)
        self.assertEqual(self.cached(), wrong)
        self.assertFalse((self.service.data / "stages/tr/patch-meta.json").exists())

    def test_valid_current_profile_cache_needs_no_translation_request(self):
        valid = "10 HP ve 5 MP yeniler."
        self.seed(valid)
        self.service.build_translation("synthetic", "tr", self.config)
        self.provider.translate_batch.assert_not_called()
        self.assertEqual(self.cached(), valid)

    def test_another_profile_namespace_cannot_supply_a_translation(self):
        self.seed("10 HP ve 5 milletvekili yeniler.", profile="older-format-profile")
        self.service.build_translation("synthetic", "tr", self.config)
        self.provider.translate_batch.assert_called_once()
        self.assertEqual(self.cached(), "Yeniler 10 HP ve 5 MP.")


if __name__ == "__main__":
    unittest.main()
