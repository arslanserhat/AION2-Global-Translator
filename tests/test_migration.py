"""Incremental updates, actual DAT validation and private-stage transactions."""
import json
from pathlib import Path
import shutil
import struct
import unittest
import uuid
from unittest.mock import patch
from aion2_global_translator import codec, migration, service as s, update_recovery as u
import test_service as transactions
import test_build_upgrade as upgrades


class IncrementalMigration(unittest.TestCase):
    def setUp(self):
        self.root = Path.cwd() / 'build/test-fixtures' / ('migration-' + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.service = s.TranslatorService(data_dir=self.root / 'private')
        self.key = b'k' * 32
        record = struct.pack('<Q', codec.locale_seed('en-US')) + self.key + bytes(8)
        self.manifest = b'manifest' + codec._aes(record, codec.blake3(codec._MANIFEST_HASH_KEY).digest(), True)
        self.old = {'stable': 'Welcome', 'changed': 'Damage 10', 'removed': 'Remove'}
        self.values = {'stable': 'Hoş geldin', 'changed': 'Hasar 10', 'removed': 'Kaldır'}
        self.current = {'stable': 'Welcome', 'changed': 'Damage 20', 'moved': 'Remove', 'new': 'Talk', 'literal': '{0}/{1}'}
        self.corrections = {'changed': 'Hasar 20', 'moved': 'Kaldır', 'new': 'Konuş'}
        self.stage = self.service.data / 'stages/tr'
        self.stage.mkdir(parents=True)
        source_bytes = json.dumps(self.old).encode()
        data = self.doc(self.old).encode(self.doc(self.old).table.translated(self.values))
        for name, value in [('entries.source.json', source_bytes), ('source-key-manifest.dat', self.manifest),
                            ('L10NString.dat', data), ('entries.translated.json', json.dumps(self.values).encode())]:
            (self.stage / name).write_bytes(value)
        self.meta = dict(steam_build='101', target_language='tr', source_entry_count=len(self.old),
            quality_gate_passed=True, remaining_untranslated_candidate_entries=0,
            source_map_sha256=s.sha(source_bytes), manifest_sha256=s.sha(self.manifest), dat_sha256=s.sha(data))
        s.json_write(self.stage / 'patch-meta.json', self.meta)
        patcher = patch.object(self.service, '_extract', return_value=(self.doc(self.current), self.manifest))
        patcher.start(); self.addCleanup(patcher.stop)
        self.file = self.root / 'corrections.json'
        s.json_write(self.file, self.corrections)

    def doc(self, values, namespace='AION2'):
        table = codec.L10NTable(codec.FString(namespace), [(codec.FString(k), codec.FString(v)) for k, v in values.items()])
        return codec.L10NDocument(table, 'en-US', b'', key=self.key, prefix=b'p' * 32)

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.stage.iterdir() if p.is_file()}

    def test_same_key_and_exact_source_only_no_numeric_or_cross_key_guess(self):
        plan = migration.plan_migration(self.old, self.values, self.current)
        self.assertEqual(plan['carried'], {'stable': 'Hoş geldin'})
        self.assertEqual(set(plan['pending']), {'changed', 'moved', 'new'})
        self.assertEqual(plan['literals'], {'literal': '{0}/{1}'})
        self.assertEqual(plan['removed'], ['removed'])

    def test_pending_update_preserves_old_pack_and_lists_only_delta(self):
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, '3 new/changed'):
            self.service.migrate_translation('synthetic', 'tr')
        self.assertEqual(self.snapshot(), before)
        pending = json.loads((self.service.data / 'updates' / s.BUILD / 'tr' / self.service.original_dat_sha / 'pending.json').read_text('utf8'))
        self.assertEqual(set(pending), set(self.corrections))

    def test_complete_delta_rebuilds_native_map_and_retains_previous_stage(self):
        before = self.snapshot()
        result = self.service.migrate_translation('synthetic', 'tr', self.file)
        self.assertEqual((result['carried'], result['translated'], result['removed']), (1, 3, 1))
        expected = dict(stable='Hoş geldin', changed='Hasar 20', moved='Kaldır', new='Konuş', literal='{0}/{1}')
        actual = codec.L10NDocument.decode((self.stage / 'L10NString.dat').read_bytes(), 'en-US', self.manifest)
        self.assertEqual(actual.table.as_dict(), expected)
        meta = json.loads((self.stage / 'patch-meta.json').read_text('utf8'))
        archive = Path(meta['prior_stage'])
        self.assertEqual({p.name: p.read_bytes() for p in archive.iterdir()}, before)
        self.assertFalse(meta['in_game_verified'])

    def test_changed_source_numbers_still_reject_wrong_translation(self):
        before = self.snapshot()
        s.json_write(self.file, dict(self.corrections, changed='Hasar 10'))
        with self.assertRaises(ValueError):
            self.service.migrate_translation('synthetic', 'tr', self.file)
        self.assertEqual(self.snapshot(), before)

    def test_automatic_corrections_from_another_source_fingerprint_are_not_reused(self):
        s.json_write(self.service.data / 'updates' / s.BUILD / 'tr' / ('0' * 64) / 'corrections.json', self.corrections)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, '3 new/changed'):
            self.service.migrate_translation('synthetic', 'tr')
        self.assertEqual(self.snapshot(), before)

    def test_tampered_editable_reference_is_rejected(self):
        s.json_write(self.stage / 'entries.translated.json', dict(self.values, stable='Different'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'disagree'):
            self.service.migrate_translation('synthetic', 'tr', self.file)
        self.assertEqual(self.snapshot(), before)

    def test_external_edit_during_migration_is_preserved(self):
        from aion2_global_translator import multilingual
        real = multilingual.apply_target_context_terms
        def edit(*args):
            s.json_write(self.stage / 'entries.translated.json', dict(self.values, stable='External edit'))
            return real(*args)
        with patch.object(multilingual, 'apply_target_context_terms', side_effect=edit):
            with self.assertRaisesRegex(ValueError, 'changed during migration'):
                self.service.migrate_translation('synthetic', 'tr', self.file)
        self.assertEqual(json.loads((self.stage / 'entries.translated.json').read_text('utf8'))['stable'], 'External edit')
        self.assertEqual((self.stage / 'L10NString.dat').read_bytes(), self.doc(self.old).encode(self.doc(self.old).table.translated(self.values)))

    def test_failed_stage_publish_restores_previous_stage(self):
        before = self.snapshot()
        rename = Path.rename
        def fail(path, target):
            if path.name.startswith('.tr-update-'):
                raise PermissionError('synthetic stage swap failure')
            return rename(path, target)
        with patch.object(Path, 'rename', fail), self.assertRaises(PermissionError):
            self.service.migrate_translation('synthetic', 'tr', self.file)
        self.assertEqual(self.snapshot(), before)

    def test_translation_server_receives_only_changed_source_and_no_saved_key(self):
        from aion2_global_translator import providers
        s.json_write(self.service.data / 'settings/tr-provider.json', {'provider': 'libretranslate', 'url': 'http://synthetic.invalid'})
        answers = {'Damage 20': 'Hasar 20', 'Remove': 'Kaldır', 'Talk': 'Konuş'}
        calls = []
        class Provider:
            def __init__(self, *args, **kwargs): pass
            def languages(self): return [{'code': 'en', 'targets': ['tr']}, {'code': 'tr'}]
            def translate_batch(self, batch):
                from aion2_global_translator.protection import prepare
                calls.extend(batch)
                for text, value in answers.items():
                    if batch == [prepare(text).html]:
                        # Reuse protected markup around literals, as real providers do.
                        return [prepare(value).html]
                raise AssertionError(batch)
        with patch.object(providers, 'LibreTranslateProvider', Provider):
            self.service.migrate_translation('synthetic', 'tr')
        self.assertEqual(len(calls), 3)
        self.assertFalse(any('Welcome' in text for text in calls))


class ActualStageValidation(unittest.TestCase):
    def setUp(self):
        self.fixture = transactions.Transactions('test_install_restore_exact_bytes')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)

    def replace(self, data):
        (self.fixture.stage / 'L10NString.dat').write_bytes(data)
        self.fixture.meta['dat_sha256'] = s.sha(data)
        self.fixture.write_meta()

    def test_hash_consistent_non_dat_is_not_an_installable_pack(self):
        self.replace(b'not a DAT but has matching hash')
        with self.assertRaises(ValueError): self.fixture.service.install_stage(self.fixture.game, self.fixture.stage)
        self.fixture.original_restored()

    def test_wrong_namespace_key_set_and_format_are_rejected_before_writes(self):
        doc = self.fixture.doc
        cases = [('OTHER', 'label', 'Ayarlar'), ('AION2', 'wrong', 'Ayarlar'), ('AION2', 'label', '{new} Ayarlar')]
        for namespace, key, value in cases:
            table = codec.L10NTable(codec.FString(namespace), [(codec.FString(key), codec.FString(value))])
            data = codec.L10NDocument(table, 'en-US', b'', key=b'k' * 32, prefix=b'p' * 32).encode()
            self.replace(data)
            with self.subTest(case=(namespace, key)), self.assertRaises(ValueError):
                self.fixture.service.install_stage(self.fixture.game, self.fixture.stage)
            self.fixture.original_restored()

    def test_quality_boolean_is_not_a_truthy_string(self):
        self.fixture.meta['quality_gate_passed'] = 'false'; self.fixture.write_meta()
        with self.assertRaises(ValueError): self.fixture.service.install_stage(self.fixture.game, self.fixture.stage)
        self.fixture.original_restored()

    def test_unknown_opaque_prefix_is_not_installed(self):
        f = self.fixture
        doc = f.doc
        alternate = codec.L10NDocument(doc.table, 'en-US', b'', key=b'k' * 32, prefix=b'x' * 32)
        data = alternate.encode(alternate.table.translated({'label': 'Ayarlar'}))
        self.replace(data)
        with self.assertRaises(ValueError): f.service.install_stage(f.game, f.stage)
        f.original_restored()

    def test_unknown_nonempty_container_is_never_disabled(self):
        f = self.fixture
        container = f.pakdir / (s.PAK + '.utoc')
        container.write_bytes(b'new nonempty content container')
        before = {p: p.read_bytes() for p in f.pakdir.iterdir()}
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            f.service.install_stage(f.game, f.stage)
        self.assertEqual({p: p.read_bytes() for p in f.pakdir.iterdir()}, before)


