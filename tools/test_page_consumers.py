import struct,unittest
from project import additional_page_consumers

class ConditionPageConsumersTests(unittest.TestCase):
    def fixture(self):
        data=bytearray(0x14000)
        for pc,at in ((0x13dcc,0x13de0),(0x13e26,0x13e34),(0x13e6e,0x13e98)):
            struct.pack_into('<H',data,pc,0x4900+(at-((pc+4)&~3))//4)
            struct.pack_into('<I',data,at,0x084b83a0)
        return data

    def test_all_three_native_extra_branches_are_relocated(self):
        self.assertEqual(additional_page_consumers('condi',0x4b83a0,self.fixture()),[0x13de0,0x13e34,0x13e98])

    def test_different_table_is_not_silently_patched(self):
        with self.assertRaises(AssertionError):additional_page_consumers('condi',0x4b83a4,self.fixture())
        self.assertEqual(additional_page_consumers('quest',0x4b83a0,self.fixture()),[])

    def test_wrong_instruction_or_pointer_is_rejected(self):
        for offset,value,fmt in ((0x13dcc,0,'<H'),(0x13e98,0x084b8400,'<I')):
            data=self.fixture();struct.pack_into(fmt,data,offset,value)
            with self.assertRaises(AssertionError):additional_page_consumers('condi',0x4b83a0,data)

class BattlePageConsumersTests(unittest.TestCase):
    def fixture(self):
        data=bytearray(0x27500)
        for pc,at in ((0x27440,0x27484),(0x274a4,0x274dc)):
            struct.pack_into('<H',data,pc,0x4900+(at-((pc+4)&~3))//4)
            struct.pack_into('<I',data,at,0x08497418)
        return data

    def test_both_additional_branches_are_relocated(self):
        self.assertEqual(additional_page_consumers('battle',0x497418,self.fixture()),[0x27484,0x274dc])

    def test_wrong_table_is_rejected(self):
        with self.assertRaises(AssertionError):additional_page_consumers('battle',0x49741c,self.fixture())

    def test_each_wrong_load_or_pointer_is_rejected(self):
        for pc,at in ((0x27440,0x27484),(0x274a4,0x274dc)):
            for offset,value,fmt in ((pc,0,'<H'),(at,0x0849741c,'<I')):
                data=self.fixture();struct.pack_into(fmt,data,offset,value)
                with self.assertRaises(AssertionError):additional_page_consumers('battle',0x497418,data)

if __name__=='__main__':unittest.main()
