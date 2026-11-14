"""Translate Remove/Info equipment captions; preserve hardware L/R graphics."""
import argparse,hashlib,json
from pathlib import Path
from ffta_lzss import decompress,compress
from prepare_ui_headings import FONT,width
SOURCE_OFFSET=0x3b53a4

def translated_bank(source,clean_remove_edge=False):
 assert len(source)==2176;result=bytearray(source)
 for off,text,main in [(0x400,'СПР.',16),(0x4c0,'СНЯТЬ',32)]:
  def pixel(x,y,c):
   at=off+((y//8)*(main//8)+x//8)*32+(y%8)*4+(x%8)//2 if x<main else off+main*8+(y//8)*32+(y%8)*4+(x%8)//2;n=x%2;result[at]=(result[at]&~(15<<(4*n)))|c<<(4*n)
  if clean_remove_edge and off==0x4c0:
   for x in range(11):pixel(x,7,0)
  for y in range(8,16):
   for x in range(main+8):pixel(x,y,0)
  assert width(text)<=main+6;body=set();x=(main+8-width(text))//2
  for c in text:
   rows=FONT[c].split('/');body.update((x+xx,y+9)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
  for x,y in body:
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    if 0<=x+dx<main+8 and 8<=y+dy<16:pixel(x+dx,y+dy,1)
  for x,y in body:pixel(x,y,3)
 # Two independent 32x8 unit-state captions, outside the button/icon areas.
 for off,text,color in [(0x300,'ТЮРЬМА',11),(0x380,'ЗАДАН.',7)]:
  def put(x,y,c):
   at=off+(x//8)*32+y*4+x%8//2;n=x%2;result[at]=(result[at]&~(15<<(4*n)))|c<<(4*n)
  assert width(text)<=30;points=set();x=(32-width(text))//2
  for c in text:
   rows=FONT[c].split('/');points.update((x+xx,y+1)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
  for y in range(8):
   for x in range(32):put(x,y,0)
  for x,y in points:
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    if 0<=x+dx<32 and 0<=y+dy<8:put(x+dx,y+dy,1)
  for x,y in points:put(x,y,color)
 assert result[:0x300]==source[:0x300] and result[0x600:]==source[0x600:]
 return bytes(result)

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--clean-remove-edge',action='store_true');a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';source,used=decompress(raw,SOURCE_OFFSET);assert used==1176;after=translated_bank(source,a.clean_remove_edge);payload=compress(after);assert len(payload)<=used and decompress(payload)==(after,len(payload));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'equipment-buttons-ru.lzss').write_bytes(payload);a.report.write_text(json.dumps({'offset':hex(SOURCE_OFFSET),'source_bytes':used,'payload_bytes':len(payload),'decoded_bytes':2176,'labels':['СПР.','СНЯТЬ','ТЮРЬМА','ЗАДАН.'],'hardware_L_R_preserved':True,'sha256':hashlib.sha256(payload).hexdigest(),'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Equipment buttons prepared',len(payload))
if __name__=='__main__':main()
