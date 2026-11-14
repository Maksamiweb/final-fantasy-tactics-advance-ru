"""Read-only structural tests using pinned upstream parser; emits metadata only."""
import argparse, collections, contextlib, hashlib, io, json, struct, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--out',type=Path,default=Path('reports/structural.json'));a=ap.parse_args()
    sys.path.insert(0,str(a.upstream.resolve()));import ffta_sect as s
    data={p.read_bytes()[0xac:0xb0].decode():p for p in a.root.rglob('*.gba')}
    result={};fonts={}
    def walk(obj,path,stats):
        if obj is None:return
        if isinstance(obj,s.c_ffta_sect_text_buf):
            stats['buffers']+=1
            stats['tokens']+=len(obj.tokens)
            encoded=bytes(obj._encode(obj.tokens))
            test=s.c_ffta_sect_text_buf(encoded,0);test.parse_size(len(encoded),1);test.parse()
            if test.tokens==obj.tokens: stats['strict_token_roundtrips']+=1
            normalized=lambda ts:[('CHR',v) if k.startswith('CHR_') else (k,v) for k,v in ts]
            assert normalized(test.tokens)==normalized(obj.tokens)
            stats['semantic_roundtrips']+=1
            return
        if isinstance(obj,s.c_ffta_sect_text_line):
            stats['compressed' if obj.compressed else 'uncompressed']+=1
            walk(obj.text,path+'/text',stats);return
        if isinstance(obj,s.c_ffta_sect_tab_ref):
            for i in range(obj.tsize):
                try:walk(obj[i],path+'/'+str(i),stats)
                except Exception as e:
                    stats['errors']+=1
                    if len(stats['error_samples'])<10:stats['error_samples'].append({'path':path+'/'+str(i),'error':type(e).__name__+': '+str(e)})
    def load_eu(fn):
        b=Path(fn).read_bytes()
        info={f's_text_{lang}':(ptr,s.c_ffta_sect_text) for lang,ptr in [('en',0x9b04),('fr',0x9af8),('de',0x9ae0),('it',0x9ae8),('es',0x9af0)]}
        for name,ptr,count in [('content',0x16644,753),('refer',0x166a4,107),('battle',0x165e4,767),('rumor',0x16764,92),('quest',0x167c4,512),('clan',0x16884,128),('system',0x168e4,84),('title',0x16824,52)]:
            info['words:'+name]=(ptr,s.c_ffta_sect_words_text,s.c_ffta_sect_rom.ARG_SELF,count)
        return s.c_ffta_sect_rom(b,0).setup(info,len(b))
    for code,loader in [('AFXE',s.load_rom_us),('AFXJ',s.load_rom_jp),('AFXP',load_eu)]:
        log=io.StringIO()
        with contextlib.redirect_stdout(log):r=loader(str(data[code]))
        b=data[code].read_bytes()
        if code=='AFXP':
            font=r.sub(0x4954dc,cls=s.c_ffta_sect_font);font.set_info({'shape':(4,8,16,2),'size':3175,'rvsbyt':False})
        else:font=r.tabs['font']
        fonts[code]=b[font.real_offset:font.real_offset+font.tsize*128]
        entry={'font_offset':hex(font.real_offset),'glyphs':font.tsize,'glyph_bytes':128,'font_sha256':hashlib.sha256(fonts[code]).hexdigest(),'tables':{},'warnings':log.getvalue()[:1000]}
        for name,obj in r.tabs.items():
            group=obj.items() if isinstance(obj,dict) else [(name,obj)]
            for sub,t in group:
                if not name.startswith('s_text') and name not in ['fx_text','pages','words']:continue
                stats={'offset':hex(t.real_offset),'entries':t.tsize,'buffers':0,'tokens':0,'semantic_roundtrips':0,'strict_token_roundtrips':0,'compressed':0,'uncompressed':0,'errors':0,'error_samples':[]}
                with contextlib.redirect_stdout(io.StringIO()):walk(t,(name+':'+sub),stats)
                entry['tables'][name+(':'+sub if isinstance(obj,dict) else '')]=stats
        result[code]=entry
    eu=data['AFXP'].read_bytes();us=data['AFXE'].read_bytes();jp=data['AFXJ'].read_bytes()
    candidates=[]
    for code,f in fonts.items():
        # Search exact 32-glyph windows and infer the common font base; matches do not prove renderer use.
        for idx in [0,0xa6,0xb0,0xca,0x100,0x300]:
            needle=f[idx*128:(idx+32)*128];pos=0;hits=[]
            while len(hits)<20:
                pos=eu.find(needle,pos)
                if pos<0:break
                hits.append({'match':hex(pos),'inferred_base':hex(pos-idx*128)});pos+=1
            candidates.append({'reference':code,'glyph_index':hex(idx),'hits':hits})
    result['AFXP']['font_window_matches']=candidates
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(a.out)
if __name__=='__main__':main()
