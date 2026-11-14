"""Author Russian mission/battle result stamps with original sprite counts.

The4 glyph sheets stay6144 bytes each and the4 BG outlines stay3840 bytes.
Only glyph offsets and target x positions in existing material records change.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from ffta_a7 import encode_literal_archive,decode_archive
from prepare_battle_goals import FONT_SHA
CASES=[
 (0x3940b4,15,['ЗА','Д','А','Н','И','Е','ВЫ','П','О','Л','Н','Е','Н','О','!'],6,'ЗАДАНИЕ ВЫПОЛНЕНО!'),
 (0x3941e0,14,['ЗА','Д','А','Н','ИЕ','ПР','О','В','А','Л','Е','Н','О','!'],5,'ЗАДАНИЕ ПРОВАЛЕНО!'),
 (0x394168,10,['','П','О','Б','Е','Д','А','','','!'],None,'ПОБЕДА!'),
 (0x394288,11,['','П','О','Р','А','Ж','Е','Н','И','Е','!'],None,'ПОРАЖЕНИЕ!')]

def tiled(im):
 w,h=im.size;assert w%8==h%8==0
 return bytes(im.getpixel((tx*8+x,ty*8+y))|im.getpixel((tx*8+x+1,ty*8+y))<<4 for ty in range(h//8)for tx in range(w//8)for y in range(8)for x in range(0,8,2))

def make_results(raw,font_path):
 assert hashlib.sha256(font_path.read_bytes()).hexdigest()==FONT_SHA;assert [len(x['data'])for x in decode_archive(raw,0x3bf308)]==[6144]*4;assert [len(x['data'])for x in decode_archive(raw,0x3c05e8)]==[3840]*4
 font=ImageFont.truetype(str(font_path),24);top=font.getbbox('ЗАДАНИЕВЫПОЛНЕНО!ПОРАЖЕНИЕ')[1];bottom=font.getbbox('ЗАДАНИЕВЫПОЛНЕНО!ПОРАЖЕНИЕ')[3];height=bottom-top;assert height<=26;all_main=[];all_bg=[];tables=[];rows=[];previews=[]
 for index,(table,count,groups,space_before,label)in enumerate(CASES):
  assert len(groups)==count;unique=list(dict.fromkeys(groups));assert len(unique)<=12;images={};adv={}
  for group in unique:
   if not group:images[group]=Image.new('L',(1,height));adv[group]=0;continue
   b=font.getbbox(group);im=Image.new('L',(b[2]-b[0],height));ImageDraw.Draw(im).text((-b[0],-top),group,font=font,fill=255);images[group]=im;adv[group]=font.getlength(group)
  gap=font.getlength(' ');total=sum(adv[g]for g in groups)+(gap if space_before is not None else 0);scale=min(1,230/total,min(30/images[g].width for g in unique if g));scaled_adv={g:adv[g]*scale for g in unique};total=sum(scaled_adv[g]for g in groups)+(gap*scale if space_before is not None else 0);left=(240-total)/2;cursor=0;glyphs={};slots={g:i for i,g in enumerate(unique)};y0=(32-height)//2
  for g,im in images.items():
   a=Image.new('L',(32,32));im=im.resize((min(30,max(1,round(im.width*scale))),height),Image.Resampling.LANCZOS)
   if g:a.paste(im,(1,y0))
   glyphs[g]=a
  output=bytearray();full=Image.new('L',(240,32));targets=[];records=bytearray(raw[table:table+count*12])
  for i,g in enumerate(groups):
   if i==space_before:cursor+=gap*scale
   x=round(left+cursor)-1;targets.append(x);struct.pack_into('<H',records,i*12+4,slots[g]*16);struct.pack_into('<h',records,i*12+8,x);a=glyphs[g]
   for y in range(32):
    for xx in range(32):
     px=x+xx
     if 0<=px<240 and a.getpixel((xx,y))>full.getpixel((px,y)):full.putpixel((px,y),a.getpixel((xx,y)))
   cursor+=scaled_adv[g]
  for g in unique:
   mask=glyphs[g];indexed=Image.new('L',(32,32))
   for y in range(32):
    for x in range(32):indexed.putpixel((x,y),min(7,round(mask.getpixel((x,y))*7/255)))
   output.extend(tiled(indexed))
  output.extend(bytes(6144-len(output)));assert len(output)==6144
  core=full.point(lambda v:255 if v>=80 else 0);outer=core.filter(ImageFilter.MaxFilter(5));inner=core.filter(ImageFilter.MaxFilter(3));bg=Image.new('L',(240,32))
  for y in range(32):
   for x in range(240):
    if outer.getpixel((x,y)):bg.putpixel((x,y),10 if inner.getpixel((x,y))else 11)
  background=tiled(bg);assert len(background)==3840
  # Native record counts, material pointers, palettes and y values remain exact.
  for i in range(count):
   assert records[i*12:i*12+4]==raw[table+i*12:table+i*12+4];assert records[i*12+6:i*12+8]==raw[table+i*12+6:table+i*12+8];assert records[i*12+10:i*12+12]==raw[table+i*12+10:table+i*12+12]
  all_main.append(bytes(output));all_bg.append(background);tables.append((table,bytes(records)));rows.append({'selector':index,'ru':label,'native_objects':count,'unique_glyph_groups':len(unique),'groups':groups,'target_x':targets,'rendered_width':round(total),'unchanged_counts_materials_palettes_y':True});previews.append((full,bg))
 return all_main,all_bg,tables,rows,previews

def main():
 p=argparse.ArgumentParser()
 for key in('rom','font','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';main,bg,tables,rows,previews=make_results(raw,a.font);a.out.mkdir(parents=True,exist_ok=True);(a.out/'results-main.a7').write_bytes(encode_literal_archive(main));(a.out/'results-bg.a7').write_bytes(encode_literal_archive(bg));(a.out/'tables.json').write_text(json.dumps([{'offset':hex(at),'data':d.hex()}for at,d in tables],indent=2)+'\n');(a.out/'manifest.json').write_text(json.dumps({'labels':4,'all_pixels_authored':True,'font_sha256':FONT_SHA,'entries':rows,'native_verified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 sheet=Image.new('RGB',(960,4*150),'#396857')
 for i,(body,bg)in enumerate(previews):
  im=Image.new('RGB',(240,32),'#396857')
  for y in range(32):
   for x in range(240):
    if bg.getpixel((x,y)):im.putpixel((x,y),(240,180,195))
    if body.getpixel((x,y))>=100:im.putpixel((x,y),(255,249,210))
  sheet.paste(im.resize((960,128)),(0,i*150))
 sheet.save(a.out/'preview.png');print('Prepared4 result stamps with native sprite counts')
if __name__=='__main__':main()

