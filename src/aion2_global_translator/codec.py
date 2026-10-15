# SPDX-License-Identifier: Apache-2.0
# AION 2 format derived from CUE4Parse, Copyright (c) 2020-2026 its contributors.
# See THIRD_PARTY_NOTICES.md and LICENSE.
"""Read/write AION2 L10N DATs using the public CUE4Parse format.

The 32-byte encrypted-payload prefix is opaque. Edited containers preserve it;
their acceptance by the game requires a pilot test. No-edit writes reconstruct
the header and AES payload while reusing the original LZ4 stream/padding.
"""

from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

_DEPS = Path(__file__).resolve().parent / "deps"
if _DEPS.is_dir():
    sys.path.insert(0, str(_DEPS))
from blake3 import blake3
import lz4.block
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_MANIFEST_HASH_KEY = bytes.fromhex(
    "eb0bc09728475ab5196af8ce785d8a79df18d2148f51cbef8b39e43b2a1d4056"
)
_XOR = bytes.fromhex("25a87e91")


def _aes(data: bytes, key: bytes, encrypt=False) -> bytes:
    if len(data) % 16 or len(key) != 32:
        raise ValueError("Invalid AES-256 ECB block/key size")
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    context = cipher.encryptor() if encrypt else cipher.decryptor()
    return context.update(data) + context.finalize()


def _xor(data: bytes, key: bytes) -> bytes:
    # FAion2DatFileArchive.DecryptData deliberately leaves short old strings.
    if len(data) <= 4 and len(key) == 4:
        return data
    return bytes(value ^ key[i % len(key)] for i, value in enumerate(data))


def read_manifest(data: bytes) -> dict[int, bytes]:
    if len(data) < 8 or (len(data) - 8) % 48:
        raise ValueError("Invalid key manifest size")
    plain = _aes(data[8:], blake3(_MANIFEST_HASH_KEY).digest())
    result = {}
    for offset in range(0, len(plain), 48):
        seed = struct.unpack_from("<Q", plain, offset)[0]
        result[seed] = plain[offset + 8:offset + 40]
    return result


def locale_seed(locale: str) -> int:
    return int.from_bytes(blake3(("L10NString_" + locale).encode()).digest()[:8], "little")


def header_key(locale: str) -> bytes:
    root = int.from_bytes(blake3(struct.pack("<Q", 0xCD02190910CE83F6)).digest()[:8], "little")
    return blake3(struct.pack("<QQii", root, locale_seed(locale), 3, 0)).digest()


