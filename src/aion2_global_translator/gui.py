"""Standard-library desktop interface; service work never runs on Tk's thread."""
from __future__ import annotations

import argparse
from pathlib import Path
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

from .service import TranslatorService


TEXT = {
    "tr": {
        "title": "AION 2 Global Translator", "subtitle": "AION 2 için yerel dil paketlerini yönet.",
        "game": "OYUN KLASÖRÜ", "folder_hint": "AION2 ana klasörünü seç; Aion2/Content alt klasörünü seçme.",
        "browse": "Klasör seç", "detect": "Otomatik bul", "choose_game": "AION2 oyun klasörünü seç",
        "language": "Dil paketi", "turkish": "Türkçe (tr)", "source": "Kaynak dil: İngilizce",
        "native": "Yerel Türkçe paketi", "native_hint": "Hazır Türkçe paketini kurabilir veya yedekteki özgün dosyaları geri yükleyebilirsin.",
        "inspect": "Kurulumu kontrol et", "install": "Türkçe paketini kur", "restore": "Özgün dosyaları geri yükle",
        "create": "Yeni çeviri oluştur…", "install_prepared": "Hazır dil paketini kur…",
        "choose_stage": "Kurulacak dil paketi klasörünü seç", "prepared": "Dil paketi hazır; kurmak için paket klasörünü seçebilirsin.",
        "planned": "Hazır paket Türkçedir. Diğer diller, sağlayıcı desteği ve ayrı doğrulama gerektirir.",
        "activity": "İŞLEM GÜNLÜĞÜ", "clear": "Temizle", "idle": "Hazır", "waiting": "Bir oyun klasörü seçerek başla.",
        "working": "İşlem sürüyor…", "done": "İşlem tamamlandı.", "failed": "İşlem tamamlanamadı.",
        "detect_work": "Oyun klasörü aranıyor…", "inspect_work": "Kurulum kontrol ediliyor…",
        "install_work": "Türkçe paketi kuruluyor…", "restore_work": "Özgün dosyalar geri yükleniyor…",
        "build_work": "Yeni çeviri hazırlanıyor…", "install_stage_work": "Seçilen dil paketi kuruluyor…",
        "not_found": "Oyun otomatik bulunamadı. Klasörü elle seçebilirsin.",
        "found": "Oyun klasörü bulundu.", "missing_folder": "Önce AION2 oyun klasörünü seç.",
        "error_title": "İşlem hatası", "busy_close": "Dosyaların güvenli kalması için işlem tamamlanana kadar uygulamayı açık tut.",
        "build": "Steam derlemesi", "status": "Durum", "installed_language": "Kurulu dil", "entries": "Metin kaydı",
        "startup": "Kurulumdan önce sürüm, dosya bütünlüğü ve yedekler denetlenir.",
        "create_title": "Yeni çeviri oluştur", "create_intro": "İngilizce kaynak metinlerden yeni bir dil paketi hazırla. Oluşturmak, oyuna kurmaz.",
        "target_code": "Hedef dil kodu", "target_hint": "Örnek: tr, de, fr. Destek, seçilen sağlayıcıya bağlıdır.",
        "provider": "Çeviri kaynağı", "offline": "Çevrimdışı JSON", "libre": "LibreTranslate sunucusu",
        "json_path": "Çevrilmiş JSON dosyası", "choose_file": "Dosya seç", "json_title": "Çevrilmiş metin JSON dosyasını seç",
        "json_hint": "İngilizce kaynakla aynı anahtarları içeren, anahtar → çevrilmiş metin nesnesi.",
        "export_source": "İngilizce kaynağı dışa aktar…", "export_work": "İngilizce kaynak metinler dışa aktarılıyor…",
        "review_unchanged": "Aynı kalan özel adları ve metinleri gözden geçirdim",
        "url": "Sunucu adresi", "key": "API anahtarı (isteğe bağlı)",
        "provider_hint": "LibreTranslate için kendi sunucunu yapılandır. Kullanılabilir diller ve olası ücretler sunucuya bağlıdır.",
        "build_notice": "Yeni paketler otomatik çeviri içerebilir. Etiket ve sayı denetimi, insan incelemesinin yerini tutmaz.",
        "cancel": "Vazgeç", "build_button": "Paketi oluştur", "bad_code": "Geçerli bir hedef dil kodu gir (ör. tr veya pt-BR).",
        "missing_json": "Çevrilmiş JSON dosyasını seç.", "bad_url": "Geçerli bir http:// veya https:// LibreTranslate sunucu adresi gir.",
        "output": "Çıktı", "unknown": "Bilinmiyor", "ready": "Kurulum incelendi", "installed": "Dil paketi kurulu",
        "original": "Özgün dosyalar", "restart_hint": "Oyunun önbelleğindeki metinler normal yeniden açılışına kadar değişmeyebilir.",
    },
    "en": {
        "title": "AION 2 Global Translator", "subtitle": "Manage native language packs for AION 2.",
        "game": "GAME FOLDER", "folder_hint": "Select the AION2 root folder, rather than its Aion2/Content subfolder.",
        "browse": "Browse", "detect": "Auto-detect", "choose_game": "Select the AION2 game folder",
        "language": "Language pack", "turkish": "Turkish (tr)", "source": "Source language: English",
        "native": "Native Turkish pack", "native_hint": "Install the bundled Turkish pack or restore the original files from the verified backup.",
        "inspect": "Check installation", "install": "Install Turkish pack", "restore": "Restore original files",
        "create": "Create a translation…", "install_prepared": "Install prepared language…",
        "choose_stage": "Select the language pack folder to install", "prepared": "Language pack prepared. Select its folder when you want to install it.",
        "planned": "The bundled pack is Turkish. Other languages require provider support and separate validation.",
        "activity": "ACTIVITY LOG", "clear": "Clear", "idle": "Ready", "waiting": "Choose a game folder to begin.",
        "working": "Working…", "done": "Operation completed.", "failed": "The operation could not be completed.",
        "detect_work": "Looking for the game folder…", "inspect_work": "Checking the installation…",
        "install_work": "Installing the Turkish pack…", "restore_work": "Restoring original files…",
        "build_work": "Preparing a new translation…", "install_stage_work": "Installing the selected language pack…",
        "not_found": "The game was not found automatically. You can select its folder.",
        "found": "Game folder found.", "missing_folder": "Select the AION2 game folder first.",
        "error_title": "Operation error", "busy_close": "Keep this application open until the operation finishes so files can be left in a safe state.",
        "build": "Steam build", "status": "Status", "installed_language": "Installed language", "entries": "Text entries",
        "startup": "Version, file integrity, and backups are checked before installation.",
        "create_title": "Create a translation", "create_intro": "Prepare a language pack from the English source text. Creating a pack does not install it.",
        "target_code": "Target language code", "target_hint": "Examples: tr, de, fr. Support depends on the selected provider.",
        "provider": "Translation source", "offline": "Offline JSON", "libre": "LibreTranslate server",
        "json_path": "Translated JSON file", "choose_file": "Browse", "json_title": "Select the translated text JSON file",
        "json_hint": "A key → translated text object containing the same keys as the English source.",
        "export_source": "Export English source…", "export_work": "Exporting the English source text…",
        "review_unchanged": "I reviewed unchanged names and text",
        "url": "Server URL", "key": "API key (optional)",
        "provider_hint": "Configure your own LibreTranslate server. Available languages and any charges depend on that server.",
        "build_notice": "New packs may contain machine translations. Tag and number checks do not replace human review.",
        "cancel": "Cancel", "build_button": "Create pack", "bad_code": "Enter a valid target language code, such as tr or pt-BR.",
        "missing_json": "Choose a translated JSON file.", "bad_url": "Enter a valid http:// or https:// LibreTranslate server URL.",
        "output": "Output", "unknown": "Unknown", "ready": "Installation checked", "installed": "Language pack installed",
        "original": "Original files", "restart_hint": "Text already cached by the game may remain until your next normal game restart.",
    },
}


