"""Guard source-language word fragments without weakening ordinary control checks."""
import unittest
from unittest.mock import patch
import project

class WordFragmentTests(unittest.TestCase):
    def setUp(self):
        self.ident='fx_text/17/39'
        self.source=[('CTR_FUNC',0x5105),('CHR_FULL',206),('CHR_FULL',220),('CTR_FUNC',0x40),('CTR_FUNC',0x42)]
        self.ru=[('CTR_FUNC',0x40),('CTR_FUNC',0x42)]

    def test_regular_name_still_requires_reference(self):
        with self.assertRaises(AssertionError):project.validate_controls('s_text/1/0',self.source,self.ru)

    def test_missing_opt_in_rejects_fragment_change(self):
        with self.assertRaises(AssertionError):project.validate_controls(self.ident,self.source,self.ru)

    def test_exception_cannot_be_used_on_a_character_line(self):
        with self.assertRaises(AssertionError):project.validate_controls('s_text/1/0',self.source,self.ru,True)

    def test_changed_source_is_rejected(self):
        with self.assertRaises(AssertionError):project.validate_controls(self.ident,self.source,self.ru,True)

    def test_dark_knight_title_is_preserved_in_ordinary_prose(self):
        source=[('CTR_FUNC',0x5137),('CTR_FUNC',0x40),('CTR_FUNC',0x42)]
        with self.assertRaises(AssertionError):project.validate_controls('fx_text/8/44',source,self.ru,True)
        project.validate_controls('fx_text/8/44',source,source)

    def test_exact_opt_in_only_removes_word_fragment(self):
        with patch.object(project,'semantic_hash',return_value=project.WORD_FRAGMENT_HASHES[self.ident]):
            project.validate_controls(self.ident,self.source,self.ru,True)
            with self.assertRaises(AssertionError):project.validate_controls(self.ident,self.source,[('CTR_FUNC',0x42)],True)

    def test_hash_alone_does_not_bypass_suffix_guard(self):
        source=list(self.source);source[1]=('CHR_FULL',207)
        with patch.object(project,'semantic_hash',return_value=project.WORD_FRAGMENT_HASHES[self.ident]):
            with self.assertRaises(AssertionError):project.validate_controls(self.ident,source,self.ru,True)

if __name__=='__main__':unittest.main()
