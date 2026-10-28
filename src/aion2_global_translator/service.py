# SPDX-License-Identifier: Apache-2.0
"""Portable, build-checked local translation and transactional installation.

Only explicitly selected game files are modified. Game content, generated
translations, provider credentials and backups stay in ignored private-data.
"""
from __future__ import annotations
from collections import Counter
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid

BUILD = "26262663"
PAK = "pakchunk502000-Windows_0_P"
ORIGINAL_SHA = "6c156d58d93cad782ef747b57b0eb2decf6e22e9e8bf5f29619cf350baa04ca3"
ORIGINAL_DAT_SHA = "932663700f42fd3180f973ea78d9ed3b76620ff04d5f032269a488ca0ddc5747"
# Public compatibility key for this build; never a provider credential.
PAK_AES = "06038EF544B6007614F8574F1B7C2A3F0D565F74CDCC1B366B4EA1A17B97CBFF"
MARKER = b"AION2_LOOSE"
EXTENSIONS = (".pak", ".sig", ".ucas", ".utoc")
DISPLAY_ENTRY_COUNT = 153297


def _turkish_language(language):
    return isinstance(language, str) and language.lower().replace("_", "-").split("-")[0] == "tr"


def _legacy_structure_and_abbreviations(source, translated):
    """Check legacy formatting while diagnosing translated HP/MP/etc. labels.

    Only recognized standalone abbreviation tokens become spaces. Runtime tags,
    macros, printf arguments, numbers and controls still pass the normal strict
    validator. Provider results never use this legacy compatibility path.
    """
    from .protection import GAME_ABBREVIATIONS, protected_parts, validate
    if source.strip() and not translated.strip():
        raise ValueError("The installed legacy translation is empty.")
    abbreviations = set(GAME_ABBREVIATIONS)
    def structure(text):
        pieces, last, observed = [], 0, Counter()
        for start, end, literal in protected_parts(text):
            pieces.append(text[last:start])
            if literal in abbreviations:
                observed[literal] += 1
                pieces.append(" " * (end - start))
            else:
                pieces.append(literal)
            last = end
        pieces.append(text[last:])
        return "".join(pieces), observed
    original, expected = structure(source)
    current, actual = structure(translated)
    validate(original, current)
    return None if expected == actual else {"source": dict(expected), "installed": dict(actual)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    path = Path(path)
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


def json_write(path, data):
    atomic(path, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))


def flat_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    value = json.loads(Path(path).read_text("utf-8-sig"), object_pairs_hook=unique)
    if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
        raise ValueError("Translation JSON must map every source key to a string")
    return value


