"""Recover only checksum-verified leftovers of our pre-update installation.

Updated original PAK/signature bytes are never replaced with an older backup.
Every removed loose/side file is copied to a private recovery directory first.
"""
from pathlib import Path
import json
import uuid

OLD_BUILD = "25926599"
OLD_PAK_SHA = "07d61d63c131ce86a5674be28e14d9d93a11631a8704eb9c85e310123f11088c"
# Compared with file content hashes in the locally installed current Steam depot.
CURRENT_FILES = {
    ".pak": "4565d9d817f6ca8a7a11bbd0d25d0d91c6306c234be5f279ecfb33d5fba47080",
    ".sig": "13cbc2d9e4282de7b8c0917dd80c7822ae31aa2f869dcc8bd513fd0d1ee1381d",
    ".ucas": "c8e7146240adc7718e7e7d0b65468a8c71f4c7dd1f8a96e60d9a8daddc30be4f",
    ".utoc": "588dd500e88bd7cc6170831e78c3409c275018ae13a9c1a8fc21633e43612c7e",
}

# These are the already verified empty IoStore companions, not arbitrary old
# content. A changed/new nonempty container must come from Steam itself.
EMPTY_COMPANIONS = {ext: CURRENT_FILES[ext] for ext in (".ucas", ".utoc")}


def find_previous_install(pakdir, loose, backup):
    """Find exactly one fully owned old installation; never guess by date."""
    from .service import PAK, EXTENSIONS, sha
    pakdir, loose, backup = Path(pakdir), Path(loose), Path(backup)
    if not loose.is_file():
        raise ValueError("Previous loose translation is missing; restore with its original installer")
    matches = []
    for old in backup.parent.iterdir() if backup.parent.is_dir() else ():
        if not old.is_dir() or not old.name.isdecimal() or old == backup:
            continue
        try:
            meta = json.loads((old / "backup.json").read_text("utf-8"))
            state = json.loads((old / "state.json").read_text("utf-8"))
            names = {PAK + ext for ext in EXTENSIONS} | {"original-loose.dat"}
            if (meta.get("steam_build") != old.name or state.get("steam_build") != old.name
                    or set(meta.get("files", {})) != names or meta["files"]["original-loose.dat"] is not None
                    or sha(loose.read_bytes()) != state.get("dat_sha256")):
                continue
            for name, digest in meta["files"].items():
                if digest is not None and sha((old / name).read_bytes()) != digest:
                    raise ValueError("Old backup checksum mismatch")
            for ext in EXTENSIONS[1:]:
                side = pakdir / (PAK + ext + ".codex-original")
                if not side.is_file() or sha(side.read_bytes()) != meta["files"][PAK + ext]:
                    raise ValueError("Old companion checksum mismatch")
            matches.append((old, meta, state))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    groups = {json.dumps(item[1]["files"], sort_keys=True) + item[2]["dat_sha256"] for item in matches}
    if len(groups) != 1:
        raise ValueError("Unverified or ambiguous pre-update files remain; restore with their original installer")
    # Build-only updates can legitimately leave several byte-identical owned
    # generations. Their content, rather than timestamps, proves equivalence.
    return max(matches, key=lambda item: int(item[0].name))


def recover_update(pakdir, loose, backup, closed, profile):
    """Archive owned leftovers while retaining the CURRENT original archives."""
    from .service import PAK, EXTENSIONS, MARKER, sha, atomic, json_write
    pakdir, loose, backup = Path(pakdir), Path(loose), Path(backup)
    sides = {ext: pakdir / (PAK + ext + ".codex-original") for ext in EXTENSIONS[1:]}
    if not loose.exists() and not any(p.exists() for p in sides.values()):
        return False
    if (backup / "state.json").exists():
        return False
    old, meta, state = find_previous_install(pakdir, loose, backup)
    snapshots = {loose: loose.read_bytes(), **{p: p.read_bytes() for p in sides.values()}}
    replacements = {}
    for ext in EXTENSIONS:
        current = pakdir / (PAK + ext)
        before = current.read_bytes() if current.exists() else None
        snapshots[current] = before
        expected = profile["pak_sha256"] if ext == ".pak" else profile.get("companions", {}).get(ext)
        if ext == ".pak" and before == MARKER:
            original = (old / (PAK + ext)).read_bytes()
            if sha(original) != expected:
                raise ValueError("Current original source differs from the owned previous archive")
            replacements[current] = original
        elif before is None:
            original = (old / (PAK + ext)).read_bytes()
            permitted = EMPTY_COMPANIONS.get(ext)
            if ext == ".sig" and snapshots[pakdir / (PAK + ".pak")] == MARKER:
                permitted = meta["files"][PAK + ext]
            if permitted is None or sha(original) != permitted or (expected is not None and expected != permitted):
                raise ValueError("Current original companion is missing or unverified; verify game files in Steam")
            replacements[current] = original
        elif expected is not None and sha(before) != expected:
            raise ValueError("Current game files changed after source verification")
    recovery = backup.parent / ("recovered-" + old.name + "-to-" + profile["build"] + "-" + uuid.uuid4().hex)
    recovery.mkdir(parents=True)
    for path, content in snapshots.items():
        if content is not None:
            atomic(recovery / ("loose-before-update.dat" if path == loose else path.name), content)
    json_write(recovery / "recovery.json", {"old_build": old.name, "current_build": profile["build"],
        "preserved": {str(p): sha(data) if data is not None else None for p, data in snapshots.items()}})
    closed()
    if any((p.read_bytes() if p.exists() else None) != before for p, before in snapshots.items()):
        raise ValueError("Game files changed during update recovery preparation")
    try:
        for path, data in replacements.items():
            atomic(path, data)
        loose.unlink()
        for side in sides.values():
            side.unlink()
    except Exception:
        for path, before in snapshots.items():
            if before is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, before)
        raise
    return True


