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
