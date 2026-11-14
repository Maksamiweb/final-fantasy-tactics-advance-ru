"""A preserved unmapped source glyph must never turn into an executable control."""
import unittest
import project

class RawGlyphTests(unittest.TestCase):
    def test_preserves_unmapped_source_glyph(self):
        self.assertEqual(project.encode('[[U1E6]][[42]]',{}),[('CHR_FULL',486),('CTR_FUNC',66)])

    def test_glyph_number_is_not_a_control(self):
        self.assertEqual(project.structural(project.encode('[[U42]][[42]]',{})),[('CTR_FUNC',66)])

    def test_rejects_unallocated_glyph(self):
        with self.assertRaises(ValueError):project.encode(f'[[U{project.COUNT:X}]]',{})

if __name__=='__main__':unittest.main()
