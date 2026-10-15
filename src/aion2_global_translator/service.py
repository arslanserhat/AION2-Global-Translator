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

BUILD = "25926599"
PAK = "pakchunk502000-Windows_0_P"
ORIGINAL_SHA = "07d61d63c131ce86a5674be28e14d9d93a11631a8704eb9c85e310123f11088c"
ORIGINAL_DAT_SHA = "694a7d39e6bbe27c85dafa127d3feaca2a4a7a3c502ccf7385078b9c74dc6a3f"
# Public compatibility key for this build; never a provider credential.
PAK_AES = "06038EF544B6007614F8574F1B7C2A3F0D565F74CDCC1B366B4EA1A17B97CBFF"
MARKER = b"AION2_LOOSE"
EXTENSIONS = (".pak", ".sig", ".ucas", ".utoc")


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
            raise ValueError("Unsupported Steam build. Expected " + BUILD + "; nothing was changed")
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
                    entries=state["entries"] if state else 153042,
                    message="Verified native translation" if state else "Verified original English game")

    def _closed(self):
        if game_running():
            raise RuntimeError("Close AION 2 before installing or restoring; restart it afterwards")

    def install_turkish(self, game_dir):
        stage = self.data / "stages/tr"
        if not (stage / "patch-meta.json").is_file():
            raise ValueError("No local Turkish pack is ready. Use Build Translation to generate one from your game or import a complete translation map first.")
        return self.install_stage(game_dir, stage)

    def install_stage(self, game_dir, stage):
        self._closed()
        game, pakdir, loose, backup = self.paths(game_dir)
        stage = Path(stage)
        meta = json.loads((stage / "patch-meta.json").read_text("utf-8"))
        dat = (stage / "L10NString.dat").read_bytes()
        if (meta.get("steam_build") != BUILD or meta.get("original_pak_sha256") != ORIGINAL_SHA
                or not meta.get("quality_gate_passed") or meta.get("remaining_untranslated_candidate_entries") != 0
                or meta.get("source_entry_count") != 153042 or sha(dat) != meta.get("dat_sha256")):
            raise ValueError("Translation package failed compatibility or coverage checks")
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
            json_write(statepath, dict(steam_build=BUILD, dat_sha256=sha(dat), target_language=language, entries=153042))
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
        if len(doc.table.entries) != 153042 or doc.encode() != data or doc.table.namespace.text != "AION2":
            raise ValueError("Source codec verification failed")
        return doc, manifest

    def build_translation(self, game_dir, target_lang, provider_config):
        from .codec import L10NDocument
        from .protection import prepare, validate, has_linguistic_content
        if not re.fullmatch(r"[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})?", target_lang):
            raise ValueError("Enter a valid provider language code, such as tr, de or pt-BR")
        self.emit("Reading original English text", 1)
        doc, manifest = self._extract(game_dir)
        source = doc.table.as_dict()
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
                db.execute("CREATE TABLE IF NOT EXISTS cache (server TEXT, lang TEXT, source TEXT, translated TEXT, PRIMARY KEY(server,lang,source))")
                unique = list(dict.fromkeys(source.values()))
                translations = {}
                for index, text in enumerate(unique):
                    if not has_linguistic_content(text):
                        translations[text] = text
                        continue
                    row = db.execute("SELECT translated FROM cache WHERE server=? AND lang=? AND source=?", (provider_config["url"], target_lang, text)).fetchone()
                    if row:
                        value = row[0]
                        validate(text, value)
                    else:
                        prepared = prepare(text)
                        value = prepared.restore(provider.translate_batch([prepared.html])[0])
                        validate(text, value)
                        db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,?)", (provider_config["url"], target_lang, text, value))
                        db.commit()
                    translations[text] = value
                    if index % 50 == 0:
                        self.emit("Translated %s / %s unique values" % (index + 1, len(unique)), 3 + index * 85 / len(unique))
                output = {key: translations[text] for key, text in source.items()}
            finally:
                db.close()
        for key, value in output.items():
            validate(source[key], value)
        unchanged = {key: value for key, value in output.items() if value == source[key] and has_linguistic_content(value)}
        stage = self.data / "stages" / target_lang
        if provider_config.get("provider") == "offline-json" and unchanged and not provider_config.get("review_unchanged", False):
            report = stage / "unchanged-review.json"
            json_write(report, unchanged)
            raise ValueError("Unchanged English candidates need review (proper names may be valid). Review " + str(report) + "; then select the reviewed-unchanged option.")
        dat = doc.encode(doc.table.translated(output))
        if L10NDocument.decode(dat, "en-US", manifest).table.as_dict() != output:
            raise ValueError("Encoded translation failed verification")
        atomic(stage / "L10NString.dat", dat)
        meta = dict(steam_build=BUILD, target_language=target_lang, source_entry_count=len(source),
                    dat_sha256=sha(dat), original_pak_sha256=ORIGINAL_SHA, quality_gate_passed=True,
                    remaining_untranslated_candidate_entries=0, machine_translation=provider_config.get("provider") != "offline-json",
                    unchanged_linguistic_entry_count=len(unchanged),
                    unchanged_linguistic_reviewed=bool(provider_config.get("review_unchanged", False)),
                    validation_scope="complete keys, protected literals and codec roundtrip; translation quality needs review",
                    human_reviewed=False, in_game_verified=False)
        json_write(stage / "patch-meta.json", meta)
        self.emit("Complete text package built locally. Use Install prepared language to apply it.", 100)
        return dict(stage=str(stage), target_language=target_lang, entries=len(source), status="prepared",
                    message="Language pack prepared. Review it, then close the game before installing.")

    def export_source(self, game_dir):
        doc, _ = self._extract(game_dir)
        output = self.data / "source" / BUILD / "entries.en.json"
        json_write(output, doc.table.as_dict())
        self.emit("Original source map exported locally: " + str(output), 100)
        return dict(source_json=str(output), entries=len(doc.table.entries), status="exported")
