"""Compile authored ID|Russian text without creating a ROM. @ means a newline.

Exact repetitions may be expanded using a private catalog and explicit table prefixes.
No English text is exported or translated by this tool.
"""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--batch',required=True);p.add_argument('--prefix',default='');p.add_argument('--append',default='')
    p.add_argument('--catalog',type=Path);p.add_argument('--expand-prefix',action='append',default=[])
    p.add_argument('--max-lines',type=int)
    a=p.parse_args();entries=[];seen=set()
    for line in a.input.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        ident,ru=line.split('|',1);ident=a.prefix+ident
        if ident in seen:raise ValueError('Duplicate authored ID: '+ident)
        seen.add(ident);entries.append({'id':ident,'ru':ru.replace('@','\n')+a.append})
    authored=len(entries)
    if a.expand_prefix:
        if not a.catalog:raise ValueError('Expansion requires the private catalog')
        cat=json.loads(a.catalog.read_text(encoding='utf-8'))['entries'];lookup={}
        for e in entries:
            source=cat[e['id']];key=(source['source'],source['source_sha256'])
            if key in lookup:raise ValueError('More than one authored entry for an exact repetition')
            lookup[key]=e
        expanded=[]
        for ident,source in cat.items():
            if not any(ident.startswith(prefix)for prefix in a.expand_prefix):continue
            original=lookup.get((source['source'],source['source_sha256']))
            if original:
                expanded.append({'id':ident,'ru':original['ru'],**({'expanded_from':original['id']}if ident!=original['id']else{})})
        if not seen.issubset({e['id']for e in expanded}):raise ValueError('Expansion dropped an authored entry')
        entries=expanded
    if a.max_lines:
        if a.max_lines<1:raise ValueError('Invalid line budget')
        for e in entries:e.update(max_width=156,max_lines=a.max_lines)
    a.out.write_text(json.dumps({'batch':a.batch,'entries':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'batch':a.batch,'records':len(entries),'authored_variants':authored,'rom_or_patch_created':False}))

if __name__=='__main__':main()
