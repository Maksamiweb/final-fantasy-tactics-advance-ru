"""Translate map encounter alert and blue mission introduction caption in place."""
import argparse,json,hashlib
from pathlib import Path
from prepare_ui_headings import FONT
from ffta_lzss import decompress,compress
GLYPHS={**FONT,'!':'1/1/1/1/0/1',':':'0/1/0/0/1/0'}
def caption(text,width,height,background,scale=1,outline=False,colors=(10,)*6):
 rows=[[background]*width for _ in range(height)];body=set();w=sum(len(GLYPHS[c].split('/')[0])+1 for c in text)-1;x0=(width-w*scale)//2;y0=(height-6*scale)//2
 assert x0>=0 and y0>=0
 for c in text:
  g=GLYPHS[c].split('/')
  for y,row in enumerate(g):
   for x,b in enumerate(row):
    if b=='1':body.update((x0+x*scale+dx,y0+y*scale+dy)for dx in range(scale)for dy in range(scale))
  x0+=(len(g[0])+1)*scale
 if outline:
  for x,y in body:
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    if 0<=x+dx<width and 0<=y+dy<height:rows[y+dy][x+dx]=1
 for x,y in body:rows[y][x]=colors[min(5,(y-y0)//scale)]
 return bytes(rows[ty*8+y][tx*8+x]|rows[ty*8+y][tx*8+x+1]<<4 for ty in range(height//8)for tx in range(width//8)for y in range(8)for x in range(0,8,2))
def translated_banks(raw,repair_encounters=False):
 engage,_=decompress(raw,0x3ad154);mission,_=decompress(raw,0x3c11bc);assert len(engage)==2496 and len(mission)==2688
 e=caption('В БОЙ!',48,8,0,outline=True,colors=(8,9,10,10,11,11))+caption('В БОЙ!',40,8,0,outline=True,colors=(8,9,10,10,11,11))+engage[0x160:]
 m=mission[:0x120]+caption('ЗАДАНИЕ:',112,16,1,scale=2,colors=(4,4,5,6,7,8))+mission[0x4a0:]
 if repair_encounters:
  # Native large word uses E,n,g,a,g,e,!; g is a shared glyph slot.
  # Russian V,P,E,R,E,D,! has the same six-unique-glyph pattern.
  e=b''.join(caption(c,8,8,0,outline=True,colors=(8,9,10,10,11,11))for c in 'ВПЕРД!')+caption('ВПЕРЕД!',40,8,0,outline=True,colors=(8,9,10,10,11,11))+engage[0x160:]
  if repair_encounters in (2,3):
   # Leave the bottom scanline transparent in every letter tile.
   e=b''.join(e[i:i+28]+bytes(4) for i in range(0,0x160,32))+e[0x160:]
  if repair_encounters==3:
   # Separate OAM pieces below both g slots use these three descender tiles.
   e=e[:0x160]+bytes(0x60)+e[0x1c0:]
  m=m[:0x4a0]+caption('ПРОТИВНИК:',112,16,1,scale=2,colors=(4,4,5,6,7,8))+m[0x820:]
 assert len(e)==len(engage) and len(m)==len(mission);tail=0x1c0 if repair_encounters==3 else 0x160;assert e[tail:]==engage[tail:] and m[:0x120]==mission[:0x120] and m[0x820 if repair_encounters else 0x4a0:]==mission[0x820 if repair_encounters else 0x4a0:]
 return {0x3ad154:e,0x3c11bc:m}
def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--repair-encounters',action='store_true');a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';a.out_private.mkdir(parents=True,exist_ok=True)
 for at,decoded in translated_banks(raw,a.repair_encounters).items():
  original,used=decompress(raw,at);payload=compress(decoded);assert len(payload)<=used and decompress(payload)==(decoded,len(payload));(a.out_private/(hex(at)+'.lzss')).write_bytes(payload);print(hex(at),len(payload),'<=',used)
if __name__=='__main__':main()
