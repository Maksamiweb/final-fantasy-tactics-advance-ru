import unittest
from classify_remaining_text import classify

class TextClassificationTests(unittest.TestCase):
    def test_placeholders_and_reserved_names(self):
        for text in ['Dummy[[40]][[42]]','(not used)','CRN_NAME071','-']:
            self.assertEqual(classify(text),'placeholder_or_reserved')
    def test_unmapped_glyph_is_not_blank(self):
        self.assertEqual(classify('[[U1E6]][[40]][[42]]'),'unmapped_glyph_content')
    def test_controls_without_words_need_no_authored_translation(self):
        self.assertEqual(classify('[[4600]][[41C]][[42]]'),'empty_or_control_only')
    def test_localized_dynamic_name_is_not_an_english_sentence(self):
        self.assertEqual(classify('...?[[5108]]?[[5108]]![[40]][[42]]'),'dynamic_name_and_punctuation')
    def test_cut_marker_is_only_a_candidate_not_unreachable_proof(self):
        self.assertEqual(classify('カット[[U9F2]]300[[40]][[42]]'),'japanese_cut_label_candidate')
    def test_japanese_after_end_is_kept_separate(self):
        self.assertEqual(classify('[[40]][[42]]モーグリ'),'japanese_after_end_marker_candidate')
    def test_real_english_text_is_a_candidate(self):
        self.assertEqual(classify('[[103]]Hello, kupo![[40]][[42]]'),'latin_text_candidate')
    def test_symbol_legend_is_not_new_translation_work(self):
        self.assertEqual(classify('-△△○○◎'),'symbol_numeric_or_punctuation_only')

if __name__=='__main__':unittest.main()
