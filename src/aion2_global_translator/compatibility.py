"""Probe actual source archives without writing to the game installation.

This module establishes content/codec compatibility, not Steam authenticity or
game acceptance of an edited container. Callers must apply their original-file
ownership/pin policy and recheck the observed profile before installation.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

_CACHE_SCHEMA = 1
_LOCALE_MEMBER = "AION2/Content/L10N/Text/en-US/L10NString.dat"
_MANIFEST_MEMBER = "Aion2/Content/StartUpData/Table/key_manifest.dat"
_COMPANIONS = (".sig", ".ucas", ".utoc")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot(path: Path) -> dict:
    before = path.stat()
    if not path.is_file():
        raise ValueError("Source is not a regular file: " + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    signature = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if signature(before) != signature(after):
        raise ValueError("Source archive changed while hashing: " + str(path))
    return {"sha256": digest.hexdigest(), "signature": signature(after)}


def _unchanged(snapshots: dict[Path, dict | None]) -> None:
    for path, previous in snapshots.items():
        current = _snapshot(path) if path.exists() else None
        if current != previous:
            raise ValueError("Source files changed during compatibility probing: " + str(path))


def _document(data: bytes, manifest: bytes):
    from .codec import L10NDocument
    try:
        doc = L10NDocument.decode(data, "en-US", manifest)
        values = doc.table.as_dict()  # Reject duplicate keys before JSON loses them.
        if not values or doc.table.namespace.text != "AION2" or doc.encode() != data:
            raise ValueError("Source namespace, entry count or byte roundtrip is invalid")
        return doc
    except (ValueError, TypeError, UnicodeError, OverflowError) as error:
        raise ValueError("Source codec compatibility verification failed") from error


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _cached(cache: Path, expected: dict):
    try:
        meta = json.loads((cache / "fingerprint.json").read_text("utf-8"))
        if meta.get("schema") != _CACHE_SCHEMA or meta.get("archives") != expected:
            return None
        data = (cache / "L10NString.dat").read_bytes()
        manifest = (cache / "key_manifest.dat").read_bytes()
        if meta.get("dat_sha256") != _digest(data) or meta.get("manifest_sha256") != _digest(manifest):
            return None
        doc = _document(data, manifest)
        if meta.get("entries") != len(doc.table.entries) or meta.get("namespace") != doc.table.namespace.text:
            return None
        return data, manifest, doc
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _member(destination: Path, expected: str) -> bytes:
    base = destination.resolve()
    files = []
    for entry in destination.rglob("*"):
        if entry.is_symlink() or not entry.resolve().is_relative_to(base):
            raise ValueError("repak produced a link or a path outside its private scratch directory")
        if entry.is_file():
            files.append(entry)
    if len(files) != 1 or files[0].relative_to(destination).as_posix().casefold() != expected.casefold():
        raise ValueError("repak did not produce exactly the requested source member")
    return files[0].read_bytes()


def _extract(repak: Path, archive: Path, destination: Path, member: str, aes: str) -> bytes:
    destination.mkdir()
    command = [str(repak), "--aes-key", aes, "unpack", str(archive),
               "-o", str(destination.resolve()), "--include", member]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("repak source extraction could not complete") from error
    if result.returncode:
        raise RuntimeError("repak source extraction failed: " + result.stderr[-1000:])
    return _member(destination, member)


def probe_source(game: Path, sourcepak: Path, repak: Path, data: Path, build: str) -> dict:
    """Return ``{profile, doc, manifest}`` for the observed original archives.

    Missing companions are omitted from ``profile['companions']``. Their
    recovery/required-presence policy belongs to the installation transaction;
    this probe never borrows old side files or modifies an original archive.
    """
    from .service import MARKER, PAK_AES  # Lazy to avoid a service import cycle.

    if not isinstance(build, str) or not re.fullmatch(r"[0-9]{1,32}", build):
        raise ValueError("Invalid Steam build identifier")
    game, sourcepak = Path(game).resolve(strict=True), Path(sourcepak).resolve(strict=True)
    data, repak = Path(data).resolve(), Path(repak).resolve()
    if data.is_relative_to(game):
        raise ValueError("Compatibility cache must be outside the game installation")
    if sourcepak.suffix.lower() != ".pak" or not sourcepak.is_file():
        raise ValueError("An original locale PAK is required")
    with sourcepak.open("rb") as stream:
        if stream.read(len(MARKER)) == MARKER:
            raise ValueError("The loose-translation marker is not an original source PAK")
    startup = game / "Aion2/Content/Paks/pakchunk0-Windows.pak"
    snapshots = {sourcepak: _snapshot(sourcepak), startup: _snapshot(startup)}
    companions = {}
    for extension in _COMPANIONS:
        path = sourcepak.with_suffix(extension)
        snapshot = _snapshot(path) if path.exists() else None
        snapshots[path] = snapshot
        if snapshot is not None:
            companions[extension] = snapshot["sha256"]
    observed = {"build": build, "pak_sha256": snapshots[sourcepak]["sha256"],
                "startup_pak_sha256": snapshots[startup]["sha256"], "companions": companions}
    fingerprint = _digest(json.dumps(observed, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    parent = data / "source-probes" / build
    cache = parent / fingerprint
    if not cache.resolve().is_relative_to(data):
        raise ValueError("Compatibility cache path leaves its private data directory")
    loaded = _cached(cache, observed)
    if loaded is None:
        if not repak.is_file():
            raise FileNotFoundError("repak.exe is required to probe uncached source archives")
        parent.mkdir(parents=True, exist_ok=True)
        scratch = parent / (".probe-" + uuid.uuid4().hex)
        scratch.mkdir()
        try:
            original = _extract(repak, sourcepak, scratch / "locale", _LOCALE_MEMBER, PAK_AES)
            manifest = _extract(repak, startup, scratch / "startup", _MANIFEST_MEMBER, PAK_AES)
            doc = _document(original, manifest)
            _unchanged(snapshots)
            # Metadata is committed last; interrupted/mixed caches fail their
            # content hashes and are rebuilt, never silently used as a source.
            cache.mkdir(exist_ok=True)
            _atomic(cache / "L10NString.dat", original)
            _atomic(cache / "key_manifest.dat", manifest)
            _atomic(cache / "fingerprint.json", json.dumps({
                "schema": _CACHE_SCHEMA, "archives": observed,
                "dat_sha256": _digest(original), "manifest_sha256": _digest(manifest),
                "entries": len(doc.table.entries), "namespace": doc.table.namespace.text,
            }, sort_keys=True).encode("utf-8"))
            loaded = _cached(cache, observed)
            if loaded is None:
                raise ValueError("Saved source compatibility cache failed verification")
        finally:
            # The only recursive removal is this freshly created private UUID
            # directory; never use a game path or an unchecked resolved target.
            if scratch.resolve().parent != parent.resolve() or scratch.is_symlink():
                raise ValueError("Private scratch cleanup path changed")
            shutil.rmtree(scratch)
    else:
        _unchanged(snapshots)
    original, manifest, doc = loaded
    profile = dict(observed, dat_sha256=_digest(original), manifest_sha256=_digest(manifest),
                   entries=len(doc.table.entries), namespace=doc.table.namespace.text)
    return {"profile": profile, "doc": doc, "manifest": manifest}
