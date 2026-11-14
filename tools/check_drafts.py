"""Validate and wrap authored scene drafts without creating a ROM or patch."""
import argparse,json,re
from pathlib import Path
import project,prepare

def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--charset',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--labels',action='store_true',help='Measure single-line draft labels; actual menu limits remain unverified');p.add_argument('--max-lines',type=int,default=3);p.add_argument('--fixed',action='store_true',help='Preserve source line count and authored spacing; no auto-wrap');p.add_argument('--references',type=Path,help='Translation snapshot supplying fixed words:refer widths for opted-in scenes');a=p.parse_args();assert a.max_lines>0;assert not(a.labels and a.fixed)
    cat=json.loads(a.catalog.read_text(encoding='utf-8'))['entries']
    raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA
    charset=json.loads(a.charset.read_text(encoding='utf-8'))[0]
    reverse={v:int(k) for k,v in reversed(list(charset.items())) if len(v)==1}
    reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
    _,w,_=project.glyphs(a.font);_,cw,_=project.compact_glyphs(a.font);widths=raw[project.WIDTH:project.WIDTH+project.COUNT]+w+cw
    scene=json.loads(a.scene.read_text(encoding='utf-8'));seen=set();issues=[];prepared=[];measurements=[]
    fixed_names=project.fixed_name_widths(json.loads(a.references.read_text(encoding='utf-8'))['entries'],reverse,widths)if a.references else None
    assert fixed_names is not None or not any(e.get('resolve_fixed_references')for e in scene['entries']),'--references required for measured fixed names'
    for e in scene['entries']:
        ident=e['id'];assert ident not in seen;seen.add(ident);source=cat[ident]
        ru=e['ru'] if a.labels or a.fixed else prepare.wrap(e['ru'],reverse,widths,156,reference_widths=fixed_names if e.get('resolve_fixed_references')else None,player_name_width=e.get('max_player_name_width'));tokens=project.encode_entry({**e,'ru':ru},reverse)
        project.validate_controls(ident,source['tokens'],tokens,e.get('literalize_word_fragment',False))
        assert project.semantic_hash(source['tokens'])==source['source_sha256']
        if a.labels:
            assert '\n' not in ru,ident+' label contains newline'
            # 42 also separates choices: their widths must not be added together.
            segments=[project.encode_entry({**e,'ru':t},reverse)for t in ru.split('[[42]]')if t]
            sizes=[sum(widths[v]if k.startswith('CHR')else 4 if k=='CTR_FUNC'and v==0x52 else -(v&255)if k=='CTR_FUNC'and v>>8==0x1b else v&255 if k=='CTR_FUNC'and v>>8==0x1d else 0 for k,v in segment)for segment in segments]
            estimated=[size+42*sum(k=='CTR_FUNC' and v>>8 in (0x04,0x51)for k,v in segment)for size,segment in zip(sizes,segments)]
            measured=max(sizes,default=0)
            measurements.append({'id':ident,'width_px':measured,'static_segment_widths_px':sizes,'estimated_with_42px_substitutions':max(estimated,default=0),'over_provisional_80px':measured>80})
        else:
            boxes=re.split(r'\[\[(?:4F|40)\]\]',ru)
            if a.fixed:
                assert ru.count('\n')==source['source'].count('\n'),ident+' fixed line count changed'
            elif any(x.count('\n')+1>a.max_lines for x in boxes):issues.append({'id':ident,'issue':f'more than {a.max_lines} lines in a box'})
        prepared.append({**e,'id':ident,'source_sha256':source['source_sha256'],'ru':ru,'status':'draft'})
    report={'batch':scene['batch'],'records':len(seen),'control_and_source_checks_pass':True,'layout_issues':issues,'rom_or_patch_created':False,'gameplay_verified':False}
    report.update(layout_scope='Fixed source line count; coordinates and widths unverified' if a.fixed else f'Calculated 156px/{a.max_lines} lines; actual window unverified',fixed_layout_verified=False)
    if a.labels:
        report.update(layout_scope='Widths measured only; actual menu windows and character caps unverified. 80px is a triage threshold, not a proven limit.',menu_layout_verified=False,labels_over_provisional_80px=sum(x['over_provisional_80px'] for x in measurements),measurements=measurements)
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    a.report.with_suffix('.prepared.json').write_text(json.dumps({'entries':prepared},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='measurements'},ensure_ascii=True))
    if issues:raise SystemExit(1)
if __name__=='__main__':main()
