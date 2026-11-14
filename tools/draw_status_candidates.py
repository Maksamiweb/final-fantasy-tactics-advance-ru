"""Authored 5x7 Cyrillic graphic candidates. No original game pixels or ROM IO.

Role indices: 0 transparent, 1 outline, 2 shadow, 3 body. These are NOT yet
verified native palette indices for the FFTA status renderer.
"""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw

GLYPHS={
'.':'00000/00000/00000/00000/00000/00000/10000',
'А':'01110/10001/10001/11111/10001/10001/10001',
'Г':'11111/10000/10000/10000/10000/10000/10000',
'Д':'01110/01010/01010/01010/01010/11111/10001',
'Е':'11111/10000/10000/11110/10000/10000/11111',
'Ж':'10101/10101/01110/00100/01110/10101/10101',
'З':'11110/00001/00001/01110/00001/00001/11110',
'И':'10001/10001/10011/10101/11001/10001/10001',
'К':'10001/10010/10100/11000/10100/10010/10001',
'Л':'00111/01001/01001/01001/01001/01001/10001',
'М':'10001/11011/10101/10101/10001/10001/10001',
'Н':'10001/10001/10001/11111/10001/10001/10001',
'О':'01110/10001/10001/10001/10001/10001/01110',
'П':'11111/10001/10001/10001/10001/10001/10001',
'Р':'11110/10001/10001/11110/10000/10000/10000',
'С':'01111/10000/10000/10000/10000/10000/01111',
'Т':'11111/00100/00100/00100/00100/00100/00100',
'У':'10001/10001/10001/01111/00001/00001/11110',
'Х':'10001/10001/01010/00100/01010/10001/10001',
'Ы':'10001/10001/10001/11101/10011/10011/11101',
'Щ':'10101/10101/10101/10101/10101/11111/00001',
'Я':'01111/10001/10001/01111/00101/01001/10001',
}
COMPACT={'Jump':'ПРЫЖ.','Exp':'ОП.','EQUIP':'СНАР.','Pow':'СИЛ.','Res':'СОП.'}
MINI={
'У':'1001/1001/0111/0001/1110',
'Р':'1110/1001/1110/1000/1000',
'О':'0110/1001/1001/1001/0110',
'П':'1111/1001/1001/1001/1001',
'.':'0000/0000/0000/0000/1000',
}

def raster(text,small=False):
    advance=5 if small else 6
    width=len(text)*advance+1
    im=Image.new('P',((width+7)//8*8,16))
    body=set()
    for i,c in enumerate(text):
        rows=(MINI if small else GLYPHS)[c].split('/')
        assert len(rows)==(5 if small else 7) and all(len(row)==(4 if small else 5)for row in rows)
        body.update((1+i*advance+x,1+y)for y,row in enumerate(rows)for x,v in enumerate(row)if v=='1')
    for x,y in body:
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:im.putpixel((x+dx,y+dy),1)
    for x,y in body:
        if (x+1,y+1)not in body:im.putpixel((x+1,y+1),2)
    for x,y in body:im.putpixel((x,y),3)
    return im

def tiles(im):
    out=bytearray()
    for ty in range(0,im.height,8):
        for tx in range(0,im.width,8):
            for y in range(8):
                for x in range(0,8,2):out.append(im.getpixel((tx+x,ty+y))|im.getpixel((tx+x+1,ty+y))<<4)
    return bytes(out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    entries=json.loads(a.manifest.read_text(encoding='utf-8'))['entries'];a.out.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGB',(420,len(entries)*44+30),'#eee7cb');draw=ImageDraw.Draw(sheet)
    draw.text((8,8),'Authored candidates / not integrated',fill='#222222');records=[]
    for i,e in enumerate(entries):
        text=COMPACT.get(e['key'],e['ru_compact'].upper());im=raster(text,small=e['key']in('Lv','Exp'));data=tiles(im);bbox=im.getbbox();width=bbox[2]-bbox[0]
        # Provisional free label areas measured from the old status screenshot;
        # excludes adjacent numeric values, not a recovered engine allocation.
        budget={'Jump':32,'Evade':32,'Weapon':48,'Magic':48,'EQUIP':32,'Exp':16,'Lv':16,'Pow':32}.get(e['key'],38 if e['key']=='Speed' else 30)
        assert width<=budget,(text,width,budget)
        pal=[238,231,203,28,26,19,130,110,64,255,245,184]+[0]*756
        im.putpalette(pal);im.save(a.out/(e['key']+'.png'),transparency=0)
        (a.out/(e['key']+'.4bpp')).write_bytes(data)
        y=30+i*44;draw.text((8,y+9),e['key'],fill='#222222');sheet.paste(im.convert('RGB').resize((im.width*3,im.height*3),Image.Resampling.NEAREST),(110,y))
        records.append({'key':e['key'],'text':text,'ink_width_px':width,'ink_height_px':bbox[3]-bbox[1],
                        'provisional_available_px':budget,'tile_canvas':[im.width,im.height],
                        'sha256_4bpp':hashlib.sha256(data).hexdigest(),'runtime_verified':False})
    sheet.save(a.out/'preview.png')
    (a.out/'manifest.json').write_text(json.dumps({'status':'authored candidates, no ROM integration','palette':'semantic roles, not verified native indices','entries':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'labels':len(records),'fit_provisional_areas':True,'rom_created':False}))

if __name__=='__main__':main()
