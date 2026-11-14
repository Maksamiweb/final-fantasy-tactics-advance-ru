"""Add two credits to the title's native BG2 map; preserve original art and OBJ menus."""
import argparse,hashlib,json,struct
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
GRAPHICS=0x960ec0;SOURCE_BYTES=0x1cd4*2;MAP=0x957d28;MAP_BYTES=30*20*2

def make_art(raw,heading_font,credit_font,dark_outline=False,readable_credit=False):
 original=raw[GRAPHICS:GRAPHICS+SOURCE_BYTES];source_map=raw[MAP:MAP+MAP_BYTES];assert len(original)==SOURCE_BYTES
 canvas=Image.new('L',(240,160));entries=struct.unpack('<600H',source_map)
 for cell,e in enumerate(entries):
  x0=cell%30*8;y0=cell//30*8;tile=e&1023;bank=e>>12
  for y in range(8):
   for x in range(8):
    xx=7-x if e&1024 else x;yy=7-y if e&2048 else y;at=tile*32+yy*4+xx//2;c=original[at]>>(xx%2*4)&15
    if c:canvas.putpixel((x0+x,y0+y),bank*16+c)
 before=canvas.copy();rows=[]
 for text,font_path,size,top,style in [('РУССКАЯ ВЕРСИЯ',heading_font,11,61,'heading'),('Перевод Maksami',credit_font,10 if readable_credit else 8,128 if readable_credit else 131,'credit')]:
  font=ImageFont.truetype(str(font_path),size);box=font.getbbox(text);mask=Image.new('L',(box[2]-box[0],box[3]-box[1]));ImageDraw.Draw(mask).text((-box[0],-box[1]),text,font=font,fill=255);left=(240-mask.width)//2;ink={(left+x,top+y)for y in range(mask.height)for x in range(mask.width)if mask.getpixel((x,y))>=70}
  assert left>0 and top+mask.height<140
  for x,y in ink:
   neighbors=[(dx,dy)for dx in(-1,0,1)for dy in(-1,0,1)if dx or dy]if dark_outline and style=='credit'else [(-1,0),(1,0),(0,-1),(0,1)]
   for dx,dy in neighbors:
    canvas.putpixel((x+dx,y+dy),7 if style=='heading' else 28 if dark_outline else 20)
  for x,y in ink:
   color=(1 if y-top<2 else 4 if y-top<5 else 12)if style=='heading'else 24
   canvas.putpixel((x,y),color)
  rows.append({'text':text,'font_sha256':hashlib.sha256(font_path.read_bytes()).hexdigest(),'size':size,'body_box':[left,top,left+mask.width,top+mask.height]})
 data=bytearray(original);data.extend(bytes((-len(data))%32));map_data=bytearray(source_map);changed=[]
 for cell in range(600):
  x0=cell%30*8;y0=cell//30*8
  if all(canvas.getpixel((x0+x,y0+y))==before.getpixel((x0+x,y0+y))for y in range(8)for x in range(8)):continue
  banks={canvas.getpixel((x0+x,y0+y))//16 for y in range(8)for x in range(8)if canvas.getpixel((x0+x,y0+y))};assert len(banks)==1;bank=banks.pop()
  tile=bytes((canvas.getpixel((x0+x,y0+y))&15)|(canvas.getpixel((x0+x+1,y0+y))&15)<<4 for y in range(8)for x in range(0,8,2));index=len(data)//32;assert index<832;data.extend(tile);struct.pack_into('<H',map_data,cell*2,(bank<<12)|index);changed.append(cell)
 assert data[:SOURCE_BYTES]==original and len(map_data)==MAP_BYTES and len(data)%2==0;assert all(a==b for i,(a,b)in enumerate(zip(source_map,map_data))if i//2 not in changed)
 return bytes(data),bytes(map_data),{'labels':rows,'changed_map_cells':changed,'original_graphics_prefix_preserved':True,'old_graphics_bytes':SOURCE_BYTES,'new_graphics_bytes':len(data),'new_copy_halfwords':len(data)//2,'palette_banks':{'heading':0,'credit':1},'credit_dark_8_neighbor_outline':dark_outline,'readable_credit':readable_credit}

def main():
 p=argparse.ArgumentParser()
 for key in('rom','heading-font','credit-font','out-private'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--dark-outline',action='store_true');p.add_argument('--readable-credit',action='store_true')
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';gfx,tiles,report=make_art(raw,a.heading_font,a.credit_font,a.dark_outline,a.readable_credit);a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'graphics.bin').write_bytes(gfx);(a.out_private/'map.bin').write_bytes(tiles);(a.out_private/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Prepared title credits',len(gfx),'bytes',len(report['changed_map_cells']),'map cells')
if __name__=='__main__':main()
