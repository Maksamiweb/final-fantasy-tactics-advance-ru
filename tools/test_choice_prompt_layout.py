import unittest
from project import validate_choice_prompt_lines

F=lambda value:('CTR_FUNC',value)

class ChoicePromptLayoutTests(unittest.TestCase):
    def test_save_overwrite_extra_line_is_rejected(self):
        with self.assertRaisesRegex(AssertionError,'hides choice row'):
            validate_choice_prompt_lines('fx_text/1/32',[F(0x4d),F(0x3211)],
                                        [F(0x4d),F(0x4d),F(0x3211)])

    def test_one_line_question_and_options_are_allowed(self):
        validate_choice_prompt_lines('fx_text/1/32',[F(0x4d),F(0x3211)],
                                    [F(0x4d),F(0x3211)])

    def test_previous_description_page_does_not_consume_choice_lines(self):
        validate_choice_prompt_lines('fx_text/1/24',[F(0x4d),F(0x4f),F(0x42),F(0x4d),F(0x3210)],
                                    [F(0x4d),F(0x4d),F(0x4f),F(0x42),F(0x4d),F(0x3210)])

    def test_later_choice_is_checked_independently(self):
        with self.assertRaisesRegex(AssertionError,'hides choice row'):
            validate_choice_prompt_lines('example',[F(0x4d),F(0x3210),F(0x42),F(0x4d),F(0x3211)],
                                        [F(0x4d),F(0x3210),F(0x42),F(0x4d),F(0x4d),F(0x3211)])

if __name__=='__main__':unittest.main()
