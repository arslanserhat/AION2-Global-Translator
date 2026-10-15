import unittest
from aion2_global_translator.codec import FString, L10NTable, L10NDocument, locale_seed


class SyntheticCodec(unittest.TestCase):
    def test_encrypted_unicode_edit_preserves_keys_prefix_and_tail(self):
        table = L10NTable(FString("SYNTHETIC"), [(FString("KEY"), FString("Hello {name}"))], trailing=b"\0\0\0\0")
        document = L10NDocument(table, "en-US", b"", key=bytes(range(32)), prefix=b"x" * 32, tail=b"tail")
        encoded = document.encode()
        decoded = L10NDocument.decode(encoded, "en-US", {locale_seed("en-US"): bytes(range(32))})
        self.assertEqual(decoded.encode(), encoded)
        changed = decoded.encode(decoded.table.translated({"KEY": "Merhaba {name} ğüşİöç"}))
        result = L10NDocument.decode(changed, "en-US", {locale_seed("en-US"): bytes(range(32))})
        self.assertEqual(result.table.as_dict(), {"KEY": "Merhaba {name} ğüşİöç"})
        self.assertEqual(result.prefix, b"x" * 32)
        self.assertEqual(result.tail, b"tail")
        self.assertEqual(result.table.trailing, table.trailing)

    def test_truncated_container_is_rejected(self):
        table = L10NTable(FString("SYNTHETIC"), [(FString("KEY"), FString("Text"))])
        doc = L10NDocument(table, "en-US", b"", key=b"k" * 32, prefix=b"p" * 32)
        encoded = doc.encode()
        with self.assertRaises(ValueError):
            L10NDocument.decode(encoded[:-16], "en-US", {locale_seed("en-US"): b"k" * 32})


if __name__ == "__main__":
    unittest.main()
