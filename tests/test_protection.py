import html
import unittest

from aion2_global_translator.protection import has_linguistic_content, prepare, protected_literals, validate


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


if __name__ == "__main__":
    unittest.main()
