"""Authored five calendar month graphics, reusing the project's existing terms."""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from prepare_ui_headings import FONT,width
from ffta_a7 import encode_literal_archive,decode_archive
MONTHS=['КОРОЛЯ','БЕЗУМЦА','МУДРЕЦА','ОХОТНИКА','БАРДА']
def chunks(compact=False):
 result=[]
 for name in MONTHS:
  pix=[[0]*48 for _ in range(16)];body=set()
  for text,y0 in ([(name,5)] if compact else [('ЛУНА',1),(name,8)]):
   assert width(text)+2<=48;x=(48-width(text))//2
   for c in text:
    rows=FONT[c].split('/');body.update((x+xx,y0+y)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
  for x,y in body:
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    if 0<=x+dx<48 and 0<=y+dy<15:pix[y+dy][x+dx]=3
  for x,y in body:pix[y][x]=1
  out=bytearray()
  # OBJ32x16 followed by OBJ16x16, exactly as the two native sprites.
  for x0,tileswide in ((0,4),(32,2)):
   for ty in range(2):
    for tx in range(tileswide):
     for y in range(8):
      for x in range(0,8,2):out.append(pix[ty*8+y][x0+tx*8+x]|pix[ty*8+y][x0+tx*8+x+1]<<4)
  result.extend(bytes(out[i:i+64])for i in range(0,384,64))
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--compact',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);data=chunks(a.compact);packed=encode_literal_archive(data);assert[x['data']for x in decode_archive(packed)]==data;(a.out/'calendar-months.a7').write_bytes(packed)
 im=Image.new('RGB',(360,5*60),'#4480b8');dr=ImageDraw.Draw(im)
 for i in range(5):
  d=b''.join(data[i*6:i*6+6]);pic=Image.new('RGB',(48,16),'#4480b8')
  for y in range(16):
   for x in range(48):
    at=((y//8)*4+x//8)*32+y%8*4+(x%8)//2 if x<32 else 256+((y//8)*2+(x-32)//8)*32+y%8*4+(x%8)//2;c=(d[at]>>(4*(x%2)))&15
    if c:pic.putpixel((x,y),(0,0,0)if c==1 else(245,245,245))
  dr.text((5,i*60+10),str(i),fill='white');im.paste(pic.resize((288,48)),(55,i*60))
 im.save(a.out/'preview.png');(a.out/'manifest.json').write_text(json.dumps({'all_pixels_authored':True,'single_line':a.compact,'month_names':['Луна '+n.lower()for n in MONTHS],'source_archive':'0x3acd68','chunks':30,'chunk_size':64,'sprite_layout':'32x16 +16x16','payload_bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Calendar authored chunks',len(data),'packed',len(packed))
if __name__=='__main__':main()
