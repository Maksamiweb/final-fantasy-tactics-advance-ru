"""Translate three roster button hints in the pinned private LZSS bank."""
import argparse,hashlib,json
from pathlib import Path
from ffta_lzss import decompress,compress
from prepare_ui_headings import FONT,width
SOURCE_OFFSET=0x3bb7f0

def translated_bank(source):
 assert len(source)==896
 result=bytearray(source)
 def pos(x,y):
  if 0<=x<64:tile=0x160+(x//8)*32
  elif 80<=x<160:tile=0x20+((x-80)//8)*32
  elif 184<=x<232:tile=0x2a0+((x-184)//8)*32
  else:raise AssertionError('Outside verified unique text span')
  return tile+y*4+(x%8)//2,x%2
 def setpixel(x,y,c):
  at,n=pos(x,y);result[at]=(result[at]&~(15<<(4*n)))|c<<(4*n)
 for x0,x1,text,body,bg in [(22,58,'СМЕНА',15,12),(120,160,'ПРЕДМЕТЫ',8,0),(198,224,'СОРТ.',15,12)]:
  assert width(text)<=x1-x0
  for y in range(8 if bg==0 else 1,8 if bg==0 else 7):
   for x in range(x0,x1):setpixel(x,y,bg)
  # Item list keeps the native dark outline; button background already contrasts.
  points=set();x=x0
  for c in text:
   rows=FONT[c].split('/');points.update((x+xx,y+1)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
  if bg==0:
   for x,y in points:
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
     if x0<=x+dx<x1 and 0<=y+dy<8:setpixel(x+dx,y+dy,3)
  for x,y in points:setpixel(x,y,body)
 return bytes(result)

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19'
 source,used=decompress(raw,SOURCE_OFFSET);assert used==582;after=translated_bank(source);packed=compress(after);assert len(packed)<=used and decompress(packed)==(after,len(packed));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'roster-ru.lzss').write_bytes(packed)
 a.report.write_text(json.dumps({'offset':hex(SOURCE_OFFSET),'decoded_bytes':896,'source_bytes':used,'payload_bytes':len(packed),'labels':['СМЕНА','ПРЕДМЕТЫ','СОРТ.'],'sha256':hashlib.sha256(packed).hexdigest(),'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Roster hints prepared:',len(packed),'bytes')
if __name__=='__main__':main()
