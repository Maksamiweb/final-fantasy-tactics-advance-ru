import unittest
from check_request_references import render_segments

class ReferenceLineSegmentTests(unittest.TestCase):
    def test_item_description_and_stats_are_different_boxes(self):
        text='Описание.[[4F]][[42]]Атака:○ Защита:○'
        self.assertEqual([s for _,_,s in render_segments(text)],['Описание.','Атака:○ Защита:○'])
    def test_two_stat_pages_do_not_add_their_widths(self):
        text='Сопр.:△[[4F]][[42]]Усиливает ветер и\nводу.[[40]][[42]]'
        self.assertEqual([s for _,_,s in render_segments(text)],['Сопр.:△','Усиливает ветер и','воду.'])
    def test_names_stay_in_their_own_rendered_segments(self):
        text='[[5160]]: история\nв 4 главах.[[4F]][[42]]Атака:-'
        self.assertEqual(list(render_segments(text)),[(1,1,'[[5160]]: история'),(2,1,'в 4 главах.'),(2,3,'Атака:-')])

if __name__=='__main__':unittest.main()
