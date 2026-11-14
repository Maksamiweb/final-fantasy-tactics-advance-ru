import unittest
from gba_graphics import decompress,literal_lz

class GBAGraphicsTests(unittest.TestCase):
    def test_literal_lz_roundtrip_with_partial_flag_group(self):
        payload=bytes(range(256))+b'end';encoded=literal_lz(payload)
        decoded,used=decompress(encoded);self.assertEqual(decoded,payload);self.assertEqual(used,len(encoded))
    def test_overlapping_back_reference(self):
        self.assertEqual(decompress(bytes.fromhex('1009000040415000'))[0],b'A'*9)
    def test_bad_distance_is_rejected(self):
        with self.assertRaises(ValueError):decompress(bytes.fromhex('10030000800000'))
    def test_rle_runs_and_literal_groups(self):
        self.assertEqual(decompress(bytes.fromhex('30060000804102424344'))[0],b'AAABCD')
    def test_large_claim_and_truncation_are_rejected(self):
        for data in [b'\x10\x01',bytes.fromhex('10ffffff'),bytes.fromhex('100200000041')]:
            with self.assertRaises(ValueError):decompress(data)

if __name__=='__main__':unittest.main()
