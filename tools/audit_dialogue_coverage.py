"""Exhaustive dialogue coverage against the private USA catalog, without ROM creation.

Every s_text record is accounted for. Non-dialogue exceptions are explicit,
source-hash pinned and kept separate from translated dialogue coverage.
"""
import argparse,collections,json,re
from pathlib import Path
import project

def classify(ident,source,exceptions):
 if ident in exceptions:
  e=exceptions[ident];assert e['source_sha256']==source['source_sha256'],ident+' exception source changed'
  return e['category']
 if not any(k.startswith('CHR')for k,v in source['tokens']):return 'control_only'
 return 'dialogue'

def check_language(ident,ru,allowed):
 assert not re.search(r'\[\[U[0-9A-Fa-f]+\]\]',ru),ident+' unmapped target glyph'
 plain=project.TAG.sub('',ru)
 assert not re.search(r'[\u3040-\u30ff\u3400-\u9fff]',plain),ident+' untranslated Japanese'
 latin=re.findall(r'[A-Za-z]+',plain)
 assert latin==allowed.get(ident,[]),ident+' unexpected Latin text: '+repr(latin)
 return latin

def main():
 p=argparse.ArgumentParser()
 for name in ('catalog','translation','charset','rom','exclusions','report'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();catalog=json.loads(a.catalog.read_text(encoding='utf8'));cat=catalog['entries'];raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA==catalog['rom_sha256'];es=json.loads(a.translation.read_text(encoding='utf8'))['entries'];tr={e['id']:e for e in es};assert len(tr)==len(es)
 manifest=json.loads(a.exclusions.read_text(encoding='utf8'));exceptions=manifest['records'];allowed=manifest['allowed_latin'];assert all(k in cat and k.startswith('s_text/')for k in exceptions)
 charset=json.loads(a.charset.read_text(encoding='utf8'))[0];reverse={v:int(k)for k,v in reversed(list(charset.items()))if len(v)==1};reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
 checked=0
 for e in es:
  k=e['id'];assert k in cat and e['source_sha256']==cat[k]['source_sha256']==project.semantic_hash(cat[k]['tokens']);encoded=project.encode_entry(e,reverse);project.validate_controls(k,cat[k]['tokens'],encoded,e.get('literalize_word_fragment',False));checked+=1
 rows=[];counts=collections.Counter();uncovered=[];latin=[];alias=collections.defaultdict(list)
 for ident,source in cat.items():
  if not ident.startswith('s_text/'):continue
  category=classify(ident,source,exceptions);counts[category]+=1
  if category=='dialogue':
   if ident not in tr:uncovered.append(ident)
   else:
    e=tr[ident];tokens=project.encode_entry(e,reverse);assert any(k.startswith('CHR')or(k=='CTR_FUNC'and(v>>8 in(4,0x51)))for k,v in tokens),ident+' empty target'
    words=check_language(ident,e['ru'],allowed)
    if words:latin.append({'id':ident,'allowed_tokens':words})
    alias[source['offset']].append((ident,e['ru']))
  rows.append({'id':ident,'source_sha256':source['source_sha256'],'category':category,'translation_present':ident in tr})
 conflicts=[{'offset':at,'ids':[k for k,v in members]}for at,members in alias.items()if len({v for k,v in members})>1]
 # No meaningful untranslated sentences in auxiliary message/quest/choice banks.
 # Pure placeholders and punctuation are recorded as such, not counted as Russian.
 auxiliary=[]
 for ident,e in cat.items():
  if not ident.startswith(('fx_text/','pages:quest/','pages:choice/'))or ident in tr:continue
  visible=project.TAG.sub('',e['source']).strip();placeholder=visible.lower()in('dummy','xxxx','')
  if not placeholder and re.search(r'[A-Za-z\u3040-\u30ff\u3400-\u9fff]',visible):auxiliary.append(ident)
 auxiliary_latin=collections.Counter();auxiliary_checked=0
 for e in es:
  if not e['id'].startswith(('fx_text/','pages:quest/','pages:choice/')):continue
  plain=project.TAG.sub('',e['ru']);assert not re.search(r'[\u3040-\u30ff\u3400-\u9fff]',plain),e['id']+' untranslated auxiliary glyphs'
  raw_glyphs=re.findall(r'\[\[(U[0-9A-Fa-f]+)\]\]',e['ru']);assert raw_glyphs==(['U1E6','U1E6']if e['id']=='fx_text/8/88'else[]),e['id']+' unexpected unmapped auxiliary glyph'
  if raw_glyphs:assert project.digest(raw[project.FONT+0x1e6*128:project.FONT+0x1e7*128])=='012282915e431d0669bbfb021af867dbcbc0c00c4f0c7f56d60b5b7db3778b7d'
  words=re.findall(r'[A-Za-z]+',plain);assert set(words)<={'R','JP','HP','MP','SELECT','AP','Game','Link','A','Boy','Advance','x','KO','Y'},e['id']+' unexpected auxiliary Latin text';auxiliary_latin.update(words);auxiliary_checked+=1
 report={'catalog_records':len(cat),'story_slots':sum(counts.values()),'categories':dict(counts),'dialogue_records':counts['dialogue'],'covered_dialogue_records':counts['dialogue']-len(uncovered),'dialogue_catalog_coverage_percent':round(100*(counts['dialogue']-len(uncovered))/counts['dialogue'],2),'unique_dialogue_source_offsets':len(alias),'uncovered_dialogues':uncovered,'shared_source_translation_conflicts':conflicts,'unexpected_auxiliary_message_gaps':auxiliary,'allowed_latin_dialogues':latin,'retained_original_brand_glyph':{'id':'fx_text/8/88','glyph':'U1E6','meaning':'registered trademark sign','count':2,'visually_verified':True},'auxiliary_message_records_language_checked':auxiliary_checked,'retained_auxiliary_latin_tokens':dict(auxiliary_latin),'all_translation_records_control_checked':checked,'translation_snapshot_sha256':project.digest(a.translation.read_bytes()),'source_rom_sha256':project.SHA,'coverage_complete':not(uncovered or conflicts or auxiliary),'full_playthrough_verified':False,'rom_or_patch_created':False,'scope':'All extracted s_text slots and meaningful auxiliary message/quest/choice gaps.452 numbered technical cut labels and6 post40/42 race tails are explicit hash-pinned exceptions, not spoken dialogue. No claim of full gameplay QA, semantic perfection or all other graphical/UI text.','records':rows}
 a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k not in('records','scope','allowed_latin_dialogues')},ensure_ascii=False));assert report['coverage_complete'],'Dialogue coverage failed'
if __name__=='__main__':main()
