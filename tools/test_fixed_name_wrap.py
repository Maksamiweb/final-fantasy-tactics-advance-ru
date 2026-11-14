import unittest
import prepare,project

class FixedNameWrapTests(unittest.TestCase):
    def test_long_fixed_name_gets_its_own_line(self):
        self.assertEqual(prepare.wrap('А [[5108]]',{'А':0},[10],70,reference_widths={8:70}),'А\n[[5108]]')

    def test_case_suffix_stays_with_reference(self):
        text='А [[5103]]а'
        self.assertEqual(prepare.wrap(text,{'А':0,'а':1},[10,7],65),text)
        self.assertEqual(prepare.wrap(text,{'А':0,'а':1},[10,7],65,reference_widths={3:50}),'А\n[[5103]]а')

    def test_player_name_keeps_separate_runtime_budget(self):
        self.assertEqual(prepare.wrap('А [[400]]',{'А':0},[10],70,reference_widths={0:100}),'А [[400]]')

    def test_fixed_width_uses_actual_profile_and_space(self):
        entries=[{'id':'words:refer/3','ru':'А А'}]
        self.assertEqual(project.fixed_name_widths(entries,{'А':0},[9]),{3:22})

class PlayerNameWrapTests(unittest.TestCase):
    def test_nine_wide_keyboard_letters_get_81px(self):
        self.assertEqual(prepare.wrap('А [[400]]',{'А':0},[10],90,player_name_width=81),'А\n[[400]]')

    def test_player_name_wrap_counts_native_indent(self):
        self.assertEqual(prepare.wrap('А [[1D10]][[400]]',{'А':0},[10],100,player_name_width=81),'А\n[[1D10]][[400]]')

    def test_player_budget_does_not_change_other_runtime_fields(self):
        self.assertEqual(prepare.wrap('А [[403]]',{'А':0},[10],90,player_name_width=81),'А [[403]]')

    def test_player_reference_and_punctuation_stay_together(self):
        self.assertEqual(prepare.wrap('А [[400]]!',{'А':0,'!':1},[10,4],90,player_name_width=81),'А\n[[400]]!')

if __name__=='__main__':unittest.main()
