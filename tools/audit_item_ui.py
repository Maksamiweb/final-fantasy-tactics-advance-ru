"""Screen all 502 item names/descriptions without building a ROM. Native window QA remains separate."""
import json,sys,re,argparse
from pathlib import Path
import project
ap=argparse.ArgumentParser();[ap.add_argument('--'+k,type=Path,required=True)for k in ('catalog','translation','charset','rom','font','report')];args=ap.parse_args();cat=json.loads(args.catalog.read_text(encoding='utf8'))['entries'];r={e['id']:e for e in json.loads(args.translation.read_text(encoding='utf8'))['entries']};cs=json.loads(args.charset.read_text(encoding='utf8'))[0];rev={v:int(k)for k,v in reversed(list(cs.items()))if len(v)==1};rev.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)});raw=args.rom.read_bytes();assert project.digest(raw)==project.SHA;w=raw[project.WIDTH:project.WIDTH+project.COUNT]+project.glyphs(args.font)[1]+project.compact_glyphs(args.font)[1]
issues=[];names=[];descs=[]
for k,e in r.items():
 if k.startswith('words:content/') and 124<=int(k.split('/')[-1])<=625:
  n=sum(w[v] if kind.startswith('CHR') else 4 if v==82 else v&255 if v>>8==29 else -(v&255)if v>>8==27 else 0 for kind,v in project.encode_entry(e,rev));names.append({'id':k,'width_px':n});assert n<=88,(k,n)
 if k.startswith(('fx_text/21/','fx_text/25/')):
  ts=project.encode_entry(e,rev);project.validate_controls(k,cat[k]['tokens'],ts,e.get('literalize_word_fragment',False));boxes=re.split(r'\[\[(?:4F|40|42)\]\]',e['ru']);m=max((box.count('\n')+1 for box in boxes if box),default=0)
  widths=[];dynamic=[]
  for box in boxes:
   for line in box.split('\n'):
    n=0
    for kind,v in project.encode(line,rev):
     if kind.startswith('CHR'):n+=w[v]
     elif v==82:n+=4
     elif v>>8==29:n+=v&255
     elif v>>8==27:n-=v&255
     elif v>>8==81:
      word=r.get(f'words:refer/{v&255}')
      if word:n+=sum(w[x]if a.startswith('CHR')else 4 if x==82 else 0 for a,x in project.encode(word['ru'],rev))
      else:dynamic.append(hex(v));n+=42
     elif v>>8==4:dynamic.append(hex(v));n+=42
    widths.append(n)
  descs.append({'id':k,'max_lines_in_box':m,'max_width_px':max(widths),'dynamic_fields':dynamic})
  if m>3 or max(widths)>e.get('max_width',156):issues.append(descs[-1])
report={'name_records':len(names),'name_max_width_px':max(x['width_px']for x in names),'description_records':len(descs),'description_warnings':issues,'measurements':descs,'scope':'Static screening, including 1B/1D and measured fixed 51 names. Dynamic 04 fields use provisional 42px. Full prose review and representative native views do not prove all late windows.'}
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k not in ('measurements','scope')},ensure_ascii=True))

assert len(names)==len(descs)==502 and not issues, "Item UI screening failed"
