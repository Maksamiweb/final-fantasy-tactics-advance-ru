"""Private Russian battle objective captions and two raw goal headings."""
import argparse,hashlib,json,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from ffta_a7 import decode_archive,encode_literal_archive
FONT_SHA='e432c1b3568bd207e30e3d52d41e6431ea53a679eb52dd79b1a36aa6a4f3b994'
LABELS=['ПОБЕДИТЕ ГЛАВАРЯ!','ПОБЕДИТЕ ВСЕХ ВРАГОВ!','ВЫЖИВИТЕ!','УНИЧТОЖЬТЕ ВСЕ ЦЕЛИ!','ДОЙДИТЕ ДО ТОЧКИ!','СНЕЖНЫЙ БОЙ!']
def alpha_label(text,font,width,height):
 b=font.getbbox(text);im=Image.new('L',(b[2]-b[0],b[3]-b[1]));ImageDraw.Draw(im).text((-b[0],-b[1]),text,font=font,fill=255)
 if im.width>width or im.height>height:im=im.resize((min(width,im.width),min(height,im.height)),Image.Resampling.LANCZOS)
 return im

def make_goals(raw,font_path):
 assert hashlib.sha256(font_path.read_bytes()).hexdigest()==FONT_SHA;original=[x['data']for x in decode_archive(raw,0x3c1834)];assert len(original)==6 and all(len(x)==1472 for x in original);font=ImageFont.truetype(str(font_path),14);blocks=[];rows=[]
 for n,(source,text)in enumerate(zip(original,LABELS)):
  values=[c for b in source for c in(b&15,b>>4)];canvas=Image.new('L',(160,16));mask=set()
  for y in range(16):
   for x in range(160):
    v=values[((y//8)*20+x//8)*64+y%8*8+x%8]
    if v:mask.add((x,y));canvas.putpixel((x,y),8)
  xs=[x for x,y in mask];x0,x1=min(xs),max(xs)+1;im=alpha_label(text,font,x1-x0-2,14);left=x0+(x1-x0-im.width)//2;top=(16-im.height)//2
  for y in range(im.height):
   for x in range(im.width):
    a=im.getpixel((x,y));xy=(left+x,top+y)
    if a:
     assert xy in mask;canvas.putpixel(xy,max(1,8-round(7*a/255)))
  out=bytearray(source)
  for y in range(16):
   for x in range(160):
    at=((y//8)*20+x//8)*32+y%8*4+x%8//2;shift=x%2*4;out[at]=(out[at]&~(15<<shift))|canvas.getpixel((x,y))<<shift
  assert out[1280:]==source[1280:];assert all((values[((y//8)*20+x//8)*64+y%8*8+x%8]==0)==(canvas.getpixel((x,y))==0)for y in range(16)for x in range(160));blocks.append(bytes(out));rows.append({'selector':n,'ru':text,'original_panel_bounds':[x0,x1],'rendered_width':im.width,'caps_and_transparent_mask_unchanged':True})
 # The raw headers use32x16+16x16 and32x16+32x16+16x16 OBJ pieces.
 headers=[];font=ImageFont.truetype(str(font_path),13)
 for text,widths in [('ЦЕЛЬ:',[32,16]),('КОМАНДНАЯ ИГРА:',[32,32,16])]:
  width=sum(widths);canvas=Image.new('L',(width,16));im=alpha_label(text,font,width-4,12);x0=1;y0=(16-im.height)//2;ink={(x+x0,y+y0)for y in range(im.height)for x in range(im.width)if im.getpixel((x,y))>=100}
  for x,y in ink:
   for dx in(-1,0,1):
    for dy in(-1,0,1):
     if 0<=x+dx<width and 0<=y+dy<16:canvas.putpixel((x+dx,y+dy),1)
  for x,y in ink:canvas.putpixel((x,y),3)
  data=bytearray();left=0
  for w in widths:
   for ty in range(2):
    for tx in range(w//8):
     for y in range(8):
      for x in range(0,8,2):data.append(canvas.getpixel((left+tx*8+x,ty*8+y))|canvas.getpixel((left+tx*8+x+1,ty*8+y))<<4)
   left+=w
  headers.append(bytes(data))
 assert len(headers[0])==384 and len(headers[1])==640
 return blocks,b''.join(headers),rows

def main():
 p=argparse.ArgumentParser()
 for k in('rom','font','out-private','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';bs,hs,rows=make_goals(raw,a.font);payload=encode_literal_archive(bs);assert [x['data']for x in decode_archive(payload)]==bs;a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'goals.a7').write_bytes(payload);(a.out_private/'headers.bin').write_bytes(hs);a.report.write_text(json.dumps({'source':'0x3c1834','raw_headers':'0x3bef08..0x3bf307','labels':6,'headers':2,'entries':rows,'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Prepared6 battle goals and2 headers')
if __name__=='__main__':main()
