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

BUILD = "26077854"
PAK = "pakchunk502000-Windows_0_P"
ORIGINAL_SHA = "4565d9d817f6ca8a7a11bbd0d25d0d91c6306c234be5f279ecfb33d5fba47080"
ORIGINAL_DAT_SHA = "4beef8a90b37ece24ec34a4684949ff40fa1f79a61550c7dfef47c63b941bfd9"
# Public compatibility key for this build; never a provider credential.
PAK_AES = "06038EF544B6007614F8574F1B7C2A3F0D565F74CDCC1B366B4EA1A17B97CBFF"
MARKER = b"AION2_LOOSE"
EXTENSIONS = (".pak", ".sig", ".ucas", ".utoc")
DISPLAY_ENTRY_COUNT = 153185


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

    def emit(self, message, progress=None):
        self.on_event(dict(message=message, progress=progress, level="info"))

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
        if not match or match.group(1) != BUILD:
            raise ValueError("Unsupported Steam build. Found " + (match.group(1) if match else "unknown")
                             + "; expected " + BUILD + ". Update the translator and rebuild the language pack; nothing was changed")
        content = game / "Aion2/Content"
        backup = self.data / "backups" / sha(str(game).casefold().encode())[:16] / BUILD
        return game, content / "Paks/L10N/Text/en-US", content / "L10N/Text/en-US/L10NString.dat", backup

    def _backup(self, backup):
        meta = json.loads((backup / "backup.json").read_text("utf-8"))
        names = {PAK + ext for ext in EXTENSIONS} | {"original-loose.dat"}
        if meta.get("steam_build") != BUILD or set(meta.get("files", {})) != names:
            raise ValueError("Backup manifest is invalid")
        for name, digest in meta["files"].items():
            if digest is not None and sha((backup / name).read_bytes()) != digest:
                raise ValueError("Backup checksum mismatch: " + name)
        if meta["files"][PAK + ".pak"] != ORIGINAL_SHA:
            raise ValueError("Unknown original PAK")
        return meta

    def _state(self, pakdir, loose, backup):
        path = backup / "state.json"
        if not path.exists():
            return None
        state = json.loads(path.read_text("utf-8"))
        self._backup(backup)
        if state.get("steam_build") != BUILD or (pakdir / (PAK + ".pak")).read_bytes() != MARKER:
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
        if state is None and sha((pakdir / (PAK + ".pak")).read_bytes()) != ORIGINAL_SHA:
            raise ValueError("Unknown patch detected. Restore it with its original installer first")
        return dict(game_dir=str(game), build=BUILD, status="installed" if state else "original",
                    installed_language=state["target_language"] if state else None,
                    entries=state["entries"] if state else DISPLAY_ENTRY_COUNT,
                    message="Verified native translation" if state else "Verified original English game")

    def _closed(self):
        if game_running():
            raise RuntimeError("Close AION 2 before installing or restoring; restart it afterwards")

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
        return self.install_stage(game_dir, stage)

    def install_stage(self, game_dir, stage):
        self._closed()
        game, pakdir, loose, backup = self.paths(game_dir)
        stage = Path(stage)
        meta = json.loads((stage / "patch-meta.json").read_text("utf-8"))
        dat = (stage / "L10NString.dat").read_bytes()
        if meta.get("steam_build") != BUILD:
            raise ValueError("Language pack build mismatch. Found " + str(meta.get("steam_build", "unknown"))
                             + "; expected " + BUILD + ". Rebuild the language pack for the current game; nothing was changed")
        if (meta.get("steam_build") != BUILD or meta.get("original_pak_sha256") != ORIGINAL_SHA
                or not meta.get("quality_gate_passed") or meta.get("remaining_untranslated_candidate_entries") != 0
                or meta.get("source_entry_count") != DISPLAY_ENTRY_COUNT or sha(dat) != meta.get("dat_sha256")):
            raise ValueError("Translation package failed compatibility or coverage checks")
        from .update_recovery import recover_known_update
        recover_known_update(pakdir, loose, backup, self._closed)
        state = self._state(pakdir, loose, backup)
        snapshots = {pakdir / (PAK + ext): (pakdir / (PAK + ext)).read_bytes() if (pakdir / (PAK + ext)).exists() else None for ext in EXTENSIONS}
        snapshots[loose] = loose.read_bytes() if loose.exists() else None
        for ext in EXTENSIONS[1:]:
            p = pakdir / (PAK + ext + ".codex-original")
            snapshots[p] = p.read_bytes() if p.exists() else None
        statepath = backup / "state.json"
        previous_state = statepath.read_bytes() if statepath.exists() else None
        if state is None:
            if sha(snapshots[pakdir / (PAK + ".pak")]) != ORIGINAL_SHA or snapshots[loose] is not None:
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
            json_write(backup / "backup.json", dict(steam_build=BUILD, files=records))
            self._backup(backup)
        self.emit("Installing native text file", 95)
        # Rejection before the first mutation must never trigger rollback over
        # the external edit that caused the rejection.
        self._closed()
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
            json_write(statepath, dict(steam_build=BUILD, dat_sha256=sha(dat), target_language=language, entries=DISPLAY_ENTRY_COUNT))
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
        return self.inspect(game)

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
        return self.inspect(game)

    def _extract(self, game_dir):
        from .codec import L10NDocument
        game, pakdir, loose, backup = self.paths(game_dir)
        state = self._state(pakdir, loose, backup)
        sourcepak = backup / (PAK + ".pak") if state else pakdir / (PAK + ".pak")
        if sha(sourcepak.read_bytes()) != ORIGINAL_SHA:
            raise ValueError("Unknown source PAK")
        if not self.repak.is_file():
            raise FileNotFoundError("repak.exe 0.2.3 is required in tools/ or REPAK_PATH; see README")
        extracted = self.data / "source" / BUILD
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
        if sha(data) != ORIGINAL_DAT_SHA:
            raise ValueError("English source DAT checksum mismatch; cached source must match the verified build")
        doc = L10NDocument.decode(data, "en-US", manifest)
        if len(doc.table.entries) != DISPLAY_ENTRY_COUNT or doc.encode() != data or doc.table.namespace.text != "AION2":
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
        if (len(source) != DISPLAY_ENTRY_COUNT or len(original.table.entries) != DISPLAY_ENTRY_COUNT
                or len(current) != DISPLAY_ENTRY_COUNT or len(installed.table.entries) != DISPLAY_ENTRY_COUNT
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
        if (decoded.table.as_dict() != corrected or len(decoded.table.entries) != DISPLAY_ENTRY_COUNT
                or decoded.table.namespace.text != "AION2"
                or [key.text for key, _ in decoded.table.entries] != [key.text for key, _ in original.table.entries]):
            raise ValueError("Heading repair failed exact dictionary/order verification")
        stages = self.data / "stages"
        prior = stages / "tr-before-font-fix"
        prior_meta = dict(steam_build=BUILD, target_language="tr", source_entry_count=len(source),
                          dat_sha256=sha(installed_dat), original_pak_sha256=ORIGINAL_SHA,
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
        if (saved_meta.get("steam_build") != BUILD or saved_meta.get("original_pak_sha256") != ORIGINAL_SHA
                or saved_meta.get("source_entry_count") != DISPLAY_ENTRY_COUNT
                or saved_meta.get("target_language") != "tr" or saved_meta.get("dat_sha256") != sha(saved_dat)
                or saved_meta.get("quality_gate_passed") is not True
                or saved_meta.get("remaining_untranslated_candidate_entries") != 0):
            raise ValueError("Existing pre-repair pack is invalid; it was preserved without overwriting")
        saved = L10NDocument.decode(saved_dat, "en-US", manifest)
        if (len(saved.table.entries) != DISPLAY_ENTRY_COUNT or set(saved.table.as_dict()) != set(source)
                or saved.table.namespace.text != "AION2"):
            raise ValueError("Existing pre-repair pack has a different key set; it was not overwritten")
        stage = stages / "tr-font-safe"
        meta = dict(steam_build=BUILD, target_language="tr", source_entry_count=len(source),
                    dat_sha256=sha(dat), original_pak_sha256=ORIGINAL_SHA, quality_gate_passed=True,
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
            if (not isinstance(meta, dict) or meta.get("steam_build") != BUILD
                    or meta.get("original_pak_sha256") != ORIGINAL_SHA
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
        meta = dict(steam_build=BUILD, target_language=target_lang, source_entry_count=len(source),
                    protection_profile=PROTECTION_PROFILE,
                    dat_sha256=sha(dat), original_pak_sha256=ORIGINAL_SHA, quality_gate_passed=True,
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
        output = self.data / "source" / BUILD / "entries.en.json"
        json_write(output, doc.table.as_dict())
        self.emit("Original source map exported locally: " + str(output), 100)
        return dict(source_json=str(output), entries=len(doc.table.entries), status="exported")
