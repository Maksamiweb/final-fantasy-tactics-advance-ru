"""Translate duplicated law headings; keep panel borders and all other pixels."""
import argparse,hashlib,json
from pathlib import Path
FONT={
'З':'11110/00001/00110/00001/00001/11110','А':'01110/10001/10001/11111/10001/10001',
'П':'11111/10001/10001/10001/10001/10001','Р':'11110/10001/10001/11110/10000/10000',
'Е':'11111/10000/11110/10000/10000/11111','Т':'11111/00100/00100/00100/00100/00100',
'Б':'11111/10000/11110/10001/10001/11110','О':'01110/10001/10001/10001/10001/01110',
'Н':'10001/10001/11111/10001/10001/10001','У':'10001/10001/01111/00001/00010/11100',
'С':'01111/10000/10000/10000/10000/01111'}
def width(text):return sum(len(FONT[c].split('/')[0])+1 for c in text)-1
from ffta_lzss import decompress,compress
SOURCE_OFFSET=0x3c4888

def translate_headers(source,forbidden,recommend):
 result=bytearray(source);allowed=set()
 for off,span,text,background,ink in [(forbidden,64,'ЗАПРЕТ',6,8),(recommend,80,'БОНУС',8,6)]:
  assert width(text)<=span and off+span*4<=len(source)
  def pixel(x,y,c):
   at=off+(x//8)*32+y*4+x%8//2;n=x%2;result[at]=(result[at]&~(15<<(n*4)))|c<<(n*4);allowed.add(at)
  for y in range(6):
   for x in range(span):pixel(x,y,background)
  x=(span-width(text))//2
  for c in text:
   rows=FONT[c].split('/')
   for y,row in enumerate(rows):
    for xx,b in enumerate(row):
     if b=='1':pixel(x+xx,y,ink)
   x+=len(rows[0])+1
 assert all(a==b or i in allowed for i,(a,b)in enumerate(zip(source,result)))
 return bytes(result)

def translated_bank(source):
 assert len(source)==1472
 return translate_headers(source,0xa0,0x440)

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';source,used=decompress(raw,SOURCE_OFFSET);assert used==542;after=translated_bank(source);packed=compress(after);assert len(packed)<=used and decompress(packed)==(after,len(packed));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'law-panel-ru.lzss').write_bytes(packed);a.report.write_text(json.dumps({'offset':hex(SOURCE_OFFSET),'decoded_bytes':1472,'source_bytes':used,'payload_bytes':len(packed),'labels':['ЗАПРЕТ','БОНУС'],'only_text_rows_0_to_5_changed':True,'sha256':hashlib.sha256(packed).hexdigest(),'native_context_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Law panel prepared',len(packed))
if __name__=='__main__':main()
