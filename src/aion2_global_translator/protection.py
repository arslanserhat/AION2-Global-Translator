"""Protect formatting literals before sending plain text to an HTML translator.

This module has no provider, network, filesystem, or game-data dependencies.
Indexed macros may move with translated grammar. Rich-text literal order and
non-positional printf argument identities must remain intact.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import html
from html.parser import HTMLParser
import re
import unicodedata


PROTECTION_PROFILE = "format-game-abbreviations-and-unicode-numbers-v3"
GAME_ABBREVIATIONS = ("HP", "MP", "XP", "EXP", "AP", "DP", "PvE", "PvP", "FPS", "DPS", "NPC", "AoE", "DoT", "HoT")
_GAME_ABBREVIATION = (r"(?<![A-Za-z0-9_])(?:" + "|".join(map(re.escape, GAME_ABBREVIATIONS))
                      + r")(?![A-Za-z0-9_])")
_PRINTF = r"%(?:\d+\$)?[-+#0']*(?:\d+|\*(?:\d+\$)?)?(?:\.(?:\d+|\*(?:\d+\$)?))?(?:hh|ll|I64|I32|[hljztL])?[diuoxXfFeEgGaAcCsSpn%]"
_TAG = re.compile(r'''<(?:[^<>"']|"[^"]*"|'[^']*')*>''')
_PRINTF_RE = re.compile(_PRINTF)
_SPECIAL = re.compile(
    _TAG.pattern + "|" + _PRINTF
    + r"|\\(?:r\\n|[nrt0\\\"']|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8})"
    + r"|\r\n|[\x00-\x1f\x7f]"
    + r"|&(?:\#[0-9]+|\#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);"
    + r"|[+\-\u2212]?(?:\d+(?:[.,:/]\d+)*|\.\d+)(?:[eE][+\-]?\d+)?%?"
    + "|" + _GAME_ABBREVIATION
)


def protected_parts(text: str):
    """Yield start/end/literal triples, including balanced nested macros."""
    if not isinstance(text, str):
        raise TypeError("Text must be a string.")
    position = 0
    while position < len(text):
        if text[position] == "{":
            depth, end = 1, position + 1
            while end < len(text) and depth:
                depth += (text[end] == "{") - (text[end] == "}")
                end += 1
            if depth == 0:
                yield position, end, text[position:end]
                position = end
                continue
        match = _SPECIAL.match(text, position)
        if match:
            yield position, match.end(), match.group()
            position = match.end()
        elif unicodedata.category(text[position]).startswith("N"):
            # Preserve Unicode numbers such as ①/Ⅳ/²/½, beyond regex \d.
            # CJK letters like 参/一 have numeric properties but are ordinary
            # word characters (category Lo), not formatting/number literals.
            yield position, position + 1, text[position]
            position += 1
        else:
            position += 1


def protected_literals(text: str) -> Counter:
    """Return exact formatting, numeric, and case-sensitive game abbreviations."""
    return Counter(literal for _, _, literal in protected_parts(text))


def has_linguistic_content(text: str) -> bool:
    last = 0
    for start, end, _ in protected_parts(text):
        if any(character.isalpha() for character in text[last:start]):
            return True
        last = end
    return any(character.isalpha() for character in text[last:])


def _nonpos_printf(literal):
    return (bool(_PRINTF_RE.fullmatch(literal)) and literal != "%%"
            and not re.match(r"%\d+\$", literal))


def validate(source: str, target: str) -> None:
    """Raise ValueError if a translation loses, invents, or changes literals."""
    if not isinstance(source, str) or not isinstance(target, str):
        raise ValueError("Source and translation must be strings.")
    if source.strip() and not target.strip():
        raise ValueError("The translation is empty.")
    if protected_literals(source) != protected_literals(target):
        raise ValueError("Protected formatting, macros, controls, numbers, or game abbreviations changed.")
    for predicate in (lambda literal: bool(_TAG.fullmatch(literal)), _nonpos_printf):
        original = [literal for _, _, literal in protected_parts(source) if predicate(literal)]
        translated = [literal for _, _, literal in protected_parts(target) if predicate(literal)]
        if original != translated:
            raise ValueError("Rich-text or non-positional printf order changed.")


validate_literals = validate


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks = []

    def handle_data(self, data):
        self.chunks.append(data)


@dataclass
class Prepared:
    source: str
    html: str
    placeholders: dict[str, str]

    @classmethod
    def create(cls, text: str) -> "Prepared":
        if not isinstance(text, str):
            raise TypeError("Text must be a string.")
        prefix = "__A2PH"
        while prefix in text:
            prefix += "X"
        pieces, placeholders, last = [], {}, 0
        for index, (start, end, literal) in enumerate(protected_parts(text)):
            pieces.append(html.escape(text[last:start], quote=False))
            token = f"{prefix}{index:05d}__"
            placeholders[token] = literal
            pieces.append(f'<span translate="no">{token}</span>')
            last = end
        pieces.append(html.escape(text[last:], quote=False))
        return cls(text, "".join(pieces), placeholders)

    make = create

    @property
    def encoded(self):
        return self.html

    @property
    def needs_translation(self):
        return has_linguistic_content(self.source)

    def check(self, translated: str) -> None:
        validate(self.source, translated)

    def restore(self, translated_html: str) -> str:
        if not isinstance(translated_html, str):
            raise ValueError("Translated HTML must be a string.")
        parser = _TextOnly()
        parser.feed(translated_html)
        parser.close()
        text = "".join(parser.chunks)
        # A newly generated Turkish possessive after a percent sign can look
        # like a printf apostrophe flag (e.g. %'si). Use the typographic mark.
        # Genuine source printf directives remain hidden in their tokens here.
        text = re.sub(r"%'(?=[A-Za-zÇĞİÖŞÜçğıöşü])", "%’", text)
        for token, literal in self.placeholders.items():
            if literal.endswith("%"):
                text = re.sub(re.escape(token) + r"'(?=[A-Za-zÇĞİÖŞÜçğıöşü])", token + "’", text)
        for token in self.placeholders:
            if text.count(token) != 1:
                raise ValueError("A protected placeholder was lost or duplicated.")
        printf_tokens = [token for token, literal in self.placeholders.items() if _nonpos_printf(literal)]
        if sorted(printf_tokens, key=text.index) != printf_tokens:
            raise ValueError("Non-positional printf argument identities changed order.")
        if self.placeholders:
            pattern = re.compile("|".join(map(re.escape, self.placeholders)))
            text = pattern.sub(lambda match: self.placeholders[match.group()], text)
        self.check(text)
        return text


def prepare(text: str) -> Prepared:
    return Prepared.create(text)
