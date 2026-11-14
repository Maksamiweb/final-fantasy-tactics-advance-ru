"""Patch integrity regressions; run with python -m unittest discover -s tools."""
import struct,unittest,zlib
import bps

class PatchTests(unittest.TestCase):
    def test_reference_literal_vector(self):
        # BPS1: 3-byte source, 3-byte target, no metadata; TargetRead of XYZ.
        source=b'abc';patch=b'BPS1\x83\x83\x80\x89XYZ'
        patch+=struct.pack('<II',zlib.crc32(source),zlib.crc32(b'XYZ'))
        patch+=struct.pack('<I',zlib.crc32(patch))
        self.assertEqual(bps.apply(source,patch),b'XYZ')
    def test_source_copies_both_directions(self):
        source=bytes(range(256))*80
        plan=[(0,128),(b'NEW',3),(15000,320),(20,1000),(b'END',3)]
        patch,target,_=bps.create(source,plan,b'test metadata')
        self.assertEqual(target,source[:128]+b'NEW'+source[15000:15320]+source[20:1020]+b'END')
        self.assertEqual(bps.apply(source,patch),target)
    def test_overlapping_target_copy(self):
        source=b'x';target=b'AAAAAA'
        patch=b'BPS1'+bps.number(1)+bps.number(6)+bps.number(0)+bps.number(1)+b'A'+bps.number(19)+bps.number(0)
        patch+=struct.pack('<II',zlib.crc32(source),zlib.crc32(target));patch+=struct.pack('<I',zlib.crc32(patch))
        self.assertEqual(bps.apply(source,patch),target)
    def test_wrong_source_rejected(self):
        patch,_,_=bps.create(b'abc',[(b'XYZ',3)])
        with self.assertRaises(AssertionError):bps.apply(b'abd',patch)
    def test_damaged_patch_rejected(self):
        patch,_,_=bps.create(b'abc',[(b'XYZ',3)])
        with self.assertRaises(AssertionError):bps.apply(b'abc',patch[:-1]+bytes([patch[-1]^1]))
    def test_target_crc_rejected(self):
        patch,_,_=bps.create(b'abc',[(b'XYZ',3)]);bad=bytearray(patch);bad[-8]^=1;bad[-4:]=struct.pack('<I',zlib.crc32(bad[:-4]))
        with self.assertRaises(AssertionError):bps.apply(b'abc',bytes(bad))

if __name__=='__main__':unittest.main()
