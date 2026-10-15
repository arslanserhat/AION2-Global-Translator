"""Language selection must change target grammar, not source context or files."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_service as fixtures
import test_build as build_fixtures
from aion2_global_translator.codec import FString, L10NTable, L10NDocument
from aion2_global_translator.multilingual import apply_target_context_terms, normalize_language
from aion2_global_translator import service as s


class TargetContext(unittest.TestCase):
    def test_all_ten_short_label_profiles_pass_shared_literal_checks(self):
        from aion2_global_translator.context_labels import CONTEXT_LABELS
        from aion2_global_translator.protection import validate
        for code, profile in CONTEXT_LABELS.items():
            source = {f'String_UI_DEMO_BUTTON_{index}_body': english for index, english in enumerate(profile['actions'])}
            for key, english in (
                ('String_STR_ITEM_EQUIP_WP_STAFF_DEMO_body', 'Staff'),
                ('SkillString_DEMO_skill_name', 'Snipe'),
                ('String_StatName_CastingTime_body', 'Cast duration'),
                ('String_UI_ITEM_BINDSTATE_body', 'Bound'),
            ):
                source[key] = english
            output, report = apply_target_context_terms(source, dict.fromkeys(source, '???'), code)
            self.assertEqual(report['changed_entries'], 39)
            for key, english in source.items():
                validate(english, output[key])
                self.assertEqual(output[key], profile['actions'].get(english, profile['terms'].get(english)))

    def test_french_build_export_edit_rebuild_preserves_accents_and_resource(self):
        fixture = build_fixtures.BuildWorkflow('test_partial_maps_never_create_installable_stage')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        talk, desc, title = 'String_UI_HUD_KEYGUIDE_DESC_TALK_body', 'SkillString_DEMO_desc', 'String_UI_MAGIC_TITLE_body'
        table = L10NTable(FString('SYNTHETIC'), [(FString(talk), FString('Talk')),
                             (FString(desc), FString('Restores 10 HP')), (FString(title), FString('Magic'))])
        document = L10NDocument(table, 'en-US', b'', key=b'k' * 32, prefix=b'p' * 32)
        fixture.source.write_text(json.dumps({talk: 'Discuter', desc: 'Rend 10 HP', title: 'Bénédictions'}), encoding='utf8')
        config = dict(provider='offline-json', json_path=str(fixture.source))
        with patch.object(fixture.service, '_extract', return_value=(document, fixture.manifest)), patch.object(fixture.service, 'install_stage') as install:
            result = fixture.service.build_translation('unused', 'FR', config)
            stage = Path(result['stage'])
            output = L10NDocument.decode((stage / 'L10NString.dat').read_bytes(), 'en-US', fixture.manifest).table.as_dict()
            self.assertEqual(output, {talk: 'Parler', desc: 'Rend 10 HP', title: 'Bénédictions'})
            editable = fixture.root / 'french-edits.json'
            fixture.service.export_translation('fr', editable)
            values = json.loads(editable.read_text('utf8')); values[desc] = 'Restaure 10 HP'
            editable.write_text(json.dumps(values), encoding='utf8')
            fixture.service.build_translation('unused', 'fr', dict(config, json_path=str(editable)))
            final = L10NDocument.decode((stage / 'L10NString.dat').read_bytes(), 'en-US', fixture.manifest).table.as_dict()
            self.assertEqual(final[desc], 'Restaure 10 HP')
            install.assert_not_called()

    def test_talk_uses_each_targets_ui_grammar_and_leaves_nouns_alone(self):
        source = {'String_UI_HUD_KEYGUIDE_DESC_TALK_body': 'Talk', 'String_UI_CHATMENU_TITLE_body': 'Talk'}
        cases = {'tr': 'Konuş', 'de': 'Sprechen', 'fr': 'Parler', 'es': 'Hablar', 'ja': '話しかける'}
        # German/French/Spanish use their conventional infinitive UI label;
        # Turkish uses an imperative. The engine never copies Turkish grammar.
        for code, label in cases.items():
            output, report = apply_target_context_terms(source, dict.fromkeys(source, 'WRONG'), code)
            self.assertEqual(output['String_UI_HUD_KEYGUIDE_DESC_TALK_body'], label)
            self.assertEqual(output['String_UI_CHATMENU_TITLE_body'], 'WRONG')
            self.assertEqual(report['changed_entries'], 1)

    def test_simplified_profile_does_not_overwrite_traditional_chinese(self):
        source = {'String_UI_HUD_KEYGUIDE_DESC_TALK_body': 'Talk'}
        output, report = apply_target_context_terms(source, dict.fromkeys(source, '交談'), 'zh-TW')
        self.assertEqual(output, dict.fromkeys(source, '交談'))
        self.assertIsNone(report['lexicon_language'])

    def test_unlisted_language_and_protected_prose_are_preserved(self):
        source = {'SkillString_DEMO_desc': '<b>{amount}</> 25 HP Talk'}
        target = {'SkillString_DEMO_desc': '<b>{amount}</> 25 HP Hallo'}
        output, report = apply_target_context_terms(source, target, 'nl')
        self.assertEqual(output, target)
        self.assertEqual(report['changed_entries'], 0)
        with self.assertRaises(ValueError):
            normalize_language('../../tr')
        self.assertEqual(normalize_language('PT_br'), 'pt-BR')

    def test_staff_weapon_does_not_replace_staff_employees(self):
        source = {'String_STR_ITEM_EQUIP_WP_STAFF_DEMO_body': 'Staff', 'NpcTalk_tavern': 'Staff'}
        output, _ = apply_target_context_terms(source, dict.fromkeys(source, 'Personal'), 'de')
        self.assertEqual(output['String_STR_ITEM_EQUIP_WP_STAFF_DEMO_body'], 'Stab')
        self.assertEqual(output['NpcTalk_tavern'], 'Personal')


class SelectedPack(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.Transactions('test_install_restore_exact_bytes')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service
        self.game = self.fixture.game

    def ready(self, code, content):
        stage = self.service.data / 'stages' / code
        stage.mkdir(parents=True, exist_ok=True)
        (stage / 'L10NString.dat').write_bytes(content)
        (stage / 'patch-meta.json').write_text(json.dumps(dict(self.fixture.meta, target_language=code, dat_sha256=s.sha(content))))
        return stage

    def test_switch_to_selected_language_keeps_original_restore_exact(self):
        self.ready('tr', b'turkish'); self.ready('fr', b'french')
        self.service.apply_language(self.game, 'tr')
        self.assertEqual(self.service.apply_language(self.game, 'fr')['installed_language'], 'fr')
        self.assertEqual(self.service.apply_language(self.game, 'en')['status'], 'original')
        self.fixture.original_restored()
        self.assertEqual(self.service.apply_language(self.game, 'en')['status'], 'original')

    def test_mislabeled_pack_refused_before_current_language_changes(self):
        self.ready('tr', b'turkish'); stage = self.ready('fr', b'french')
        self.service.apply_language(self.game, 'tr')
        meta = json.loads((stage / 'patch-meta.json').read_text())
        meta['target_language'] = 'de'; (stage / 'patch-meta.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.service.apply_language(self.game, 'fr')
        self.assertEqual(self.service.inspect(self.game)['installed_language'], 'tr')

    def test_failed_language_switch_preserves_previous_pack(self):
        self.ready('tr', b'turkish'); self.ready('fr', b'french')
        self.service.apply_language(self.game, 'tr')
        with patch.object(s, 'json_write', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.service.apply_language(self.game, 'fr')
        self.assertEqual(self.service.inspect(self.game)['installed_language'], 'tr')
        self.service.apply_language(self.game, 'en'); self.fixture.original_restored()

    def test_export_is_editable_unicode_and_never_installs(self):
        stage = self.ready('fr', b'french')
        values = {'talk': 'Parler', 'use': 'Utiliser'}
        meta_path = stage / 'patch-meta.json'
        meta = json.loads(meta_path.read_text()); meta['source_entry_count'] = len(values)
        meta_path.write_text(json.dumps(meta))
        (stage / 'entries.translated.json').write_text(json.dumps(values), encoding='utf8')
        destination = self.service.data.parent / 'editable.json'
        self.service.export_translation('fr', destination)
        self.assertEqual(json.loads(destination.read_text('utf8')), values)
        self.fixture.original_restored()


if __name__ == '__main__':
    unittest.main()
