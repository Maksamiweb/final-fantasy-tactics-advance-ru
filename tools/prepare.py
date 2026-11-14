"""Compile authored text files against a private source catalog, adding measured line wraps."""
import argparse,json,re
from pathlib import Path
import project

def wrap(txt,reverse,widths,limit,substitution=42,reference_widths=None,player_name_width=None,control_offsets=False,dynamic_widths=None):
    # Control tags for page/end events split text; dynamic names remain atomic words.
    sections=re.split(r'(\n|\[\[(?:4F|40|42)\]\])',txt)
    result=[]
    for section in sections:
        if section=='\n' or re.fullmatch(r'\[\[(?:4F|40|42)\]\]',section):result.append(section);continue
        words=section.split();line=0;out=[]
        for word in words:
            ts=project.encode(word,reverse)
            size=sum((dynamic_widths or {})[f'{v:04X}'] if k=='CTR_FUNC' and f'{v:04X}'in(dynamic_widths or {}) else widths[v] if k.startswith('CHR') else (reference_widths or {}).get(v&255,substitution) if k=='CTR_FUNC'and v>>8==0x51 else (player_name_width if v==0x400 and player_name_width is not None else substitution) if k=='CTR_FUNC'and v>>8==0x04 else (v&255) if (player_name_width is not None or control_offsets) and k=='CTR_FUNC'and v>>8==0x1d else -(v&255) if (player_name_width is not None or control_offsets) and k=='CTR_FUNC'and v>>8==0x1b else 0 for k,v in ts)
            if size>limit:raise ValueError('Word exceeds line limit: '+word)
            if line and line+4+size>limit:out.append('\n');line=0
            elif line:out.append(' ');line+=4
            out.append(word);line+=size
        result.append(''.join(out))
    return ''.join(result)

def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--opening',type=Path,required=True);p.add_argument('--scene',type=Path,action='append',default=[]);p.add_argument('--ui',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    _,raw,_,charset=project.load(a.rom,a.upstream);_,w,_=project.glyphs(a.font);widths=raw[project.WIDTH:project.WIDTH+project.COUNT]+w
    reverse={v:k for k,v in reversed(list(charset.items())) if len(v)==1};reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
    catalog=json.loads(a.catalog.read_text(encoding='utf-8'))['entries'];entries=[]
    for line in a.opening.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        idx,ru=line.split('|',1);ident='s_text/1/'+idx
        entries.append({'id':ident,'source_sha256':catalog[ident]['source_sha256'],'ru':wrap(ru,reverse,widths,156),'max_width':156,'max_lines':3,'status':'draft'})
    for scene in a.scene:
        for e in json.loads(scene.read_text(encoding='utf-8'))['entries']:
            ident=e['id'];width=e.get('max_width',156)
            entries.append({**e,'source_sha256':catalog[ident]['source_sha256'],'ru':wrap(e['ru'],reverse,widths,width),'max_width':width,'max_lines':e.get('max_lines',3),'status':'draft'})
    if a.ui:
        for e in json.loads(a.ui.read_text(encoding='utf-8'))['entries']:
            ident=e['id'];width=e.get('max_width',80)
            ru=wrap(e['ru'],reverse,widths,width) if e.get('max_lines',1)>1 else e['ru']
            entries.append({**e,'source_sha256':catalog[ident]['source_sha256'],'ru':ru,'status':'draft'})
    assert len({e['id'] for e in entries})==len(entries)
    a.out.write_text(json.dumps({'source_sha256':project.SHA,'status':'development draft; not a complete translation','entries':entries},indent=2,ensure_ascii=False),encoding='utf-8');print('Prepared authored records:',len(entries))
if __name__=='__main__':main()
