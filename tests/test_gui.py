"""Language selection and Tk worker tests. Every service operation is a fake."""
import json
from pathlib import Path
import shutil
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch
import uuid

from aion2_global_translator import gui
from aion2_global_translator.languages import language_choices, language_code, language_label


class LanguageCatalog(unittest.TestCase):
    def test_native_labels_custom_codes_and_source_english_parse_safely(self):
        for interface in ("tr", "en"):
            self.assertEqual(language_code(language_label("en", interface)), "en")
            self.assertEqual(language_code(language_label("de", interface)), "de")
        self.assertEqual(language_code("pt_br"), "pt-BR")
        self.assertEqual(language_code("zh-hant"), "zh-Hant")
        self.assertEqual(language_code("fil"), "fil")
        for value in ("", "../de", "de/../../tr", "german", "zh-Hant-CN", "x"):
            self.assertIsNone(language_code(value), value)
        self.assertIn("Français (fr)", language_choices())


class FakeService:
    def __init__(self, on_event, data):
        self.on_event, self.data = on_event, data
        self.calls = []
        self.gate = None

    def inspect(self, game):
        self.calls.append(("inspect", game, threading.get_ident()))
        self.on_event(dict(message="Synthetic progress", progress=25))
        if self.gate:
            self.gate.wait(2)
        return dict(status="original", installed_language=None, entries=4, build="synthetic")

    def detect_game(self):
        self.calls.append(("detect", threading.get_ident()))
        return "synthetic-game"

    def apply_language(self, game, code):
        self.calls.append(("apply", game, code, threading.get_ident()))
        return dict(status="original" if code == "en" else "installed", installed_language=code, entries=4)

    def repair_turkish_headings(self, game):
        self.calls.append(("repair", game, threading.get_ident()))
        return dict(status="installed", installed_language="tr", entries=4)

    def export_translation(self, code, destination):
        self.calls.append(("export_translation", code, destination, threading.get_ident()))
        return dict(output_path=destination)

    def export_source(self, game):
        return dict(source_json="synthetic-source.json")


