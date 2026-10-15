"""Bounded target-language UI terminology; never a full sentence translator."""
from __future__ import annotations

import re

from .protection import validate
from .terminology import _action_field, _staff_weapon_field, apply_turkish_context_terms


def normalize_language(code: str) -> str:
    if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8}){0,2}", code.strip()):
        raise ValueError("Enter a valid target language code, such as tr, de or pt-BR")
    parts = code.strip().replace('_', '-').split('-')
    return '-'.join([parts[0].lower()] + [p.upper() if len(p) == 2 else p.title() for p in parts[1:]])


def apply_target_context_terms(source: dict[str, str], translated: dict[str, str], target_language: str) -> tuple[dict[str, str], dict]:
    """Correct exact short labels only in their verified field context.

    Each language chooses its own UI grammar. Unlisted languages keep provider
    output and all languages retain the shared structural validation. This
    report says nothing about game-side font support or paragraph quality.
    """
    from .context_labels import CONTEXT_LABELS
    code = normalize_language(target_language)
    if code.split('-')[0] == 'tr':
        return apply_turkish_context_terms(source, translated)
    for mapping in (source, translated):
        if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()):
            raise TypeError("Source and translation must be string dictionaries")
    if source.keys() != translated.keys():
        raise ValueError("Complete source and translation key sets must match")
    # Simplified Chinese terminology must never overwrite Traditional Chinese.
    base = code.split('-')[0]
    lexicon_code = ('zh' if code in ('zh', 'zh-CN', 'zh-Sg', 'zh-SG', 'zh-Hans') else None) if base == 'zh' else base
    lexicon = CONTEXT_LABELS.get(lexicon_code, {})
    actions, terms = lexicon.get('actions', {}), lexicon.get('terms', {})
    output = dict(translated)
    rules = {'action_label': [], 'weapon_staff': [], 'skill_snipe': [], 'casting_time': [], 'binding_flag': []}
    for key, english in source.items():
        canonical, rule = None, None
        if english in actions and _action_field(key, english):
            canonical, rule = actions[english], 'action_label'
        elif english == 'Staff' and _staff_weapon_field(key, english) and terms.get('Staff'):
            canonical, rule = terms['Staff'], 'weapon_staff'
        elif english == 'Snipe' and key.startswith('SkillString') and key.endswith('_skill_name') and terms.get('Snipe'):
            canonical, rule = terms['Snipe'], 'skill_snipe'
        elif key == 'String_StatName_CastingTime_body' and english == 'Cast duration' and terms.get('Cast duration'):
            canonical, rule = terms['Cast duration'], 'casting_time'
        elif english in ('Bound', '(Bound)') and ('ITEM' in key.upper().split('_') or 'BIND' in key.upper()) and terms.get('Bound'):
            value = terms['Bound']
            canonical, rule = ('(' + value + ')' if english == '(Bound)' else value), 'binding_flag'
        if canonical is not None and canonical != output[key]:
            validate(english, canonical)
            output[key] = canonical
            rules[rule].append(key)
    affected = sorted({key for keys in rules.values() for key in keys})
    return output, dict(profile='multilingual-context-labels-v1', target_language=code,
                       lexicon_language=lexicon_code if lexicon else None,
                       available_action_labels=len(actions), changed_entries=len(affected), affected_fields=affected,
                       rule_keys=rules, rule_counts={k: len(v) for k, v in rules.items()},
                       scope='Exact short UI labels in verified field contexts; not a full semantic review.',
                       human_reviewed=False, in_game_verified=False)
