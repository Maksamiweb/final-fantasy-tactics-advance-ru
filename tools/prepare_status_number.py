"""Add an authored number sign to the pinned 12-label private status stream."""
import argparse,hashlib,json
from pathlib import Path
from ffta_lzss import decompress,compress
BASE_SHA='17b01550928240cb62bb0dc37fe6093b138ce3c940af7cba32f416bcaef1e175'
def number_bank(source):
 assert len(source)==7264;result=bytearray(source);pix=[[0]*16 for _ in range(8)];rows=['100100110','110101001','101101001','100100110','100100000','100100111'];body={(x+2,y+1)for y,row in enumerate(rows)for x,b in enumerate(row)if b=='1'}
 for x,y in body:
  for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):pix[y+dy][x+dx]=1
 for x,y in body:pix[y][x]=3
 data=bytes(pix[y][tile*8+x]|pix[y][tile*8+x+1]<<4 for tile in range(2)for y in range(8)for x in range(0,8,2));result[0x560:0x5a0]=data;assert result[:0x560]==source[:0x560]and result[0x5a0:]==source[0x5a0:];return bytes(result)
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-status',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();raw=a.source_status.read_bytes();assert hashlib.sha256(raw).hexdigest()==BASE_SHA;source,_=decompress(raw);after=number_bank(source);payload=compress(after);assert len(payload)<=4000 and decompress(payload)==(after,len(payload));a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'status-number-ru.lzss').write_bytes(payload);report={'base_sha256':BASE_SHA,'payload_sha256':hashlib.sha256(payload).hexdigest(),'decoded_sha256':hashlib.sha256(after).hexdigest(),'payload_bytes':len(payload),'only_new_decoded_span':'0x560..0x59f','new_label':'№','native_verified':False};a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
