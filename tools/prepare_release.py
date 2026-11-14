"""Prepare a test snapshot from the current release plus pending authored resources.

Unverified single-line/fixed layouts remain explicitly marked as such.
"""
import argparse,collections,json
from pathlib import Path
import project,prepare

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True)
    p.add_argument('--catalog',type=Path,required=True);p.add_argument('--charset',type=Path,required=True)
    p.add_argument('--rom',type=Path,required=True);p.add_argument('--font',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    cat=json.loads(a.catalog.read_text(encoding='utf-8'))['entries'];raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA
    charset=json.loads(a.charset.read_text(encoding='utf-8'))[0]
    reverse={v:int(k)for k,v in reversed(list(charset.items()))if len(v)==1}
    reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
    _,newwidths,_=project.glyphs(a.font);_,compact_widths,_=project.compact_glyphs(a.font)
    widths=raw[project.WIDTH:project.WIDTH+project.COUNT]+newwidths+compact_widths
    compact_wrap_widths=widths[:project.COUNT]+compact_widths+compact_widths
    state=json.loads((a.project/'translation/translation_status.json').read_text(encoding='utf-8'))
    entries=json.loads((a.project/'translation/ru.json').read_text(encoding='utf-8'))['entries'];entries=[dict(e)for e in entries]
    reference_entries={e['id']:e for e in entries if e['id'].startswith('words:refer/')}
    for key in ('pending_scene_files','pending_label_files','pending_fixed_files','pending_revision_files'):
        for filename in state.get(key,[]):
            for original in json.loads((a.project/filename).read_text(encoding='utf-8'))['entries']:
                if original['id'].startswith('words:refer/'):
                    reference_entries[original['id']]={**reference_entries.get(original['id'],{}),**original}
    fixed_names=project.fixed_name_widths(list(reference_entries.values()),reverse,widths)
    files=[]
    for key in ['pending_scene_files','pending_label_files','pending_fixed_files']:
        for filename in state[key]:
            authored=json.loads((a.project/filename).read_text(encoding='utf-8'))['entries'];files.append(filename)
            for original in authored:
                e=dict(original);ident=e['id'];e['source_sha256']=cat[ident]['source_sha256'];e['runtime_verified']=False
                if key=='pending_scene_files':
                    e.update(max_width=e.get('max_width',156),max_lines=e.get('max_lines',3),layout_profile='large_help_unverified'if e.get('max_lines',3)>3 else'dialogue')
                    e['ru']=prepare.wrap(e['ru'],reverse,compact_wrap_widths if e.get('font_profile')=='compact_ui'else widths,e['max_width'],reference_widths=fixed_names if e.get('resolve_fixed_references')else None,player_name_width=e.get('max_player_name_width'),control_offsets=e.get('measure_control_offsets',False),dynamic_widths=e.get('dynamic_widths'))
                elif key=='pending_fixed_files':
                    assert e['ru'].count('\n')==cat[ident]['source'].count('\n'),ident+' fixed line count changed'
                    e.update(max_width=216,max_lines=e['ru'].count('\n')+1,layout_profile='fixed_coordinates_unverified')
                else:
                    assert '\n'not in e['ru']
                    # Whole-row test budgets; narrower real widgets require visual QA.
                    limit=216 if ident.startswith(('pages:battle/','pages:condi/')) else 156
                    if ident.startswith('words:ico/'):limit=28
                    e.update(max_width=limit,max_lines=1,layout_profile='single_line_unverified')
                project.validate_controls(ident,cat[ident]['tokens'],project.encode(e['ru'],reverse),e.get('literalize_word_fragment',False))
                entries.append(e)
    positions={e['id']:i for i,e in enumerate(entries)};revised=set()
    for filename in state.get('pending_revision_files',[]):
        files.append(filename)
        for revision in json.loads((a.project/filename).read_text(encoding='utf-8'))['entries']:
            ident=revision['id'];assert ident in positions and ident not in revised,'Revision must replace exactly one existing ID'
            revised.add(ident);previous=entries[positions[ident]];e={**previous,**revision}
            e['source_sha256']=cat[ident]['source_sha256'];e['runtime_verified']=False
            profile=e.get('layout_profile','dialogue')
            if profile=='fixed_coordinates_unverified':
                assert e['ru'].count('\n')==cat[ident]['source'].count('\n'),ident+' revision changed fixed line count'
            elif profile=='single_line_unverified':
                assert '\n'not in e['ru'],ident+' revision introduced a label newline'
            else:e['ru']=prepare.wrap(e['ru'],reverse,compact_wrap_widths if e.get('font_profile')=='compact_ui'else widths,e.get('max_width',156),reference_widths=fixed_names if e.get('resolve_fixed_references')else None,player_name_width=e.get('max_player_name_width'),control_offsets=e.get('measure_control_offsets',False),dynamic_widths=e.get('dynamic_widths'))
            project.validate_controls(ident,cat[ident]['tokens'],project.encode(e['ru'],reverse),e.get('literalize_word_fragment',False))
            entries[positions[ident]]=e
    assert len(entries)==len(positions)==state['authored_translated_records']
    a.out.write_text(json.dumps({'source_sha256':project.SHA,'status':'test alpha; layout and gameplay incomplete','entries':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'records':len(entries),'revised_existing_records':sorted(revised),'pending_files':files,'profiles':dict(collections.Counter(e.get('layout_profile','previous_release')for e in entries)),
            'runtime_layout_verified':False,'single_line_budget_scope':'Provisional 216px whole battle/condition row, 156px names/choices, 28px element icons. Narrower real widgets unverified.',
            'fixed_scope':'Preserved source line count and controls; 216px whole-row screening only, coordinates unverified.',
            'rom_or_patch_created':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k!='pending_files'}))

if __name__=='__main__':main()
