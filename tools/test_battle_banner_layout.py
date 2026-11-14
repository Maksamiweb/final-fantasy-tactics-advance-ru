import unittest
from PIL import ImageFont
from prepare_save_counter import translated_bank
from prepare_battle_goals import alpha_label
class BannerLayoutTests(unittest.TestCase):
 def test_save_counter_keeps_adjacent_assets(self):
  source=bytes((i*13)%256 for i in range(1664));after=translated_bank(source)
  self.assertEqual(len(after),1664);self.assertEqual(after[320:],source[320:]);self.assertNotEqual(after[:320],source[:320])
 def test_save_counter_uses_only_native_counter_palette(self):
  data=translated_bank(bytes(1664))
  self.assertLessEqual({v for b in data[:320]for v in(b&15,b>>4)},{0,1,3,5,7})
 def test_goal_fitting_obeys_both_dimensions(self):
  im=alpha_label('LONG OBJECTIVE',ImageFont.load_default(),50,10)
  self.assertLessEqual(im.width,50);self.assertLessEqual(im.height,10)
if __name__=='__main__':unittest.main()
