"""Translate LAW/Info world-map captions; preserve hardware L/R graphics."""
import argparse,hashlib,json
from pathlib import Path
from ffta_lzss import decompress,compress
from prepare_ui_headings import FONT,width
SOURCE_OFFSET=0x3adb08

def translated_bank(source):
 assert len(source)==2176;result=bytearray(source)
 for off,text in [(0x700,'ЗАК.'),(0x7c0,'СПР.')]:
  def pixel(x,y,c):
   at=off+((y//8)*2+x//8)*32+(y%8)*4+(x%8)//2 if x<16 else off+128+(y//8)*32+(y%8)*4+(x%8)//2;n=x%2;result[at]=(result[at]&~(15<<(4*n)))|c<<(4*n)
  for y in range(8,16):
   for x in range(24):pixel(x,y,0)
  assert width(text)<=22;body=set();x=(24-width(text))//2
  for c in text:
   rows=FONT[c].split('/');body.update((x+xx,y+9)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
  for x,y in body:
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    if 0<=x+dx<24 and 8<=y+dy<16:pixel(x+dx,y+dy,1)
  for x,y in body:pixel(x,y,3)
 return bytes(result)

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';source,used=decompress(raw,SOURCE_OFFSET);assert used==1676;after=translated_bank(source);payload=compress(after);assert len(payload)<=used and decompress(payload)==(after,len(payload));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'world-buttons-ru.lzss').write_bytes(payload);a.report.write_text(json.dumps({'offset':hex(SOURCE_OFFSET),'source_bytes':used,'payload_bytes':len(payload),'decoded_bytes':2176,'labels':['ЗАК.','СПР.'],'hardware_L_R_preserved':True,'sha256':hashlib.sha256(payload).hexdigest(),'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('World buttons prepared',len(payload))
if __name__=='__main__':main()
