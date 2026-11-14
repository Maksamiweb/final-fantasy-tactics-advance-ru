"""Private in-place mission RANK/PAGE graphic preparation; source pixels stay private."""
import argparse,hashlib,json
from pathlib import Path
from ffta_lzss import decompress,compress
from prepare_ui_headings import FONT,width
SOURCE_OFFSET=0x3aeea4

def translated_bank(source,clean_funds=False):
 assert len(source)==2880
 from prepare_world_hud import funds_row
 result=bytearray(funds_row(source,0,clean_funds))
 for at,span,text,color in [(0x280,3,'СПР.',3),(0x5e0,4,'РАНГ',7),(0x660,3,'СТР.',3)]:
  assert width(text)+2<=span*8
  pixels=[[0]*(span*8)for _ in range(8)];body=set();x=1
  for c in text:
   rows=FONT[c].split('/')
   body.update((x+xx,y+1)for y,row in enumerate(rows)for xx,b in enumerate(row)if b=='1');x+=len(rows[0])+1
  for x,y in body:
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    if 0<=x+dx<span*8 and 0<=y+dy<8:pixels[y+dy][x+dx]=1
  for x,y in body:pixels[y][x]=color
  data=bytes(pixels[y][tile*8+x]|pixels[y][tile*8+x+1]<<4 for tile in range(span)for y in range(8)for x in range(0,8,2))
  result[at:at+len(data)]=data
 assert result[:0x20]==source[:0x20]and result[0x120:0x280]==source[0x120:0x280]and result[0x2e0:0x5e0]==source[0x2e0:0x5e0]and result[0x6c0:]==source[0x6c0:]
 return bytes(result)

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--clean-funds',action='store_true');a=p.parse_args()
 raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19'
 before,used=decompress(raw,SOURCE_OFFSET);assert used==1629
 after=translated_bank(before,a.clean_funds);payload=compress(after);assert decompress(payload)==(after,len(payload));assert len(payload)<=used
 a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'mission-ru.lzss').write_bytes(payload)
 report={'source_offset':hex(SOURCE_OFFSET),'decoded_bytes':2880,'source_consumed_bytes':used,'new_consumed_bytes':len(payload),'changed_tile_spans':['0x20..0x11f','0x280..0x2df','0x5e0..0x6bf'],'all_other_decoded_bytes_unchanged':True,'source_vram_matches':'All seven original tiles exactly matched ordinary mission VRAM9020..90ff','labels':['КАЗНА','СПР.','РАНГ','СТР.'],'payload_sha256':hashlib.sha256(payload).hexdigest(),'funds_background_rebuilt':a.clean_funds,'native_verified':False};a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
