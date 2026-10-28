"""Synthetic source archives only; no real game, network or repak process."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from aion2_global_translator import compatibility as c, codec


class SourceCompatibility(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / "build/test-fixtures" / ("compatibility-" + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.game = self.root / "game"
        self.startup = self.game / "Aion2/Content/Paks/pakchunk0-Windows.pak"
        self.startup.parent.mkdir(parents=True)
        self.startup.write_bytes(b"synthetic original startup archive")
        self.source = self.game / "locale.pak"
        self.source.write_bytes(b"synthetic original locale archive")
        for ext in (".sig", ".ucas", ".utoc"):
            self.source.with_suffix(ext).write_bytes(("original companion " + ext).encode())
        self.repak = self.root / "repak.exe"
        self.repak.write_bytes(b"mocked, never executed")
        self.data = self.root / "private"
        self.key = bytes(range(32))
        record = struct.pack("<Q", codec.locale_seed("en-US")) + self.key + bytes(8)
        self.manifest = b"manifest" + codec._aes(record, codec.blake3(codec._MANIFEST_HASH_KEY).digest(), True)
        self.dat = self.document()
        self.calls = []
        self.extra = False
        self.mutate = False
        self.runner = patch.object(c.subprocess, "run", side_effect=self.unpack).start()
        self.addCleanup(patch.stopall)

    def document(self, namespace="AION2", entries=None):
        entries = entries if entries is not None else [("KEY", "Hello {name}"), ("HP", "Restores 10 HP")]
        table = codec.L10NTable(codec.FString(namespace), [(codec.FString(k), codec.FString(v)) for k, v in entries])
        return codec.L10NDocument(table, "en-US", b"", key=self.key, prefix=b"p" * 32).encode()

    def unpack(self, command, **kwargs):
        self.calls.append(command)
        self.assertFalse(kwargs.get("shell", False))
        destination = Path(command[command.index("-o") + 1])
        self.assertTrue(destination.resolve().is_relative_to(self.data.resolve()))
        member = command[command.index("--include") + 1]
        target = destination / member
        target.parent.mkdir(parents=True)
        target.write_bytes(self.dat if member.endswith("L10NString.dat") else self.manifest)
        if self.extra:
            (destination / "unexpected.txt").write_text("must not be extracted")
        if self.mutate and member.endswith("key_manifest.dat"):
            self.source.write_bytes(b"external archive update during extraction")
        return SimpleNamespace(returncode=0, stderr="")

    def probe(self, build="99900001"):
        return c.probe_source(self.game, self.source, self.repak, self.data, build)

    def game_snapshot(self):
        return {str(p.relative_to(self.game)): p.read_bytes() for p in self.game.rglob("*") if p.is_file()}

    def test_fresh_unknown_build_uses_actual_archive_members_and_preserves_game(self):
        before = self.game_snapshot()
        result = self.probe()
        profile = result["profile"]
        digest = lambda b: hashlib.sha256(b).hexdigest()
        self.assertEqual(profile["build"], "99900001")
        self.assertEqual(profile["pak_sha256"], digest(self.source.read_bytes()))
        self.assertEqual(profile["startup_pak_sha256"], digest(self.startup.read_bytes()))
        self.assertEqual(profile["dat_sha256"], digest(self.dat))
        self.assertEqual(profile["manifest_sha256"], digest(self.manifest))
        self.assertEqual(profile["namespace"], "AION2")
        self.assertEqual(profile["entries"], 2)
        self.assertEqual(result["manifest"], self.manifest)
        self.assertEqual(result["doc"].table.as_dict()["KEY"], "Hello {name}")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0][-1], "AION2/Content/L10N/Text/en-US/L10NString.dat")
        self.assertEqual(self.game_snapshot(), before)

    def test_same_fingerprint_reuses_only_verified_complete_cache(self):
        self.probe()
        self.repak.unlink()  # A valid cache does not require executing a tool.
        self.assertEqual(self.probe()["doc"].table.as_dict()["HP"], "Restores 10 HP")
        self.assertEqual(len(self.calls), 2)

    def test_corrupt_cached_dat_or_manifest_is_extracted_again(self):
        self.probe()
        for name in ("L10NString.dat", "key_manifest.dat"):
            path = next(self.data.rglob(name))
            path.write_bytes(b"stale or damaged cache")
            result = self.probe()
            self.assertEqual(result["profile"]["dat_sha256"], hashlib.sha256(self.dat).hexdigest())
        self.assertEqual(len(self.calls), 6)

    def test_cache_metadata_cannot_claim_a_different_archive_fingerprint(self):
        self.probe()
        path = next(self.data.rglob("fingerprint.json"))
        value = json.loads(path.read_text())
        value["archives"]["pak_sha256"] = "0" * 64
        path.write_text(json.dumps(value))
        self.probe()
        self.assertEqual(len(self.calls), 4)

    def test_same_build_updated_archive_never_reuses_stale_source_text(self):
        old = self.probe()
        self.source.write_bytes(b"updated locale archive under the same Steam build")
        self.dat = self.document(entries=[("KEY", "Different English meaning")])
        new = self.probe()
        self.assertNotEqual(old["profile"]["pak_sha256"], new["profile"]["pak_sha256"])
        self.assertEqual(new["doc"].table.as_dict(), {"KEY": "Different English meaning"})
        self.assertEqual(len(self.calls), 4)

    def test_startup_archive_or_build_change_has_separate_cache_namespace(self):
        self.probe()
        self.startup.write_bytes(b"updated startup archive")
        self.probe()
        self.probe("99900002")
        self.assertEqual(len(self.calls), 6)

    def test_marker_is_not_a_source_archive(self):
        self.source.write_bytes(b"AION2_LOOSE")
        before = self.game_snapshot()
        with self.assertRaisesRegex(ValueError, "marker"):
            self.probe()
        self.assertFalse(self.calls)
        self.assertEqual(self.game_snapshot(), before)

    def test_malformed_duplicate_empty_or_wrong_namespace_source_is_rejected(self):
        before = self.game_snapshot()
        candidates = [b"not a DAT", self.document(namespace="UNRELATED"),
                      self.document(entries=[]), self.document(entries=[("DUP", "a"), ("DUP", "b")])]
        for value in candidates:
            self.dat = value
            with self.subTest(dat=value[:8]), self.assertRaisesRegex(ValueError, "codec compatibility"):
                self.probe()
        self.assertEqual(self.game_snapshot(), before)
        self.assertFalse(list(self.data.rglob("fingerprint.json")))
        self.assertFalse(list(self.data.rglob(".probe-*")))

    def test_concurrent_archive_update_aborts_without_overwriting_external_change(self):
        self.mutate = True
        with self.assertRaisesRegex(ValueError, "changed during"):
            self.probe()
        self.assertEqual(self.source.read_bytes(), b"external archive update during extraction")
        self.assertFalse(list(self.data.rglob("fingerprint.json")))

    def test_unexpected_extracted_file_is_rejected_and_private_scratch_removed(self):
        self.extra = True
        before = self.game_snapshot()
        with self.assertRaisesRegex(ValueError, "exactly the requested"):
            self.probe()
        self.assertEqual(self.game_snapshot(), before)
        self.assertFalse(list(self.data.rglob(".probe-*")))

    def test_repak_failure_never_publishes_cache_or_changes_game(self):
        before = self.game_snapshot()
        self.runner.side_effect = None
        self.runner.return_value = SimpleNamespace(returncode=7, stderr="synthetic extraction failure")
        with self.assertRaisesRegex(RuntimeError, "source extraction failed"):
            self.probe()
        self.assertEqual(self.game_snapshot(), before)
        self.assertFalse(list(self.data.rglob("fingerprint.json")))

    def test_missing_companion_is_reported_without_borrowing_old_side_files(self):
        self.source.with_suffix(".ucas").unlink()
        self.source.with_suffix(".ucas.codex-original").write_bytes(b"unverified old companion")
        result = self.probe()
        self.assertEqual(set(result["profile"]["companions"]), {".sig", ".utoc"})

    def test_cache_inside_game_or_non_numeric_build_is_rejected_before_writes(self):
        before = self.game_snapshot()
        with self.assertRaisesRegex(ValueError, "outside the game"):
            c.probe_source(self.game, self.source, self.repak, self.game / "cache", "99900001")
        with self.assertRaisesRegex(ValueError, "build identifier"):
            self.probe("../../game")
        self.assertEqual(self.game_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
