import unittest
from PIL import Image
from prepare_world_hud import funds_row
from prepare_map_locations import pack_canvas
class MapAndFundsTests(unittest.TestCase):
 def test_clean_funds_removes_old_bottom_letter_pixels(self):
  source=bytes([0x77])*3168;after=funds_row(source,0x640,True)
  self.assertEqual(after[:0x660],source[:0x660]);self.assertEqual(after[0x760:],source[0x760:])
  for tile in range(1,9):
   for y in(6,7):self.assertEqual(after[0x640+tile*32+y*4:0x640+tile*32+y*4+4],b'\xee'*4)
 def test_native_32_plus_16_plus_8_layout_packs_boundaries(self):
  im=Image.new('L',(56,16));im.putpixel((31,7),3);im.putpixel((0,8),2);im.putpixel((32,0),1);im.putpixel((55,15),3);data=pack_canvas(im,[(0,0,32,16,0),(32,0,16,16,8),(48,0,8,16,12)])
  self.assertEqual(len(data),448);self.assertEqual((data[127]>>4,data[128]&15,data[256]&15,data[447]>>4),(3,2,1,3))
 def test_overlapping_native_tiles_are_rejected(self):
  with self.assertRaises(AssertionError):pack_canvas(Image.new('L',(40,16)),[(0,0,32,16,0),(32,0,8,16,0)])
if __name__=='__main__':unittest.main()