class GeneralUpdateRecovery(unittest.TestCase):
    def setUp(self):
        self.fixture = upgrades.BuildUpgrade('test_recovery_preserves_updated_pak_and_sig_and_archives_old_loose')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.profile = dict(build=s.BUILD, pak_sha256=s.sha(self.fixture.current['.pak']),
                            companions={ext: s.sha(value) for ext, value in self.fixture.current.items() if ext != '.pak'})
        p = patch.object(u, 'EMPTY_COMPANIONS', {ext: s.sha(self.fixture.current[ext]) for ext in ('.ucas', '.utoc')})
        p.start(); self.addCleanup(p.stop)

    def recover(self, closed=lambda: None):
        f = self.fixture
        return u.recover_update(f.pakdir, f.loose, f.backup, closed, self.profile)

    def test_generic_recovery_preserves_updated_originals(self):
        self.assertTrue(self.recover())
        f = self.fixture
        self.assertFalse(f.loose.exists())
        for ext, data in f.current.items(): self.assertEqual((f.pakdir / (s.PAK + ext)).read_bytes(), data)

    def test_repeated_build_only_updates_accept_byte_identical_owned_generations(self):
        f = self.fixture
        second = f.old.parent / '26000000'
        shutil.copytree(f.old, second)
        for name in ('backup.json', 'state.json'):
            value = json.loads((second / name).read_text())
            value['steam_build'] = second.name
            (second / name).write_text(json.dumps(value))
        found = u.find_previous_install(f.pakdir, f.loose, f.backup)
        self.assertEqual(found[0], second)
        self.assertTrue(self.recover())

    def test_modified_loose_and_companions_have_no_ownership(self):
        f = self.fixture; f.loose.write_bytes(b'external')
        with self.assertRaisesRegex(ValueError, 'Unverified'): self.recover()
        self.assertEqual(f.loose.read_bytes(), b'external')

    def test_cleanup_failure_rolls_back_all_files(self):
        f = self.fixture
        before = {p: p.read_bytes() for p in [f.loose, *f.pakdir.iterdir()] if p.is_file()}
        unlink = Path.unlink
        def fail(path, *args, **kwargs):
            if path.name.endswith('.sig.codex-original'): raise PermissionError('locked')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail), self.assertRaises(PermissionError): self.recover()
        self.assertEqual({p: p.read_bytes() for p in [f.loose, *f.pakdir.iterdir()] if p.is_file()}, before)

    def test_future_build_with_owned_unchanged_marker_reaches_update_pending(self):
        f = self.fixture
        (f.pakdir / (s.PAK + '.pak')).write_bytes(s.MARKER)
        f.manifest.write_text('"buildid" "99900001"')
        self.profile.update(build='99900001', pak_sha256=s.sha(f.previous['.pak']), entries=2, dat_sha256='verified-by-probe')
        with patch('aion2_global_translator.compatibility.probe_source', return_value={'profile': self.profile, 'doc': None, 'manifest': b''}) as probe:
            result = f.service.inspect(f.game)
        self.assertEqual(result['status'], 'update_pending')
        self.assertEqual(Path(probe.call_args.args[1]), f.old / (s.PAK + '.pak'))
