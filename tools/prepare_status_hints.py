"""Translate the status bank Info/Remove raster spans; private mixed asset only."""
import argparse,hashlib,json
from pathlib import Path
from ffta_lzss import decompress,compress
from prepare_ui_headings import FONT,width
from prepare_battle_graphics import FONT as SMALL_FONT
BASE_SHA='5329198614cab66eb6b8ecac9022de397303f8de2326701717706effec19f01c'
SPANS=[(0xc0,24,'СПР.'),(0x9a0,40,'СНЯТЬ')]
def hint_bank(source):
 assert len(source)==7264;out=bytearray(source)
 for at,w,text in SPANS:
  assert width(text)<=w-2;pix=[[0]*w for _ in range(8)];points=set();x=(w-width(text))//2
  for c in text:
   rows=FONT[c].split('/');points.update((x+xx,y+1)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
  for x,y in points:
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    if 0<=x+dx<w and 0<=y+dy<8:pix[y+dy][x+dx]=1
  for x,y in points:pix[y][x]=3
  out[at:at+w*4]=bytes(pix[y][t*8+x]|pix[y][t*8+x+1]<<4 for t in range(w//8)for y in range(8)for x in range(0,8,2))
 # MASTER! is a separate 40x16 row-major banner; preserve its sparkle (x0..8).
 def master_pixel(x,y,c):
  at=0x5a0+((y//8)*5+x//8)*32+(y%8)*4+(x%8)//2;n=x%2;out[at]=(out[at]&~(15<<(4*n)))|c<<(4*n)
 for y in range(16):
  for x in range(9,40):master_pixel(x,y,0)
 points=set();x=10
 for c in 'ИЗУЧЕНО!':
  rows=SMALL_FONT[c].split('/');points.update((x+xx,y+6)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
 assert x<=40
 for x,y in points:
  for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
   if 9<=x+dx<40 and 0<=y+dy<16:master_pixel(x+dx,y+dy,1)
 for x,y in points:master_pixel(x,y,7)
 for i,(a,b)in enumerate(zip(source,out)):
  assert a==b or any(at<=i<at+w*4 for at,w,_ in SPANS)or 0x5a0<=i<0x6e0
 for y in range(16):
  for x in range(9):
   at=0x5a0+((y//8)*5+x//8)*32+(y%8)*4+x%8//2;n=x%2;assert(out[at]>>(4*n))&15==(source[at]>>(4*n))&15
 return bytes(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-status',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();payload=a.source_status.read_bytes();assert hashlib.sha256(payload).hexdigest()==BASE_SHA;source,_=decompress(payload);bank=hint_bank(source);packed=compress(bank);assert len(packed)<=4000 and decompress(packed)==(bank,len(packed));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'status-hints-ru.lzss').write_bytes(packed);r={'payload_sha256':hashlib.sha256(packed).hexdigest(),'decoded_sha256':hashlib.sha256(bank).hexdigest(),'payload_bytes':len(packed),'labels':['СПР.','СНЯТЬ','ИЗУЧЕНО!'],'master_sparkle_preserved':True,'master_span':'0x5a0..0x6df excluding sparkle x0..8','spans':[[hex(at),w*4]for at,w,_ in SPANS],'native_verified':False};a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(r))
if __name__=='__main__':main()
