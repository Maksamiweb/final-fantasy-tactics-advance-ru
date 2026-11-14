import unittest
from ffta_a7 import decode_archive,encode_literal_archive

class A7Tests(unittest.TestCase):
    def test_literal_roundtrip_multiple_chunks_and_packets(self):
        chunks=[bytes(range(256)),b'R'*256]
        self.assertEqual([c['data']for c in decode_archive(encode_literal_archive(chunks))],chunks)
    def test_dictionary_reference_and_literal(self):
        # One six-byte chunk: dictionary ABC followed by literal XYZ.
        archive=b'A7\0\1'+(18).to_bytes(4,'big')+(12).to_bytes(4,'big')
        archive+=b'\0\0\x82XYZ'+b'\0\5\0\6ABC'
        self.assertEqual(decode_archive(archive)[0]['data'],b'ABCXYZ')
    def test_type3_per_chunk_size(self):
        archive=b'A7\0\1'+(18).to_bytes(4,'big')+(12).to_bytes(4,'big')
        archive+=b'\0\3\x82ABC'+b'\3\5'
        self.assertEqual(decode_archive(archive)[0]['data'],b'ABC')
    def test_truncation_and_output_limit(self):
        archive=encode_literal_archive([b'ABCD'])
        with self.assertRaises(ValueError):decode_archive(archive[:-1])
        with self.assertRaises(ValueError):decode_archive(archive,max_output=3)
    def test_bad_offsets_and_dictionary_copy(self):
        archive=bytearray(encode_literal_archive([b'ABCD']))
        archive[8:12]=(0).to_bytes(4,'big')
        with self.assertRaises(ValueError):decode_archive(archive)
        bad=b'A7\0\1'+(14).to_bytes(4,'big')+(12).to_bytes(4,'big')+b'\0\x20\0\5\0\3'
        with self.assertRaises(ValueError):decode_archive(bad)
    def test_encoder_rejects_inconsistent_chunks(self):
        for chunks in [[],[b''],[b'AB',b'C']]:
            with self.assertRaises(ValueError):encode_literal_archive(chunks)

if __name__=='__main__':unittest.main()
