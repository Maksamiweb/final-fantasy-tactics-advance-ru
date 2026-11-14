"""Measure an explicit narrative scene set with fixed reference names resolved.

Dynamic 04 widths remain provisional; this does not execute the story engine.
"""
import argparse,json,re
from pathlib import Path
import project

def main():
    p=argparse.ArgumentParser()
    for key in ('catalog','translation','charset','rom','font','report'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--scene',type=Path,action='append',required=True);p.add_argument('--revisions',type=Path)
    a=p.parse_args();cat=json.loads(a.catalog.read_text(encoding='utf8'))['entries'];entries=json.loads(a.translation.read_text(encoding='utf8'))['entries'];by={e['id']:e for e in entries}
    charset=json.loads(a.charset.read_text(encoding='utf8'))[0];reverse={v:int(k)for k,v in reversed(list(charset.items()))if len(v)==1};reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
    raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA
    widths=raw[project.WIDTH:project.WIDTH+project.COUNT]+project.glyphs(a.font)[1]+project.compact_glyphs(a.font)[1];fixed=project.fixed_name_widths(entries,reverse,widths)
    ids=[];files=[]
    for path in a.scene:
        es=json.loads(path.read_text(encoding='utf8'))['entries'];files.append({'file':path.name,'records':len(es)});ids.extend(e['id']for e in es)
    assert len(ids)==len(set(ids)),'Repeated ID in requested scope'
    rows=[];issues=[];unresolved=[]
    for ident in ids:
        e=by[ident];tokens=project.encode_entry(e,reverse);project.validate_controls(ident,cat[ident]['tokens'],tokens,e.get('literalize_word_fragment',False));assert project.semantic_hash(cat[ident]['tokens'])==e['source_sha256']
        n=0;line=1;max_lines=1;widest=0;count=0;dynamic=[]
        for kind,value in tokens:
            if kind.startswith('CHR'):n+=widths[value]
            elif kind=='CTR_FUNC':
                if value==0x52:n+=4
                elif value==0x4d:widest=max(widest,n);n=0;line+=1
                elif value in (0x40,0x42,0x4f):widest=max(widest,n);max_lines=max(max_lines,line);n=0;line=1
                elif value>>8==0x1b:n-=value&255
                elif value>>8==0x1d:n+=value&255
                elif value>>8==0x51:
                    index=value&255;n+=fixed.get(index,42);count+=1
                    if index not in fixed:unresolved.append({'id':ident,'index':index})
                elif value>>8==4:n+=e.get('max_player_name_width',e.get('substitution_width',42))if value==0x400 else e.get('substitution_width',42);dynamic.append(hex(value))
        widest=max(widest,n);max_lines=max(max_lines,line);row={'id':ident,'max_width_px':widest,'max_lines':max_lines,'fixed_references':count,'dynamic_fields':dynamic};rows.append(row)
        if widest>e.get('max_width',156)or max_lines>e.get('max_lines',3):issues.append(row)
    suffixes=[]
    if a.revisions:
        allowed={3:('Мьют',{'а','у'}),9:('Бабус',{'у'})}
        for e in json.loads(a.revisions.read_text(encoding='utf8'))['entries']:
            assert not re.search(r'\[\[4[0-9A-F]{2}\]\][а-яё]+',e['ru']),e['id']+' suffix on player-entered field'
            for index,suffix in re.findall(r'\[\[51([0-9A-F]{2})\]\]([а-яё]+)',e['ru']):
                index=int(index,16);assert index in allowed and suffix in allowed[index][1];assert by[f'words:refer/{index}']['ru']==allowed[index][0]
                suffixes.append({'id':e['id'],'reference':index,'expanded':allowed[index][0]+suffix})
    report={'scene_files':files,'records_checked':len(rows),'fixed_reference_occurrences':sum(x['fixed_references']for x in rows),'dynamic_field_occurrences':sum(len(x['dynamic_fields'])for x in rows),'unresolved_fixed_references':unresolved,'layout_issues':issues,'fixed_suffix_checks':suffixes,'measurements':rows,'scope':'Static source/control and measured 51 widths. Dynamic 04 fields retain a provisional budget. Source records may be alternate branches, not one continuous playthrough. Native scene execution is separate.','rom_created':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k not in ('measurements','scene_files','scope','fixed_suffix_checks')}))
    assert not issues and not unresolved,'Scene layout audit failed'

if __name__=='__main__':main()
