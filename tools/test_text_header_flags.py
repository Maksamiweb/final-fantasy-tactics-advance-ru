import unittest
from project import uncompressed_text_flags

class TextHeaderTests(unittest.TestCase):
    def test_native_equipment_help_keeps_upper_metadata(self):
        # Actual compressed Bronze Helm source header; its second help page
        # disappears when the high 0x18 byte is discarded.
        self.assertEqual(uncompressed_text_flags(0x182a),0x1828)

    def test_only_encoding_and_compression_bits_are_cleared(self):
        self.assertEqual(uncompressed_text_flags(0xffef),0xffec)
        self.assertEqual(uncompressed_text_flags(0x20),0x20)

if __name__=='__main__':unittest.main()
