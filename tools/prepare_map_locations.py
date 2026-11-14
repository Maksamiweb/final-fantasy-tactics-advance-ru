"""Author all30 map place labels from translated canonical location names.

Repack the existing five native40..72px OAM layouts; retain native geometry.
All archive pixels are authored. Source graphics are not copied into outputs.
"""
import argparse,hashlib,json,math,re,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from ffta_a7 import encode_literal_archive,decode_archive
SOURCE=0x3ab42c;WIDTH_TABLE=0x391de4;OFFSET_TABLE=0x391e02
SIZES=[[(8,8),(16,16),(32,32),(64,64)],[(16,8),(32,8),(32,16),(64,32)],[(8,16),(8,32),(16,32),(32,64)]]
FONT_SHA='9cc831490532009bae2b3ce0d39c62adfc889060beb421593bfd9d2396d0f10a'
def material(raw,code):
 p=struct.unpack_from('<I',raw,0x391a48+code*4)[0]-0x08000000;n=struct.unpack_from('<H',raw,p)[0];parts=[]
 for j in range(n):
  a,b,c=struct.unpack_from('<HHH',raw,p+2+j*6);w,h=SIZES[a>>14][b>>14];assert not a&0x2100 and not b&0x3000;parts.append((b&511,a&255,w,h,(c&1023)-0x4c))
 assert max(x+w for x,y,w,h,t in parts)==40+8*code and max(y+h for x,y,w,h,t in parts)==16
 return parts

def pack_canvas(canvas,parts):
 width,height=canvas.size;pixels=[0]*(width*16);seen=set()
 for x0,y0,w,h,start in parts:
  for y in range(h):
   for x in range(w):
    px=x0+x;py=y0+y;ref=(start+(y//8)*(w//8)+x//8)*64+(y%8)*8+x%8
    assert ref not in seen;seen.add(ref);pixels[ref]=canvas.getpixel((px,py))
 assert seen==set(range(width*16))
 return bytes(pixels[i]|pixels[i+1]<<4 for i in range(0,len(pixels),2))

def make_asset(raw,entries,font_path):
 assert hashlib.sha256(font_path.read_bytes()).hexdigest()==FONT_SHA
 by={e['id']:e for e in entries};font=ImageFont.truetype(str(font_path),12);blocks=[];codes=[];offsets=[];rows=[];previews=[]
 old_codes=list(raw[WIDTH_TABLE:WIDTH_TABLE+30]);old_offsets=struct.unpack_from('<30H',raw,OFFSET_TABLE);assert len(decode_archive(raw,SOURCE))==225
 assert list(old_offsets)==[sum(5+x for x in old_codes[:i])*2 for i in range(30)]
 for i in range(30):
  ident=f'words:content/{718+i}';name=by[ident]['ru'].replace('[[1D02]]',' ');name=re.sub(r'\[\[[^\]]*\]\]','',name);assert re.fullmatch(r'[А-Яа-яЁё ]+',name),ident
  box=font.getbbox(name);body=Image.new('L',(box[2]-box[0],box[3]-box[1]));ImageDraw.Draw(body).text((-box[0],-box[1]),name,font=font,fill=255)
  natural=body.width;code=min(4,max(0,math.ceil((natural+2-40)/8)));width=40+code*8
  if natural>width-2:body=body.resize((width-2,body.height),Image.Resampling.LANCZOS)
  assert body.height<=14;canvas=Image.new('L',(width,16));x0=(width-body.width)//2;y0=(16-body.height)//2;ink={(x+x0,y+y0)for y in range(body.height)for x in range(body.width)if body.getpixel((x,y))>=100}
  for x,y in ink:
   for dx in(-1,0,1):
    for dy in(-1,0,1):
     if 0<=x+dx<width and 0<=y+dy<16:canvas.putpixel((x+dx,y+dy),1)
  for x,y in ink:canvas.putpixel((x,y),3)
  packed=pack_canvas(canvas,material(raw,code));assert len(packed)==64*(5+code);offsets.append(len(blocks)*2);codes.append(code);blocks.extend(packed[a:a+64]for a in range(0,len(packed),64));rows.append({'index':i,'reference':ident,'ru':name,'width':width,'native_layout_class':code,'natural_body_width':natural,'rendered_body_width':body.width,'body_height':body.height,'start_chunk':offsets[-1]//2,'chunks':5+code});previews.append(canvas)
 return blocks,bytes(codes),struct.pack('<30H',*offsets),rows,previews

def main():
 p=argparse.ArgumentParser()
 for key in('rom','translation','font','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';entries=json.loads(a.translation.read_text(encoding='utf8'))['entries'];blocks,codes,offsets,rows,previews=make_asset(raw,entries,a.font);packed=encode_literal_archive(blocks);assert [x['data']for x in decode_archive(packed)]==blocks;a.out.mkdir(parents=True,exist_ok=True);(a.out/'map-locations.a7').write_bytes(packed);(a.out/'width-codes.bin').write_bytes(codes);(a.out/'tile-offsets.bin').write_bytes(offsets);(a.out/'manifest.json').write_text(json.dumps({'source':hex(SOURCE),'labels':30,'chunks':len(blocks),'decoded_bytes':64*len(blocks),'all_pixels_authored':True,'native_geometry_preserved':True,'sha256':hashlib.sha256(packed).hexdigest(),'entries':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 sheet=Image.new('RGB',(600,30*66),'#505050');dr=ImageDraw.Draw(sheet)
 for i,(row,im)in enumerate(zip(rows,previews)):
  dr.text((5,i*66+8),str(i)+' '+row['ru'],font=ImageFont.truetype(str(a.font),15),fill='white');rgb=Image.new('RGB',im.size,'#718a75')
  for y in range(16):
   for x in range(im.width):
    c=im.getpixel((x,y))
    if c:rgb.putpixel((x,y),(0,0,0)if c==1 else(255,255,255))
  sheet.paste(rgb.resize((im.width*4,64)),(280,i*66))
 sheet.save(a.out/'preview.png');print('Prepared30 map names',len(blocks),'chunks')
if __name__=='__main__':main()
