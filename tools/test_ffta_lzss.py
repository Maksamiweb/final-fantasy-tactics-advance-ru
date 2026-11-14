import unittest
from ffta_lzss import decompress,compress

class FFTALZSSTests(unittest.TestCase):
    def test_overlap_near(self):
        self.assertEqual(decompress(bytes.fromhex('0000000a4041b000'))[0],b'A'*10)
    def test_far_and_long_opcodes(self):
        self.assertEqual(decompress(bytes.fromhex('000000054041100000'))[0],b'A'*5)
        self.assertEqual(decompress(bytes.fromhex('00000006404100000000'))[0],b'A'*6)
    def test_zero_and_ff_runs(self):
        self.assertEqual(decompress(bytes.fromhex('0000000a2002000102'))[0],b'\0'*5+b'\xff'*5)
    def test_bad_packets_rejected(self):
        for data in [b'',bytes.fromhex('00000003c000'),bytes.fromhex('000000016141'),bytes.fromhex('0000000103')]:
            with self.assertRaises(ValueError):decompress(data)
    def test_compressor_roundtrip_varied_packets(self):
        for data in [bytes(range(256)),b'A'*1024,b'ABCD'*200,b'\0'*300+b'\xff'*300,bytes(range(256))*3]:
            packed=compress(data);decoded,used=decompress(packed)
            self.assertEqual(decoded,data);self.assertEqual(used,len(packed))
    def test_size_bounds(self):
        with self.assertRaises(ValueError):compress(b'')
        with self.assertRaises(ValueError):decompress(bytes.fromhex('0000002020'),max_output=16)

if __name__=='__main__':unittest.main()
