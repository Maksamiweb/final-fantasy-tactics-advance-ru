"""Authored 4x6 raster and literal A7 archive for the 30 USA UI heading chunks.

All pixels authored here; no original ROM/graphics input. Layouts follow the
source-pinned 33-record selector table; no label exceeds its copied tile span.
"""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw
from ffta_a7 import encode_literal_archive,decode_archive
FONT={
'А':'0110/1001/1001/1111/1001/1001','Б':'1111/1000/1110/1001/1001/1110','В':'1110/1001/1110/1001/1001/1110',
'Г':'1111/1000/1000/1000/1000/1000','Д':'0110/0110/0110/0110/1111/1001','Е':'1111/1000/1110/1000/1000/1111',
'Ё':'1001/0000/1111/1110/1000/1111','Ж':'1001/1001/0110/0110/1001/1001','З':'1110/0001/0110/0001/0001/1110',
'И':'1001/1001/1011/1101/1001/1001','Й':'0110/0000/1001/1011/1101/1001','К':'1001/1010/1100/1100/1010/1001',
'Л':'0111/0101/0101/0101/1001/1001','М':'1001/1111/1111/1001/1001/1001','Н':'1001/1001/1111/1001/1001/1001',
'О':'0110/1001/1001/1001/1001/0110','П':'1111/1001/1001/1001/1001/1001','Р':'1110/1001/1001/1110/1000/1000',
'С':'0111/1000/1000/1000/1000/0111','Т':'1111/0110/0110/0110/0110/0110','У':'1001/1001/0111/0001/0001/1110',
'Ф':'0110/1111/1111/1111/0110/0110','Х':'1001/1001/0110/0110/1001/1001','Ц':'1010/1010/1010/1010/1111/0001',
'Ч':'1001/1001/1111/0001/0001/0001','Ш':'1001/1001/1111/1111/1111/1111','Щ':'1001/1001/1111/1111/1111/0001',
'Ъ':'1100/0100/0110/0101/0101/0110','Ы':'1001/1001/1101/1111/1111/1101','Ь':'1000/1000/1110/1001/1001/1110',
'Э':'1110/0001/0111/0001/0001/1110','Ю':'1011/1101/1101/1101/1101/1011','Я':'0111/1001/1001/0111/0101/1001',
'J':'0011/0001/0001/0001/1001/0110','P':'1110/1001/1001/1110/1000/1000','D':'1110/1001/1001/1001/1001/1110',
'1':'0100/1100/0100/0100/0100/1110','2':'0110/1001/0001/0010/0100/1111',
'.':'0/0/0/0/0/1',' ':'00/00/00/00/00/00',
}
# (chunk, authored text, copied width in tiles). Chunk6 has two independent spans.
LABELS=[(0,'СПР.',3),(1,'ВНИМ.',4),(2,'МЕНЮ',4),(3,'УМЕНИЯ',6),(4,'СНАРЯЖ.',5),(5,'ШТРАФ',6),
(6,'КОЛ.',3),(7,'СПИС.',3),(8,'НАСТРОЙКИ',6),(9,'ЦЕНА',4),(10,'ОБМЕН',6),(11,'СТАТУС',6),
(12,'ПРЕДМ.',4),(13,'КАРТЫ',4),(14,'ИТОГИ',6),(15,'СВЕД.',4),(16,'ЗНАКИ',6),(17,'СИСТЕМА',6),
(18,'ВСЕ',3),(19,'ДНИ',4),(20,'ПОДРОБНО',5),(21,'ОТЧЁТ',6),(22,'СЛУХИ',6),(23,'СОСТАВ',6),
(24,'ДЕЙСТВ.',5),(25,'ЗАДАНИЕ',5),(26,'СНАР.',4),(27,'СНАР.',3),(28,'ФАЙЛ 1',6),(29,'ФАЙЛ 2',6)]
SELECTORS=[(0,0,0),(3,0,0),(4,0,1),(4,0,2),(6,0,3),(3,0,27),(3,0,18),(6,0,5),(3,0,6),(2,3,6),(3,0,7),(6,0,8),(4,0,9),(6,0,10),(6,0,11),(4,0,12),(4,0,13),(6,0,14),(4,0,15),(6,0,16),(6,0,17),(4,0,19),(5,0,20),(6,0,21),(6,0,22),(6,0,23),(5,0,24),(5,0,25),(4,0,26),(5,0,4),(6,18,27),(6,0,28),(6,0,29)]
def width(text):return sum(len(FONT[c].split('/')[0])+1 for c in text)-1

def chunks():
 result=[]
 for index,text,tiles in LABELS:
  pixels=[[0]*48 for _ in range(8)]
  def draw(text,x0,span,dark=False):
   assert width(text)<=span*8,(text,width(text),span)
   for y in range(8):
    for x in range(x0,x0+span*8):pixels[y][x]=12 if y<6 else 11 if y==6 else 9
   x=x0
   for c in text:
    rows=FONT[c].split('/');assert len(rows)==6 and len(set(map(len,rows)))==1
    for y,row in enumerate(rows):
     for xx,v in enumerate(row):
      if v=='1':pixels[y][x+xx]=1 if dark else 15
    x+=len(rows[0])+1
  draw(text,0,tiles,index in(0,1))
  if index==6:draw('JP',24,2)
  if index==19:draw('D',40,1)
  data=bytearray()
  for tile in range(6):
   for y in range(8):
    for x in range(tile*8,tile*8+8,2):data.append(pixels[y][x]|pixels[y][x+1]<<4)
  result.append(bytes(data))
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 data=chunks();packed=encode_literal_archive(data);assert [x['data']for x in decode_archive(packed)]==data
 (a.out/'ui-headings.a7').write_bytes(packed)
 im=Image.new('RGB',(360,30*26),'#e8e8e8');d=ImageDraw.Draw(im)
 for i,chunk in enumerate(data):
  label=Image.new('RGB',(48,8))
  for y in range(8):
   for x in range(48):
    c=(chunk[(x//8)*32+y*4+(x%8)//2]>>(4*(x%2)))&15;label.putpixel((x,y),(c*17,)*3)
  d.text((3,i*26+4),str(i),fill='black');im.paste(label.resize((288,24)),(55,i*26))
 im.save(a.out/'preview.png')
 meta={'all_pixels_authored':True,'source_archive_offset':'0x3d5070','source_pointer_fields':['0x1857c','0x185b0'],'selector_table':'0x36d6e4','chunks':30,'decoded_bytes':5760,'packed_bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),'labels':[{'chunk':i,'text':t,'copied_tiles':w,'ink_width':width(t)}for i,t,w in LABELS],'native_verified':False};(a.out/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in meta.items()if k!='labels'}))
if __name__=='__main__':main()
