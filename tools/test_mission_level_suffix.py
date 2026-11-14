import unittest
from project import validate_level_suffix
class MissionLevelSuffixTests(unittest.TestCase):
 def template(self,letters):return [('CTR_FUNC',0x418)]+[('CHR_FULL',n)for n in range(letters)]+[('CTR_FUNC',0x41a),('CTR_FUNC',0x4d)]
 def test_shorter_suffix_cannot_consume_newline(self):
  with self.assertRaises(AssertionError):validate_level_suffix(self.template(5),self.template(4))
 def test_original_length_is_allowed(self):validate_level_suffix(self.template(5),self.template(5))
 def test_space_is_a_display_token(self):
  t=self.template(5);t[2]=('CTR_FUNC',0x52);validate_level_suffix(self.template(5),t)
if __name__=='__main__':unittest.main()
