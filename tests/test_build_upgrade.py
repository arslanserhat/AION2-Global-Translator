"""Current Steam build support and non-destructive pre-update recovery."""
from pathlib import Path
import json
import shutil
import unittest
import uuid
from unittest.mock import patch
from aion2_global_translator import service as s
from aion2_global_translator import update_recovery as u
from aion2_global_translator.gui import localized_service_error


class BuildUpgrade(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / "build/test-fixtures" / ("upgrade-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.game = self.root / "steamapps/common/AION2"
        exe = self.game / "Aion2/Binaries/Win64/AION2.exe"
        exe.parent.mkdir(parents=True); exe.write_bytes(b"fake")
        self.manifest = self.game.parents[1] / "appmanifest_3393110.acf"
        self.manifest.write_text('"buildid" "' + s.BUILD + '"')
        self.service = s.TranslatorService(data_dir=self.root / "private")
        _, self.pakdir, self.loose, self.backup = self.service.paths(self.game)
        self.pakdir.mkdir(parents=True); self.loose.parent.mkdir(parents=True)
        self.old = self.backup.parent / u.OLD_BUILD; self.old.mkdir(parents=True)
        self.current = {ext: ("new original " + ext).encode() for ext in s.EXTENSIONS}
        self.previous = {ext: ("old original " + ext).encode() for ext in s.EXTENSIONS}
        self.previous[".ucas"] = self.current[".ucas"]
        self.previous[".utoc"] = self.current[".utoc"]
        records = {}
        for ext, content in self.previous.items():
            (self.old / (s.PAK + ext)).write_bytes(content); records[s.PAK + ext] = s.sha(content)
            if ext != ".pak": (self.pakdir / (s.PAK + ext + ".codex-original")).write_bytes(content)
        for ext in (".pak", ".sig"): (self.pakdir / (s.PAK + ext)).write_bytes(self.current[ext])
        records["original-loose.dat"] = None
        self.loose.write_bytes(b"old owned translated table")
        (self.old / "backup.json").write_text(json.dumps({"steam_build": u.OLD_BUILD, "files": records}))
        (self.old / "state.json").write_text(json.dumps({"steam_build": u.OLD_BUILD, "dat_sha256": s.sha(self.loose.read_bytes())}))
        self.addCleanup(patch.stopall)
        patch.object(u, "OLD_PAK_SHA", records[s.PAK + ".pak"]).start()
        patch.object(u, "CURRENT_FILES", {ext: s.sha(data) for ext, data in self.current.items()}).start()

    def recover(self, closed=lambda: None):
        return u.recover_known_update(self.pakdir, self.loose, self.backup, closed)

    def test_current_build_and_entry_count_are_explicit(self):
        self.assertEqual(s.BUILD, "26262663")
        self.assertEqual(s.DISPLAY_ENTRY_COUNT, 153297)

    def test_unknown_build_reports_actual_and_leaves_files_untouched(self):
        self.manifest.write_text('"buildid" "99999999"')
        before = self.loose.read_bytes()
        with patch("aion2_global_translator.compatibility.probe_source", side_effect=ValueError("Unsupported source format")):
            with self.assertRaisesRegex(ValueError, "Unsupported source format"):
                self.service.paths(self.game)
        self.assertEqual(self.loose.read_bytes(), before)

    def test_recovery_preserves_updated_pak_and_sig_and_archives_old_loose(self):
        self.assertTrue(self.recover())
        self.assertFalse(self.loose.exists())
        for ext, data in self.current.items(): self.assertEqual((self.pakdir / (s.PAK + ext)).read_bytes(), data)
        self.assertFalse(any(self.pakdir.glob("*.codex-original")))
        copies = list(self.backup.parent.glob("recovered-*/loose-before-update.dat"))
        self.assertEqual(len(copies), 1); self.assertEqual(copies[0].read_bytes(), b"old owned translated table")
        self.assertTrue((self.old / "state.json").exists())

    def test_unowned_loose_is_never_removed(self):
        self.loose.write_bytes(b"external edit")
        with self.assertRaisesRegex(ValueError, "translation was changed"): self.recover()
        self.assertEqual(self.loose.read_bytes(), b"external edit")

    def test_unknown_current_original_is_never_overwritten(self):
        path = self.pakdir / (s.PAK + ".pak"); path.write_bytes(b"unexpected new original")
        with self.assertRaisesRegex(ValueError, "verified updated build"): self.recover()
        self.assertEqual(path.read_bytes(), b"unexpected new original")
        self.assertTrue(self.loose.exists())

    def test_changed_pre_update_side_file_blocks_recovery(self):
        path = self.pakdir / (s.PAK + ".sig.codex-original"); path.write_bytes(b"external")
        with self.assertRaisesRegex(ValueError, "companion was changed"): self.recover()
        self.assertEqual(path.read_bytes(), b"external")

    def test_running_game_guard_is_called_before_first_game_mutation(self):
        def closed(): raise RuntimeError("game is running")
        with self.assertRaises(RuntimeError): self.recover(closed)
        self.assertTrue(self.loose.exists()); self.assertFalse((self.pakdir / (s.PAK + ".ucas")).exists())

    def test_concurrent_edit_during_prepare_is_preserved(self):
        def closed(): self.loose.write_bytes(b"external concurrent edit")
        with self.assertRaisesRegex(ValueError, "changed during"): self.recover(closed)
        self.assertEqual(self.loose.read_bytes(), b"external concurrent edit")

    def test_localized_build_errors_explain_rebuild(self):
        message = "Unsupported Steam build. Found 123; expected 26077854. More text"
        self.assertIn("123", localized_service_error(message, "tr"))
        self.assertIn("26077854", localized_service_error(message, "tr"))
        self.assertEqual(localized_service_error(message, "en"), message)
        self.assertIn("yeniden oluşturmak", localized_service_error("Language pack build mismatch. Found 25926599; expected 26077854.", "tr"))
        self.assertIn("Admin.exe", localized_service_error("[WinError 5] Access denied", "tr"))

    def test_failure_after_loose_removal_restores_every_snapshot(self):
        before = {p: p.read_bytes() for p in self.pakdir.iterdir() if p.is_file()}
        loose_before = self.loose.read_bytes()
        original_unlink = Path.unlink
        def fail(path, *args, **kwargs):
            if path.name == s.PAK + ".sig.codex-original":
                raise PermissionError("synthetic locked companion")
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", fail), self.assertRaises(PermissionError):
            self.recover()
        self.assertEqual(self.loose.read_bytes(), loose_before)
        self.assertEqual({p: p.read_bytes() for p in self.pakdir.iterdir() if p.is_file()}, before)