class TranslatorApp:
    def __init__(self, root: tk.Tk, game_dir: str = ""):
        self.root = root
        self.language = "tr"
        self.events = queue.Queue()
        self._busy = False
        self._operation = ""
        self._status_key = "waiting"
        self._bindings = []
        self._controls = []
        self._secrets = set()
        self._last_inspection = None
        self.game_path = tk.StringVar(value=game_dir)
        self.interface_language = tk.StringVar(value="Türkçe")
        self.status_text = tk.StringVar()
        self.operation_text = tk.StringVar()
        self.progress_text = tk.StringVar(value="")
        self.pack_text = tk.StringVar()
        self.detail_text = tk.StringVar()
        self.service = TranslatorService(on_event=self._service_event)
        self._style()
        self._layout()
        self._refresh_language()
        self._log(self.tr("startup"))
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(80, self._poll)
        if game_dir:
            self.root.after(200, lambda: self._inspect(quiet=True))
        else:
            self.root.after(200, lambda: self._detect(quiet=True))

    def tr(self, key):
        return TEXT[self.language][key]

    def _style(self):
        self.root.geometry("880x650")
        self.root.minsize(820, 620)
        self.root.configure(background="#10151f")
        self.root.option_add("*Font", "{Segoe UI} 10")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#10151f")
        style.configure("Card.TFrame", background="#192230")
        style.configure("TLabel", background="#10151f", foreground="#e7edf6")
        style.configure("Muted.TLabel", foreground="#9aaac1")
        style.configure("Card.TLabel", background="#192230", foreground="#e7edf6")
        style.configure("CardMuted.TLabel", background="#192230", foreground="#a5b4c9")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Section.TLabel", foreground="#86a1c4", font=("Segoe UI", 9, "bold"))
        style.configure("CardTitle.TLabel", background="#192230", foreground="#e7edf6", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", padding=(12, 8), background="#263449", foreground="#edf3fc", borderwidth=0)
        style.map("TButton", background=[("active", "#344864"), ("disabled", "#1c2839")],
                  foreground=[("disabled", "#6f8098")])
        style.configure("Primary.TButton", background="#4788ee", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#60a0ff"), ("disabled", "#25436d")])
        style.configure("Small.TButton", padding=(9, 3))
        style.configure("TEntry", fieldbackground="#101925", foreground="#e7edf6", insertcolor="#e7edf6", padding=7)
        style.configure("TCombobox", fieldbackground="#101925", foreground="#e7edf6", background="#263449", padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", "#101925")], foreground=[("readonly", "#e7edf6")])
        style.configure("Horizontal.TProgressbar", background="#569bff", troughcolor="#243146", borderwidth=0)
        style.configure("TSeparator", background="#2a374a")
        style.configure("TCheckbutton", background="#10151f", foreground="#e7edf6", padding=(0, 3))
        style.map("TCheckbutton", background=[("active", "#10151f")])
        self.root.option_add("*TCombobox*Listbox.background", "#192230")
        self.root.option_add("*TCombobox*Listbox.foreground", "#e7edf6")

    def _text(self, widget, key):
        self._bindings.append((widget, key))
        return widget

    def _button(self, parent, key, command, **kwargs):
        button = self._text(ttk.Button(parent, command=command, **kwargs), key)
        self._controls.append(button)
        return button

    def _layout(self):
        body = ttk.Frame(self.root, padding=(24, 19, 24, 14))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(5, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        self._text(ttk.Label(header, style="Title.TLabel"), "title").grid(row=0, column=0, sticky="w")
        switch = ttk.Combobox(header, values=("Türkçe", "English"), textvariable=self.interface_language,
                              state="readonly", width=10)
        switch.grid(row=0, column=1, sticky="e")
        switch.bind("<<ComboboxSelected>>", self._switch_language)
        self._text(ttk.Label(header, style="Muted.TLabel"), "subtitle").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        folder = ttk.Frame(body, style="Card.TFrame", padding=14)
        folder.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        folder.columnconfigure(0, weight=1)
        self._text(ttk.Label(folder, style="CardTitle.TLabel"), "game").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        path_entry = ttk.Entry(folder, textvariable=self.game_path)
        path_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self._controls.append(path_entry)
        self._button(folder, "browse", self._browse).grid(row=1, column=1, padx=(0, 7))
        self._button(folder, "detect", self._detect).grid(row=1, column=2)
        self._text(ttk.Label(folder, style="CardMuted.TLabel"), "folder_hint").grid(row=2, column=0, columnspan=3, sticky="w", pady=(7, 0))

        native = ttk.Frame(body, style="Card.TFrame", padding=14)
        native.grid(row=2, column=0, sticky="ew", pady=(0, 11))
        native.columnconfigure(0, weight=1)
        self._text(ttk.Label(native, style="CardTitle.TLabel"), "native").grid(row=0, column=0, sticky="w")
        ttk.Label(native, textvariable=self.pack_text, style="CardMuted.TLabel").grid(row=0, column=1, sticky="e")
        self._text(ttk.Label(native, style="CardMuted.TLabel", wraplength=760), "native_hint").grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 10))
        actions = ttk.Frame(native, style="Card.TFrame")
        actions.grid(row=2, column=0, columnspan=2, sticky="ew")
        self._button(actions, "install", self._install, style="Primary.TButton").pack(side="left", padx=(0, 8))
        self._button(actions, "inspect", self._inspect).pack(side="left", padx=(0, 8))
        self._button(actions, "restore", self._restore).pack(side="left")
        ttk.Label(native, textvariable=self.detail_text, style="CardMuted.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(9, 0))

        translation = ttk.Frame(body)
        translation.grid(row=3, column=0, sticky="ew", pady=(0, 11))
        translation.columnconfigure(0, weight=1)
        self._text(ttk.Label(translation, style="Muted.TLabel", wraplength=500), "planned").grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        self._button(translation, "create", self._translation_dialog, width=27).grid(row=0, column=1, sticky="e", pady=(0, 6))
        self._button(translation, "install_prepared", self._install_prepared, width=27).grid(row=1, column=1, sticky="e")

        progress = ttk.Frame(body)
        progress.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        progress.columnconfigure(0, weight=1)
        ttk.Label(progress, textvariable=self.operation_text, style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 5))
        ttk.Label(progress, textvariable=self.progress_text, style="Muted.TLabel").grid(row=0, column=1, sticky="e", pady=(0, 5))
        self.progress = ttk.Progressbar(progress, mode="determinate", maximum=100)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew")

        log_frame = ttk.Frame(body)
        log_frame.grid(row=5, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        self._text(ttk.Label(log_frame, style="Section.TLabel"), "activity").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._text(ttk.Button(log_frame, command=self._clear_log, style="Small.TButton"), "clear").grid(row=0, column=1, sticky="e", pady=(0, 6))
        self.log = tk.Text(log_frame, height=6, wrap="word", background="#0b111b", foreground="#bdcbe0",
                           insertbackground="#e7edf6", relief="flat", borderwidth=0, padx=11, pady=9,
                           font=("Consolas", 9), state="disabled", takefocus=True)
        self.log.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.tag_configure("error", foreground="#ff999d")
        self.log.tag_configure("warning", foreground="#efc878")
        self.log.tag_configure("success", foreground="#8bd5b4")
        ttk.Label(body, textvariable=self.status_text, style="Muted.TLabel").grid(row=6, column=0, sticky="w", pady=(10, 0))

    def _switch_language(self, _event=None):
        self.language = "en" if self.interface_language.get() == "English" else "tr"
        self._refresh_language()

    def _refresh_language(self):
        self.root.title(self.tr("title"))
        for widget, key in self._bindings:
            widget.configure(text=self.tr(key))
        self.pack_text.set(self.tr("turkish") + "  ·  " + self.tr("source"))
        self.status_text.set(self.tr(self._status_key))
        self.operation_text.set(self.tr(self._operation + "_work") if self._busy else self.tr("idle"))
        self._inspection_details()

    def _inspection_details(self):
        if not self._last_inspection:
            self.detail_text.set("")
            return
        result = self._last_inspection
        parts = []
        for key in ("build", "status", "installed_language", "entries"):
            if result.get(key) is not None:
                value = str(result[key])
                if key == "status" and value in ("ready", "installed", "original"):
                    value = self.tr(value)
                parts.append(self.tr(key) + ": " + value)
        self.detail_text.set("   ·   ".join(parts))

    def _service_event(self, event):
        # Called from service/worker threads: never touch a Tk variable here.
        self.events.put(("event", event))

    def _start(self, operation, function, *args, quiet=False):
        if self._busy:
            return
        self._busy = True
        self._operation = operation
        self._status_key = "working"
        for widget in self._controls:
            widget.configure(state="disabled")
        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        self.progress_text.set("")
        self._refresh_language()

        def work():
            try:
                self.events.put(("result", operation, function(*args)))
            except Exception as exc:
                self.events.put(("error", operation, str(exc), quiet))
            finally:
                self.events.put(("done", operation))

        threading.Thread(target=work, name="AION2-" + operation, daemon=False).start()

    def _poll(self):
        for _ in range(150):
            try:
                item = self.events.get_nowait()
            except queue.Empty:
                break
            kind = item[0]
            if kind == "event":
                event = item[1]
                if isinstance(event, dict):
                    if event.get("message"):
                        self._log(event["message"], event.get("level", "info"))
                    value = event.get("progress")
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        value = max(0, min(100, value))
                        self.progress.stop()
                        self.progress.configure(mode="determinate", value=value)
                        self.progress_text.set(f"{value:.0f}%")
                elif event is not None:
                    self._log(str(event))
            elif kind == "result":
                self._result(item[1], item[2])
            elif kind == "error":
                self._status_key = "failed"
                error = self._redact(item[2]) or self.tr("failed")
                self._log(error, "error")
                if not item[3]:
                    messagebox.showerror(self.tr("error_title"), error, parent=self.root)
            elif kind == "done":
                self._busy = False
                self.progress.stop()
                self.progress.configure(mode="determinate")
                for widget in self._controls:
                    widget.configure(state="normal")
                self._refresh_language()
        self.root.after(80, self._poll)

    def _result(self, operation, result):
        self._status_key = "done"
        if operation == "detect":
            path = result.get("game_dir") or result.get("path") if isinstance(result, dict) else result
            if path:
                self.game_path.set(str(path))
                self._status_key = "found"
            else:
                self._status_key = "not_found"
            self._log(self.tr(self._status_key))
            return
        if isinstance(result, dict):
            if operation == "inspect":
                self._last_inspection = result
                self._inspection_details()
            if result.get("message"):
                self._log(str(result["message"]), "success")
            for key in ("output_dir", "output_path", "stage_path", "stage", "source_json"):
                if result.get(key):
                    self._log(self.tr("output") + ": " + str(result[key]))
            if operation == "build" and result.get("status") == "prepared":
                self._status_key = "prepared"
        self._log(self.tr("done"), "success")
        if operation in ("install", "install_stage"):
            self._log(self.tr("restart_hint"))
        self.progress.configure(value=100)
        self.progress_text.set("100%")

    def _redact(self, text):
        text = str(text)
        for secret in self._secrets:
            if secret:
                text = text.replace(secret, "***")
        return text

    def _log(self, message, level="info"):
        self.log.configure(state="normal")
        self.log.insert("end", self._redact(message) + "\n", str(level).lower())
        # Bound memory use during large translation jobs.
        if int(self.log.index("end-1c").split(".")[0]) > 2500:
            self.log.delete("1.0", "501.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _browse(self):
        path = filedialog.askdirectory(title=self.tr("choose_game"), parent=self.root)
        if path:
            self.game_path.set(path)
            self._inspect()

    def _detect(self, quiet=False):
        self._start("detect", self.service.detect_game, quiet=quiet)

    def _game(self):
        path = self.game_path.get().strip()
        if not path:
            messagebox.showinfo(self.tr("title"), self.tr("missing_folder"), parent=self.root)
            return None
        return path

    def _inspect(self, quiet=False):
        path = self._game()
        if path:
            self._start("inspect", self.service.inspect, path, quiet=quiet)

    def _install(self):
        path = self._game()
        if path:
            self._start("install", self.service.install_turkish, path)

    def _restore(self):
        path = self._game()
        if path:
            self._start("restore", self.service.restore, path)

    def _install_prepared(self):
        game = self._game()
        if not game:
            return
        options = dict(parent=self.root, title=self.tr("choose_stage"), mustexist=True)
        data = getattr(self.service, "data", None)
        if data:
            options["initialdir"] = str(Path(data) / "stages")
        stage = filedialog.askdirectory(**options)
        if stage:
            self._start("install_stage", self.service.install_stage, game, stage)

    def _translation_dialog(self):
        game = self._game()
        if not game:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(self.tr("create_title"))
        dialog.configure(background="#10151f")
        dialog.geometry("620x555")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=22)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=self.tr("create_intro"), wraplength=570).grid(row=0, column=0, sticky="w", pady=(0, 15))
        target = tk.StringVar(value="tr")
        provider = tk.StringVar(value=self.tr("offline"))
        json_path = tk.StringVar()
        review_unchanged = tk.BooleanVar(value=False)
        url = tk.StringVar(value="http://localhost:5000")
        key = tk.StringVar()
        ttk.Label(frame, text=self.tr("target_code")).grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=target, width=16).grid(row=2, column=0, sticky="w", pady=(4, 3))
        ttk.Label(frame, text=self.tr("target_hint"), style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=(0, 13))
        ttk.Label(frame, text=self.tr("provider")).grid(row=4, column=0, sticky="w")
        choice = ttk.Combobox(frame, textvariable=provider, values=(self.tr("offline"), self.tr("libre")), state="readonly")
        choice.grid(row=5, column=0, sticky="ew", pady=(4, 12))

        config = ttk.Frame(frame)
        config.grid(row=6, column=0, sticky="ew")
        config.columnconfigure(0, weight=1)
        offline = ttk.Frame(config)
        offline.grid(row=0, column=0, sticky="ew")
        offline.columnconfigure(0, weight=1)
        ttk.Label(offline, text=self.tr("json_path")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(offline, textvariable=json_path).grid(row=1, column=0, sticky="ew", pady=(4, 5), padx=(0, 8))

        def browse_json():
            path = filedialog.askopenfilename(parent=dialog, title=self.tr("json_title"), filetypes=[("JSON", "*.json")])
            if path:
                json_path.set(path)

        ttk.Button(offline, text=self.tr("choose_file"), command=browse_json).grid(row=1, column=1, pady=(4, 5))
        ttk.Label(offline, text=self.tr("json_hint"), style="Muted.TLabel", wraplength=565).grid(row=2, column=0, columnspan=2, sticky="w")

        def export_source():
            dialog.destroy()
            self._start("export", self.service.export_source, game)

        ttk.Button(offline, text=self.tr("export_source"), command=export_source).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Checkbutton(offline, text=self.tr("review_unchanged"), variable=review_unchanged).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        libre = ttk.Frame(config)
        libre.grid(row=0, column=0, sticky="ew")
        libre.columnconfigure(0, weight=1)
        ttk.Label(libre, text=self.tr("url")).grid(row=0, column=0, sticky="w")
        ttk.Entry(libre, textvariable=url).grid(row=1, column=0, sticky="ew", pady=(4, 8))
        ttk.Label(libre, text=self.tr("key")).grid(row=2, column=0, sticky="w")
        ttk.Entry(libre, textvariable=key, show="•").grid(row=3, column=0, sticky="ew", pady=(4, 6))
        ttk.Label(libre, text=self.tr("provider_hint"), style="Muted.TLabel", wraplength=565).grid(row=4, column=0, sticky="w")
        libre.grid_remove()

        def provider_changed(_event=None):
            if provider.get() == self.tr("offline"):
                libre.grid_remove()
                offline.grid()
            else:
                offline.grid_remove()
                libre.grid()

        choice.bind("<<ComboboxSelected>>", provider_changed)
        ttk.Label(frame, text=self.tr("build_notice"), style="Muted.TLabel", wraplength=565).grid(row=7, column=0, sticky="sw", pady=(17, 10))
        frame.rowconfigure(7, weight=1)
        buttons = ttk.Frame(frame)
        buttons.grid(row=8, column=0, sticky="e")

        def create():
            language = target.get().strip()
            if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,2}", language):
                messagebox.showerror(self.tr("error_title"), self.tr("bad_code"), parent=dialog)
                return
            if provider.get() == self.tr("offline"):
                path = json_path.get().strip()
                if not path:
                    messagebox.showerror(self.tr("error_title"), self.tr("missing_json"), parent=dialog)
                    return
                configuration = {"provider": "offline-json", "json_path": path,
                                 "review_unchanged": review_unchanged.get()}
            else:
                address = url.get().strip().rstrip("/")
                parsed = urlparse(address)
                if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
                    messagebox.showerror(self.tr("error_title"), self.tr("bad_url"), parent=dialog)
                    return
                api_key = key.get().strip()
                if api_key:
                    self._secrets.add(api_key)
                configuration = {"provider": "libretranslate", "url": address, "api_key": api_key}
            dialog.destroy()
            self._start("build", self.service.build_translation, game, language, configuration)

        ttk.Button(buttons, text=self.tr("cancel"), command=dialog.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text=self.tr("build_button"), command=create, style="Primary.TButton").pack(side="left")

    def _close(self):
        if self._busy:
            messagebox.showinfo(self.tr("title"), self.tr("busy_close"), parent=self.root)
            return
        self.root.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description="AION 2 Global Translator desktop interface")
    parser.add_argument("--game-dir", default="", help="Initial AION2 root folder")
    args = parser.parse_args(argv)
    root = tk.Tk()
    TranslatorApp(root, args.game_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
