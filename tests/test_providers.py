import io
import json
import ssl
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from aion2_global_translator.providers import LibreTranslateProvider, ProviderError, _NoRedirect


class Response:
    def __init__(self, value=None, *, body=None, status=200, content_type="application/json; charset=utf-8"):
        self.status = status
        self.headers = {"Content-Type": content_type}
        self.body = json.dumps(value, ensure_ascii=False).encode("utf-8") if body is None else body

    def read(self, length):
        return self.body[:length]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Opener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def http_error(status, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("https://example.invalid/translate", status, "private-test-key echoed by server",
                     headers, io.BytesIO(b"private-test-key in an error body"))


class LibreTranslateTests(unittest.TestCase):
    def provider(self, *responses, **options):
        provider = LibreTranslateProvider("https://example.invalid/api/translate", **options)
        opener = Opener(*responses)
        provider._opener = opener
        return provider, opener

    def test_utf8_html_batch_and_explicit_key_use_json_not_url(self):
        texts = ['Open <span translate="no">__TOKEN__</span>', "Şehir ve eşya"]
        expected = ['<span translate="no">__TOKEN__</span> aç', "City and item"]
        provider, opener = self.provider(Response({"translatedText": expected}), api_key="private-test-key")
        self.assertEqual(provider.translate_batch(texts), expected)
        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, "https://example.invalid/api/translate")
        self.assertEqual(timeout, 45)
        self.assertNotIn("private-test-key", request.full_url)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload, {"q": texts, "source": "en", "target": "tr", "format": "html", "api_key": "private-test-key"})
        self.assertIn("Şehir".encode("utf-8"), request.data)

    def test_languages_use_configured_prefix_and_validate_records(self):
        provider, opener = self.provider(Response([{"code": "en", "name": "English", "targets": ["tr"]},
                                                   {"code": "tr", "name": "Türkçe"}]))
        self.assertEqual(provider.languages(), [{"code": "en", "name": "English"}, {"code": "tr", "name": "Türkçe"}])
        request, _ = opener.requests[0]
        self.assertEqual(request.full_url, "https://example.invalid/api/languages")
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.data)

    def test_single_item_scalar_compatibility_and_empty_input(self):
        provider, opener = self.provider(Response({"translatedText": "Merhaba"}))
        self.assertEqual(provider.translate_batch([]), [])
        self.assertEqual(len(opener.requests), 0)
        self.assertEqual(provider.translate_batch(["Hello"]), ["Merhaba"])

    def test_only_explicit_local_http_is_permitted(self):
        for url in ("http://localhost:5000", "http://127.0.0.1:5000/translate"):
            self.assertTrue(LibreTranslateProvider(url).url.startswith("http://"))
        for url in ("http://example.invalid", "http://127.0.0.2:5000", "file:///tmp/provider",
                    "https://user:private-test-key@example.invalid", "https://example.invalid/?api_key=private-test-key",
                    "https://example.invalid/#private-test-key", "", "https://example.invalid:0",
                    "http://local\nhost:5000", "https://example.invalid/a path"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                LibreTranslateProvider(url)

    def test_tls_validation_is_enabled_and_redirects_are_refused(self):
        provider = LibreTranslateProvider("https://example.invalid")
        https = next(handler for handler in provider._opener.handlers if hasattr(handler, "_context"))
        self.assertTrue(https._context.check_hostname)
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)
        with self.assertRaises(ProviderError) as error:
            _NoRedirect().redirect_request(None, None, 307, "redirect", {}, "http://elsewhere.invalid/private-test-key")
        self.assertNotIn("private-test-key", str(error.exception))

    @patch("aion2_global_translator.providers.time.sleep")
    def test_rate_limit_and_unavailable_retry_are_bounded_and_honor_cap(self, sleep):
        provider, opener = self.provider(http_error(429, "99999"), http_error(503, "0"),
                                        Response({"translatedText": ["Merhaba"]}))
        self.assertEqual(provider.translate_batch(["Hello"]), ["Merhaba"])
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [30.0, 0.0])

    @patch("aion2_global_translator.providers.time.sleep")
    def test_exhausted_retry_and_auth_error_do_not_expose_server_secrets(self, sleep):
        provider, opener = self.provider(http_error(503), http_error(503), http_error(503), api_key="private-test-key")
        with self.assertRaises(ProviderError) as error:
            provider.translate_batch(["Hello"])
        self.assertEqual(len(opener.requests), 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertNotIn("private-test-key", str(error.exception))
        provider, opener = self.provider(http_error(403))
        with self.assertRaises(ProviderError):
            provider.translate_batch(["Hello"])
        self.assertEqual(len(opener.requests), 1)

    @patch("aion2_global_translator.providers.time.sleep")
    def test_http_date_retry_after_is_honored_with_the_same_bound(self, sleep):
        future = format_datetime(datetime.now(timezone.utc) + timedelta(minutes=5), usegmt=True)
        provider, _ = self.provider(http_error(429, future), Response({"translatedText": ["Merhaba"]}))
        self.assertEqual(provider.translate_batch(["Hello"]), ["Merhaba"])
        sleep.assert_called_once_with(30.0)

    def test_bad_or_partial_success_is_rejected(self):
        cases = [Response({"translatedText": ["only one"]}), Response({"translatedText": ["ok", 2]}),
                 Response({"translatedText": ["", "ok"]}), Response({"error": "private-test-key"}),
                 Response(body=b"not JSON"), Response(body=b"\xff"),
                 Response(body=b"<html>private-test-key</html>", content_type="text/html")]
        for response in cases:
            with self.subTest(response=response.body):
                provider, _ = self.provider(response)
                with self.assertRaises(ProviderError) as error:
                    provider.translate_batch(["Hello", "World"])
                self.assertNotIn("private-test-key", str(error.exception))

    def test_language_list_validation_rejects_ambiguous_or_malformed_data(self):
        for data in ([], {"en": "English"}, [{"code": "en", "name": ""}],
                     [{"code": "en", "name": "English"}, {"code": "en", "name": "duplicate"}]):
            provider, _ = self.provider(Response(data))
            with self.assertRaises(ProviderError):
                provider.languages()

    def test_tls_errors_are_sanitized(self):
        provider, _ = self.provider(URLError(ssl.SSLCertVerificationError("private-test-key")))
        with self.assertRaises(ProviderError) as error:
            provider.translate_batch(["Hello"])
        self.assertIn("TLS", str(error.exception))
        self.assertNotIn("private-test-key", str(error.exception))

    def test_batch_input_and_response_memory_are_bounded(self):
        provider, _ = self.provider()
        for texts in ("Hello", ["Hello", None]):
            with self.assertRaises(TypeError):
                provider.translate_batch(texts)
        provider, _ = self.provider(Response(body=b"x" * 101))
        with patch("aion2_global_translator.providers.MAX_RESPONSE_BYTES", 100):
            with self.assertRaises(ProviderError):
                provider.translate_batch(["Hello"])


if __name__ == "__main__":
    unittest.main()