def game_running():
    if sys.platform != "win32":
        raise RuntimeError("Installation requires Windows")
    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError("Cannot inspect running processes")
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(handle, ctypes.byref(entry))
        if not more and ctypes.get_last_error() != 18:
            raise OSError("Cannot enumerate processes")
        while more:
            if entry.szExeFile.lower() == "aion2.exe":
                return True
            more = kernel.Process32NextW(handle, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:
            raise OSError("Process enumeration failed")
        return False
    finally:
        kernel.CloseHandle(handle)


class TranslatorService:
    def __init__(self, on_event=None, data_dir=None, repak_path=None):
        self.root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
        self.data = Path(data_dir) if data_dir else self.root / "private-data"
        self.repak = Path(repak_path or os.environ.get("REPAK_PATH", self.root / "tools/repak.exe"))
        if not self.repak.exists() and getattr(sys, "frozen", False):
            self.repak = Path(sys._MEIPASS) / "tools/repak.exe"
        self.on_event = on_event or (lambda event: None)
        self._profile = None
        self._probed = None
        self._verified_pending_marker = False

    @property
    def build(self):
        return self._profile["build"] if self._profile else BUILD

    @property
    def original_sha(self):
        return self._profile["pak_sha256"] if self._profile else ORIGINAL_SHA

    @property
    def original_dat_sha(self):
        return self._profile["dat_sha256"] if self._profile else ORIGINAL_DAT_SHA

    @property
    def entry_count(self):
        return self._profile["entries"] if self._profile else DISPLAY_ENTRY_COUNT

    def emit(self, message, progress=None):
        self.on_event(dict(message=message, progress=progress, level="info"))

    def automatic_settings(self):
        path = self.data / "settings/automatic.json"
        try:
            value = json.loads(path.read_text("utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def set_automatic(self, enabled):
        settings = self.automatic_settings()
        settings["enabled"] = bool(enabled)
        json_write(self.data / "settings/automatic.json", settings)

    def automatic_update(self, game_dir):
        settings = self.automatic_settings()
        if not settings.get("enabled") or not settings.get("language") or settings.get("game_dir") != str(Path(game_dir).resolve()):
            return dict(status="unchanged")
        if game_running():
            return dict(status="waiting_game", message="Close AION 2; automatic repair will continue while this app remains open.")
        info = self.inspect(game_dir)
        if info["status"] == "installed" and info.get("installed_language") == settings["language"]:
            return dict(status="unchanged")
        return self.apply_language(game_dir, settings["language"])

    def detect_game(self):
        roots = []
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                roots.append(Path(winreg.QueryValueEx(key, "SteamPath")[0]))
        except (ImportError, OSError):
            pass
        roots.append(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam")
        for steam in list(roots):
            library = steam / "steamapps/libraryfolders.vdf"
            if library.is_file():
                for match in re.finditer(r'"path"\s+"([^"\r\n]+)"', library.read_text("utf-8")):
                    roots.append(Path(match.group(1).replace("\\\\", "\\")))
        for root in roots:
            game = root / "steamapps/common/AION2"
            if (game / "Aion2/Binaries/Win64/AION2.exe").is_file():
                return str(game)
        return None

    def paths(self, game_dir):
        game = Path(game_dir).resolve(strict=True)
        if not (game / "Aion2/Binaries/Win64/AION2.exe").is_file():
            raise ValueError("Select the AION2 Steam game folder")
        manifest = game.parents[1] / "appmanifest_3393110.acf"
        match = re.search(r'"buildid"\s+"(\d+)"', manifest.read_text("utf-8"))
        if not match:
            raise ValueError("Steam build could not be read; nothing was changed")
        build = match.group(1)
        content = game / "Aion2/Content"
        backup = self.data / "backups" / sha(str(game).casefold().encode())[:16] / build
        pakdir, loose = content / "Paks/L10N/Text/en-US", content / "L10N/Text/en-US/L10NString.dat"
        self._verified_pending_marker = False
        if build == BUILD:
            self._profile = None
            self._probed = None
        else:
            from .compatibility import probe_source
            sourcepak = pakdir / (PAK + ".pak")
            if sourcepak.is_file() and sourcepak.read_bytes() == MARKER:
                if (backup / "state.json").is_file():
                    # Same-build installation: verify its own recorded original.
                    meta = json.loads((backup / "backup.json").read_text("utf-8"))
                    sourcepak = backup / (PAK + ".pak")
                    if meta.get("steam_build") != build or sha(sourcepak.read_bytes()) != meta.get("files", {}).get(PAK + ".pak"):
                        raise ValueError("Original backup is invalid")
                else:
                    from .update_recovery import find_previous_install
                    old, _, _ = find_previous_install(pakdir, loose, backup)
                    sourcepak = old / (PAK + ".pak")
                    self._verified_pending_marker = True
            self.emit("Checking updated localization format and source fingerprints", 2)
            probe = probe_source(game, sourcepak, self.repak, self.data, build)
            self._profile, self._probed = probe["profile"], probe
        return game, pakdir, loose, backup

    def _backup(self, backup):
        meta = json.loads((backup / "backup.json").read_text("utf-8"))
        names = {PAK + ext for ext in EXTENSIONS} | {"original-loose.dat"}
        if meta.get("steam_build") != self.build or set(meta.get("files", {})) != names:
            raise ValueError("Backup manifest is invalid")
        for name, digest in meta["files"].items():
            if digest is not None and sha((backup / name).read_bytes()) != digest:
                raise ValueError("Backup checksum mismatch: " + name)
        if meta["files"][PAK + ".pak"] != self.original_sha:
            raise ValueError("Unknown original PAK")
        return meta

    def _state(self, pakdir, loose, backup):
        path = backup / "state.json"
        if not path.exists():
            return None
        state = json.loads(path.read_text("utf-8"))
        self._backup(backup)
        if state.get("steam_build") != self.build or (pakdir / (PAK + ".pak")).read_bytes() != MARKER:
            raise ValueError("Game packages changed since installation")
        if not loose.is_file() or sha(loose.read_bytes()) != state["dat_sha256"]:
            raise ValueError("Installed translation changed since installation")
        meta = self._backup(backup)
        for ext in EXTENSIONS[1:]:
            side = pakdir / (PAK + ext + ".codex-original")
            if (pakdir / (PAK + ext)).exists() or not side.is_file() or sha(side.read_bytes()) != meta["files"][PAK + ext]:
                raise ValueError("Locale companion files changed")
        return state

    def inspect(self, game_dir):
        game, pakdir, loose, backup = self.paths(game_dir)
        state = self._state(pakdir, loose, backup)
        if state is None and not self._verified_pending_marker and sha((pakdir / (PAK + ".pak")).read_bytes()) != self.original_sha:
            raise ValueError("Unknown patch detected. Restore it with its original installer first")
        leftovers = state is None and (loose.exists() or any(pakdir.glob("*.codex-original")))
        return dict(game_dir=str(game), build=self.build, status="update_pending" if leftovers else "installed" if state else "original",
                    installed_language=state["target_language"] if state else None,
                    entries=state["entries"] if state else self.entry_count,
                    message="Verified native translation" if state else "Verified original English game")

    def _closed(self):
        if game_running():
            raise RuntimeError("Close AION 2 before installing or restoring; restart it afterwards")

    def _closed_build(self, game):
        self._closed()
        text = (Path(game).parents[1] / "appmanifest_3393110.acf").read_text("utf-8")
        current = re.search(r'"buildid"\s+"(\d+)"', text)
        if current is None or current.group(1) != self.build:
            raise ValueError("Steam build changed during preparation; nothing was installed")
        if self._profile and self._profile.get("startup_pak_sha256"):
            startup = Path(game) / "Aion2/Content/Paks/pakchunk0-Windows.pak"
            if sha(startup.read_bytes()) != self._profile["startup_pak_sha256"]:
                raise ValueError("Startup source changed during preparation; nothing was installed")

    def install_turkish(self, game_dir):
        stage = self.data / "stages/tr"
        if not (stage / "patch-meta.json").is_file():
            raise ValueError("No local Turkish pack is ready. Use Build Translation to generate one from your game or import a complete translation map first.")
        return self.install_stage(game_dir, stage)

    def apply_language(self, game_dir, target_language):
        """Apply the selected private pack, or restore the English source."""
        from .multilingual import normalize_language
        code = normalize_language(target_language)
        self._closed()
        if code.split('-')[0] == 'en':
            state = self.inspect(game_dir)
            return self.restore(game_dir) if state['status'] == 'installed' else state
        stage = self.data / 'stages' / code
        meta = json.loads((stage / 'patch-meta.json').read_text('utf-8'))
        if normalize_language(meta.get('target_language', '')) != code:
            raise ValueError('Prepared pack language does not match the selected target')
        self.paths(game_dir)
        if meta.get("steam_build") != self.build or meta.get("original_pak_sha256") != self.original_sha:
            self.migrate_translation(game_dir, code)
        return self.install_stage(game_dir, stage)

    def install_stage(self, game_dir, stage):
        self._closed()
        game, pakdir, loose, backup = self.paths(game_dir)
        stage = Path(stage)
        meta = json.loads((stage / "patch-meta.json").read_text("utf-8"))
        dat = (stage / "L10NString.dat").read_bytes()
        if meta.get("steam_build") != self.build:
            raise ValueError("Language pack build mismatch. Found " + str(meta.get("steam_build", "unknown"))
                             + "; expected " + self.build + ". Rebuild the language pack for the current game; nothing was changed")
        if (meta.get("steam_build") != self.build or meta.get("original_pak_sha256") != self.original_sha
                or meta.get("quality_gate_passed") is not True or meta.get("remaining_untranslated_candidate_entries") != 0
                or meta.get("source_entry_count") != self.entry_count or sha(dat) != meta.get("dat_sha256")):
            raise ValueError("Translation package failed compatibility or coverage checks")
        from .update_recovery import recover_update, EMPTY_COMPANIONS
        for ext, expected in EMPTY_COMPANIONS.items():
            container = pakdir / (PAK + ext)
            if not container.exists():
                container = pakdir / (PAK + ext + ".codex-original")
            if not container.is_file() or sha(container.read_bytes()) != expected:
                raise ValueError("Unrecognized/nonempty locale container; automatic installation is unavailable for this format")
        self._validate_stage(game, dat, meta)
        profile = self._profile or dict(build=self.build, pak_sha256=self.original_sha,
            companions={".sig": "0c33b72da6c6e3e5e335f76f4cb950d6ef473322fdfb2d0bd1a78e64b0b23546", **EMPTY_COMPANIONS})
        recover_update(pakdir, loose, backup, lambda: self._closed_build(game), profile)
        state = self._state(pakdir, loose, backup)
        snapshots = {pakdir / (PAK + ext): (pakdir / (PAK + ext)).read_bytes() if (pakdir / (PAK + ext)).exists() else None for ext in EXTENSIONS}
        snapshots[loose] = loose.read_bytes() if loose.exists() else None
        for ext in EXTENSIONS[1:]:
            p = pakdir / (PAK + ext + ".codex-original")
            snapshots[p] = p.read_bytes() if p.exists() else None
        statepath = backup / "state.json"
        previous_state = statepath.read_bytes() if statepath.exists() else None
        if state is None:
            if sha(snapshots[pakdir / (PAK + ".pak")]) != self.original_sha or snapshots[loose] is not None:
                raise ValueError("Expected original English files and no loose translation")
            if any(snapshots[pakdir / (PAK + ext + ".codex-original")] is not None for ext in EXTENSIONS[1:]):
                raise ValueError("Existing companion backup belongs to another installer")
            if any(snapshots[pakdir / (PAK + ext)] is None for ext in EXTENSIONS):
                raise ValueError("Original locale companion is missing")
            backup.mkdir(parents=True, exist_ok=True)
            records = {}
            for ext in EXTENSIONS:
                name = PAK + ext
                data = snapshots[pakdir / name]
                atomic(backup / name, data)
                records[name] = sha(data)
            records["original-loose.dat"] = None
            json_write(backup / "backup.json", dict(steam_build=self.build, files=records))
            self._backup(backup)
        self.emit("Installing native text file", 95)
        # Rejection before the first mutation must never trigger rollback over
        # the external edit that caused the rejection.
        self._closed_build(game)
        if any((p.read_bytes() if p.exists() else None) != before for p, before in snapshots.items()):
            raise ValueError("Game files changed during preparation")
        if (statepath.read_bytes() if statepath.exists() else None) != previous_state:
            raise ValueError("Installed state changed during preparation")
        try:
            if state is None:
                for ext in EXTENSIONS[1:]:
                    os.replace(pakdir / (PAK + ext), pakdir / (PAK + ext + ".codex-original"))
                atomic(pakdir / (PAK + ".pak"), MARKER)
            atomic(loose, dat)
            language = meta.get("target_language", "tr")
            json_write(statepath, dict(steam_build=self.build, dat_sha256=sha(dat), target_language=language, entries=self.entry_count))
            self._state(pakdir, loose, backup)
        except Exception:
            for path, data in snapshots.items():
                if data is None:
                    path.unlink(missing_ok=True)
                elif not path.exists() or path.read_bytes() != data:
                    atomic(path, data)
            if previous_state is None:
                statepath.unlink(missing_ok=True)
            else:
                atomic(statepath, previous_state)
            raise
        self.emit("Installed. Restart AION 2 to load the new text.", 100)
        settings = self.automatic_settings()
        json_write(self.data / "settings/automatic.json", dict(settings,
            enabled=settings.get("enabled", True), game_dir=str(game), language=language))
        return self.inspect(game)

    def _validate_stage(self, game, data, meta):
        """Validate the actual DAT, independent of self-reported quality flags."""
        from .codec import L10NDocument
        from .protection import validate
        original, manifest = self._extract(game)
        if (meta.get("steam_build") != self.build or meta.get("original_pak_sha256") != self.original_sha
                or (meta.get("original_dat_sha256") and meta["original_dat_sha256"] != self.original_dat_sha)):
            raise ValueError("Language pack source changed during validation; nothing was installed")
        decoded = L10NDocument.decode(data, "en-US", manifest)
        source, values = original.table.as_dict(), decoded.table.as_dict()
        if (decoded.table.namespace.text != original.table.namespace.text
                or len(decoded.table.entries) != len(original.table.entries)
                or [k.text for k, _ in decoded.table.entries] != [k.text for k, _ in original.table.entries]
                or decoded.table.version != original.table.version or decoded.encode() != data
                or decoded.prefix != original.prefix or decoded.tail != original.tail
                or decoded.table.trailing != original.table.trailing):
            raise ValueError("Language DAT namespace, key order, version or codec verification failed")
        for key, value in values.items():
            try:
                validate(source[key], value)
            except ValueError:
                # Earlier local Turkish packs used translated HP/MP labels.
                # Their tags, placeholders, numbers and controls still must
                # independently match the current original source exactly.
                if not _turkish_language(meta.get("target_language")):
                    raise
                _legacy_structure_and_abbreviations(source[key], value)
        return decoded

    def restore(self, game_dir):
        self._closed()
        game, pakdir, loose, backup = self.paths(game_dir)
        if self._state(pakdir, loose, backup) is None:
            raise ValueError("No verified translation to restore")
        meta = self._backup(backup)
        paths = {name: loose if name == "original-loose.dat" else pakdir / name for name in meta["files"]}
        paths.update({PAK + ext + ".codex-original": pakdir / (PAK + ext + ".codex-original") for ext in EXTENSIONS[1:]})
        before = {p: p.read_bytes() if p.exists() else None for p in paths.values()}
        statepath = backup / "state.json"
        previous = statepath.read_bytes()
        self._closed()
        if any((p.read_bytes() if p.exists() else None) != data for p, data in before.items()):
            raise ValueError("Game files changed during preparation")
        if statepath.read_bytes() != previous:
            raise ValueError("Installed state changed during preparation")
        try:
            for name, digest in meta["files"].items():
                path = paths[name]
                if digest is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, (backup / name).read_bytes())
            for ext in EXTENSIONS[1:]:
                (pakdir / (PAK + ext + ".codex-original")).unlink()
            statepath.unlink()
            self.inspect(game)
        except Exception:
            for path, data in before.items():
                if data is None:
                    path.unlink(missing_ok=True)
                elif not path.exists() or path.read_bytes() != data:
                    atomic(path, data)
            atomic(statepath, previous)
            raise
        self.emit("Original English files restored", 100)
        self.set_automatic(False)
        return self.inspect(game)

    def _extract(self, game_dir):
        from .codec import L10NDocument
        game, pakdir, loose, backup = self.paths(game_dir)
        state = self._state(pakdir, loose, backup)
        sourcepak = backup / (PAK + ".pak") if state else pakdir / (PAK + ".pak")
        if self._probed is not None:
            return self._probed["doc"], self._probed["manifest"]
        if sha(sourcepak.read_bytes()) != self.original_sha:
            raise ValueError("Unknown source PAK")
        if not self.repak.is_file():
            raise FileNotFoundError("repak.exe 0.2.3 is required in tools/ or REPAK_PATH; see README")
        extracted = self.data / "source" / self.build
        datpath = extracted / "locale/Aion2/Content/L10N/Text/en-US/L10NString.dat"
        manifestpath = extracted / "startup/Aion2/Content/StartUpData/Table/key_manifest.dat"
        for source, destination, wanted in [(sourcepak, extracted / "locale", datpath),
                (game / "Aion2/Content/Paks/pakchunk0-Windows.pak", extracted / "startup", manifestpath)]:
            if wanted.exists():
                continue
            destination.mkdir(parents=True, exist_ok=True)
            args = [str(self.repak), "--aes-key", PAK_AES, "unpack", str(source), "-o", str(destination.resolve())]
            if wanted == manifestpath:
                args += ["--include", "Aion2/Content/StartUpData/Table/key_manifest.dat"]
            result = subprocess.run(args, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode or not wanted.is_file():
                raise RuntimeError("repak extraction failed: " + result.stderr[-1000:])
        data, manifest = datpath.read_bytes(), manifestpath.read_bytes()
        if sha(data) != self.original_dat_sha:
            raise ValueError("English source DAT checksum mismatch; cached source must match the verified build")
        doc = L10NDocument.decode(data, "en-US", manifest)
        if len(doc.table.entries) != self.entry_count or doc.encode() != data or doc.table.namespace.text != "AION2":
            raise ValueError("Source codec verification failed")
        return doc, manifest

    def repair_turkish_headings(self, game_dir):
        """Prepare a reversible heading-only repair, then use normal installation."""
        from .codec import L10NDocument
        from .display import apply_turkish_heading_compatibility
        from .protection import validate
        from .terminology import apply_turkish_context_terms
        self._closed()
        game, pakdir, loose, backup = self.paths(game_dir)
        state = self._state(pakdir, loose, backup)
        if state is None or not _turkish_language(state.get("target_language")):
            raise ValueError("A verified installed Turkish translation is required for heading repair")
        statepath = backup / "state.json"
        state_bytes = statepath.read_bytes()
        if json.loads(state_bytes.decode("utf-8")) != state:
            raise ValueError("Installed translation state changed during heading repair preparation")
        installed_dat = loose.read_bytes()
        if sha(installed_dat) != state.get("dat_sha256"):
            raise ValueError("Installed translation changed during heading repair preparation")
        self.emit("Reading the verified Turkish translation and original source", 5)
        original, manifest = self._extract(game)
        source = original.table.as_dict()
        installed = L10NDocument.decode(installed_dat, "en-US", manifest)
        current = installed.table.as_dict()
        if (len(source) != self.entry_count or len(original.table.entries) != self.entry_count
                or len(current) != self.entry_count or len(installed.table.entries) != self.entry_count
                or set(current) != set(source) or installed.table.namespace.text != "AION2"
                or original.table.namespace.text != "AION2"):
            raise ValueError("Installed Turkish translation does not match the complete original source key set")
        abbreviation_differences = {}
        for key in source:
            try:
                diagnostic = _legacy_structure_and_abbreviations(source[key], current[key])
            except ValueError as error:
                raise ValueError("Installed legacy translation has invalid structural literals: " + key) from error
            if diagnostic:
                abbreviation_differences[key] = diagnostic
        canonical, context_report = apply_turkish_context_terms(source, current)
        fixed_names = context_report["rule_keys"]["skill_snipe"]
        corrected, display_report = apply_turkish_heading_compatibility(canonical)
        affected = sorted(key for key in source if corrected[key] != current[key])
        for key in affected:
            validate(current[key], corrected[key])
        display_report = dict(display_report, canonical_skill_name_fixes=fixed_names,
                              changed_installed_entries=len(affected), context_terms_report=context_report,
                              legacy_abbreviation_difference_count=len(abbreviation_differences))
        if not affected:
            return dict(status="installed", target_language="tr", entries=len(source),
                        display_profile=display_report["profile"], display_report=display_report,
                        context_terms_report=context_report,
                        legacy_abbreviation_differences=abbreviation_differences,
                        message="Installed Turkish headings already use the compatible display profile.")
        dat = original.encode(original.table.translated(corrected))
        decoded = L10NDocument.decode(dat, "en-US", manifest)
        if (decoded.table.as_dict() != corrected or len(decoded.table.entries) != self.entry_count
                or decoded.table.namespace.text != "AION2"
                or [key.text for key, _ in decoded.table.entries] != [key.text for key, _ in original.table.entries]):
            raise ValueError("Heading repair failed exact dictionary/order verification")
        stages = self.data / "stages"
        prior = stages / "tr-before-font-fix"
        prior_meta = dict(steam_build=self.build, target_language="tr", source_entry_count=len(source),
                          dat_sha256=sha(installed_dat), original_pak_sha256=self.original_sha,
                          quality_gate_passed=True, remaining_untranslated_candidate_entries=0,
                          restore_point="before-turkish-heading-font-repair",
                          validation_scope="verified legacy translation, complete keys, original structural literals and codec decode; not a full semantic review",
                          human_reviewed=False, in_game_verified=False)
        if not prior.exists():
            stages.mkdir(parents=True, exist_ok=True)
            temporary = stages / (".tr-before-font-fix-" + uuid.uuid4().hex)
            temporary.mkdir()
            try:
                atomic(temporary / "L10NString.dat", installed_dat)
                json_write(temporary / "installed-state.json", state)
                json_write(temporary / "patch-meta.json", prior_meta)
                # Windows rename refuses to overwrite an existing directory.
                try:
                    temporary.rename(prior)
                except FileExistsError:
                    pass
            finally:
                if temporary.exists():
                    for name in ("L10NString.dat", "installed-state.json", "patch-meta.json"):
                        (temporary / name).unlink(missing_ok=True)
                    temporary.rmdir()
        saved_meta = json.loads((prior / "patch-meta.json").read_text("utf-8"))
        saved_dat = (prior / "L10NString.dat").read_bytes()
        if (saved_meta.get("steam_build") != self.build or saved_meta.get("original_pak_sha256") != self.original_sha
                or saved_meta.get("source_entry_count") != self.entry_count
                or saved_meta.get("target_language") != "tr" or saved_meta.get("dat_sha256") != sha(saved_dat)
                or saved_meta.get("quality_gate_passed") is not True
                or saved_meta.get("remaining_untranslated_candidate_entries") != 0):
            raise ValueError("Existing pre-repair pack is invalid; it was preserved without overwriting")
        saved = L10NDocument.decode(saved_dat, "en-US", manifest)
        if (len(saved.table.entries) != self.entry_count or set(saved.table.as_dict()) != set(source)
                or saved.table.namespace.text != "AION2"):
            raise ValueError("Existing pre-repair pack has a different key set; it was not overwritten")
        stage = stages / "tr-font-safe"
        meta = dict(steam_build=self.build, target_language="tr", source_entry_count=len(source),
                    dat_sha256=sha(dat), original_pak_sha256=self.original_sha, quality_gate_passed=True,
                    remaining_untranslated_candidate_entries=0, display_profile=display_report["profile"],
                    display_report=display_report, repaired_from_dat_sha256=sha(installed_dat),
                    context_terms_report=context_report,
                    legacy_abbreviation_difference_count=len(abbreviation_differences),
                    prior_stage=str(prior), human_reviewed=False, in_game_verified=False,
                    validation_scope="font display and exact context terminology repair of verified legacy translation; original structural literals, current protected literals and exact codec roundtrip; not a full semantic review")
        atomic(stage / "L10NString.dat", dat)
        json_write(stage / "display-report.json", display_report)
        json_write(stage / "context-terms-report.json", context_report)
        json_write(stage / "legacy-abbreviation-report.json", abbreviation_differences)
        json_write(stage / "patch-meta.json", meta)
        self._closed()
        if (self._state(pakdir, loose, backup) != state or loose.read_bytes() != installed_dat
                or statepath.read_bytes() != state_bytes):
            raise ValueError("Installed translation changed while preparing heading repair; nothing was installed")
        self.emit("Compatible Turkish heading pack prepared; installing through verified backups", 90)
        result = self.install_stage(game, stage)
        return dict(result, stage=str(stage), prior_stage=str(prior),
                    display_profile=display_report["profile"], display_report=display_report,
                    context_terms_report=context_report,
                    legacy_abbreviation_difference_count=len(abbreviation_differences),
                    message="Turkish heading repair installed. Restart the game to load it; the previous pack remains available for installation.")

    def _verified_legacy_reference(self, stage, target_lang, source_doc, manifest):
        """Read the existing same-language DAT as a bounded migration reference."""
        from .codec import L10NDocument
        from .multilingual import normalize_language
        try:
            meta_bytes = (stage / "patch-meta.json").read_bytes()
            meta = json.loads(meta_bytes.decode("utf-8"))
            data = (stage / "L10NString.dat").read_bytes()
            source = source_doc.table.as_dict()
            if (not isinstance(meta, dict) or meta.get("steam_build") != self.build
                    or meta.get("original_pak_sha256") != self.original_sha
                    or normalize_language(meta.get("target_language", "")) != target_lang
                    or meta.get("source_entry_count") != len(source)
                    or meta.get("quality_gate_passed") is not True
                    or meta.get("remaining_untranslated_candidate_entries") != 0
                    or meta.get("dat_sha256") != sha(data)):
                raise ValueError("Legacy reference pack metadata or checksum is invalid")
            decoded = L10NDocument.decode(data, "en-US", manifest)
            values = decoded.table.as_dict()
            if (len(decoded.table.entries) != len(source) or set(values) != set(source)
                    or decoded.table.namespace.text != source_doc.table.namespace.text
                    or [k.text for k, _ in decoded.table.entries] != [k.text for k, _ in source_doc.table.entries]
                    or decoded.encode() != data):
                raise ValueError("Legacy reference pack key set, namespace or codec verification failed")
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ValueError("Unchanged legacy Turkish cells require an existing verified same-language pack") from error
        return dict(stage=stage, values=values, dat=data, meta_bytes=meta_bytes,
                    dat_sha256=sha(data), meta_sha256=sha(meta_bytes))

    def _migration_reference(self, stage, language):
        """Recover source and translations together; a matching ID alone is insufficient."""
        from .codec import L10NDocument
        from .display import apply_turkish_heading_compatibility
        meta_bytes = (stage / "patch-meta.json").read_bytes()
        meta = json.loads(meta_bytes)
        data = (stage / "L10NString.dat").read_bytes()
        values = flat_json(stage / "entries.translated.json")
        if (meta.get("target_language") != language or meta.get("quality_gate_passed") is not True
                or meta.get("dat_sha256") != sha(data) or meta.get("remaining_untranslated_candidate_entries") != 0):
            raise ValueError("Previous pack metadata or checksum is invalid")
        old_build = str(meta.get("steam_build", ""))
        if not old_build.isdecimal():
            raise ValueError("Previous pack build is invalid")
        cached = self.data / "source" / old_build
        source_path = stage / "entries.source.json"
        if source_path.is_file():
            source_bytes = source_path.read_bytes()
            if sha(source_bytes) != meta.get("source_map_sha256"):
                raise ValueError("Previous source snapshot checksum mismatch")
            source = flat_json(source_path)
        else:
            # Compatibility with packs created before source snapshots existed.
            datpath = cached / "locale/Aion2/Content/L10N/Text/en-US/L10NString.dat"
            manifestpath = cached / "startup/Aion2/Content/StartUpData/Table/key_manifest.dat"
            original = datpath.read_bytes()
            expected = {"25926599": "694a7d39e6bbe27c85dafa127d3feaca2a4a7a3c502ccf7385078b9c74dc6a3f",
                        "26077854": "4beef8a90b37ece24ec34a4684949ff40fa1f79a61550c7dfef47c63b941bfd9",
                        BUILD: ORIGINAL_DAT_SHA}.get(old_build)
            if expected is None or sha(original) != expected:
                raise ValueError("Verified previous English source is required for automatic migration")
            source = L10NDocument.decode(original, "en-US", manifestpath.read_bytes()).table.as_dict()
        manifestpath = stage / "source-key-manifest.dat"
        if not manifestpath.is_file():
            manifestpath = cached / "startup/Aion2/Content/StartUpData/Table/key_manifest.dat"
        manifest = manifestpath.read_bytes()
        if meta.get("manifest_sha256") and sha(manifest) != meta["manifest_sha256"]:
            raise ValueError("Previous key manifest checksum mismatch")
        decoded = L10NDocument.decode(data, "en-US", manifest)
        displayed = values
        if _turkish_language(language) and (meta.get("font_compatible_titles") or meta.get("display_profile")):
            displayed, _ = apply_turkish_heading_compatibility(values)
        if (set(source) != set(values) or displayed != decoded.table.as_dict()
                or decoded.table.namespace.text != "AION2" or decoded.encode() != data
                or len(decoded.table.entries) != len(source)):
            raise ValueError("Previous editable map, source and native DAT disagree")
        for key in source:
            _legacy_structure_and_abbreviations(source[key], values[key])
        return source, values, meta, meta_bytes, data

    def migrate_translation(self, game_dir, target_language, corrections_path=None):
        """Rebuild against CURRENT English; never install stale or partial tables."""
        from .codec import L10NDocument
        from .migration import plan_migration, finish_migration
        from .multilingual import normalize_language, apply_target_context_terms
        from .protection import prepare, validate
        from .display import apply_turkish_heading_compatibility
        language = normalize_language(target_language)
        self.emit("Comparing updated English with the previous translation", 5)
        doc, manifest = self._extract(game_dir)
        source = doc.table.as_dict()
        stage = self.data / "stages" / language
        reference_files = {stage / name: (stage / name).read_bytes() if (stage / name).exists() else None
            for name in ("patch-meta.json", "L10NString.dat", "entries.translated.json", "entries.source.json", "source-key-manifest.dat")}
        prior_source, prior_values, prior_meta, prior_meta_bytes, prior_dat = self._migration_reference(stage, language)
        if any((path.read_bytes() if path.exists() else None) != data for path, data in reference_files.items()):
            raise ValueError("Previous pack changed while reading migration reference")
        plan = plan_migration(prior_source, prior_values, source)
        update = self.data / "updates" / self.build / language / self.original_dat_sha
        pending_path = update / "pending.json"
        json_write(pending_path, plan["pending"])
        corrections = {}
        correction_file = Path(corrections_path) if corrections_path else update / "corrections.json"
        if correction_file.is_file():
            corrections = flat_json(correction_file)
        elif plan["pending"]:
            settings_path = self.data / "settings" / (language + "-provider.json")
            settings = json.loads(settings_path.read_text("utf-8")) if settings_path.is_file() else {}
            if settings.get("provider") == "libretranslate" and settings.get("url"):
                from .providers import LibreTranslateProvider
                provider = LibreTranslateProvider(settings["url"], os.environ.get("AION2_TRANSLATION_API_KEY", ""), target=language)
                languages = provider.languages()
                english = next((x for x in languages if x["code"] == "en"), None)
                if not english or language not in {x["code"] for x in languages} or ("targets" in english and language not in english["targets"]):
                    raise ValueError("Configured provider does not support this English-to-target pair")
                for index, (key, item) in enumerate(plan["pending"].items()):
                    protected = prepare(item["source"])
                    value = protected.restore(provider.translate_batch([protected.html])[0])
                    validate(item["source"], value)
                    corrections[key] = value
                    self.emit("Translating changed text %s / %s" % (index + 1, len(plan["pending"])), 10 + 70 * (index + 1) / len(plan["pending"]))
            else:
                raise ValueError("Update needs translations for " + str(len(plan["pending"]))
                    + " new/changed records. Existing translation and game files were preserved. Review " + str(pending_path)
                    + "; configure your translation server or provide corrections.json for this update.")
        canonical = finish_migration(plan, corrections)
        canonical, context_report = apply_target_context_terms(source, canonical, language)
        displayed, display_report = canonical, None
        if _turkish_language(language) and prior_meta.get("font_compatible_titles", True):
            displayed, display_report = apply_turkish_heading_compatibility(canonical)
        for key, value in displayed.items():
            if key in plan["carried"]:
                _legacy_structure_and_abbreviations(source[key], value)
                # Corrections/context rules may not invent new structural tokens.
                validate(prior_values[key], value)
            else:
                validate(source[key], value)
        dat = doc.encode(doc.table.translated(displayed))
        if L10NDocument.decode(dat, "en-US", manifest).table.as_dict() != displayed:
            raise ValueError("Migrated translation codec verification failed")
        source_bytes = json.dumps(source, ensure_ascii=False, indent=2).encode("utf-8")
        archive = self.data / "history" / language / (str(prior_meta["steam_build"]) + "-" + uuid.uuid4().hex)
        temporary = stage.parent / ("." + language + "-update-" + uuid.uuid4().hex)
        temporary.mkdir(parents=True)
        meta = dict(steam_build=self.build, target_language=language, source_entry_count=len(source),
            original_pak_sha256=self.original_sha, original_dat_sha256=self.original_dat_sha,
            dat_sha256=sha(dat), quality_gate_passed=True, remaining_untranslated_candidate_entries=0,
            source_map_sha256=sha(source_bytes), manifest_sha256=sha(manifest),
            editable_translation_map="entries.translated.json", font_compatible_titles=bool(display_report),
            display_profile=display_report["profile"] if display_report else None,
            migrated_from=str(prior_meta["steam_build"]), prior_stage=str(archive),
            migration_carried=len(plan["carried"]), migration_translated=len(corrections),
            migration_removed=len(plan["removed"]), human_reviewed=False, in_game_verified=False,
            validation_scope="identical key and English source carry-forward; strict new/changed protected literals; original structure for legacy abbreviation aliases; exact native roundtrip, not complete semantic/in-game review")
        try:
            atomic(temporary / "L10NString.dat", dat)
            atomic(temporary / "entries.source.json", source_bytes)
            atomic(temporary / "source-key-manifest.dat", manifest)
            json_write(temporary / "entries.translated.json", canonical)
            json_write(temporary / "patch-meta.json", meta)
            json_write(temporary / "migration-report.json", {k: meta[k] for k in ("migrated_from", "migration_carried", "migration_translated", "migration_removed")})
            if display_report:
                json_write(temporary / "display-report.json", display_report)
            if any((path.read_bytes() if path.exists() else None) != data for path, data in reference_files.items()):
                raise ValueError("Previous pack changed during migration; nothing was replaced")
            archive.parent.mkdir(parents=True, exist_ok=True)
            stage.rename(archive)
            try:
                temporary.rename(stage)
            except Exception:
                archive.rename(stage)
                raise
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return dict(status="prepared", stage=str(stage), build=self.build, entries=len(source),
            carried=len(plan["carried"]), translated=len(corrections), removed=len(plan["removed"]))

    def build_translation(self, game_dir, target_lang, provider_config):
        from .codec import L10NDocument
        from .protection import PROTECTION_PROFILE, prepare, validate, has_linguistic_content
        from .multilingual import apply_target_context_terms, normalize_language
        target_lang = normalize_language(target_lang)
        if target_lang.split('-')[0] == 'en':
            raise ValueError('English is the original source; use Restore original instead')
        self.emit("Reading original English text", 1)
        doc, manifest = self._extract(game_dir)
        source = doc.table.as_dict()
        stage = self.data / "stages" / target_lang
        offline_turkish = provider_config.get("provider") == "offline-json" and _turkish_language(target_lang)
        reference = None
        carried_values = {}

        def matches_reference(key, value):
            if value == reference["values"][key]:
                return True
            from .display import apply_turkish_heading_compatibility
            displayed, _ = apply_turkish_heading_compatibility({key: value})
            return displayed[key] == reference["values"][key]

        def validate_translation_cell(key, value, *, initial=False):
            nonlocal reference
            if key in carried_values:
                # Context/display processing cannot use an inherited exception
                # to introduce new identifiers, text or formatting changes.
                _legacy_structure_and_abbreviations(source[key], value)
                validate(carried_values[key], value)
                if not matches_reference(key, value):
                    raise ValueError("Legacy cell changed after validation: " + key)
                return
            try:
                validate(source[key], value)
            except ValueError:
                if not initial or not offline_turkish:
                    raise
                if reference is None:
                    reference = self._verified_legacy_reference(stage, target_lang, doc, manifest)
                _legacy_structure_and_abbreviations(source[key], value)
                if not matches_reference(key, value):
                    raise ValueError("Changed legacy cell must pass current strict validation: " + key)
                carried_values[key] = value

        output = {}
        if provider_config.get("provider") == "offline-json":
            output = flat_json(provider_config["json_path"])
            if set(output) != set(source):
                raise ValueError("JSON must contain the complete source key set; partial translations cannot be installed")
        else:
            from .providers import LibreTranslateProvider
            provider = LibreTranslateProvider(provider_config.get("url", ""), provider_config.get("api_key", ""), target=target_lang)
            languages = provider.languages()
            english = next((item for item in languages if item["code"] == "en"), None)
            if english is None or ("targets" in english and target_lang not in english["targets"]) or target_lang not in {x["code"] for x in languages}:
                raise ValueError("This server does not advertise the selected English-to-target language pair")
            self.data.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.data / "provider-cache.sqlite")
            try:
                # Legacy rows stay intact. A protection revision has a separate
                # namespace so older, semantically ambiguous output is not reused.
                db.execute("CREATE TABLE IF NOT EXISTS cache_v2 (profile TEXT, server TEXT, lang TEXT, source TEXT, translated TEXT, PRIMARY KEY(profile,server,lang,source))")
                unique = list(dict.fromkeys(source.values()))
                translations = {}
                for index, text in enumerate(unique):
                    if not has_linguistic_content(text):
                        translations[text] = text
                        continue
                    row = db.execute("SELECT translated FROM cache_v2 WHERE profile=? AND server=? AND lang=? AND source=?",
                                     (PROTECTION_PROFILE, provider_config["url"], target_lang, text)).fetchone()
                    value = None
                    if row:
                        try:
                            validate(text, row[0])
                        except ValueError:
                            # Keep the old row until a new answer passes every
                            # check. A failed request must not destroy the cache.
                            self.emit("Cached result failed current protection checks; translating again")
                        else:
                            value = row[0]
                    if value is None:
                        prepared = prepare(text)
                        value = prepared.restore(provider.translate_batch([prepared.html])[0])
                        validate(text, value)
                        db.execute("INSERT OR REPLACE INTO cache_v2 VALUES (?,?,?,?,?)",
                                   (PROTECTION_PROFILE, provider_config["url"], target_lang, text, value))
                        db.commit()
                    translations[text] = value
                    if index % 50 == 0:
                        self.emit("Translated %s / %s unique values" % (index + 1, len(unique)), 3 + index * 85 / len(unique))
                output = {key: translations[text] for key, text in source.items()}
            finally:
                db.close()
        for key, value in output.items():
            validate_translation_cell(key, value, initial=True)
        output, context_report = apply_target_context_terms(source, output, target_lang)
        canonical_output = dict(output)
        canonical_names = []
        if _turkish_language(target_lang):
            canonical_names = context_report["rule_keys"]["skill_snipe"]
        unchanged = {key: value for key, value in output.items() if value == source[key] and has_linguistic_content(value)}
        display_report = None
        if _turkish_language(target_lang):
            if provider_config.get("font_compatible_titles", True):
                from .display import apply_turkish_heading_compatibility
                output, display_report = apply_turkish_heading_compatibility(output)
        for key, value in output.items():
            validate_translation_cell(key, value)
        dat = doc.encode(doc.table.translated(output))
        if L10NDocument.decode(dat, "en-US", manifest).table.as_dict() != output:
            raise ValueError("Encoded translation failed verification")
        if reference is not None:
            if ((stage / "patch-meta.json").read_bytes() != reference["meta_bytes"]
                    or (stage / "L10NString.dat").read_bytes() != reference["dat"]):
                raise ValueError("Legacy reference pack changed while rebuilding; nothing was written")
        if provider_config.get("provider") == "offline-json" and unchanged and not provider_config.get("review_unchanged", False):
            report = stage / "unchanged-review.json"
            json_write(report, unchanged)
            raise ValueError("Unchanged English candidates need review (proper names may be valid). Review " + str(report) + "; then select the reviewed-unchanged option.")
        atomic(stage / "L10NString.dat", dat)
        json_write(stage / "entries.translated.json", canonical_output)
        source_bytes = json.dumps(source, ensure_ascii=False, indent=2).encode("utf-8")
        atomic(stage / "entries.source.json", source_bytes)
        # Synthetic callers can use a parsed manifest dictionary in unit tests.
        if isinstance(manifest, bytes):
            atomic(stage / "source-key-manifest.dat", manifest)
        meta = dict(steam_build=self.build, target_language=target_lang, source_entry_count=len(source),
                    source_map_sha256=sha(source_bytes),
                    manifest_sha256=sha(manifest) if isinstance(manifest, bytes) else None,
                    protection_profile=PROTECTION_PROFILE,
                    dat_sha256=sha(dat), original_pak_sha256=self.original_sha, quality_gate_passed=True,
                    remaining_untranslated_candidate_entries=0, machine_translation=provider_config.get("provider") != "offline-json",
                    unchanged_linguistic_entry_count=len(unchanged),
                    unchanged_linguistic_reviewed=bool(provider_config.get("review_unchanged", False)),
                    validation_scope=("complete keys, strict protected literals for new/changed cells; "
                        + ("unchanged verified legacy Turkish cells retain original structural literals and exact reference/display equivalence; " if carried_values else "")
                        + "codec roundtrip; not a full semantic review"),
                    carry_forward_legacy_keys=sorted(carried_values),
                    carry_forward_legacy_count=len(carried_values),
                    carry_forward_legacy_reference=({"dat_sha256": reference["dat_sha256"],
                        "meta_sha256": reference["meta_sha256"], "target_language": target_lang} if reference else None),
                    canonical_skill_name_fixes=canonical_names,
                    context_terms_report=context_report,
                    editable_translation_map="entries.translated.json",
                    font_compatible_titles=bool(display_report),
                    display_profile=display_report["profile"] if display_report else None,
                    display_report=display_report,
                    human_reviewed=False, in_game_verified=False)
        if display_report:
            json_write(stage / "display-report.json", display_report)
        else:
            (stage / "display-report.json").unlink(missing_ok=True)
        if context_report:
            json_write(stage / "context-terms-report.json", context_report)
        else:
            (stage / "context-terms-report.json").unlink(missing_ok=True)
        json_write(stage / "patch-meta.json", meta)
        if provider_config.get("provider") not in (None, "offline-json") and provider_config.get("url"):
            # Never persist provider credentials. Later API keys may be supplied
            # explicitly through AION2_TRANSLATION_API_KEY.
            json_write(self.data / "settings" / (target_lang + "-provider.json"),
                dict(provider="libretranslate", url=provider_config["url"]))
        self.emit("Complete text package built locally. Use Install prepared language to apply it.", 100)
        return dict(stage=str(stage), target_language=target_lang, entries=len(source), status="prepared",
                    message="Language pack prepared. Review it, then close the game before installing.")

    def export_translation(self, target_language, destination):
        """Export a private editable map; exporting never installs it."""
        from .multilingual import normalize_language
        code = normalize_language(target_language)
        stage = self.data / 'stages' / code
        meta = json.loads((stage / 'patch-meta.json').read_text('utf-8'))
        values = flat_json(stage / 'entries.translated.json')
        if normalize_language(meta.get('target_language', '')) != code or len(values) != meta.get('source_entry_count'):
            raise ValueError('Editable translation map does not match the selected pack')
        output = Path(destination)
        json_write(output, values)
        self.emit('Editable translation map exported locally: ' + str(output), 100)
        return dict(translation_json=str(output), target_language=code, entries=len(values), status='exported')

    def export_source(self, game_dir):
        doc, _ = self._extract(game_dir)
        output = self.data / "source" / self.build / "entries.en.json"
        json_write(output, doc.table.as_dict())
        self.emit("Original source map exported locally: " + str(output), 100)
        return dict(source_json=str(output), entries=len(doc.table.entries), status="exported")
