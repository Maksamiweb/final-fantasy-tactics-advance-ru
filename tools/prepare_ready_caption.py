"""Author a160x24 Russian Get Ready caption using the original palette/geometry."""
import argparse,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from ffta_lzss import decompress,compress
SOURCE=0x3c2fe0

def translated_bank(font_path):
 f=ImageFont.truetype(str(font_path),20);text='ГОТОВЬТЕСЬ!';box=f.getbbox(text);mask=Image.new('L',(box[2]-box[0],box[3]-box[1]));ImageDraw.Draw(mask).text((-box[0],-box[1]),text,font=f,fill=255);assert mask.width<=156 and mask.height<=20
 m=Image.new('L',(160,24));m.paste(mask,((160-mask.width)//2,(24-mask.height)//2));core=m.point(lambda v:255 if v>=80 else 0);outer=core.filter(ImageFilter.MaxFilter(5));inner=core.filter(ImageFilter.MaxFilter(3));im=Image.new('L',(160,24))
 for y in range(24):
  for x in range(160):
   if outer.getpixel((x,y)):im.putpixel((x,y),1)
   if inner.getpixel((x,y)):im.putpixel((x,y),10)
   if core.getpixel((x,y)):im.putpixel((x,y),9 if y<10 else 8 if y<15 else 7)
 return bytes(im.getpixel((tx*8+x,ty*8+y))|im.getpixel((tx*8+x+1,ty*8+y))<<4 for ty in range(3)for tx in range(20)for y in range(8)for x in range(0,8,2))
def main():
 p=argparse.ArgumentParser()
 for k in('rom','font','out-private'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';old,n=decompress(raw,SOURCE);assert n==1019 and len(old)==1920;d=translated_bank(a.font);payload=compress(d);assert decompress(payload)==(d,len(payload));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'ready.lzss').write_bytes(payload);print('Ready bytes',len(payload),'original',n)
if __name__=='__main__':main()
