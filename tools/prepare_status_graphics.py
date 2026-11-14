"""Prepare a private translated graphics stream and a software layout model.

Never writes a ROM or patch. Output bank/stream include original pixels and
must stay private. Runtime integration and other consumers remain unverified.
"""
import argparse,collections,json,struct
from pathlib import Path
from PIL import Image
import project
from ffta_lzss import decompress,compress
from draw_status_candidates import raster,COMPACT

LABELS=[('Move',3,(8,64,40,76)),('Jump',3,(8,76,40,88)),('Evade',3,(64,76,96,88)),
        ('Weapon',3,(8,92,56,104)),('Atk',3,(56,92,88,104)),('Def',3,(56,104,88,116)),
        ('Magic',3,(8,116,56,128)),('Pow',3,(56,116,88,128)),('Res',3,(56,128,88,140)),
        ('Speed',3,(24,140,64,152)),('Lv',1,(0,48,16,56)),('Exp',1,(32,48,48,56))]

def mapping(video,bg,x,y):
    base={1:0x6000,3:0x5000}[bg]
    entry=struct.unpack_from('<H',video,base+(y//8*32+x//8)*2)[0]
    xx=x%8;yy=y%8
    if entry&0x400:xx=7-xx
    if entry&0x800:yy=7-yy
    return 0x8000+(entry&1023)*32+yy*4+xx//2,xx%2,entry>>12

def value(video,bg,x,y):
    byte,nibble,_=mapping(video,bg,x,y)
    return(video[byte]>>(4*nibble))&15

def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--memory',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA
    video=(a.memory/'map-06000000.bin').read_bytes();palette=(a.memory/'map-05000000.bin').read_bytes()
    source,used=decompress(raw,0x3b4214);assert len(source)==7264 and used==4000
    assert source[:199*32]==video[0x9280:0xab60]
    names={e['key']:e['ru_compact']for e in json.loads(a.manifest.read_text(encoding='utf-8'))['entries']}
    desired={};records=[]
    for key,bg,(x0,y0,x1,y1)in LABELS:
        text=COMPACT.get(key,names[key].upper());small=key in('Lv','Exp');im=raster(text,small=small)
        origin=(x0+1,y0 if small else y0+1);bbox=im.getbbox()
        assert origin[0]+bbox[2]<=x1 and origin[1]+bbox[3]<=y1,(key,'ink exceeds allocated cells')
        for y in range(y0,y1):
            for x in range(x0,x1):desired[bg,x,y]=0
        for y in range(bbox[3]):
            for x in range(bbox[2]):
                role=im.getpixel((x,y))
                if role:
                    # Preserve palette families: outline 1, dark shadow 4,
                    # native bright-to-dark body ramp 11/10/9 (or white 3).
                    c=1 if role==1 else 4 if role==2 else 3 if small else 11 if y<3 else 10 if y<5 else 9
                    desired[bg,origin[0]+x,origin[1]+y]=c
        records.append({'key':key,'text':text,'bg':bg,'clear_rectangle':[x0,y0,x1,y1],'ink_origin':list(origin),'runtime_verified':False})
    requests=collections.defaultdict(set)
    for(bg,x,y),c in desired.items():
        byte,nibble,_=mapping(video,bg,x,y);requests[byte,nibble].add(c)
    edited=bytearray(source);changed={}
    for(byte,nibble),colors in requests.items():
        assert len(colors)==1,('Aliased pixel has conflicting requests',hex(byte),nibble,colors)
        c=next(iter(colors));old=(video[byte]>>(nibble*4))&15
        if c==old:continue
        assert 0x9280<=byte<0xab60,('Edit outside verified source prefix',hex(byte))
        index=byte-0x9280;edited[index]=(edited[index]&~(15<<(nibble*4)))|(c<<(nibble*4));changed[byte,nibble]=c
    # Prove the software model changes only intended pixels on the two relevant
    # visible layers, including any shared tile references between words.
    outside=[]
    for bg in (1,3):
        for y in range(160):
            for x in range(240):
                byte,nibble,_=mapping(video,bg,x,y)
                if(byte,nibble)in changed and(bg,x,y)not in desired:outside.append([bg,x,y])
    assert not outside,('Shared tiles affect pixels outside label rectangles',outside[:12])
    packed=compress(bytes(edited));decoded,consumed=decompress(packed)
    assert decoded==edited and consumed==len(packed)
    assert len(packed)<=used,'Repacked asset requires relocation; do not claim in-place fit'
    assert edited[199*32:]==source[199*32:],'Unused tail changed'
    a.out_private.mkdir(parents=True,exist_ok=True)
    (a.out_private/'status-ru.bank').write_bytes(edited);(a.out_private/'status-ru.lzss').write_bytes(packed)
    # Native palette and screen maps, only the verified translated bank differs.
    model_video=bytearray(video);model_video[0x9280:0xab60]=edited[:199*32]
    picture=Image.new('RGB',(240,160),'#267f94');pixels=picture.load()
    for bg in (1,3):
        for y in range(160):
            for x in range(240):
                byte,nibble,pal=mapping(model_video,bg,x,y);c=(model_video[byte]>>(nibble*4))&15
                if c:
                    color=int.from_bytes(palette[(pal*16+c)*2:(pal*16+c)*2+2],'little')
                    pixels[x,y]=tuple(((color>>k)&31)*255//31 for k in(0,5,10))
    picture.resize((720,480),Image.Resampling.NEAREST).save(a.out_private/'status-ru-layout-model.png')
    report={'scope':'Private stream preparation and two-layer software model; no ROM integration',
            'source_rom_offset':'0x3b4214','decoder_function':'0x0800543c','source_decoded_bytes':len(source),'source_consumed_bytes':used,
            'source_decoded_sha256':project.digest(source),'translated_decoded_sha256':project.digest(edited),'translated_stream_sha256':project.digest(packed),
            'verified_vram_start':'0x06009280','exact_prefix_tiles':199,'source_tiles':227,'tail_overwritten_by_next_bank':28,
            'translated_stream_bytes':len(packed),'fits_original_consumed_extent':len(packed)<=used,
            'changed_bytes':sum(a!=b for a,b in zip(source,edited)),'changed_nibbles':len(changed),
            'unintended_visible_changes_on_bg1_bg3':len(outside),'labels':records,'deferred_labels':['EQUIP'],
            'rom_or_patch_created':False,'runtime_verified':False,'other_consumers_verified':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items()if k not in('labels',)}))

if __name__=='__main__':main()
