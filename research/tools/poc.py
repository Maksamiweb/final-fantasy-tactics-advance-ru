"""Create a tiny reversible Cyrillic experiment, never alter source; IPS contains authored bytes only."""
import argparse, hashlib, json, struct, sys
from pathlib import Path

# Authored 5x7 bitmap shapes; doubled horizontally into a 16x16 glyph cell.
GLYPHS={
 'П':['11111','10001','10001','10001','10001','10001','10001'],
 'р':['00000','00000','11110','10001','11110','10000','10000'],
 'и':['00000','00000','10001','10011','10101','11001','10001'],
 'в':['00000','00000','11110','10001','11110','10001','11110'],
 'е':['00000','00000','01110','10001','11111','10000','01111'],
 'т':['00000','00000','11111','00100','00100','00100','00100'],
 'м':['00000','00000','10001','11011','10101','10001','10001'],
 ',':['00000','00000','00000','00000','00000','00100','01000'],
 '!':['00100','00100','00100','00100','00100','00000','00100'],
}
KNOWN={'AFXE':('43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19',0x13474,0x13480),
       'AFXJ':('b13dd536808ef5d0fd4494386a9499f6feb8310835d3f867cd17cc340d82bf9a',0x133f4,0x13400),
       'AFXP':('8fab1e390cb9d5e695bfdb86e81246892e1aa8c0cb4014db8235ff76538ea632',0x135cc,0x135d8)}

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--private-out',type=Path,required=True);p.add_argument('--patch-out',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.upstream.resolve()));import ffta_sect as s
    original=a.rom.read_bytes();code=original[0xac:0xb0].decode();digest,fp,wp=KNOWN[code]
    assert hashlib.sha256(original).hexdigest()==digest,'Unsupported input hash'
    if code=='AFXP':r=s.c_ffta_sect_rom(original,0).setup({'s_text':(0x9b04,s.c_ffta_sect_text)},len(original))
    else:r=(s.load_rom_us if code=='AFXE' else s.load_rom_jp)(str(a.rom))
    line=r.tabs['s_text'][1][0];font=struct.unpack_from('<I',original,fp)[0]-0x8000000;width=struct.unpack_from('<I',original,wp)[0]-0x8000000
    changes=[]
    def change(offset,data):
        assert 0<=offset and offset+len(data)<=len(original)
        changes.append((offset,bytes(data)))
    glyph_ids={ch:0x300+i for i,ch in enumerate(GLYPHS)}
    for ch,rows in GLYPHS.items():
        pixels=[[0]*16 for _ in range(16)]
        for y,row in enumerate(rows):
            for x,val in enumerate(row):
                if val=='1':
                    for yy in (y*2+1,y*2+2):pixels[yy][x*2+1]=pixels[yy][x*2+2]=3
        # Two vertical 8x16 tile strips, 4bpp, low nibble first.
        values=[pixels[y][tile*8+x] for tile in range(2) for y in range(16) for x in range(8)]
        packed=bytes(values[i]|(values[i+1]<<4) for i in range(0,256,2))
        change(font+glyph_ids[ch]*128,packed);change(width+glyph_ids[ch],bytes([12]))
    tokens=[('CTR_FUNC',0x52) if ch==' ' else ('CHR_FULL',glyph_ids[ch]) for ch in 'Привет, мир!']
    tokens += [('CTR_FUNC',0x40),('CTR_FUNC',0x42)]
    encoded=bytes(line.text._encode(tokens));payload=struct.pack('<H',line.U16(0)&0xfc)+encoded
    assert len(payload)<=line.raw_len,'Test does not fit verified allocation'
    change(line.real_offset,payload+bytes(line.raw_len-len(payload)))
    modified=bytearray(original)
    for offset,new in changes:modified[offset:offset+len(new)]=new
    # Verify exact authored writes, preserved size/header, and parse the inserted text.
    assert len(modified)==len(original) and modified[:0xc0]==original[:0xc0]
    test=s.c_ffta_sect_text_line(bytes(modified),line.real_offset);test.parse_size(line.raw_len,2);test.parse();assert test.text.tokens==tokens
    a.private_out.mkdir(parents=True,exist_ok=True);a.patch_out.mkdir(parents=True,exist_ok=True)
    dest=a.private_out/(code+'-cyrillic.gba');dest.write_bytes(modified)
    ips=bytearray(b'PATCH')
    for off,new in sorted(changes):ips+=off.to_bytes(3,'big')+len(new).to_bytes(2,'big')+new
    ips+=b'EOF';patch=a.patch_out/(code+'-cyrillic.ips');patch.write_bytes(ips)
    # Independently apply IPS and prove its output matches the generated private ROM.
    applied=bytearray(original);i=5
    while ips[i:i+3]!=b'EOF':
        off=int.from_bytes(ips[i:i+3],'big');n=int.from_bytes(ips[i+3:i+5],'big');i+=5;applied[off:off+n]=ips[i:i+n];i+=n
    assert applied==modified
    report={'code':code,'source_sha256':digest,'modified_sha256':hashlib.sha256(modified).hexdigest(),'patch_sha256':hashlib.sha256(ips).hexdigest(),'line_offset':hex(line.real_offset),'original_allocation':line.raw_len,'inserted_bytes':len(payload),'font_offset':hex(font),'width_offset':hex(width),'glyph_ids':glyph_ids,'records':len(changes),'changed_bytes':sum(x!=y for x,y in zip(original,modified)),'static_parse_pass':True,'ips_application_pass':True,'warning':'Experimental glyph slots overwrite existing CJK glyphs; not a production localization.'}
    (a.patch_out/(code+'-poc.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
