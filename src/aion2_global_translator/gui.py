"""Standard-library desktop interface; service work never runs on Tk's thread."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

from .service import TranslatorService
from .languages import language_choices, language_code, language_label, original_language, turkish_language


TEXT = {
    "tr": {
        "title": "AION 2 Global Translator", "subtitle": "Oyunun dilini kolayca değiştir.",
        "game_selected": "AION 2 klasörü seçili", "game_missing": "Oyun klasörü seçilmedi",
        "change_folder": "Klasörü değiştir", "other_languages": "Çeviri ayarları…", "details": "Ayrıntılar…",
        "details_title": "Ayrıntılar", "advanced_files": "Gelişmiş dosya seçenekleri",
        "game": "OYUN KLASÖRÜ", "folder_hint": "AION2 ana klasörünü seç; Aion2/Content alt klasörünü seçme.",
        "browse": "Klasör seç", "detect": "Otomatik bul", "choose_game": "AION2 oyun klasörünü seç",
        "language": "Dil paketi", "turkish": "Türkçe (tr)", "source": "Kaynak dil: İngilizce",
        "native": "Yerel Türkçe paketi", "native_hint": "Hazır Türkçe paketini kurabilir veya yedekteki özgün dosyaları geri yükleyebilirsin.",
        "inspect": "Kurulumu kontrol et", "install": "Çeviriyi uygula", "restore": "Orijinale dön",
        "target_language": "Hedef dil", "pack_available": "Yerel paket bulundu; uygularken denetlenir.",
        "pack_unavailable": "Yerel paket yok. Uygula ile bu dilin çeviri ayarlarını aç.",
        "english_original": "Özgün İngilizce dosyalara döner; yeni çeviri oluşturmaz.",
        "language_code_hint": "Listeden seçebilir veya dil kodu yazabilirsin (ör. de, pt-BR).",
        "english_settings": "İngilizce kaynak dildir. Ana ekrandan Orijinale dön seçeneğini kullan.",
        "validation_hint": "Her dilde metin anahtarları, etiketler ve sayılar denetlenir. Çeviri doğruluğu ayrıca gözden geçirilmelidir.",
        "create": "Yeni çeviri oluştur…", "install_prepared": "Hazır dil paketini kur…",
        "choose_stage": "Kurulacak dil paketi klasörünü seç", "prepared": "Dil paketi hazır; kurmak için paket klasörünü seçebilirsin.",
        "planned": "Hazır paket Türkçedir. Diğer diller, sağlayıcı desteği ve ayrı doğrulama gerektirir.",
        "activity": "İŞLEM GÜNLÜĞÜ", "clear": "Temizle", "idle": "Hazır", "waiting": "Bir oyun klasörü seçerek başla.",
        "working": "İşlem sürüyor…", "done": "İşlem tamamlandı.", "failed": "İşlem tamamlanamadı.",
        "detect_work": "Oyun klasörü aranıyor…", "inspect_work": "Kurulum kontrol ediliyor…",
        "install_work": "Türkçe paketi kuruluyor…", "restore_work": "Özgün dosyalar geri yükleniyor…",
        "build_work": "Yeni çeviri hazırlanıyor…", "install_stage_work": "Seçilen dil paketi kuruluyor…",
        "repair": "Başlıkları düzelt (Türkçe)", "repair_work": "Türkçe başlıklar düzeltiliyor…",
        "repair_hint": "Başlıklarda uyumlu harfler kullanır (Ö→O, ü→u). Açıklamalardaki Türkçe harfleri korur.",
        "font_compatible_titles": "Türkçe başlıkları oyun fontuna uyarla (Ö→O, ü→u)",
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
        "export_translation": "Çeviriyi dışa aktar…", "export_translation_work": "Seçilen dilin çevirisi dışa aktarılıyor…",
        "translation_json_title": "Düzenlemek için çeviri JSON dosyasını kaydet",
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
        "title": "AION 2 Global Translator", "subtitle": "Change your game's language with ease.",
        "game_selected": "AION 2 folder selected", "game_missing": "No game folder selected",
        "change_folder": "Change folder", "other_languages": "Translation settings…", "details": "Details…",
        "details_title": "Details", "advanced_files": "Advanced file options",
        "game": "GAME FOLDER", "folder_hint": "Select the AION2 root folder, rather than its Aion2/Content subfolder.",
        "browse": "Browse", "detect": "Auto-detect", "choose_game": "Select the AION2 game folder",
        "language": "Language pack", "turkish": "Turkish (tr)", "source": "Source language: English",
        "native": "Native Turkish pack", "native_hint": "Install the bundled Turkish pack or restore the original files from the verified backup.",
        "inspect": "Check installation", "install": "Apply translation", "restore": "Restore original",
        "target_language": "Target language", "pack_available": "Local pack found; it is checked when applied.",
        "pack_unavailable": "No local pack. Apply opens translation settings for this language.",
        "english_original": "Restores original English files; does not create a translation.",
        "language_code_hint": "Choose a language or type its code (e.g. de, pt-BR).",
        "english_settings": "English is the source language. Use Restore original on the main screen.",
        "validation_hint": "Text keys, tags and numbers are checked in every language. Translation accuracy needs separate review.",
        "create": "Create a translation…", "install_prepared": "Install prepared language…",
        "choose_stage": "Select the language pack folder to install", "prepared": "Language pack prepared. Select its folder when you want to install it.",
        "planned": "The bundled pack is Turkish. Other languages require provider support and separate validation.",
        "activity": "ACTIVITY LOG", "clear": "Clear", "idle": "Ready", "waiting": "Choose a game folder to begin.",
        "working": "Working…", "done": "Operation completed.", "failed": "The operation could not be completed.",
        "detect_work": "Looking for the game folder…", "inspect_work": "Checking the installation…",
        "install_work": "Installing the Turkish pack…", "restore_work": "Restoring original files…",
        "build_work": "Preparing a new translation…", "install_stage_work": "Installing the selected language pack…",
        "repair": "Fix headings (Turkish)", "repair_work": "Repairing Turkish headings…",
        "repair_hint": "Uses compatible title letters (Ö→O, ü→u), while preserving Turkish letters in descriptions.",
        "font_compatible_titles": "Adapt Turkish titles to the game font (Ö→O, ü→u)",
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
        "export_translation": "Export translation…", "export_translation_work": "Exporting the selected language translation…",
        "translation_json_title": "Save the translation JSON for editing",
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


TEXT["tr"].update(auto_update="Güncelleme sonrası otomatik onar", auto_update_work="Çeviri güncellemeye uyarlanıyor…", auto_waiting="Oyun kapanınca çeviri otomatik onarılacak.")
TEXT["en"].update(auto_update="Repair automatically after game updates", auto_update_work="Adapting translation to the update…", auto_waiting="Translation repair will continue after the game closes.")

def localized_service_error(message, language):
    message = str(message)
    if "[WinError 5]" in message:
        return (("Windows oyun dosyasına yazmayı engelledi; kurulum tamamlanmadı. "
                 "Oyunu kapat, uygulama klasöründeki AION2-Global-Translator-Admin.exe ile yeniden açıp tekrar dene.")
                if language == "tr" else "Windows denied access to a game file. Close the game, open AION2-Global-Translator-Admin.exe from the extracted application folder, and retry.")
    match = re.search(r"^(Unsupported Steam build|Language pack build mismatch)\. Found ([^;]+); expected (\d+)\.", message)
    if not match or language != "tr":
        return message
    kind, found, expected = match.groups()
    if kind == "Unsupported Steam build":
        return (f"Oyunun Steam sürümü {found}; bu uygulama {expected} için doğrulandı. "
                "Güncel uygulamayı kullanıp oyun sürümüne uygun yeni dil paketi oluştur. Hiçbir oyun dosyası değiştirilmedi.")
    return (f"Hazır dil paketi {found} sürümüne ait; güncel oyun {expected}. "
            "Eski paketi yeniden kurmak yerine güncel kaynaklardan yeniden oluşturmak gerekiyor. Hiçbir oyun dosyası değiştirilmedi.")


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
        self._log_entries = []
        self._details = None
        self._translation = None
        self.log = None
        self.game_path = tk.StringVar(value=game_dir)
        self.game_status = tk.StringVar()
        self.interface_language = tk.StringVar(value="Türkçe")
        self.selected_language = tk.StringVar(value=language_label("tr"))
        self.status_text = tk.StringVar()
        self.operation_text = tk.StringVar()
        self.progress_text = tk.StringVar(value="")
        self.pack_text = tk.StringVar()
        self.detail_text = tk.StringVar()
        self.validation_text = tk.StringVar()
        self.service = TranslatorService(on_event=self._service_event)
        self._auto_checked = False
        self._auto_timer = None
        settings = self.service.automatic_settings() if hasattr(self.service, "automatic_settings") else {}
        self.auto_enabled = tk.BooleanVar(value=settings.get("enabled", True))
        self._style()
        self._layout()
        self.game_path.trace_add("write", self._path_changed)
        self.selected_language.trace_add("write", self._target_changed)
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
        self.root.geometry("520x520")
        self.root.minsize(520, 520)
        self.root.configure(background="#10151f")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#10151f")
        style.configure("Card.TFrame", background="#192230")
        style.configure("TLabel", background="#10151f", foreground="#e7edf6")
        style.configure("Muted.TLabel", foreground="#9aaac1")
        style.configure("Card.TLabel", background="#192230", foreground="#e7edf6")
        style.configure("CardMuted.TLabel", background="#192230", foreground="#a5b4c9")
        style.configure("Title.TLabel", font=("Segoe UI", 17, "bold"))
        style.configure("Section.TLabel", foreground="#86a1c4", font=("Segoe UI", 9, "bold"))
        style.configure("CardTitle.TLabel", background="#192230", foreground="#e7edf6", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", padding=(12, 8), background="#263449", foreground="#edf3fc", borderwidth=0)
        style.map("TButton", background=[("active", "#344864"), ("disabled", "#1c2839")],
                  foreground=[("disabled", "#6f8098")])
        style.configure("Primary.TButton", background="#4788ee", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#60a0ff"), ("disabled", "#25436d")])
        style.configure("Main.TButton", padding=(14, 9), font=("Segoe UI", 11))
        style.configure("MainPrimary.TButton", padding=(14, 12), background="#4788ee", foreground="#ffffff",
                        font=("Segoe UI", 12, "bold"))
        style.map("MainPrimary.TButton", background=[("active", "#60a0ff"), ("disabled", "#25436d")])
        style.configure("Link.TButton", padding=(8, 4), background="#10151f", foreground="#a9c6ef")
        style.map("Link.TButton", background=[("active", "#192230"), ("disabled", "#10151f")],
                  foreground=[("disabled", "#6f8098")])
        style.configure("Small.TButton", padding=(9, 3))
        style.configure("TEntry", fieldbackground="#101925", foreground="#e7edf6", insertcolor="#e7edf6", padding=7)
        style.configure("TCombobox", fieldbackground="#101925", foreground="#e7edf6", background="#263449", padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", "#101925")], foreground=[("readonly", "#e7edf6")])
        style.configure("Horizontal.TProgressbar", background="#569bff", troughcolor="#243146", borderwidth=0)
        style.configure("TSeparator", background="#2a374a")
        style.configure("TLabelframe", background="#10151f", bordercolor="#2a374a")
        style.configure("TLabelframe.Label", background="#10151f", foreground="#9aaac1")
        style.configure("TCheckbutton", background="#10151f", foreground="#e7edf6", padding=(0, 3))
        style.map("TCheckbutton", background=[("active", "#10151f")])
        self.root.option_add("*TCombobox*Listbox.background", "#192230")
        self.root.option_add("*TCombobox*Listbox.foreground", "#e7edf6")

    def _text(self, widget, key):
        self._bindings.append((widget, key))
        widget.configure(text=self.tr(key))
        return widget

    def _button(self, parent, key, command, **kwargs):
        button = self._text(ttk.Button(parent, command=command, **kwargs), key)
        self._controls.append(button)
        if self._busy:
            button.configure(state="disabled")
        return button

    def _layout(self):
        body = ttk.Frame(self.root, padding=(22, 19, 22, 14))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        self._text(ttk.Label(header, style="Title.TLabel"), "title").grid(row=0, column=0, sticky="w")
        switch = ttk.Combobox(header, values=("Türkçe", "English"), textvariable=self.interface_language,
                              state="readonly", width=8)
        switch.grid(row=0, column=1, sticky="e")
        switch.bind("<<ComboboxSelected>>", self._switch_language)
        self._text(ttk.Label(header, style="Muted.TLabel", wraplength=470), "subtitle").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))

        folder = ttk.Frame(body)
        folder.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        folder.columnconfigure(0, weight=1)
        ttk.Label(folder, textvariable=self.game_status, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self._button(folder, "change_folder", self._browse, style="Link.TButton").grid(row=0, column=1, sticky="e")

        actions = ttk.Frame(body)
        actions.grid(row=2, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)
        self._text(ttk.Label(actions, style="Section.TLabel"), "target_language").grid(row=0, column=0, sticky="w")
        self.target_picker = ttk.Combobox(actions, textvariable=self.selected_language, values=language_choices())
        self.target_picker.grid(row=1, column=0, sticky="ew", pady=(5, 6))
        self._controls.append(self.target_picker)
        ttk.Label(actions, textvariable=self.pack_text, style="Muted.TLabel", wraplength=470).grid(
            row=2, column=0, sticky="w", pady=(0, 11))
        self.apply_button = self._button(actions, "install", self._install, style="MainPrimary.TButton")
        self.apply_button.grid(row=3, column=0, sticky="ew")
        self.repair_button = self._button(actions, "repair", self._repair_headings, style="Main.TButton")
        self.repair_button.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.restore_button = self._button(actions, "restore", self._restore, style="Main.TButton")
        self.restore_button.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        automatic = self._text(ttk.Checkbutton(actions, variable=self.auto_enabled, command=self._automatic_changed), "auto_update")
        automatic.grid(row=6, column=0, sticky="w", pady=(8, 0))
        self._controls.append(automatic)

        progress = ttk.Frame(body)
        progress.grid(row=4, column=0, sticky="ew", pady=(14, 13))
        progress.columnconfigure(0, weight=1)
        ttk.Label(progress, textvariable=self.status_text, style="Muted.TLabel", wraplength=420).grid(row=0, column=0, sticky="w", pady=(0, 7))
        ttk.Label(progress, textvariable=self.progress_text, style="Muted.TLabel").grid(row=0, column=1, sticky="e", pady=(0, 5))
        self.progress = ttk.Progressbar(progress, mode="determinate", maximum=100, length=200)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew")

        footer = ttk.Frame(body)
        footer.grid(row=5, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.settings_button = self._button(footer, "other_languages", self._translation_dialog, style="Link.TButton")
        self.settings_button.grid(row=0, column=0, sticky="w")
        self._text(ttk.Button(footer, command=self._details_dialog, style="Link.TButton"), "details").grid(row=0, column=1, sticky="e")

    def _path_changed(self, *_args):
        self.game_status.set(self.tr("game_selected" if self.game_path.get().strip() else "game_missing"))

    def _automatic_changed(self):
        if hasattr(self.service, "set_automatic"):
            self.service.set_automatic(self.auto_enabled.get())
        if self.auto_enabled.get():
            self._schedule_automatic(150)
        elif self._auto_timer is not None:
            self.root.after_cancel(self._auto_timer)
            self._auto_timer = None

    def _schedule_automatic(self, delay):
        if self._auto_timer is not None:
            self.root.after_cancel(self._auto_timer)
        self._auto_timer = self.root.after(delay, self._automatic_check)

    def _automatic_check(self):
        self._auto_timer = None
        if self._busy:
            self._schedule_automatic(500)
        elif self.auto_enabled.get() and self.game_path.get().strip() and hasattr(self.service, "automatic_update"):
            self._start("auto_update", self.service.automatic_update, self.game_path.get().strip())

    def _switch_language(self, _event=None):
        self.language = "en" if self.interface_language.get() == "English" else "tr"
        self._refresh_language()

    def _refresh_language(self):
        self.root.title(self.tr("title"))
        self._bindings = [(widget, key) for widget, key in self._bindings if widget.winfo_exists()]
        for widget, key in self._bindings:
            widget.configure(text=self.tr(key))
        code = language_code(self.selected_language.get())
        previous_labels = language_choices("tr") + language_choices("en")
        self.target_picker.configure(values=language_choices(self.language))
        if code and self.selected_language.get() in previous_labels:
            self.selected_language.set(language_label(code, self.language))
        work_key = self._operation + "_work" if self._operation else "working"
        self.status_text.set(self.tr(work_key) if self._busy else self.tr(self._status_key))
        self.operation_text.set(self.tr(work_key) if self._busy else self.tr("idle"))
        self._path_changed()
        self._inspection_details()
        self._target_changed()
        if self._details and self._details.winfo_exists():
            self._details.title(self.tr("details_title"))

    def _prepared_stage(self, code):
        """Read local availability only; service validates the pack at application."""
        data = getattr(self.service, "data", None)
        if data is None:
            return None
        stage = Path(data) / "stages" / code
        if not (stage / "L10NString.dat").is_file() or not (stage / "patch-meta.json").is_file():
            return None
        try:
            meta = json.loads((stage / "patch-meta.json").read_text("utf-8"))
        except (OSError, ValueError):
            return None
        if (not isinstance(meta, dict) or not isinstance(meta.get("target_language"), str)
                or language_code(meta["target_language"]) != code or not meta.get("quality_gate_passed")):
            return None
        return stage

    def _target_changed(self, *_args):
        code = language_code(self.selected_language.get())
        valid = code is not None
        english = valid and original_language(code)
        turkish = valid and turkish_language(code)
        if not valid:
            self.pack_text.set(self.tr("language_code_hint"))
        else:
            key = "english_original" if english else ("pack_available" if self._prepared_stage(code) else "pack_unavailable")
            self.pack_text.set(language_label(code, self.language) + "  ·  " + self.tr(key))
        self.apply_button.configure(text=self.tr("restore" if english else "install"),
                                    state="normal" if valid and not self._busy else "disabled")
        self.repair_button.configure(state="normal" if turkish and not self._busy else "disabled")
        self.settings_button.configure(state="normal" if valid and not english and not self._busy else "disabled")
        export_button = getattr(self, "export_translation_button", None)
        if export_button is not None and export_button.winfo_exists():
            export_button.configure(state="normal" if valid and not english and not self._busy else "disabled")
        if english:
            self.restore_button.grid_remove()
        else:
            self.restore_button.grid()
        self.validation_text.set(self.tr("validation_hint") + ("\n" + self.tr("repair_hint") if turkish else ""))

    def _set_controls(self, state):
        self._controls = [widget for widget in self._controls if widget.winfo_exists()]
        for widget in self._controls:
            widget.configure(state=state)

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
        self._set_controls("disabled")
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
                error = localized_service_error(self._redact(item[2]), self.language) or self.tr("failed")
                self._log(error, "error")
                if not item[3]:
                    messagebox.showerror(self.tr("error_title"), error, parent=self.root)
            elif kind == "done":
                self._busy = False
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self._set_controls("normal")
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
            if path:
                self.root.after(150, lambda: self._inspect(quiet=True))
            return
        if isinstance(result, dict):
            if operation == "inspect" or (operation in ("install", "install_stage", "restore", "repair")
                                          and result.get("status") in ("installed", "original")):
                self._last_inspection = result
                self._inspection_details()
            if result.get("message"):
                self._log(str(result["message"]), "success")
            for key in ("output_dir", "output_path", "stage_path", "stage", "source_json"):
                if result.get(key):
                    self._log(self.tr("output") + ": " + str(result[key]))
            if operation == "build" and result.get("status") == "prepared":
                self._status_key = "prepared"
        if operation == "inspect" and not self._auto_checked:
            self._auto_checked = True
            self._schedule_automatic(150)
        if operation == "auto_update" and isinstance(result, dict):
            waiting = result.get("status") == "waiting_game"
            if waiting:
                self._status_key = "auto_waiting"
            self._schedule_automatic(3000 if waiting else 15000)
        if operation == "restore":
            self.auto_enabled.set(False)
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
        text = self._redact(message)
        level = str(level).lower()
        self._log_entries.append((text, level))
        if len(self._log_entries) > 2500:
            del self._log_entries[:500]
        if not self.log or not self.log.winfo_exists():
            return
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", level)
        # Bound memory use during large translation jobs.
        if int(self.log.index("end-1c").split(".")[0]) > 2500:
            self.log.delete("1.0", "501.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self._log_entries.clear()
        if self.log and self.log.winfo_exists():
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            self.log.configure(state="disabled")

    def _details_dialog(self):
        if self._details and self._details.winfo_exists():
            self._details.lift()
            return
        dialog = self._details = tk.Toplevel(self.root)
        dialog.title(self.tr("details_title"))
        dialog.configure(background="#10151f")
        dialog.geometry("760x570")
        dialog.minsize(640, 500)
        dialog.transient(self.root)
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(7, weight=1)
        self._text(ttk.Label(frame, style="Section.TLabel"), "game").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.game_path, state="readonly").grid(row=1, column=0, sticky="ew", pady=(6, 8))
        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, sticky="w")
        self._button(actions, "inspect", self._inspect, style="Small.TButton").pack(side="left", padx=(0, 8))
        self._button(actions, "detect", self._detect, style="Small.TButton").pack(side="left")
        summary = ttk.Label(frame, textvariable=self.detail_text, style="Muted.TLabel", wraplength=700)
        summary.grid(row=3, column=0, sticky="ew", pady=(9, 5))
        validation = ttk.Label(frame, textvariable=self.validation_text, style="Muted.TLabel", wraplength=700)
        validation.grid(row=4, column=0, sticky="ew", pady=(0, 14))

        def reflow(event):
            if event.widget == dialog:
                summary.configure(wraplength=max(300, event.width - 60))
                validation.configure(wraplength=max(300, event.width - 60))

        dialog.bind("<Configure>", reflow)

        advanced = ttk.LabelFrame(frame, padding=10)
        self._text(advanced, "advanced_files")
        advanced.grid(row=5, column=0, sticky="ew", pady=(0, 15))
        self._button(advanced, "export_source", self._export_source, style="Small.TButton").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._button(advanced, "install_prepared", self._install_prepared, style="Small.TButton").grid(row=0, column=1, sticky="w")
        self.export_translation_button = self._button(advanced, "export_translation", self._export_translation, style="Small.TButton")
        self.export_translation_button.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._target_changed()

        heading = ttk.Frame(frame)
        heading.grid(row=6, column=0, sticky="ew", pady=(0, 6))
        heading.columnconfigure(0, weight=1)
        self._text(ttk.Label(heading, style="Section.TLabel"), "activity").grid(row=0, column=0, sticky="w")
        self._text(ttk.Button(heading, command=self._clear_log, style="Small.TButton"), "clear").grid(row=0, column=1, sticky="e")
        logs = ttk.Frame(frame)
        logs.grid(row=7, column=0, sticky="nsew")
        logs.columnconfigure(0, weight=1)
        logs.rowconfigure(0, weight=1)
        self.log = tk.Text(logs, height=8, wrap="word", background="#0b111b", foreground="#bdcbe0",
                           insertbackground="#e7edf6", relief="flat", borderwidth=0, padx=11, pady=9,
                           font=("Consolas", 9), state="disabled", takefocus=True)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(logs, command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.tag_configure("error", foreground="#ff999d")
        self.log.tag_configure("warning", foreground="#efc878")
        self.log.tag_configure("success", foreground="#8bd5b4")
        self.log.configure(state="normal")
        for text, level in self._log_entries:
            self.log.insert("end", text + "\n", level)
        self.log.see("end")
        self.log.configure(state="disabled")

        def close():
            self.log = None
            self._details = None
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close)

    def _export_source(self):
        game = self._game()
        if game:
            self._start("export", self.service.export_source, game)

    def _export_translation(self):
        if self._busy:
            return
        code = language_code(self.selected_language.get())
        if code is None or original_language(code):
            return
        destination = filedialog.asksaveasfilename(parent=self._details or self.root,
            title=self.tr("translation_json_title"), defaultextension=".json",
            initialfile="AION2-" + code + ".json", filetypes=[("JSON", "*.json")])
        if destination:
            self._start("export_translation", self.service.export_translation, code, destination)

    def _browse(self):
        if self._busy:
            return
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
        if self._busy:
            return
        code = language_code(self.selected_language.get())
        if code is None:
            messagebox.showerror(self.tr("error_title"), self.tr("bad_code"), parent=self.root)
            return
        path = self._game()
        if path:
            if original_language(code):
                self._start("restore", self.service.apply_language, path, "en")
            elif self._prepared_stage(code):
                self._start("install_stage", self.service.apply_language, path, code)
            else:
                self._translation_dialog(target_code=code)

    def _restore(self):
        path = self._game()
        if path:
            self._start("restore", self.service.apply_language, path, "en")

    def _repair_headings(self):
        code = language_code(self.selected_language.get())
        if self._busy or code is None or not turkish_language(code):
            return
        path = self._game()
        if path:
            self._start("repair", self.service.repair_turkish_headings, path)

    def _install_prepared(self):
        if self._busy:
            return
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

    def _translation_dialog(self, target_code=None):
        if self._busy:
            return
        code = language_code(target_code or self.selected_language.get())
        if code is None:
            messagebox.showerror(self.tr("error_title"), self.tr("bad_code"), parent=self.root)
            return
        if original_language(code):
            messagebox.showinfo(self.tr("title"), self.tr("english_settings"), parent=self.root)
            return
        if self._translation and self._translation.winfo_exists():
            self._translation_target.set(code)
            self._translation.lift()
            return
        game = self._game()
        if not game:
            return
        dialog = self._translation = tk.Toplevel(self.root)
        dialog.title(self.tr("create_title"))
        dialog.configure(background="#10151f")
        dialog.geometry("640x600")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=22)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=self.tr("create_intro"), wraplength=570).grid(row=0, column=0, sticky="w", pady=(0, 15))
        target = self._translation_target = tk.StringVar(value=code)
        provider = tk.StringVar(value=self.tr("offline"))
        json_path = tk.StringVar()
        review_unchanged = tk.BooleanVar(value=False)
        font_compatible_titles = tk.BooleanVar(value=True)
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
        font_option = ttk.Checkbutton(frame, text=self.tr("font_compatible_titles"), variable=font_compatible_titles)
        font_option.grid(row=7, column=0, sticky="w", pady=(14, 0))

        def target_changed(*_args):
            target_code = language_code(target.get())
            is_turkish = bool(target_code and turkish_language(target_code))
            font_option.configure(state="normal" if is_turkish else "disabled")
            font_compatible_titles.set(is_turkish)

        target.trace_add("write", target_changed)
        target_changed()
        ttk.Label(frame, text=self.tr("build_notice"), style="Muted.TLabel", wraplength=585).grid(row=8, column=0, sticky="sw", pady=(12, 10))
        frame.rowconfigure(8, weight=1)
        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, sticky="e")

        def create():
            language = language_code(target.get())
            if language is None:
                messagebox.showerror(self.tr("error_title"), self.tr("bad_code"), parent=dialog)
                return
            if original_language(language):
                messagebox.showinfo(self.tr("title"), self.tr("english_settings"), parent=dialog)
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
            configuration["font_compatible_titles"] = turkish_language(language) and font_compatible_titles.get()
            dialog.destroy()
            self.selected_language.set(language_label(language, self.language))
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
