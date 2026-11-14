"""Russian ability type captions in four 40x16 interleaved A7 graphics.

Preserve all upper icon pixels and the lower two border rows.
"""
import argparse,hashlib,json
from pathlib import Path
from ffta_a7 import decode_archive,encode_literal_archive
from prepare_ui_headings import FONT,width
LABELS=['ДЕЙСТВ.','РЕАКЦИЯ','ПОДДЕРЖ.','КОМБО']
def chunks(raw):
 source=[x['data']for x in decode_archive(raw,0x3c5744)];assert len(source)==4 and all(len(x)==320 for x in source);result=[]
 for data,text in zip(source,LABELS):
  assert width(text)<=40;out=bytearray(data)
  def pos(x,y):return ((x//8)*2+y//8)*32+(y%8)*4+(x%8)//2
  def pixel(x,y,c):
   at=pos(x,y);n=x%2;out[at]=(out[at]&~(15<<(4*n)))|c<<(4*n)
  for y in range(8,14):
   for x in range(40):pixel(x,y,0)
  x=(40-width(text))//2
  for c in text:
   rows=FONT[c].split('/')
   for y,row in enumerate(rows):
    for xx,b in enumerate(row):
     if b=='1':pixel(x+xx,y+8,3)
   x+=len(rows[0])+1
  for y in list(range(8))+[14,15]:
   for x in range(40):
    at=pos(x,y);n=x%2;assert(out[at]>>(4*n))&15==(data[at]>>(4*n))&15
  result.append(bytes(out))
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';data=chunks(raw);packed=encode_literal_archive(data);assert [x['data']for x in decode_archive(packed)]==data;a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'ability-types-ru.a7').write_bytes(packed);a.report.write_text(json.dumps({'source':'0x3c5744','chunks':4,'decoded_bytes':1280,'labels':LABELS,'icon_upper_half_and_border_rows_unchanged':True,'payload_sha256':hashlib.sha256(packed).hexdigest(),'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Ability type graphics prepared')
if __name__=='__main__':main()
