"""Opt-in Turkish title spelling for game fonts without Turkish glyphs.

This is a display compatibility profile, not a translation or Unicode repair.
Only explicit name/title fields are selected. The original mapping is retained,
and formatting literals never pass through the character substitution table.
"""

from __future__ import annotations

from collections import Counter

from .protection import protected_parts, validate


PROFILE = "turkish-heading-font-safe-v1"
_TURKISH_TO_LATIN = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")
_BODY_TOKENS = ("DESC", "DESCRIPTION", "EFFECT", "SUMMARY", "TOOLTIP", "STEP", "TEXT", "BODY")


def _field_profile(key: str) -> str | None:
    if key.startswith("SkillString") and key.endswith("_skill_name"):
        return "skill_name"
    if key.endswith("_desc_name"):
        return "status_name"
    if key.endswith("_achievement_title"):
        return "achievement_title"
    if key.endswith("_quest_title"):
        return "quest_title"
    if key.endswith("_title"):
        return "explicit_title"
    if not key.startswith("String_") or not key.endswith("_body"):
        return None
    # Here '_body' is the string-table column suffix. Description/effect/etc.
    # tokens within the identifier still exclude it from the heading profile.
    tokens = key.split("_")[:-1]
    upper = [token.upper() for token in tokens]
    if any(token.startswith(_BODY_TOKENS) for token in upper):
        return None
    if "TITLE" in tokens:
        return "ui_title"
    if key.startswith("String_STR_ITEM_"):
        return "item_name"
    return None


def _fold_visible_text(text: str) -> str:
    pieces, last = [], 0
    for start, end, literal in protected_parts(text):
        pieces.append(text[last:start].translate(_TURKISH_TO_LATIN))
        pieces.append(literal)
        last = end
    pieces.append(text[last:].translate(_TURKISH_TO_LATIN))
    return "".join(pieces)


def apply_turkish_heading_compatibility(entries: dict[str, str]) -> tuple[dict[str, str], dict]:
    """Return a new mapping and an exact, uncapped report of changed fields.

    Turkish letters in visible heading text receive basic-Latin counterparts.
    No normalization, case conversion, punctuation conversion, or substitution
    of other Unicode characters occurs. Regular descriptions, dialogue and
    quest-step text are outside this profile. The caller explicitly opts in.
    """
    if not isinstance(entries, dict) or any(not isinstance(key, str) or not isinstance(value, str)
                                            for key, value in entries.items()):
        raise TypeError("Entries must be a dictionary mapping string keys to string values.")
    result = dict(entries)
    changed, field_counts, selected = [], Counter(), 0
    for key, value in entries.items():
        field = _field_profile(key)
        if field is None:
            continue
        selected += 1
        folded = _fold_visible_text(value)
        if folded == value:
            continue
        validate(value, folded)
        result[key] = folded
        changed.append(key)
        field_counts[field] += 1
    report = {
        "profile": PROFILE,
        "changed_entries": len(changed),
        "affected_fields": sorted(changed),
        "selected_entries": selected,
        "field_counts": dict(sorted(field_counts.items())),
        "protected_literals_preserved": True,
        "regular_body_fields_unchanged": True,
        "conversion": "çÇğĞıİöÖşŞüÜ → cCgGiIoOsSuU in visible heading text only",
    }
    return result, report
