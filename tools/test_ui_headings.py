import struct,unittest
from ffta_a7 import decode_archive,encode_literal_archive
from prepare_ui_headings import chunks,SELECTORS,LABELS,width
from prepare_mission_graphics import translated_bank
from project import validate_ui_headings
class UIHeadingTests(unittest.TestCase):
 def fixture(self):
  raw=bytearray(0x36d6e4+len(SELECTORS)*4)
  raw[0x36d6e4:]=b''.join(bytes((*r,0))for r in SELECTORS)
  for pc,at in ((0x18542,0x1857c),(0x18584,0x185b0)):
   struct.pack_into('<H',raw,pc,0x4800+(at-((pc+4)&~3))//4);struct.pack_into('<I',raw,at,0x083d5070)
  return raw
 def test_all_authored_chunks_fit_actual_spans(self):
  data=chunks();self.assertEqual(len(data),30);self.assertTrue(all(len(x)==192 for x in data))
  for _,text,tiles in LABELS:self.assertLessEqual(width(text),tiles*8)
  self.assertLessEqual(width('JP'),16)
 def test_payload_and_source_selector_pins(self):
  payload=encode_literal_archive(chunks());self.assertEqual(validate_ui_headings(self.fixture(),payload),(0x1857c,0x185b0))
  for at in (0x18542,0x1857c,0x18584,0x185b0,0x36d6e4+4):
   raw=self.fixture();raw[at]^=1
   with self.assertRaises(AssertionError):validate_ui_headings(raw,payload)
 def test_noncanonical_artwork_is_rejected(self):
  data=chunks();data[26]=b'\0'*192
  with self.assertRaises(AssertionError):validate_ui_headings(self.fixture(),encode_literal_archive(data))
 def test_mission_rewrite_only_changes_funds_info_and_seven_mission_tiles(self):
  original=bytes((x%256 for x in range(2880)));result=translated_bank(original)
  self.assertEqual(len(result),2880);self.assertEqual(result[:0x20],original[:0x20]);self.assertEqual(result[0x120:0x280],original[0x120:0x280]);self.assertEqual(result[0x2e0:0x5e0],original[0x2e0:0x5e0]);self.assertEqual(result[0x6c0:],original[0x6c0:]);self.assertNotEqual(result[0x5e0:0x6c0],original[0x5e0:0x6c0])
 def test_mission_wrong_bank_size_is_rejected(self):
  with self.assertRaises(AssertionError):translated_bank(bytes(2879))
class RosterHintTests(unittest.TestCase):
 def test_only_three_text_spans_change(self):
  from prepare_roster_graphics import translated_bank
  original=bytes((x%256 for x in range(896)));after=translated_bank(original)
  self.assertEqual(len(after),896)
  self.assertEqual(after[:0xc0],original[:0xc0])
  self.assertEqual(after[0x160:0x1a0],original[0x160:0x1a0])
  self.assertEqual(after[0x260:0x2c0],original[0x260:0x2c0])
  self.assertEqual(after[0x340:],original[0x340:])

class CalendarHudTests(unittest.TestCase):
 def test_calendar_keeps_native_chunk_shape(self):
  from prepare_calendar_graphics import chunks
  data=chunks();self.assertEqual(len(data),30);self.assertTrue(all(len(x)==64 for x in data))
  for i in range(5):self.assertEqual(len(b''.join(data[i*6:i*6+6])),384)
 def test_funds_keep_frame_rows_and_shared_border_tile(self):
  from prepare_world_hud import funds_row
  original=bytes((x%256 for x in range(3168)));after=funds_row(original,0x640)
  self.assertEqual(after[:0x660],original[:0x660]);self.assertEqual(after[0x760:],original[0x760:])
  for at in range(0x660,0x760,32):self.assertEqual(after[at+24:at+32],original[at+24:at+32])
 def test_world_hud_changes_only_intended_ranges(self):
  from prepare_world_hud import translated_bank
  original=bytes((x%256 for x in range(3168)));after=translated_bank(original)
  allowed=lambda i:0x660<=i<0x760 or 0x920<=i<0x960 or 0xa60<=i<0xaa0
  self.assertTrue(all(a==b or allowed(i)for i,(a,b)in enumerate(zip(original,after))))

class WorldButtonAndNumberTests(unittest.TestCase):
 def test_world_buttons_preserve_hardware_pictures(self):
  from prepare_world_buttons import translated_bank
  original=bytes(x%256 for x in range(2176));after=translated_bank(original)
  allowed=lambda i:any(off+64<=i<off+128 or off+160<=i<off+192 for off in (0x700,0x7c0))
  self.assertTrue(all(a==b or allowed(i)for i,(a,b)in enumerate(zip(original,after))))
 def test_number_sign_preserves_all_other_status_art(self):
  from prepare_status_number import number_bank
  original=bytes(x%256 for x in range(7264));after=number_bank(original)
  self.assertEqual(after[:0x560],original[:0x560]);self.assertEqual(after[0x5a0:],original[0x5a0:]);self.assertNotEqual(after[0x560:0x5a0],original[0x560:0x5a0])

if __name__=='__main__':unittest.main()
