# SPDX-License-Identifier: Apache-2.0
"""Small, explicit Turkish terminology rules for verified string-table fields.

These rules are not a sentence translator. Exact labels and field context are
required; closed Staff and (Bound) corrections cover weapon names and item flags.
"""

from __future__ import annotations

import re

from .protection import protected_parts, validate


PROFILE = "turkish-context-terms-v1"
CLASS_LEXICON_SOURCE = "https://cmsstatic.aion.gameforge.com/Patchnotes_4_5_1002v_TR_final.pdf"
CLASS_LABELS = {
    "Gladiator": "Gladyatör", "Templar": "Tapınakçı", "Ranger": "Avcı",
    "Assassin": "Suikastçı", "Spiritmaster": "Ruh Çağırıcı",
    "Sorcerer": "Sihirbaz", "Cleric": "Ruhban", "Chanter": "Kantor",
    # AION 2's verified class shop fields call the Spiritmaster Elementalist.
    "Elementalist": "Ruh Çağırıcı",
}
ACTION_LABELS = {
    "Talk": "Konuş", "Use": "Kullan", "Collect": "Topla", "Craft": "Üret",
    "Equip": "Kuşan", "Unequip": "Çıkar", "Open": "Aç", "Close": "Kapat",
    "Buy": "Satın al", "Purchase": "Satın al", "Sell": "Sat", "Confirm": "Onayla",
    "Accept": "Kabul et", "Cancel": "İptal", "Apply": "Uygula", "Send": "Gönder",
    "Search": "Ara", "Learn": "Öğren", "Enhance": "Güçlendir", "Upgrade": "Geliştir",
    "Enter": "Gir", "Exit": "Çık", "Leave": "Ayrıl", "Join": "Katıl",
    "Invite": "Davet et", "Abandon": "Bırak", "Teleport": "Işınlan", "Claim": "Al",
    "Claim All": "Tümünü al", "Select": "Seç", "Create": "Oluştur", "Delete": "Sil",
    "Reset": "Sıfırla", "Attack": "Saldır", "Return": "Dön",
}
_ACTION_CONTEXT = {"BUTTON", "BTN", "ACTION", "COMMAND", "INTERACT", "INTERACTION",
                   "CONTEXTMENU", "CONFIRM", "KEYGUIDE"}
_NOUN_FIELDS = {"TITLE", "NAME", "TAB", "CATEGORY", "CLASS", "CHANNEL", "CHATMENU"}
_CLASS_PREFIXES = (
    "String_STR_CLASS_",
    "String_UI_ITEM_TOOLTIP_MOUSEOVER_TEXT_",
    "String_UI_SHOP_ENUM_CATEGORY_Abyss_Stigma_",
    "String_UI_SHOP_ENUM_CATEGORY_Abyss_SpecializedSkill_",
)
_STAFF_FORMS = {"Personel": "Asa", "personel": "asa", "Personeli": "Asası", "personeli": "asası"}
_STAFF_FORM = re.compile(r"(?<!\w)(?:Personeli|personeli|Personel|personel)(?!\w)")


def _action_field(key: str, english: str) -> bool:
    if key.startswith("InputKeyMapping_") and key.endswith("_desc"):
        return True
    if key.startswith("PcSocialAction_") and key.endswith("_action_name"):
        return True
    if not key.startswith("String_UI_") or not key.endswith("_body"):
        return False
    tokens = set(key.upper().split("_")[:-1])
    if tokens & _NOUN_FIELDS or any(token.startswith("TITLE") for token in tokens):
        return False
    if tokens & _ACTION_CONTEXT or {"CONTEXT", "MENU"} <= tokens:
        return True
    # Known direct interaction prompts sometimes omit BUTTON/ACTION in the ID.
    # An identifier for the exact verb is required; generic prose isn't selected.
    if tokens & {"MENU", "CHAT", "TOOLTIP", "DESCRIPTION", "SUMMARY", "TEXT"}:
        return False
    return re.sub(r"[^A-Z]", "", english.upper()) in tokens


def _class_field(key: str) -> bool:
    if key.startswith(_CLASS_PREFIXES):
        return True
    if not key.startswith("String_UI_") or not key.endswith("_body"):
        return False
    return "CLASS" in key.upper().split("_")


