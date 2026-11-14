import unittest,struct
from pathlib import Path
from project import additional_fixed_page_consumers
class ClanPageConsumersTests(unittest.TestCase):
 def fixture(self):
  d=bytearray(0x50200)
  for pc,at in((0x4ecf4,0x4ed3c),(0x4fc00,0x4fd14),(0x50116,0x50134)):
   struct.pack_into('<H',d,pc,0x4900+(at-((pc+4)&~3))//4);struct.pack_into('<I',d,at,0x084c3798)
  return d
 def test_three_direct_users_relocate(self):self.assertEqual(additional_fixed_page_consumers(0x4c3798,self.fixture()),[0x4ed3c,0x4fd14,0x50134])
 def test_changed_instruction_rejected(self):
  d=self.fixture();d[0x4fc00]=0
  with self.assertRaises(AssertionError):additional_fixed_page_consumers(0x4c3798,d)
 def test_other_pages_unchanged(self):self.assertEqual(additional_fixed_page_consumers(0x4c379c,bytes()),[])
 def test_system_notifications_include_prison_release(self):
  raw=bytearray(0x6e000)
  for pc,at in ((0x548cc,0x5493c),(0x65be2,0x65c18),(0x6debe,0x6df5c)):
   struct.pack_into('<H',raw,pc,0x4900+(at-((pc+4)&~3))//4)
   struct.pack_into('<I',raw,at,0x084c3e60)
  self.assertEqual(additional_fixed_page_consumers(0x4c3e60,raw),[0x5493c,0x65c18,0x6df5c])
  struct.pack_into('<I',raw,0x5493c,0x084c3e64)
  with self.assertRaises(AssertionError):additional_fixed_page_consumers(0x4c3e60,raw)
if __name__=='__main__':unittest.main()
