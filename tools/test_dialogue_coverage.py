import unittest
from audit_dialogue_coverage import classify,check_language
from prepare import wrap
class DialogueCoverageTests(unittest.TestCase):
 def test_unknown_source_glyph_is_dialogue_not_empty(self):
  self.assertEqual(classify('s_text/0/1',{'tokens':[('CHR_FULL',0x9f2)],'source_sha256':'a'},{}),'dialogue')
 def test_exception_requires_same_source_hash(self):
  with self.assertRaises(AssertionError):classify('s_text/0/1',{'source_sha256':'b'},{'s_text/0/1':{'source_sha256':'a','category':'technical_cut_label'}})
 def test_unlisted_english_is_rejected(self):
  with self.assertRaises(AssertionError):check_language('s_text/0/1','Hello![[40]][[42]]',{})
 def test_unmapped_target_glyph_is_rejected(self):
  with self.assertRaises(AssertionError):check_language('s_text/0/1','[[U9F2]][[40]][[42]]',{})
 def test_explicit_title_policy_is_allowed(self):
  self.assertEqual(check_language('s_text/0/1','Игра Final\nFantasy.',{'s_text/0/1':['Final','Fantasy']}),['Final','Fantasy'])
 def test_indent_can_be_measured_without_player_name(self):
  self.assertEqual(wrap('А [[1D10]]А',{'А':0},[10],30,control_offsets=True),'А\n[[1D10]]А')
  self.assertEqual(wrap('А [[1D10]]А',{'А':0},[10],30),'А [[1D10]]А')
 def test_negative_spacing_keeps_real_line_budget(self):
  self.assertEqual(wrap('А [[1B04]]А',{'А':0},[10],20,control_offsets=True),'А [[1B04]]А')
if __name__=='__main__':unittest.main()