class LanguageSelectionGUI(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest("Tk display unavailable: " + str(error))
        self.root.withdraw()
        parent = (Path.cwd() / "build/test-fixtures").resolve()
        parent.mkdir(parents=True, exist_ok=True)
        self.folder = parent / ("gui-" + uuid.uuid4().hex)
        self.folder.mkdir()
        self.assertTrue(self.folder.is_relative_to(parent))
        self.addCleanup(shutil.rmtree, self.folder)
        def factory(on_event):
            self.fake = FakeService(on_event, self.folder)
            return self.fake
        self.factory = patch.object(gui, "TranslatorService", side_effect=factory)
        self.factory.start()
        self.addCleanup(self.factory.stop)
        self.info = patch.object(gui.messagebox, "showinfo")
        self.error = patch.object(gui.messagebox, "showerror")
        self.info.start()
        self.error.start()
        self.addCleanup(self.info.stop)
        self.addCleanup(self.error.stop)
        self.app = gui.TranslatorApp(self.root, "synthetic-game")
        # Cancel startup timers: no auto inspect/detect call is part of these tests.
        for timer in self.root.tk.call("after", "info"):
            self.root.after_cancel(timer)
        self.root.update_idletasks()
        self.addCleanup(self.close)

    def close(self):
        if self.fake.gate:
            self.fake.gate.set()
        if self.root.winfo_exists():
            self.root.update_idletasks()
            for timer in self.root.tk.call("after", "info"):
                self.root.after_cancel(timer)
            self.root.destroy()

    def ready(self, code, *, target=None):
        stage = self.folder / "stages" / code
        stage.mkdir(parents=True)
        (stage / "L10NString.dat").write_bytes(b"synthetic pack - never installed")
        (stage / "patch-meta.json").write_text(json.dumps(dict(target_language=target or code, quality_gate_passed=True)), encoding="utf-8")
        return stage

    def finish(self):
        deadline = time.monotonic() + 3
        while self.app._busy and time.monotonic() < deadline:
            self.app._poll()
            self.root.update()
            time.sleep(0.005)
        self.assertFalse(self.app._busy)

    def test_ready_language_uses_generic_apply_and_english_restores_without_building(self):
        self.ready("de")
        self.app.selected_language.set("Deutsch (de)")
        self.assertIn("Yerel paket bulundu", self.app.pack_text.get())
        self.assertEqual(str(self.app.repair_button["state"]), "disabled")
        self.app._install()
        self.finish()
        self.assertEqual(self.fake.calls[0][:3], ("apply", "synthetic-game", "de"))
        self.assertNotEqual(self.fake.calls[0][-1], threading.get_ident())
        self.app.selected_language.set(language_label("en"))
        self.assertEqual(self.app.apply_button["text"], "Orijinale dön")
        self.assertEqual(str(self.app.settings_button["state"]), "disabled")
        with patch.object(self.app, "_translation_dialog") as dialog:
            self.app._install()
            self.finish()
            dialog.assert_not_called()
        self.assertEqual(self.fake.calls[-1][:3], ("apply", "synthetic-game", "en"))

    def test_missing_pack_opens_settings_with_selected_code_and_tr_fix_stays_scoped(self):
        self.app.selected_language.set("fr")
        self.assertIn("Yerel paket yok", self.app.pack_text.get())
        with patch.object(self.app, "_translation_dialog") as dialog:
            self.app._install()
            dialog.assert_called_once_with(target_code="fr")
        self.app._repair_headings()
        self.assertEqual(self.fake.calls, [])
        self.app._translation_dialog()
        self.assertEqual(self.app._translation_target.get(), "fr")
        self.app._translation.destroy()
        self.app.selected_language.set("tr")
        self.assertEqual(str(self.app.repair_button["state"]), "normal")
        self.app._repair_headings()
        self.finish()
        self.assertEqual(self.fake.calls[-1][0], "repair")

    def test_bad_stage_language_cannot_be_selected_as_ready(self):
        self.ready("es", target="tr")
        self.app.selected_language.set("es")
        self.assertIsNone(self.app._prepared_stage("es"))
        self.app.selected_language.set("../../elsewhere")
        self.assertEqual(str(self.app.apply_button["state"]), "disabled")

    def test_interface_language_switch_keeps_the_game_target(self):
        self.app.selected_language.set("Deutsch (de)")
        self.app.interface_language.set("English")
        self.app._switch_language()
        self.assertEqual(language_code(self.app.selected_language.get()), "de")
        self.assertEqual(self.app.apply_button["text"], "Apply translation")
        self.assertIn("No local pack", self.app.pack_text.get())
        self.assertEqual(str(self.app.repair_button["state"]), "disabled")

    def test_worker_queue_disables_picker_and_duplicate_operation_is_ignored(self):
        self.fake.gate = threading.Event()
        self.app._inspect()
        deadline = time.monotonic() + 1
        while not self.fake.calls and time.monotonic() < deadline:
            time.sleep(0.005)
        self.app._inspect()
        self.app._poll()
        self.assertEqual(len(self.fake.calls), 1)
        self.assertNotEqual(self.fake.calls[0][-1], threading.get_ident())
        self.assertEqual(str(self.app.target_picker["state"]), "disabled")
        self.assertEqual(self.app.progress_text.get(), "25%")
        self.fake.gate.set()
        self.finish()
        self.assertEqual(str(self.app.target_picker["state"]), "normal")
        self.assertEqual(self.app.progress_text.get(), "100%")

    def test_export_uses_selected_language_and_background_service_api(self):
        self.app.selected_language.set("de")
        destination = str(self.folder / "edited-de.json")
        with patch.object(gui.filedialog, "asksaveasfilename", return_value=destination):
            self.app._export_translation()
            self.finish()
        self.assertEqual(self.fake.calls[-1][:3], ("export_translation", "de", destination))
        self.assertFalse(Path(destination).exists())

    def assert_inside(self, window):
        self.root.update_idletasks()
        left, top, width, height = window.winfo_rootx(), window.winfo_rooty(), window.winfo_width(), window.winfo_height()
        def descendants(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Toplevel):
                    continue
                yield child
                yield from descendants(child)
        for widget in descendants(window):
            if not widget.winfo_viewable():
                continue
            with self.subTest(widget=str(widget)):
                self.assertGreaterEqual(widget.winfo_rootx(), left - 1)
                self.assertGreaterEqual(widget.winfo_rooty(), top - 1)
                self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), left + width + 1)
                self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), top + height + 1)

    def test_main_details_and_prefilled_translation_geometry_in_both_interfaces(self):
        self.root.deiconify()
        for interface in ("Türkçe", "English"):
            self.app.interface_language.set(interface)
            self.app._switch_language()
            self.app.selected_language.set(language_label("pt-BR", self.app.language))
            self.root.update()
            self.assertEqual(self.root.winfo_width(), 520)
            self.assert_inside(self.root)
            self.app._details_dialog()
            self.root.update()
            self.assert_inside(self.app._details)
            self.app._details.geometry("640x500")
            self.root.update()
            self.assert_inside(self.app._details)
            self.app._details.destroy()
            self.app._translation_dialog()
            self.root.update()
            self.assertEqual(self.app._translation_target.get(), "pt-BR")
            self.assert_inside(self.app._translation)
            self.app._translation.destroy()


if __name__ == "__main__":
    unittest.main()
