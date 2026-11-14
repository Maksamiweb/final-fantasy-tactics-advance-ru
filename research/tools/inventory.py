"""Read-only GBA inventory. Python 3.10+, standard library only."""
import argparse, hashlib, json, struct, zlib
from pathlib import Path

def find_offsets(b, needle):
    out=[]; start=0
    while len(out)<30:
        i=b.find(needle,start)
        if i<0: break
        out.append(f'0x{i:X}'); start=i+1
    return out

def inspect(path):
    b = path.read_bytes()
    code = b[0xac:0xb0].decode('ascii', errors='replace')
    return {'filename': path.name, 'size': len(b), 'title': b[0xa0:0xac].rstrip(b'\0').decode('ascii', errors='replace'),
            'game_code': code, 'region_code': code[-1:], 'maker': b[0xb0:0xb2].decode('ascii', errors='replace'),
            'revision': b[0xbc], 'fixed_byte_valid': b[0xb2] == 0x96,
            'header_checksum_stored': b[0xbd], 'header_checksum_computed': (-sum(b[0xa0:0xbd])-0x19)&255,
            'header_checksum_valid': b[0xbd] == ((-sum(b[0xa0:0xbd])-0x19)&255),
            'sha256': hashlib.sha256(b).hexdigest(), 'sha1': hashlib.sha1(b).hexdigest(),
            'crc32': f'{zlib.crc32(b):08X}',
            'ascii_probe_offsets': {s: find_offsets(b, s.encode()) for s in ['New Game','Marche','English','Deutsch','Italiano','Francais','Espa','Soldier']}}

def main():
    p=argparse.ArgumentParser(); p.add_argument('root', type=Path); p.add_argument('--out',type=Path,default=Path('reports')); a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    rows=[inspect(f) for f in sorted(a.root.rglob('*.gba'))]
    (a.out/'rom_inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    lines=['# ROM inventory','', 'Verified from local bytes. Region labels use header suffix E=USA, J=Japan, P=Europe; retail revision identity has not been database-verified. No ROM bytes are included.','', '| Code | Title | Maker | Revision | Bytes | Header checksum | CRC32 |','|---|---|---|---|---|---|---|']
    for r in rows:
        lines += [f"| {r['game_code']} | {r['title']} | {r['maker']} | {r['revision']} | {r['size']} | {r['header_checksum_valid']} | {r['crc32']} |"]
    for r in rows:
        lines += ['',f"## {r['game_code']}",f"SHA-256: `{r['sha256']}`",f"SHA-1: `{r['sha1']}`",f"Header complement: stored {r['header_checksum_stored']:02X}, computed {r['header_checksum_computed']:02X}; fixed byte valid: {r['fixed_byte_valid']}."]
    (a.out/'rom_inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(rows,indent=2,ensure_ascii=True))
if __name__=='__main__': main()
