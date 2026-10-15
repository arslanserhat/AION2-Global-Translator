# SPDX-License-Identifier: Apache-2.0
"""Language picker examples, independent of provider availability or pack status."""
from __future__ import annotations

import re


LANGUAGES = (
    ("tr", "Türkçe"), ("en", "English"), ("de", "Deutsch"), ("fr", "Français"),
    ("es", "Español"), ("it", "Italiano"), ("pt", "Português"),
    ("pt-BR", "Português (Brasil)"), ("ru", "Русский"), ("uk", "Українська"),
    ("pl", "Polski"), ("nl", "Nederlands"), ("sv", "Svenska"), ("fi", "Suomi"),
    ("cs", "Čeština"), ("ro", "Română"), ("el", "Ελληνικά"), ("ar", "العربية"),
    ("fa", "فارسی"), ("ko", "한국어"), ("ja", "日本語"),
    ("zh", "简体中文"), ("zh-TW", "繁體中文"),
)
_CODE = re.compile(r"[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})?")


def language_code(value: str) -> str | None:
    """Accept a picker label or an explicit service-compatible language code."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not _CODE.fullmatch(value):
        match = re.search(r"\(([A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})?)\)$", value)
        if not match:
            return None
        value = match[1]
    parts = value.replace("_", "-").split("-")
    code = parts[0].lower()
    if len(parts) == 2:
        region = parts[1]
        code += "-" + (region.title() if len(region) == 4 and region.isalpha() else region.upper())
    return code


def original_language(code: str) -> bool:
    return code.lower().split("-")[0] == "en"


def turkish_language(code: str) -> bool:
    return code.lower().split("-")[0] == "tr"


def language_label(code: str, interface: str = "tr") -> str:
    name = next((name for known, name in LANGUAGES if known.lower() == code.lower()), None)
    if name is None:
        return code
    if code.lower() == "en":
        name += " — " + ("orijinal" if interface == "tr" else "original")
    return f"{name} ({code})"


def language_choices(interface: str = "tr") -> tuple[str, ...]:
    return tuple(language_label(code, interface) for code, _ in LANGUAGES)
