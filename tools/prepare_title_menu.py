"""Author title-screen menu labels in the existing raw OBJ tile spans."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageFont,ImageDraw,ImageFilter
CASES=[(0x9665f8,'НАЖМИТЕ START',[32,32,32,16]),(0x966978,'НОВАЯ ИГРА',[32,32]),(0x966b78,'ЗАГРУЗИТЬ',[32,32,8]),(0x966db8,'ЦВЕТА',[32,32,16])]
def make_art(font_path,left_align=False):
 font=ImageFont.truetype(str(font_path),14);out=[]
 for offset,text,parts in CASES:
  width=sum(parts);bbox=font.getbbox(text);mask=Image.new('L',(bbox[2]-bbox[0],bbox[3]-bbox[1]));ImageDraw.Draw(mask).text((-bbox[0],-bbox[1]),text,font=font,fill=255)
  max_width=60 if left_align and offset!=0x9665f8 else width-4
  if mask.width>max_width or mask.height>12:mask=mask.resize((min(max_width,mask.width),min(12,mask.height)),Image.Resampling.LANCZOS)
  canvas=Image.new('L',(width,16));canvas.paste(mask,((width-mask.width)//2,(16-mask.height)//2));outline=canvas.filter(ImageFilter.MaxFilter(3));im=Image.new('L',(width,16))
  for y in range(16):
   for x in range(width):
    a=canvas.getpixel((x,y));im.putpixel((x,y),max(1,round(a*8/255))if a>=32 else 1 if outline.getpixel((x,y))>=100 else 0)
  if left_align and offset!=0x9665f8:
   native_x={0x966978:28,0x966b78:20,0x966db8:12}[offset];box=im.getbbox();aligned=Image.new('L',(width,16));aligned.paste(im.crop(box),(29-native_x,box[1]));im=aligned
  data=bytearray();left=0
  for pw in parts:
   data.extend(im.getpixel((left+tx*8+x,ty*8+y))|im.getpixel((left+tx*8+x+1,ty*8+y))<<4 for ty in range(2)for tx in range(pw//8)for y in range(8)for x in range(0,8,2));left+=pw
  assert len(data)==width*8;out.append((offset,bytes(data)))
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--font',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--left-align',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 for offset,data in make_art(a.font,a.left_align):(a.out/(hex(offset)+'.bin')).write_bytes(data)
 (a.out/'manifest.json').write_text(json.dumps({'authored_pixels':True,'left_aligned':a.left_align,'labels':[{'offset':hex(o),'ru':t,'native_parts':s}for o,t,s in CASES],'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
