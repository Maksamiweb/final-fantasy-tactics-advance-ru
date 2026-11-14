"""Find EU English page candidates by exact unique USA records, then validate every record.

This is structural evidence, not proof that a renderer reaches every candidate page.
"""
import argparse, collections, contextlib, io, json, struct, sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--out',type=Path,default=Path('reports/eu_pages.json'));a=p.parse_args()
    sys.path.insert(0,str(a.upstream.resolve()));import ffta_sect as s
    paths={f.read_bytes()[0xac:0xb0].decode():f for f in a.root.rglob('*.gba')};us=s.load_rom_us(str(paths['AFXE']));eu=paths['AFXP'].read_bytes();host=s.c_ffta_sect_rom(eu,0);host.parse_size(len(eu),1);out={}
    groups=[(f'fx_text/{i}',us.tabs['fx_text'][i]) for i in range(us.tabs['fx_text'].tsize)]
    groups += [('pages/'+k,v) for k,v in us.tabs['pages'].items()]
    for name,page in groups:
        if page is None:continue
        votes=collections.Counter()
        for i in range(min(page.tsize,20)):
            line=page[i];raw=bytes(line.U8(j) for j in range(line.raw_len))
            if len(raw)<12:continue
            pos=eu.find(raw)
            if pos<0 or eu.find(raw,pos+1)>=0:continue
            votes[pos-(line.real_offset-page.real_offset)]+=1
        candidates=[]
        for base,v in votes.most_common(3):
            if base<0:continue
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    target=host.subsect(base,s.c_ffta_sect_text_page)
                    assert 0<target.tsize<2000
                    count=0
                    for j in range(target.tsize):
                        line=target[j];tokens=line.text.tokens;enc=bytes(line.text._encode(tokens))
                        check=s.c_ffta_sect_text_buf(enc,0);check.parse_size(len(enc),1);check.parse()
                        norm=lambda ts:[('CHR',x) if k.startswith('CHR_') else (k,x) for k,x in ts]
                        assert norm(tokens)==norm(check.tokens);count+=1
                needle=struct.pack('<I',0x8000000+base);refs=[];st=0
                while True:
                    st=eu.find(needle,st)
                    if st<0:break
                    if st%4==0:refs.append(hex(st))
                    st+=1
                candidates.append({'base':hex(base),'matching_unique_lines':v,'parsed_lines':count,'absolute_refs':refs,'normalized_roundtrip_pass':True})
            except Exception as e:candidates.append({'base':hex(base),'matching_unique_lines':v,'error':type(e).__name__+': '+str(e)})
        out[name]=candidates
    a.out.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
