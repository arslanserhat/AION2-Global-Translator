import unittest

from aion2_global_translator.display import PROFILE, apply_turkish_heading_compatibility
from aion2_global_translator.protection import protected_literals


class TurkishHeadingDisplayTests(unittest.TestCase):
    def test_circumflex_missing_from_heading_fonts_is_folded_only_in_selected_visible_text(self):
        entries = {"SkillString_SAMPLE_skill_name": "Rüzgâr Âlemi", "NpcTalk_SAMPLE_cv_text": "Rüzgâr âlemi"}
        result, _ = apply_turkish_heading_compatibility(entries)
        self.assertEqual(result["SkillString_SAMPLE_skill_name"], "Ruzgar Alemi")
        self.assertEqual(result["NpcTalk_SAMPLE_cv_text"], entries["NpcTalk_SAMPLE_cv_text"])

    def test_selected_headings_change_while_bodies_keep_turkish_letters(self):
        entries = {
            "SkillString_EXAMPLE_skill_name": "Keskin Atış",
            "SkillAbnormalString_EXAMPLE_desc_name": "Güçlü Koruyucu",
            "AchievementString_EXAMPLE_achievement_title": "Çığ Gibi",
            "QuestString_EXAMPLE_quest_title": "İçimizdeki Işık",
            "GuideData_EXAMPLE_title": "Öğrenmeye Başla",
            "String_UI_ACHIEVEMENT_GETREWARD_TITLE_body": "Ödül Kazanıldı",
            "String_UI_ACHIEVEMENT_GET_REWARD_LIST_TITLE_body": "Ödül Listesi",
            "SkillString_EXAMPLE_skill_desc_effect": "Rüzgâr hasarı verir ve güç kazandırır.",
            "SkillString_EXAMPLE_specialized_skill_desc": "Güçlendirme süresi uzar.",
            "QuestString_EXAMPLE_step1_obj_1": "İçerideki kişiye ulaş.",
            "QuestString_EXAMPLE_quest_summary": "Işığı arayan kişinin öyküsü.",
            "NpcTalk_EXAMPLE_cv_text": "Görüşürüz, güçlü savaşçı!",
        }
        before = dict(entries)
        result, report = apply_turkish_heading_compatibility(entries)
        self.assertEqual(result["SkillString_EXAMPLE_skill_name"], "Keskin Atis")
        self.assertEqual(result["String_UI_ACHIEVEMENT_GETREWARD_TITLE_body"], "Odul Kazanildi")
        self.assertEqual(result["String_UI_ACHIEVEMENT_GET_REWARD_LIST_TITLE_body"], "Odul Listesi")
        for key in entries:
            if key not in report["affected_fields"]:
                self.assertEqual(result[key], entries[key])
        self.assertEqual(entries, before)
        self.assertIsNot(result, entries)
        self.assertEqual(report["changed_entries"], 7)
        self.assertEqual(report["profile"], PROFILE)

    def test_item_names_are_explicit_and_description_title_words_do_not_trigger_it(self):
        entries = {
            "String_STR_ITEM_EXAMPLE_body": "Gümüş Kılıç",
            "String_STR_ITEM_EXAMPLE_DESC_body": "İşlendiğinde güç kazandırır.",
            "String_STR_ITEM_EXAMPLE_DESC2_body": "Gümüş renkli eski bir eşya.",
            "String_UI_EXAMPLE_TITLE_DESCRIPTION_body": "Başlık öğesinin açıklaması.",
            "String_UI_EXAMPLE_TITLE_EFFECT_body": "Başlık etkisi güç kazandırır.",
            "SkillString_TITLE_EXAMPLE_skill_desc_effect": "Başlık etkisi güçlüdür.",
        }
        result, report = apply_turkish_heading_compatibility(entries)
        self.assertEqual(result["String_STR_ITEM_EXAMPLE_body"], "Gumus Kilic")
        self.assertEqual(report["affected_fields"], ["String_STR_ITEM_EXAMPLE_body"])
        for key in entries:
            if key != "String_STR_ITEM_EXAMPLE_body":
                self.assertEqual(result[key], entries[key])

    def test_nested_macros_markup_printf_numbers_and_controls_remain_exact(self):
        key = "SkillString_EXAMPLE_skill_name"
        text = '<style label="ğ">Çığ {öğe:{0}}</> %s +12.5%\r\n①\\n'
        result, report = apply_turkish_heading_compatibility({key: text})
        self.assertEqual(result[key], '<style label="ğ">Cig {öğe:{0}}</> %s +12.5%\r\n①\\n')
        self.assertEqual(protected_literals(text), protected_literals(result[key]))
        self.assertTrue(report["protected_literals_preserved"])

    def test_idempotence_and_other_unicode_are_preserved(self):
        entries = {"QuestString_EXAMPLE_quest_title": "İçgörü — Été Ω 中 ñ ə", "NpcTalk_EXAMPLE_cv_text": "İçgörü"}
        first, _ = apply_turkish_heading_compatibility(entries)
        second, report = apply_turkish_heading_compatibility(first)
        self.assertEqual(first, second)
        self.assertEqual(first["QuestString_EXAMPLE_quest_title"], "Icgoru — Été Ω 中 ñ ə")
        self.assertEqual(first["NpcTalk_EXAMPLE_cv_text"], "İçgörü")
        self.assertEqual(report["changed_entries"], 0)
        self.assertEqual(report["affected_fields"], [])

    def test_report_contains_every_changed_key_without_a_display_cap(self):
        entries = {f"Example_{index:04}_title": "Çığ" for index in range(301)}
        _, report = apply_turkish_heading_compatibility(entries)
        self.assertEqual(report["changed_entries"], 301)
        self.assertEqual(report["affected_fields"], sorted(entries))

    def test_invalid_flat_dictionary_is_rejected(self):
        for entries in (None, ["text"], {1: "text"}, {"key": None}):
            with self.assertRaises(TypeError):
                apply_turkish_heading_compatibility(entries)


if __name__ == "__main__":
    unittest.main()
