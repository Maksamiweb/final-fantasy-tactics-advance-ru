"""Native large help sizes must not loosen unrelated text limits."""
import unittest
from project import encoded_text_limit

class TextLimitTests(unittest.TestCase):
    def test_native_large_help_extent(self):
        self.assertEqual(encoded_text_limit('fx_text/8/86',970),970)

    def test_small_help_retains_previous_guard(self):
        self.assertEqual(encoded_text_limit('fx_text/8/1',20),512)

    def test_other_tables_cannot_use_help_allowance(self):
        for ident in ['s_text/8/86','fx_text/18/86','fx_text/80/86','words:content/8']:
            self.assertEqual(encoded_text_limit(ident,970),512)

if __name__=='__main__':unittest.main()
