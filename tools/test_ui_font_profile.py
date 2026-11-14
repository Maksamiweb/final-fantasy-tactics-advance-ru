import unittest
import project

class UIFontProfileTests(unittest.TestCase):
    def setUp(self):
        self.reverse={'А':project.COUNT,'а':project.COUNT+33,'A':175}
    def test_default_profile_keeps_existing_indices(self):
        self.assertEqual(project.encode_entry({'ru':'АA'},self.reverse),project.encode('АA',self.reverse))
    def test_compact_changes_only_new_cyrillic_slots(self):
        tokens=project.encode_entry({'ru':'АA[[U123]]','font_profile':'compact_ui'},self.reverse)
        self.assertEqual(tokens,[('CHR_FULL',project.COUNT+len(project.ALPHABET)),('CHR_FULL',175),('CHR_FULL',0x123)])
    def test_controls_preserved(self):
        text='А[[1B01]][[1D03]]а[[42]]'
        default=project.encode_entry({'ru':text},self.reverse)
        compact=project.encode_entry({'ru':text,'font_profile':'compact_ui'},self.reverse)
        self.assertEqual(project.structural(default),project.structural(compact))
    def test_unknown_profile_rejected(self):
        with self.assertRaises(AssertionError):project.encode_entry({'ru':'А','font_profile':'bad'},self.reverse)

if __name__=='__main__':unittest.main()
