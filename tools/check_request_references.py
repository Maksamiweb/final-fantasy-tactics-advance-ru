"""Measure mission-request lines using authored words:refer names, without building a ROM.

1B/1D positioning and runtime 04 fields are deliberately not claimed verified.
Older contexts are listed for review when newly authored names are substituted.
"""
import argparse,json,re
from pathlib import Path
import project

def render_segments(text):
    # End/next-box markers cannot contribute to the same rendered line width.
    # Keep source line numbers so the report remains useful for editorial review.
    for line_number,line in enumerate(text.splitlines(),1):
        for segment_number,segment in enumerate(re.split(r'\[\[(?:4F|40|42)\]\]',line),1):
            if segment:yield line_number,segment_number,segment

def main():
    p=argparse.ArgumentParser();p.add_argument('--translation',type=Path,required=True);p.add_argument('--new-names',type=Path,required=True);p.add_argument('--charset',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    entries=json.loads(a.translation.read_text(encoding='utf-8'))['entries'];names={int(e['id'].split('/')[-1]):e['ru']for e in entries if e['id'].startswith('words:refer/')}
    changed={int(e['id'].split('/')[-1])for e in json.loads(a.new_names.read_text(encoding='utf-8'))['entries']}
    cs=json.loads(a.charset.read_text(encoding='utf-8'))[0];reverse={v:int(k)for k,v in reversed(list(cs.items()))if len(v)==1};reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
    raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA;_,w,_=project.glyphs(a.font);widths=raw[project.WIDTH:project.WIDTH+project.COUNT]+w
    def plain_width(text):return sum(widths[v]if k.startswith('CHR')else 4 if k=='CTR_FUNC'and v==0x52 else 0 for k,v in project.encode(text,reverse))
    name_widths={n:plain_width(t)for n,t in names.items()};issues=[];unknown=[];older=[];request_count=uses=0
    for e in entries:
        is_request=e['id'].startswith(('pages:quest/0/','pages:quest/1/'))
        tokens=project.encode(e['ru'],reverse);referred={v&255 for k,v in tokens if k=='CTR_FUNC'and v>>8==0x51}
        if not is_request and not referred.intersection(changed):continue
        if is_request:request_count+=1;uses+=sum(k=='CTR_FUNC'and v>>8==0x51 for k,v in tokens)
        record_issues=[]
        for n,segment_number,line in render_segments(e['ru']):
            size=0
            for k,v in project.encode(line,reverse):
                if k.startswith('CHR'):size+=widths[v]
                elif k=='CTR_FUNC'and v>>8==0x51:
                    if (v&255)not in name_widths:unknown.append({'id':e['id'],'reference_index':v&255})
                    size+=name_widths.get(v&255,42)
                elif k=='CTR_FUNC'and v>>8==4:size+=42
                elif k=='CTR_FUNC'and v==0x52:size+=4
            if size>e.get('max_width',156):record_issues.append({'id':e['id'],'line':n,'segment':segment_number,'estimated_width':size,'budget':e.get('max_width',156)})
        if is_request:issues.extend(record_issues)
        else:older.append({'id':e['id'],'new_reference_indices':sorted(referred&changed),'estimated_line_width_warnings':record_issues})
    report={'mission_requests_checked':request_count,'reference_occurrences_in_requests':uses,'unresolved_reference_names':unknown,'request_width_issues':issues,'older_records_affected':len(older),'older_records_with_estimated_width_warnings':sum(bool(x['estimated_line_width_warnings'])for x in older),'older_context_review':older,'scope':'Authored fixed 51 names substituted at measured font widths. Runtime 04 fields use an unverified 42px budget. 1B/1D positions and real window bounds are unverified; no gameplay or ROM build. Older estimates are triage, not proven visual errors.','rom_or_patch_created':False,'gameplay_verified':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k not in ('older_context_review','scope')}))
    if issues or unknown:raise SystemExit(1)
if __name__=='__main__':main()
