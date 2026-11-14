"""The glossary must not confuse spell names with settings or replace word fragments."""
import unittest
from terminology import check_labels

class TerminologyTests(unittest.TestCase):
    def setUp(self):
        self.registry={'entries':[{'term_id':'T1','en':'Slow','ru':'Замедление','short_ru':None,'decision':'accepted','excluded_rom_ids':['words:battle/762']},{'term_id':'T2','en':'Fire','ru':'Огонь','short_ru':None,'decision':'accepted','excluded_rom_ids':[]},{'term_id':'T3','en':'Morpher','ru':'Оборотень','short_ru':None,'decision':'review','excluded_rom_ids':[]}]}
    def test_setting_is_not_spell(self):
        n,errors=check_labels(self.registry,{'words:battle/762':{'source':'Slow'}},[{'id':'words:battle/762','ru':'Медл.'}])
        self.assertEqual((n,errors),(0,[]))
    def test_spell_conflict_is_rejected(self):
        n,errors=check_labels(self.registry,{'spell':{'source':'Slow'}},[{'id':'spell','ru':'Медл.'}])
        self.assertEqual(n,1);self.assertEqual(len(errors),1)
    def test_no_substring_replacement(self):
        n,errors=check_labels(self.registry,{'dragon':{'source':'Firewyrm'}},[{'id':'dragon','ru':'Огненный змей'}])
        self.assertEqual((n,errors),(0,[]))
    def test_proposal_does_not_override_editor(self):
        n,errors=check_labels(self.registry,{'job':{'source':'Morpher'}},[{'id':'job','ru':'Морфер'}])
        self.assertEqual((n,errors),(0,[]))
    def test_case_and_whitespace_are_not_conflicts(self):
        n,errors=check_labels(self.registry,{'spell':{'source':'Fire'}},[{'id':'spell','ru':' огонь '}])
        self.assertEqual((n,errors),(1,[]))
    def test_icon_abbreviation_does_not_leak_into_spell(self):
        self.registry['entries'][1].update(short_ru='ОГН',short_ru_ids=['icon'])
        n,errors=check_labels(self.registry,{'icon':{'source':'FIRE'},'spell':{'source':'Fire'}},[{'id':'icon','ru':'ОГН'},{'id':'spell','ru':'ОГН'}])
        self.assertEqual(n,2);self.assertEqual([e['id'] for e in errors],['spell'])

if __name__=='__main__':unittest.main()
