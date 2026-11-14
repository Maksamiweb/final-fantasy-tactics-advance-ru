"""Private common world HUD preparation: treasury label and day abbreviation."""
import argparse,hashlib,json
from pathlib import Path
from ffta_lzss import decompress,compress
from prepare_ui_headings import FONT,width
SOURCE_OFFSET=0x3ad5f8

def funds_row(source,offset,clean_background=False):
 result=bytearray(source)
 def pixel(x,y,c):
  at=offset+(x//8)*32+y*4+(x%8)//2;n=x%2;result[at]=(result[at]&~(15<<(n*4)))|c<<(n*4)
 for y in range(8 if clean_background else 6):
  for x in range(8,72):pixel(x,y,(0 if y<4 else 1 if y==4 else 15 if y==5 else 14)if clean_background else 0)
 mini={'К':['1001','1010','1100','1010','1001'],'А':['0110','1001','1111','1001','1001'],'З':['1110','0001','0110','0001','1110'],'Н':['1001','1001','1111','1001','1001']}
 body=set();x=24
 for c in 'КАЗНА':
  body.update((x+xx,y)for y,row in enumerate(mini[c])for xx,b in enumerate(row)if b=='1');x+=5
 for x,y in body:
  for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
   if 8<=x+dx<72 and 0<=y+dy<6:pixel(x+dx,y+dy,1)
 for x,y in body:pixel(x,y,7)
 return bytes(result)

def translated_bank(source,law_headings=False,clean_funds=False):
 assert len(source)==3168;result=bytearray(funds_row(source,0x640,clean_funds))
 def at(x,y):return (0x920 if y<8 else 0xa60)+(x//8)*32+(y%8)*4+(x%8)//2,x%2
 def pixel(x,y,c):
  pos,n=at(x,y);result[pos]=(result[pos]&~(15<<(n*4)))|c<<(n*4)
 for y in range(16):
  clean=0x900 if y<8 else 0x9c0
  for x in range(16):
   b=source[clean+(y%8)*4+(x%8)//2];pixel(x,y,(b>>(4*(x%2)))&15)
 text='ДН.';assert width(text)<16;body=set();x=1
 for c in text:
  body.update((x+xx,y+4)for y,row in enumerate(FONT[c].split('/'))for xx,b in enumerate(row)if b=='1');x+=len(FONT[c].split('/')[0])+1
 for x,y in body:
  for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
   if 0<=x+dx<16 and 0<=y+dy<16:pixel(x+dx,y+dy,8)
 for x,y in body:pixel(x,y,1)
 if law_headings:
  from prepare_law_headings import translate_headers
  result=translate_headers(bytes(result),0x120,0x4c0)
 return bytes(result)

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--law-headings',action='store_true');p.add_argument('--clean-funds',action='store_true');a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';source,used=decompress(raw,SOURCE_OFFSET);assert used==1295
 result=translated_bank(source,a.law_headings,a.clean_funds);packed=compress(result);assert len(packed)<=used and decompress(packed)==(result,len(packed));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'world-hud-ru.lzss').write_bytes(packed);a.report.write_text(json.dumps({'offset':hex(SOURCE_OFFSET),'decoded_bytes':3168,'source_bytes':used,'payload_bytes':len(packed),'labels':['КАЗНА','ДН.']+(['ЗАПРЕТ','БОНУС']if a.law_headings else[]),'sha256':hashlib.sha256(packed).hexdigest(),'funds_background_rebuilt':a.clean_funds,'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('World HUD packed',len(packed))
if __name__=='__main__':main()
