"""Screen the selected late-story arc with real fixed-name widths; no ROM build."""
import json,sys,re,argparse
from pathlib import Path
import project
ap=argparse.ArgumentParser();[ap.add_argument('--'+k,type=Path,required=True)for k in ('project','catalog','translation','charset','rom','font','report')];args=ap.parse_args();p=args.project;c=json.loads(args.catalog.read_text(encoding='utf8'))['entries'];entries=json.loads(args.translation.read_text(encoding='utf8'))['entries'];r={e['id']:e for e in entries};cs=json.loads(args.charset.read_text(encoding='utf8'))[0];rev={v:int(k)for k,v in reversed(list(cs.items()))if len(v)==1};rev.update({ch:project.COUNT+i for i,ch in enumerate(project.ALPHABET)});raw=args.rom.read_bytes();assert project.digest(raw)==project.SHA;w=raw[project.WIDTH:project.WIDTH+project.COUNT]+project.glyphs(args.font)[1];fixed=project.fixed_name_widths(entries,rev,w)
ids=[]
for f in ['palace-confrontation','doned-reconciliation','amber-ritz-farewell','remedi-final-battle','farewell-epilogue']:ids.extend(e['id']for e in json.load(open(p/'translation'/(f+'.ru.json'),encoding='utf8'))['entries'])
ids.append('s_text/1/19');seen=set();issues=[];rows=[]
for k in ids:
 assert k not in seen;seen.add(k);e=r[k];project.validate_controls(k,c[k]['tokens'],project.encode(e['ru'],rev),e.get('literalize_word_fragment',False));sizes=[];names=0;dynamic=[]
 for box in re.split(r'\[\[(?:40|42|4F)\]\]',e['ru']):
  for line in box.split('\n'):
   size=0
   for kind,v in project.encode(line,rev):
    if kind.startswith('CHR'):size+=w[v]
    elif v==0x52:size+=4
    elif v>>8==0x51:size+=fixed.get(v&255,42);names+=1
    elif v>>8==4:size+=42;dynamic.append(hex(v))
    elif v>>8==0x1b:size-=v&255
    elif v>>8==0x1d:size+=v&255
   sizes.append(size)
 row={'id':k,'max_width_px':max(sizes),'fixed_references':names,'dynamic_fields':dynamic};rows.append(row)
 if max(sizes)>156:issues.append(row)
report={'review_records':len(rows),'static_width_issues':issues,'fixed_reference_occurrences':sum(e['fixed_references']for e in rows),'measurements':rows,'scope':'Real authored fixed reference widths; dynamic 04 fields still provisional 42px, late scenes not runtime reached.'};args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k not in ('measurements','scope')},ensure_ascii=True))

# Only invariant NPC names can take these additive suffixes. Player-entered
# names must never inherit this rule. The source controls are preserved.
allowed={3:('Мьют',{'а','у'}),9:('Бабус',{'у'})}
revision=json.loads((p/'translation/editorial-late-story-07.ru.json').read_text(encoding='utf8'))['entries'];suffixes=[]
for e in revision:
    assert not re.search(r'\[\[4[0-9A-F]{2}\]\][а-яё]+',e['ru']),e['id']+' player-name suffix'
    for index,suffix in re.findall(r'\[\[51([0-9A-F]{2})\]\]([а-яё]+)',e['ru']):
        index=int(index,16);assert index in allowed and suffix in allowed[index][1]
        assert r[f'words:refer/{index}']['ru']==allowed[index][0]
        suffixes.append({'id':e['id'],'index':index,'suffix':suffix,'expanded':allowed[index][0]+suffix})
report['fixed_name_suffix_checks']=suffixes
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert len(rows)==368 and not issues