def recover_known_update(pakdir, loose, backup, closed):
    from .service import PAK, BUILD, EXTENSIONS, sha, atomic, json_write
    pakdir, loose, backup = Path(pakdir), Path(loose), Path(backup)
    sides = {ext: pakdir / (PAK + ext + ".codex-original") for ext in EXTENSIONS[1:]}
    if not loose.exists() and not any(p.exists() for p in sides.values()):
        return False
    # A normal currently installed pack must use the ordinary transaction path.
    if (backup / "state.json").exists():
        return False
    old = backup.parent / OLD_BUILD
    try:
        meta = json.loads((old / "backup.json").read_text("utf-8"))
        state = json.loads((old / "state.json").read_text("utf-8"))
        names = {PAK + ext for ext in EXTENSIONS} | {"original-loose.dat"}
        if meta.get("steam_build") != OLD_BUILD or set(meta.get("files", {})) != names:
            raise ValueError("Unrecognized pre-update backup")
        if state.get("steam_build") != OLD_BUILD or meta["files"][PAK + ".pak"] != OLD_PAK_SHA:
            raise ValueError("Unrecognized pre-update installation")
        for name, digest in meta["files"].items():
            if digest is not None and sha((old / name).read_bytes()) != digest:
                raise ValueError("Pre-update backup checksum mismatch")
        if not loose.is_file() or sha(loose.read_bytes()) != state["dat_sha256"]:
            raise ValueError("Pre-update loose translation was changed")
        for ext, side in sides.items():
            if not side.is_file() or sha(side.read_bytes()) != meta["files"][PAK + ext]:
                raise ValueError("Pre-update companion was changed")
    except (OSError, KeyError, TypeError) as exc:
        raise ValueError("Unverified files from an older patch remain; restore with its original installer") from exc
    snapshots = {loose: loose.read_bytes()}
    snapshots.update({p: p.read_bytes() for p in sides.values()})
    for ext, expected in CURRENT_FILES.items():
        current = pakdir / (PAK + ext)
        snapshots[current] = current.read_bytes() if current.exists() else None
        content = snapshots[current]
        if content is None:
            # Only unchanged empty-container companions may be recovered.
            if ext not in (".ucas", ".utoc") or sha(snapshots[sides[ext]]) != expected:
                raise ValueError("Current original companion is missing or unverified")
        elif sha(content) != expected:
            raise ValueError("Current original files do not match the verified updated build")
    recovery = backup.parent / ("recovered-" + OLD_BUILD + "-to-" + BUILD + "-" + uuid.uuid4().hex)
    recovery.mkdir(parents=True)
    for path, content in snapshots.items():
        if content is not None:
            atomic(recovery / ("loose-before-update.dat" if path == loose else path.name), content)
    json_write(recovery / "recovery.json", {"old_build": OLD_BUILD, "current_build": BUILD,
        "preserved": {str(p): sha(data) if data is not None else None for p, data in snapshots.items()}})
    closed()
    if any((p.read_bytes() if p.exists() else None) != before for p, before in snapshots.items()):
        raise ValueError("Game files changed during update recovery preparation")
    try:
        for ext in (".ucas", ".utoc"):
            current = pakdir / (PAK + ext)
            if snapshots[current] is None:
                atomic(current, snapshots[sides[ext]])
        loose.unlink()
        for side in sides.values():
            side.unlink()
    except Exception:
        for path, before in snapshots.items():
            if before is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, before)
        raise
    return True
