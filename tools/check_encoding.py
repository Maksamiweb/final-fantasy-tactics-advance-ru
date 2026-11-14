"""Encode/decode authored resources in memory; never create a ROM or patch."""
import argparse,collections,contextlib,io,json,sys
from pathlib import Path
import project

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--catalog',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--translation',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    a=p.parse_args();sys.path.insert(0,str(a.upstream.resolve()));import ffta_sect as parser
    cat=json.loads(a.catalog.read_text(encoding='utf-8'))['entries']
    charset=json.loads((a.upstream/'charset_us.json').read_text(encoding='utf-8'))[0]
    reverse={v:int(k)for k,v in reversed(list(charset.items()))if len(v)==1}
    reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
    entries=json.loads(a.translation.read_text(encoding='utf-8'))['entries'];seen=set();large=[];maximum=0;literalized=[]
    def decode(data):
        obj=parser.c_ffta_sect_text_buf(data,0);obj.parse_size(None,1);obj.parse();return obj
    with contextlib.redirect_stdout(io.StringIO()):
        encoder=decode(bytes([0]))
        for e in entries:
            ident=e['id'];assert ident not in seen;seen.add(ident);source=cat[ident]
            assert project.semantic_hash(source['tokens'])==source['source_sha256']
            tokens=project.encode_entry(e,reverse)
            project.validate_controls(ident,source['tokens'],tokens,e.get('literalize_word_fragment',False))
            original_unknown=collections.Counter(v for k,v in source['tokens']if k.startswith('CHR')and str(v)not in charset)
            retained_unknown=collections.Counter(v for k,v in tokens if k.startswith('CHR')and v<project.COUNT and str(v)not in charset)
            assert retained_unknown==original_unknown,ident+' unmapped source glyphs changed'
            if e.get('literalize_word_fragment'):literalized.append(ident)
            encoded=bytes(encoder._encode(tokens));decoded=decode(encoded)
            assert project.norm(decoded.tokens)==project.norm(tokens),ident+' resource round-trip mismatch'
            maximum=max(maximum,len(encoded))
            if len(encoded)>512:large.append({'id':ident,'encoded_bytes':len(encoded)})
    report={'records':len(seen),'source_and_control_checks_pass':True,'resource_roundtrip_pass':True,'unmapped_source_glyphs_preserved':True,
            'scope':'Text buffers encoded and decoded in memory only; no ROM relocation, renderer or save test.',
            'literalized_word_fragments':literalized,'max_encoded_bytes':maximum,
            'over_provisional_builder_512_byte_cap':large,'rom_or_patch_created':False,'gameplay_verified':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items()if k!='over_provisional_builder_512_byte_cap'}))
    print(json.dumps({'records_over_provisional_builder_cap':len(large)}))

if __name__=='__main__':main()