@dataclass
class FString:
    text: str
    wide: bool = False
    zero_length: bool = False
    original_text: str = field(default="", repr=False)

    def write(self, xor_key: bytes | None = None) -> bytes:
        if self.zero_length and not self.text:
            return struct.pack("<i", 0)
        wide = self.wide or (self.text != self.original_text and not self.text.isascii())
        if wide:
            body = self.text.encode("utf-16-le") + b"\0\0"
            size = -(len(body) // 2)
        else:
            body = self.text.encode("utf-8") + b"\0"
            size = len(body)
        if xor_key:
            body = _xor(body, xor_key)
        return struct.pack("<i", size) + body


class _Reader:
    def __init__(self, data: bytes, xor_key=None):
        self.data, self.pos, self.xor_key = data, 0, xor_key

    def int(self):
        if self.pos + 4 > len(self.data):
            raise ValueError("Truncated FString/table integer")
        value = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return value

    def string(self):
        count = self.int()
        if count == 0:
            return FString("", zero_length=True)
        size = count if count > 0 else -2 * count
        if size < 1 or size > len(self.data) - self.pos:
            raise ValueError("Invalid FString length at offset " + str(self.pos - 4))
        body = self.data[self.pos:self.pos + size]
        self.pos += size
        if self.xor_key:
            body = _xor(body, self.xor_key)
        end = b"\0\0" if count < 0 else b"\0"
        if not body.endswith(end):
            raise ValueError("FString terminator missing at offset " + str(self.pos - size))
        text = body[:-len(end)].decode("utf-16-le" if count < 0 else "utf-8")
        return FString(text, wide=count < 0, original_text=text)


@dataclass
class L10NTable:
    namespace: FString
    entries: list[tuple[FString, FString]]
    version: int | None = 1
    trailing: bytes = field(default=b"", repr=False)

    @classmethod
    def parse(cls, plain: bytes, modern=True):
        reader = _Reader(plain, None if modern else _XOR)
        version = reader.int() if modern else None
        if modern and version != 1:
            raise ValueError("Unsupported plaintext L10N version")
        namespace = reader.string()
        count = reader.int()
        if count < 0 or count > (len(plain) - reader.pos) // 8:
            raise ValueError("Invalid L10N entry count")
        entries = [(reader.string(), reader.string()) for _ in range(count)]
        return cls(namespace, entries, version, plain[reader.pos:])

    def write(self) -> bytes:
        xor_key = None if self.version is not None else _XOR
        out = bytearray(struct.pack("<i", self.version) if self.version is not None else b"")
        out += self.namespace.write(xor_key)
        out += struct.pack("<i", len(self.entries))
        for key, value in self.entries:
            out += key.write(xor_key)
            out += value.write(xor_key)
        out += self.trailing
        return bytes(out)

    def as_dict(self) -> dict[str, str]:
        result = {key.text: value.text for key, value in self.entries}
        if len(result) != len(self.entries):
            raise ValueError("Duplicate entry keys would be lost in JSON map")
        return result

    def translated(self, translations: dict[str, str]):
        unknown = set(translations) - {key.text for key, _ in self.entries}
        if unknown:
            raise ValueError("Translation map has unknown keys")
        return replace(self, entries=[
            (key, replace(value, text=translations[key.text])) if key.text in translations else (key, value)
            for key, value in self.entries
        ])


@dataclass
class L10NDocument:
    table: L10NTable
    locale: str
    original_plaintext: bytes = field(repr=False)
    key: bytes | None = field(default=None, repr=False)
    prefix: bytes = field(default=b"", repr=False)
    packed: bytes = field(default=b"", repr=False)
    padding: bytes = field(default=b"", repr=False)
    tail: bytes = field(default=b"", repr=False)

    @classmethod
    def decode(cls, data: bytes, locale: str, manifest: bytes | dict[int, bytes]):
        if len(data) < 24 or struct.unpack_from("<I", data)[0] != 2:
            table = L10NTable.parse(data, modern=False)
            return cls(table, locale, data)
        packed_size, encryption_type, aligned_size, raw_size = struct.unpack(
            "<iiii", _xor(data[4:20], header_key(locale))
        )
        if encryption_type != 2 or packed_size < 0 or raw_size < 0 or aligned_size % 16:
            raise ValueError("Unsupported or invalid modern L10N header")
        if aligned_size < packed_size + 32 or aligned_size > len(data) - 20:
            raise ValueError("Modern L10N payload exceeds container")
        keys = read_manifest(manifest) if isinstance(manifest, bytes) else manifest
        try:
            key = keys[locale_seed(locale)]
        except KeyError:
            raise ValueError("Locale's L10N key is absent from manifest") from None
        payload = _aes(data[20:20 + aligned_size], key)
        packed = payload[32:32 + packed_size]
        plain = lz4.block.decompress(packed, uncompressed_size=raw_size)
        if len(plain) != raw_size:
            raise ValueError("L10N decompressed length mismatch")
        return cls(L10NTable.parse(plain), locale, plain, key, payload[:32],
                   packed, payload[32 + packed_size:], data[20 + aligned_size:])

    def encode(self, table: L10NTable | None = None) -> bytes:
        plain = (table or self.table).write()
        if self.key is None:
            return plain
        unchanged = plain == self.original_plaintext
        packed = self.packed if unchanged else lz4.block.compress(
            plain, mode="high_compression", compression=9, store_size=False
        )
        # Opaque 32-byte prefix is preserved, not represented as a verified hash.
        padding = self.padding if unchanged else b"\0" * (-(32 + len(packed)) % 16)
        payload = self.prefix + packed + padding
        header = struct.pack("<iiii", len(packed), 2, len(payload), len(plain))
        return struct.pack("<i", 2) + _xor(header, header_key(self.locale)) + _aes(payload, self.key, True) + self.tail

    def summary(self):
        values = [value.text for _, value in self.table.entries]
        patterns = {
            "brace": r"\{[^{}\n]{1,100}\}",
            "printf": r"%(?:\d+\$)?[-+#0]*\d*(?:\.\d+)?(?:hh|ll|[hlLzjt])?[diuoxXfFeEgGaAcspn%]",
            "angle_tag": r"</>|</?[A-Za-z][^>\n]{0,180}>",
            "square_token": r"\[[A-Za-z0-9_:/.-]{1,60}\]",
        }
        placeholders = {}
        for name, pattern in patterns.items():
            matches = Counter(match for value in values for match in re.findall(pattern, value))
            placeholders[name] = dict(values_with_match=sum(bool(re.search(pattern, value)) for value in values),
                                      occurrences=sum(matches.values()), common=matches.most_common(12))
        samples = []
        for key, value in self.table.entries:
            if 3 <= len(value.text) <= 65 and value.text.isascii() and re.search("[A-Za-z]", value.text):
                samples.append(dict(key=key.text[:90], value=value.text))
                if len(samples) == 8:
                    break
        return dict(locale=self.locale, namespace=self.table.namespace.text,
                    format="aes_lz4_v2" if self.key is not None else "legacy_xor",
                    entries=len(self.table.entries), value_characters=sum(map(len, values)),
                    key_characters=sum(len(k.text) for k, _ in self.table.entries),
                    utf16_values=sum(v.wide for _, v in self.table.entries),
                    plaintext_bytes=len(self.original_plaintext), packed_bytes=len(self.packed),
                    trailing_plaintext_bytes=len(self.table.trailing),
                    values_with_actual_newlines=sum("\n" in v for v in values),
                    values_with_literal_backslash_n=sum("\\n" in v for v in values),
                    opaque_prefix_bytes=len(self.prefix), opaque_prefix_semantics_verified=False,
                    placeholders=placeholders, samples=samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dat", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--locale", default="en-US")
    parser.add_argument("--entries-json", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--roundtrip-output", type=Path)
    args = parser.parse_args()
    data, manifest = args.dat.read_bytes(), args.manifest.read_bytes()
    doc = L10NDocument.decode(data, args.locale, manifest)
    plaintext = doc.table.write()
    encoded = doc.encode()
    summary = doc.summary()
    summary.update(source_dat_bytes=len(data), manifest_entries=len(read_manifest(manifest)),
                   manifest_records=(len(manifest) - 8) // 48,
                   plaintext_roundtrip_exact=plaintext == doc.original_plaintext,
                   container_roundtrip_exact=encoded == data,
                   source_sha256=hashlib.sha256(data).hexdigest(),
                   roundtrip_sha256=hashlib.sha256(encoded).hexdigest())
    if not summary["plaintext_roundtrip_exact"] or not summary["container_roundtrip_exact"]:
        raise AssertionError("No-edit byte-exact roundtrip verification failed")
    # Also exercise actual changed Unicode FString + LZ4 + AES serialization.
    pilot_key, pilot_value = doc.table.entries[0]
    probe = doc.table.translated({pilot_key.text: pilot_value.text + " Türkçe ğüşİöç"})
    probe_dat = doc.encode(probe)
    probe_doc = L10NDocument.decode(probe_dat, args.locale, manifest)
    summary["unicode_edit_encode_decode_roundtrip"] = probe_doc.table.as_dict()[pilot_key.text] == pilot_value.text + " Türkçe ğüşİöç"
    if not summary["unicode_edit_encode_decode_roundtrip"]:
        raise AssertionError("Unicode edited roundtrip failed")
    if args.entries_json:
        args.entries_json.write_text(json.dumps(doc.table.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    if args.summary_json:
        args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.roundtrip_output:
        args.roundtrip_output.write_bytes(encoded)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
