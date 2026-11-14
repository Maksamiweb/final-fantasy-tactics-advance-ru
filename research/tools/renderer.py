"""Disassemble verified glyph-loader routines; requires capstone. Offsets are ROM offsets."""
import argparse, collections, json, struct
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--out',type=Path,default=Path('reports/renderer.json'));a=p.parse_args();out={};cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    for f in a.root.rglob('*.gba'):
        b=f.read_bytes();code=b[0xac:0xb0].decode();start,lit={'AFXE':(0x1344c,0x13474),'AFXJ':(0x133cc,0x133f4),'AFXP':(0x135a4,0x135cc)}[code]
        font=struct.unpack_from('<I',b,lit)[0]-0x8000000;width=struct.unpack_from('<I',b,lit+12)[0]-0x8000000
        out[code]={'loader_offset':hex(start),'font_literal_offset':hex(lit),'font_offset':hex(font),'width_literal_offset':hex(lit+12),'width_offset':hex(width),'glyph_stride':128,'width_histogram':dict(collections.Counter(b[width:width+(3174 if code=='AFXJ' else 3175)])),'instructions':[f'{i.address-0x8000000:06X}: {i.mnemonic} {i.op_str}' for i in cs.disasm(b[start:lit],0x8000000+start)]}
    a.out.write_text(json.dumps(out,indent=2));print(a.out)
if __name__=='__main__':main()
