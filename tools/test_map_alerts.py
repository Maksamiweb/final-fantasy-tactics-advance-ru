import unittest
from unittest.mock import patch
from prepare_map_alerts import caption,translated_banks
from prepare_calendar_graphics import chunks
class MapAlertTests(unittest.TestCase):
 def test_separate_english_descenders_are_transparent(self):
  engage=bytes([0x55])*2496
  mission=bytes([0x11])*2688
  def source_bank(raw,offset):return (engage if offset==0x3ad154 else mission),0
  with patch('prepare_map_alerts.decompress',side_effect=source_bank):
   previous=translated_banks(b'',2)[0x3ad154]
   repaired=translated_banks(b'',3)[0x3ad154]
  self.assertEqual(repaired[:0x160],previous[:0x160])
  self.assertEqual(repaired[0x160:0x1c0],bytes(0x60))
  self.assertEqual(repaired[0x1c0:],engage[0x1c0:])
 def test_encounter_caption_fits_both_native_spans(self):
  for width in(40,48):
   data=caption('В БОЙ!',width,8,0,outline=True)
   self.assertEqual(len(data),width*4)
 def test_oversized_caption_is_rejected(self):
  with self.assertRaises(AssertionError):caption('ЗАДАНИЕ:',16,8,1,scale=2)
 def test_singleline_month_uses_same_native_shapes(self):
  blocks=chunks(True);self.assertEqual(len(blocks),30);self.assertEqual([len(b)for b in blocks],[64]*30);self.assertNotEqual(blocks,chunks())
  for n in range(5):
   data=b''.join(blocks[n*6:n*6+6])
   for x in range(48):
    for y in list(range(4))+list(range(12,16)):
     at=((y//8)*4+x//8)*32+y%8*4+x%8//2 if x<32 else 256+((y//8)*2+(x-32)//8)*32+y%8*4+x%8//2
     self.assertEqual(data[at]>>(x%2*4)&15,0)
if __name__=='__main__':unittest.main()
