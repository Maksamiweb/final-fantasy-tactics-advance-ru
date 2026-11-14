"""Translate the40x16 completed-mission counter on save/load slots."""
import argparse,hashlib,json
from pathlib import Path
from prepare_ui_headings import FONT,width
from ffta_lzss import decompress,compress
SOURCE=0x3bba38

def translated_bank(source):
 assert len(source)==1664;canvas=[[0]*40 for _ in range(16)]
 for text,y0 in [('ЗАДАНИЙ',1),('ПРОЙДЕНО',9)]:
  assert width(text)<=40;ink=set();x0=(40-width(text))//2
  for c in text:
   rows=FONT[c].split('/');ink.update((x0+x,y0+y)for y,row in enumerate(rows)for x,b in enumerate(row)if b=='1');x0+=len(rows[0])+1
  for x,y in ink:
   for dx in(-1,0,1):
    for dy in(-1,0,1):
     if 0<=x+dx<40 and 0<=y+dy<16:canvas[y+dy][x+dx]=1
  for x,y in ink:canvas[y][x]=3 if y-y0<2 else 7 if y-y0<4 else 5
 data=bytes(canvas[ty*8+y][tx*8+x]|canvas[ty*8+y][tx*8+x+1]<<4 for ty in range(2)for tx in range(5)for y in range(8)for x in range(0,8,2));out=data+source[320:];assert len(out)==len(source)and out[320:]==source[320:];return out

def main():
 p=argparse.ArgumentParser()
 for key in('rom','out-private','report'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';source,used=decompress(raw,SOURCE);assert used==580;after=translated_bank(source);payload=compress(after);assert len(payload)<=used and decompress(payload)==(after,len(payload));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'save-counter.lzss').write_bytes(payload);a.report.write_text(json.dumps({'source':hex(SOURCE),'source_bytes':used,'new_bytes':len(payload),'changed_decoded_span':[0,320],'all_other_pixels_unchanged':True,'ru':['ЗАДАНИЙ','ПРОЙДЕНО'],'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Save counter prepared',len(payload))
if __name__=='__main__':main()

