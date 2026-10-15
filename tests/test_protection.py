import html
import unittest

from aion2_global_translator.protection import GAME_ABBREVIATIONS, has_linguistic_content, prepare, protected_literals, validate


class ProtectionTests(unittest.TestCase):
    def test_utf8_fragment_preserves_nested_macros_rich_text_controls_and_stats(self):
        source = '<accent>Damage {effect:{0}}</> +12.5%\r\nCooldown: %02d seconds\\n①'
        item = prepare(source)
        translated_html = item.html.replace("Damage", "Hasar").replace("Cooldown", "Bekleme").replace("seconds", "saniye")
        result = item.restore(translated_html)
        self.assertEqual(result, '<accent>Hasar {effect:{0}}</> +12.5%\r\nBekleme: %02d saniye\\n①')
        self.assertEqual(protected_literals(source), protected_literals(result))

    def test_indexed_macros_can_move_with_turkish_grammar(self):
        item = prepare("{0} gives {1} a gift.")
        tokens = list(item.placeholders)
        result = item.restore(f'{tokens[1]} için {tokens[0]} bir hediye verir.')
        self.assertEqual(result, "{1} için {0} bir hediye verir.")

    def test_identical_tag_pairs_may_move_but_actual_tag_order_must_remain_valid(self):
        item = prepare("<accent>Before</> and <accent>after</>")
        tokens = list(item.placeholders)
        result = item.restore(f"{tokens[2]}sonra{tokens[3]} ve {tokens[0]}önce{tokens[1]}")
        self.assertEqual(result, "<accent>sonra</> ve <accent>önce</>")
        with self.assertRaises(ValueError):
            item.restore(f"{tokens[1]}önce{tokens[0]} ve {tokens[2]}sonra{tokens[3]}")

    def test_identical_nonpositional_printf_arguments_keep_their_identity(self):
        item = prepare("Owner %s and recipient %s")
        tokens = list(item.placeholders)
        with self.assertRaises(ValueError):
            item.restore(f"Alıcı {tokens[1]}, sahibi {tokens[0]}")

    def test_missing_duplicate_and_modified_literals_are_rejected(self):
        item = prepare("Value {0} at 20%")
        token = next(iter(item.placeholders))
        for response in ("Değer yok", item.html + token, item.html.replace(token, "broken")):
            with self.assertRaises(ValueError):
                item.restore(response)
        for source, target in (("Chance 20%", "Şans 21%"), ("Line\nNext", "Satır Sonraki"),
                               ("Choice ①", "Seçim 1"), ("Count {value}", "Sayı {other}")):
            with self.assertRaises(ValueError):
                validate(source, target)

    def test_content_detection_does_not_freeze_user_facing_square_bracket_labels(self):
        self.assertTrue(has_linguistic_content("[Example class]"))
        self.assertTrue(has_linguistic_content("100% chance"))
        self.assertFalse(has_linguistic_content("<accent>{value:{0}}</> ① 100%\\n"))

    def test_percent_possessive_is_readable_without_inventing_a_printf_directive(self):
        item = prepare("{value}% of health")
        token = next(iter(item.placeholders))
        self.assertEqual(item.restore(token + "%’si kadar can"), "{value}%’si kadar can")
        self.assertEqual(item.restore(token + "%'si kadar can"), "{value}%’si kadar can")
        actual_printf = prepare("Name %'s")
        token = next(iter(actual_printf.placeholders))
        self.assertEqual(actual_printf.restore("Ad " + token), "Ad %'s")

    def test_plain_angle_characters_entities_and_preexisting_token_shape_roundtrip(self):
        for source in ('2 < 3 & "quoted"', "&amp; remains an entity", "__A2PH00000__ marker 4"):
            item = prepare(source)
            self.assertEqual(item.restore(item.html), source)
        self.assertEqual(prepare("Hello").restore(html.escape("Merhaba & iyi günler")), "Merhaba & iyi günler")

    def test_game_mechanics_abbreviations_are_hidden_from_the_html_provider(self):
        source = "Restores 20 HP and 10 MP during PvP combat."
        item = prepare(source)
        for abbreviation in ("HP", "MP", "PvP"):
            self.assertIn(abbreviation, item.placeholders.values())
            self.assertNotIn(abbreviation, item.html)
        target = item.restore(item.html.replace("Restores", "Yeniler").replace("and", "ve").replace("during", "sırasında").replace("combat", "savaş"))
        self.assertIn("20 HP", target)
        self.assertIn("10 MP", target)
        self.assertEqual(protected_literals(source), protected_literals(target))

    def test_hp_mp_may_move_with_grammar_but_exact_counts_are_mandatory(self):
        validate("Restores HP and consumes MP", "MP harcar ve HP yeniler")
        for target in ("HP harcar ve HP yeniler", "MP harcar ve can yeniler", "Milletvekili ve beygir gücü yeniler"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate("Restores HP and consumes MP", target)
        with self.assertRaises(ValueError):
            validate("HP HP MP", "HP MP MP")

    def test_domain_abbreviations_are_case_sensitive_whole_ascii_words(self):
        source = "HP hp Hp CHPower MP3 EXPRESSION DPS_counter hpMP NPCs AoE DoT HoT"
        literals = protected_literals(source)
        self.assertEqual(literals["HP"], 1)
        for value in ("MP", "EXP", "DPS", "NPC"):
            self.assertNotIn(value, literals)
        self.assertEqual([value for value in ("AoE", "DoT", "HoT") if literals[value] == 1], ["AoE", "DoT", "HoT"])
        self.assertFalse(has_linguistic_content(" / ".join(GAME_ABBREVIATIONS)))
        self.assertTrue(has_linguistic_content("Restores HP"))

    def test_macros_and_tag_attributes_contain_no_nested_abbreviation_tokens(self):
        source = '{effect:{HP:MP}} <accent title="HP MP">PvP</> HP'
        item = prepare(source)
        values = list(item.placeholders.values())
        self.assertIn("{effect:{HP:MP}}", values)
        self.assertIn('<accent title="HP MP">', values)
        self.assertEqual(values.count("HP"), 1)
        self.assertNotIn("MP", values)
        self.assertEqual(item.restore(item.html), source)

    def test_turkish_expansion_cannot_silently_replace_the_stat_abbreviation(self):
        with self.assertRaises(ValueError):
            validate("Restores HP", "Can yeniler")
        validate("Restores HP", "HP yeniler")

    def test_cjk_words_with_numeric_properties_remain_translatable(self):
        self.assertEqual(prepare("Join").restore("参加"), "参加")
        validate("Join", "参加")
        reference = prepare("参照")
        self.assertEqual(reference.html, "参照")
        self.assertEqual(reference.restore("Reference"), "Reference")
        self.assertFalse(protected_literals("一緒に参加"))
        self.assertTrue(has_linguistic_content("一"))

    def test_unicode_number_symbols_ascii_and_arabic_digits_stay_strict(self):
        source = "Stage ① Ⅳ x² ½ 12 ١٢"
        item = prepare(source)
        target = item.restore(item.html.replace("Stage", "Aşama"))
        self.assertEqual(target, "Aşama ① Ⅳ x² ½ 12 ١٢")
        for before, after in [("①", "1"), ("Ⅳ", "IV"), ("²", "2"), ("½", ".5"),
                              ("12", "13"), ("١٢", "12")]:
            with self.subTest(number=before), self.assertRaises(ValueError):
                validate(source, target.replace(before, after))

    def test_cjk_macro_names_and_tag_attributes_still_remain_exact_literals(self):
        source = '<accent title="参一">Reference {参:一} %s</>'
        item = prepare(source)
        target = item.restore(item.html.replace("Reference", "参照"))
        self.assertEqual(target, '<accent title="参一">参照 {参:一} %s</>')
        self.assertIn('<accent title="参一">', item.placeholders.values())
        self.assertIn("{参:一}", item.placeholders.values())
        with self.assertRaises(ValueError):
            validate(source, target.replace("{参:一}", "{ref:one}"))


if __name__ == "__main__":
    unittest.main()
