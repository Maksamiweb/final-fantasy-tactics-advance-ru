import unittest
from prepare_law_headings import translate_headers,translated_bank
class LawHeadingTests(unittest.TestCase):
 def test_only_text_rows_change_and_shared_blank_tiles_stay(self):
  source=bytes([0x55])*3168;after=translate_headers(source,0x120,0x4c0)
  self.assertEqual(after[:0x120],source[:0x120]);self.assertEqual(after[0x220:0x4c0],source[0x220:0x4c0]);self.assertEqual(after[0x600:],source[0x600:])
  for off,tiles in [(0x120,8),(0x4c0,10)]:
   for tile in range(tiles):self.assertEqual(after[off+tile*32+24:off+tile*32+32],source[off+tile*32+24:off+tile*32+32])
  self.assertNotEqual(after,source)
 def test_text_colors_follow_dark_and_light_headers(self):
  after=translate_headers(bytes(3168),0x120,0x4c0)
  for off,n in [(0x120,8),(0x4c0,10)]:
   colors={c for t in range(n)for b in after[off+t*32:off+t*32+24]for c in(b&15,b>>4)};self.assertEqual(colors,{6,8})
 def test_duplicate_panel_wrong_size_rejected(self):
  with self.assertRaises(AssertionError):translated_bank(bytes(1471))
if __name__=='__main__':unittest.main()
