import unittest
import prepare
from project import validate_level_suffix

class DynamicFieldTests(unittest.TestCase):
    def test_dynamic_name_and_punctuation_wrap_together(self):
        self.assertEqual(prepare.wrap('A [[40C]]!', {'A':0,'!':1}, [10,4], 90,
                                     dynamic_widths={'040C':81}), 'A\n[[40C]]!')

    def test_icon_and_title_both_use_reserved_width(self):
        self.assertEqual(prepare.wrap('A [[4600]][[41C]]', {'A':0}, [10], 130,
                                     dynamic_widths={'4600':16,'041C':104}),
                         'A\n[[4600]][[41C]]')

    def test_json_catalog_tokens_are_accepted(self):
        tokens=[['CTR_FUNC',0x418]]+[['CHR_FULL',i]for i in range(5)]+[['CTR_FUNC',0x41a]]
        validate_level_suffix(tokens,[tuple(t)for t in tokens])

if __name__=='__main__': unittest.main()