def _staff_weapon_field(key: str, english: str) -> bool:
    if not re.search(r"\bStaff\b", english):
        return False
    upper = key.upper()
    return ((key.startswith("Skin_WP_") and "_ST_" in upper)
            or (key.startswith("Skin_EQUIP_") and "STAFF" in upper.split("_"))
            or (key.startswith("String_STR_ITEM_") and "_EQUIP_WP_STAFF_" in upper
                and not {"DESC", "DESCRIPTION"} & set(upper.split("_")))
            or (key.startswith("String_") and "(Skin: Staff)" in english))


def _visible_transform(text: str, transform) -> str:
    pieces, last = [], 0
    for start, end, literal in protected_parts(text):
        pieces.extend([transform(text[last:start]), literal])
        last = end
    pieces.append(transform(text[last:]))
    return "".join(pieces)


def _staff_visible_text(text: str) -> str:
    return _visible_transform(text, lambda fragment: _STAFF_FORM.sub(lambda match: _STAFF_FORMS[match.group()], fragment))


def _has_visible_bound_flag(text: str) -> bool:
    if "(Bound)" not in text:
        return False
    last = 0
    for start, end, _ in protected_parts(text):
        if "(Bound)" in text[last:start]:
            return True
        last = end
    return "(Bound)" in text[last:]


def apply_turkish_context_terms(source: dict[str, str], translated: dict[str, str]) -> tuple[dict[str, str], dict]:
    """Apply exact, context-qualified labels without mutating either mapping."""
    for mapping in (source, translated):
        if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                for k, v in mapping.items()):
            raise TypeError("Source and translation must be dictionaries of string keys and values.")
    if source.keys() != translated.keys():
        raise ValueError("Source and translation must contain the same complete key set.")
    result = dict(translated)
    rule_keys = {"action_imperative": [], "class_label": [], "skill_snipe": [],
                 "casting_time_stat": [], "staff_weapon_polysemy": [], "bound_item_flag": []}
    for key, english in source.items():
        canonical, rule = None, None
        if english == "Snipe" and key.startswith("SkillString") and key.endswith("_skill_name"):
            canonical, rule = "Keskin Atış", "skill_snipe"
        elif english in CLASS_LABELS and _class_field(key):
            canonical, rule = CLASS_LABELS[english], "class_label"
        elif english in ACTION_LABELS and _action_field(key, english):
            canonical, rule = ACTION_LABELS[english], "action_imperative"
        elif key == "String_StatName_CastingTime_body" and english == "Cast duration":
            canonical, rule = "Beceri hazırlık süresi", "casting_time_stat"
        elif _staff_weapon_field(key, english):
            canonical, rule = ("Asa" if english == "Staff" else _staff_visible_text(result[key])), "staff_weapon_polysemy"
            validate(result[key], canonical)
        if canonical is None or canonical == result[key]:
            continue
        if rule != "staff_weapon_polysemy":
            validate(english, canonical)
        result[key] = canonical
        rule_keys[rule].append(key)
    # The complete parenthesized flag identifies the game meaning. A book's
    # ordinary "ciltli" adjective, Hardbound, and protected contents stay intact.
    # Run after other terminology rules so a Staff name can receive both fixes.
    for key, english in source.items():
        if not _has_visible_bound_flag(english):
            continue
        canonical = _visible_transform(result[key], lambda fragment: fragment.replace("(Ciltli)", "(Bağlı)"))
        if canonical != result[key]:
            validate(result[key], canonical)
            result[key] = canonical
            rule_keys["bound_item_flag"].append(key)
    rule_keys = {rule: sorted(keys) for rule, keys in rule_keys.items()}
    affected = sorted({key for keys in rule_keys.values() for key in keys})
    return result, {
        "profile": PROFILE, "changed_entries": len(affected), "affected_fields": affected,
        "rule_counts": {rule: len(keys) for rule, keys in rule_keys.items()}, "rule_keys": rule_keys,
        "action_style": "Turkish imperative in verified action fields",
        "class_lexicon_source": CLASS_LEXICON_SOURCE, "class_lexicon_pages": "10-12",
        "scope": "Exact English labels, observed Staff weapon forms and the visible (Bound) item flag; not a full semantic review.",
    }
