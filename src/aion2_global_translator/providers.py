"""A user-configured LibreTranslate provider using only the Python stdlib.

API reference: https://docs.libretranslate.com/api/operations/translate/
No public endpoint, credential, text corpus, or network action is configured at
import time. TLS verification is enabled and redirects are deliberately refused.
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


MAX_ATTEMPTS = 3
MAX_RETRY_AFTER = 30.0
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 2 * 1024 * 1024
_LANGUAGE = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,31}\Z")


class ProviderError(RuntimeError):
    """A sanitized provider failure, safe to show without exposing credentials."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        # A redirect can forward text or a JSON API key to another origin. Ask
        # the user to configure the endpoint's final URL instead.
        raise ProviderError("The endpoint redirected. Configure its final base URL.")


def _base_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Configure a LibreTranslate URL first.")
    value = value.strip()
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("URL whitespace and control characters must be encoded.")
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise ValueError("Invalid LibreTranslate URL.") from None
    if (parts.scheme.lower() not in ("https", "http") or not host
            or parts.username is not None or parts.password is not None
            or parts.query or parts.fragment or any(character.isspace() for character in parts.netloc)):
        raise ValueError("Use an HTTP(S) base URL without credentials, query, or fragment.")
    if parts.scheme.lower() == "http" and host.lower() not in ("localhost", "127.0.0.1"):
        raise ValueError("HTTPS is required except for localhost or 127.0.0.1.")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid endpoint port.")
    path = parts.path.rstrip("/")
    if path.rsplit("/", 1)[-1] in ("translate", "languages"):
        path = path.rsplit("/", 1)[0]
    return urlunsplit((parts.scheme.lower(), parts.netloc, path, "", ""))


def _retry_delay(value, attempt: int) -> float:
    if value is not None:
        try:
            seconds = float(value)
            if math.isfinite(seconds):
                return min(MAX_RETRY_AFTER, max(0.0, seconds))
        except (ValueError, TypeError):
            pass
        try:
            moment = parsedate_to_datetime(value)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
            return min(MAX_RETRY_AFTER, max(0.0, (moment - datetime.now(timezone.utc)).total_seconds()))
        except (ValueError, TypeError, OverflowError):
            pass
    return min(MAX_RETRY_AFTER, 2.0 ** attempt)


class LibreTranslateProvider:
    """Translate HTML batches through the endpoint explicitly supplied by a user.

    ``url`` may be a base URL, an API path prefix, or its /translate endpoint.
    Language availability depends on the models installed by that operator.
    """

    def __init__(self, url: str, api_key: str = "", source: str = "en",
                 target: str = "tr", timeout: float = 45):
        self.url = _base_url(url)
        if not isinstance(api_key, str):
            raise TypeError("API key must be a string.")
        if not isinstance(source, str) or not _LANGUAGE.fullmatch(source):
            raise ValueError("Invalid source language code.")
        if not isinstance(target, str) or not _LANGUAGE.fullmatch(target) or target == "auto":
            raise ValueError("Invalid target language code.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be a positive finite number.")
        self.source, self.target, self.timeout = source, target, timeout
        self._api_key = api_key
        self._opener = build_opener(HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())

    def _json(self, endpoint: str, payload=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if data is not None and len(data) > MAX_REQUEST_BYTES:
            raise ProviderError("Translation batch is too large. Use a smaller batch.")
        request = Request(self.url + "/" + endpoint, data=data, method="GET" if data is None else "POST",
                          headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8",
                                   "User-Agent": "AION2-Global-Translator/1"})
        for attempt in range(MAX_ATTEMPTS):
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    if response.status != 200:
                        raise ProviderError("The endpoint returned an unexpected HTTP status.")
                    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
                    if content_type != "application/json" and not content_type.endswith("+json"):
                        raise ProviderError("The endpoint did not return JSON.")
                    body = response.read(MAX_RESPONSE_BYTES + 1)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise ProviderError("The endpoint response is too large.")
                try:
                    return json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise ProviderError("The endpoint returned invalid UTF-8 JSON.") from None
            except HTTPError as error:
                status = error.code
                retry_after = error.headers.get("Retry-After") if error.headers else None
                error.close()
                if status in (429, 503) and attempt + 1 < MAX_ATTEMPTS:
                    time.sleep(_retry_delay(retry_after, attempt))
                    continue
                raise ProviderError(f"The endpoint returned HTTP {status}.") from None
            except URLError as error:
                if isinstance(error.reason, ssl.SSLError):
                    raise ProviderError("TLS verification failed. Check the endpoint certificate.") from None
                raise ProviderError("The translation endpoint could not be reached.") from None
            except (OSError, TimeoutError):
                raise ProviderError("The translation endpoint connection failed or timed out.") from None
        raise ProviderError("The translation endpoint retry limit was reached.")

    def languages(self) -> list[dict]:
        result = self._json("languages")
        if not isinstance(result, list) or not result or len(result) > 1000:
            raise ProviderError("The endpoint returned an invalid language list.")
        languages, seen = [], set()
        for item in result:
            if not isinstance(item, dict):
                raise ProviderError("The endpoint returned an invalid language record.")
            code, name = item.get("code"), item.get("name")
            if (not isinstance(code, str) or not _LANGUAGE.fullmatch(code) or code in seen
                    or not isinstance(name, str) or not name.strip() or len(name) > 200
                    or any(ord(character) < 32 for character in name)):
                raise ProviderError("The endpoint returned an invalid language record.")
            seen.add(code)
            languages.append({"code": code, "name": name})
        return languages

    def translate_batch(self, texts: list[str]) -> list[str]:
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise TypeError("texts must be a list of strings.")
        if not texts:
            return []
        payload = {"q": texts, "source": self.source, "target": self.target, "format": "html"}
        if self._api_key:
            payload["api_key"] = self._api_key
        result = self._json("translate", payload)
        if not isinstance(result, dict) or "error" in result:
            raise ProviderError("The endpoint returned a translation error.")
        translated = result.get("translatedText")
        # Some deployments return a scalar even for a one-item array.
        if isinstance(translated, str) and len(texts) == 1:
            translated = [translated]
        if (not isinstance(translated, list) or len(translated) != len(texts)
                or any(not isinstance(text, str) for text in translated)
                or any(source.strip() and not target.strip() for source, target in zip(texts, translated))):
            raise ProviderError("The endpoint returned an incomplete translation batch.")
        return translated
