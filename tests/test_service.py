"""Synthetic install transactions. Never reads a real game installation."""
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import uuid
from unittest.mock import patch
from aion2_global_translator import service as s


class Transactions(unittest.TestCase):
    def setUp(self):
        root = Path.cwd() / "build/test-fixtures" / str(uuid.uuid4())
        root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, root)
        self.game = root / "steamapps/common/AION2"
        self.game.mkdir(parents=True)
        exe = self.game / "Aion2/Binaries/Win64/AION2.exe"
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"synthetic executable")
        (root / "steamapps/appmanifest_3393110.acf").write_text('"buildid" "25926599"')
        self.pakdir = self.game / "Aion2/Content/Paks/L10N/Text/en-US"
        self.pakdir.mkdir(parents=True)
        self.original = {}
        for ext in s.EXTENSIONS:
            data = ("synthetic original " + ext).encode()
            (self.pakdir / (s.PAK + ext)).write_bytes(data)
            self.original[s.PAK + ext] = data
        self.addCleanup(patch.stopall)
        patch.object(s, "ORIGINAL_SHA", s.sha(self.original[s.PAK + ".pak"])).start()
        patch.object(s, "game_running", return_value=False).start()
        self.service = s.TranslatorService(data_dir=root / "data")
        self.stage = root / "stage"
        self.stage.mkdir()
        (self.stage / "L10NString.dat").write_bytes(b"synthetic translated DAT")
        self.meta = dict(steam_build=s.BUILD, original_pak_sha256=s.ORIGINAL_SHA,
                         quality_gate_passed=True, remaining_untranslated_candidate_entries=0,
                         source_entry_count=153042, dat_sha256=s.sha(b"synthetic translated DAT"), target_language="tr")
        self.write_meta()

    def write_meta(self):
        (self.stage / "patch-meta.json").write_text(json.dumps(self.meta))

    def original_restored(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.pakdir.iterdir()}, self.original)
        self.assertFalse((self.game / "Aion2/Content/L10N/Text/en-US/L10NString.dat").exists())

    def test_install_restore_exact_bytes(self):
        result = self.service.install_stage(self.game, self.stage)
        self.assertEqual(result["installed_language"], "tr")
        self.service.restore(self.game)
        self.original_restored()

    def test_corrupt_dat_or_incomplete_stage_is_rejected_before_mutation(self):
        for field, value in [("dat_sha256", "0" * 64), ("remaining_untranslated_candidate_entries", 1), ("steam_build", "wrong")]:
            old = self.meta[field]
            self.meta[field] = value
            self.write_meta()
            with self.assertRaises(ValueError):
                self.service.install_stage(self.game, self.stage)
            self.original_restored()
            self.meta[field] = old

    def test_running_game_refuses_install(self):
        with patch.object(s, "game_running", return_value=True):
            with self.assertRaises(RuntimeError):
                self.service.install_stage(self.game, self.stage)
        self.original_restored()

    def test_state_write_failure_restores_original_files(self):
        real = s.json_write
        def fail(path, data):
            if Path(path).name == "state.json":
                raise PermissionError("simulated locked state file")
            return real(path, data)
        with patch.object(s, "json_write", side_effect=fail):
            with self.assertRaises(PermissionError):
                self.service.install_stage(self.game, self.stage)
        self.original_restored()

    def test_restore_refuses_updated_game_and_preserves_installed_data(self):
        self.service.install_stage(self.game, self.stage)
        (self.game.parents[1] / "appmanifest_3393110.acf").write_text('"buildid" "99999999"')
        with self.assertRaises(ValueError):
            self.service.restore(self.game)
        self.assertEqual((self.pakdir / (s.PAK + ".pak")).read_bytes(), s.MARKER)

    def test_external_companion_changes_are_not_overwritten(self):
        self.service.install_stage(self.game, self.stage)
        changed = self.pakdir / (s.PAK + ".sig.codex-original")
        changed.write_bytes(b"external change")
        with self.assertRaises(ValueError):
            self.service.restore(self.game)
        self.assertEqual(changed.read_bytes(), b"external change")

    def test_install_concurrent_change_is_preserved_before_transaction(self):
        calls, expected = [], {}
        def closed():
            calls.append(True)
            if len(calls) == 2:
                (self.pakdir / (s.PAK + ".sig")).write_bytes(b"external edit during preparation")
                expected.update({str(p.relative_to(self.game)): p.read_bytes()
                                 for p in self.game.rglob("*") if p.is_file()})
        with patch.object(self.service, "_closed", side_effect=closed):
            with self.assertRaisesRegex(ValueError, "Game files changed"):
                self.service.install_stage(self.game, self.stage)
        self.assertEqual(len(calls), 2)
        self.assertEqual({str(p.relative_to(self.game)): p.read_bytes()
                          for p in self.game.rglob("*") if p.is_file()}, expected)

    def test_restore_concurrent_change_is_preserved_before_transaction(self):
        self.service.install_stage(self.game, self.stage)
        _, _, loose, backup = self.service.paths(self.game)
        state = (backup / "state.json").read_bytes()
        calls, expected = [], {}
        def closed():
            calls.append(True)
            if len(calls) == 2:
                loose.write_bytes(b"external edit during restore preparation")
                expected.update({str(p.relative_to(self.game)): p.read_bytes()
                                 for p in self.game.rglob("*") if p.is_file()})
        with patch.object(self.service, "_closed", side_effect=closed):
            with self.assertRaisesRegex(ValueError, "Game files changed"):
                self.service.restore(self.game)
        self.assertEqual(len(calls), 2)
        self.assertEqual({str(p.relative_to(self.game)): p.read_bytes()
                          for p in self.game.rglob("*") if p.is_file()}, expected)
        self.assertEqual((backup / "state.json").read_bytes(), state)

    def test_cached_source_checksum_is_verified_before_decode(self):
        from aion2_global_translator import codec
        extracted = self.service.data / "source" / s.BUILD
        dat = extracted / "locale/Aion2/Content/L10N/Text/en-US/L10NString.dat"
        manifest = extracted / "startup/Aion2/Content/StartUpData/Table/key_manifest.dat"
        for path, data in ((dat, b"cached file from an unverified source"), (manifest, b"cached manifest")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.service.repak = self.stage / "synthetic-repak.exe"
        self.service.repak.write_bytes(b"never executed")
        with patch.object(codec.L10NDocument, "decode") as decode:
            with self.assertRaisesRegex(ValueError, "English source DAT checksum mismatch"):
                self.service._extract(self.game)
        decode.assert_not_called()

    def test_json_rejects_duplicate_keys(self):
        path = self.stage / "duplicate.json"
        path.write_text('{"a":"one","a":"two"}')
        with self.assertRaises(ValueError):
            s.flat_json(path)


if __name__ == "__main__":
    unittest.main()
