"""Reproduce the reviewed source-glyph map in a separate analysis directory.

This copies the parser and extends its character names only. It writes no ROM or
font bitmap and refuses to overwrite the base upstream directory.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
import project

def main():
    p=argparse.ArgumentParser();p.add_argument('--base-upstream',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--map',type=Path,default=Path(__file__).resolve().parents[1]/'translation/SOURCE_GLYPH_MAP.json');p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    assert a.out.resolve()!=a.base_upstream.resolve(),'Use a separate generated analysis directory'
    raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA
    mapping=json.loads(a.map.read_text(encoding='utf-8'));assert mapping['source_sha256']==project.SHA
    base_bytes=(a.base_upstream/'charset_us.json').read_bytes();cs=json.loads(base_bytes);original=dict(cs[0]);seen=set()
    for entry in mapping['glyphs']:
        index=entry['glyph_index'];char=entry['unicode'];assert isinstance(index,int)and 0<=index<project.COUNT and index not in seen;seen.add(index)
        assert len(char)==1 and str(index)not in original
        start=project.FONT+index*128;assert project.digest(raw[start:start+128])==entry['original_128_bytes_sha256']
        cs[0][str(index)]=char
    assert len(seen)==124 and all(cs[0][k]==v for k,v in original.items())
    a.out.mkdir(parents=True,exist_ok=True)
    for name in ['ffta_sect.py','LICENSE']:
        source=a.base_upstream/name
        if source.exists():shutil.copyfile(source,a.out/name)
    target=a.out/'charset_us.json';target.write_text(json.dumps(cs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert (a.base_upstream/'charset_us.json').read_bytes()==base_bytes
    report={'source_sha256':project.SHA,'mapping_entries_added':len(seen),'base_entries_preserved':True,'base_charset_unchanged':True,'extended_charset_sha256':project.digest(target.read_bytes()),'parser_copy_identical':(a.out/'ffta_sect.py').read_bytes()==(a.base_upstream/'ffta_sect.py').read_bytes(),'source_font_modified':False,'rom_or_patch_created':False,'scope':'Character names transcribed from original font raster with Japanese textual context. No blanket exception to unknown-glyph preservation.'}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
