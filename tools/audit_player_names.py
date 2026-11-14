"""Audit all player-name substitutions at the observed native 9x9px bound.

Fixed references use actual translated widths. Other runtime substitutions retain
provisional budgets, and fixed-coordinate screens still require native review.
"""
import argparse,json,re
from pathlib import Path
import project

def main():
 p=argparse.ArgumentParser()
 for k in ('rom','charset','font','catalog','before','translation','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA;cs=json.loads(a.charset.read_text(encoding='utf8'))[0];rv={v:int(k)for k,v in reversed(list(cs.items()))if len(v)==1};rv.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)});widths=raw[project.WIDTH:project.WIDTH+project.COUNT]+project.glyphs(a.font)[1]+project.compact_glyphs(a.font)[1]
 allowed='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,-';widest=max(widths[rv[c]]for c in allowed);assert widest==9;bound=9*widest
 old={e['id']:e for e in json.loads(a.before.read_text(encoding='utf8'))['entries']};new={e['id']:e for e in json.loads(a.translation.read_text(encoding='utf8'))['entries']};cat=json.loads(a.catalog.read_text(encoding='utf8'))['entries'];fixed=project.fixed_name_widths(list(new.values()),rv,widths);rows=[]
 def measure(e):
  w=0;wide=0;line=1;lines=1
  for k,v in project.encode_entry(e,rv):
   if k.startswith('CHR'):w+=widths[v]
   elif k=='CTR_FUNC':
    if v==0x52:w+=4
    elif v==0x4d:wide=max(wide,w);w=0;line+=1
    elif v in (0x40,0x42,0x4f):wide=max(wide,w);lines=max(lines,line);w=0;line=1
    elif v>>8==0x51:w+=fixed.get(v&255,42)
    elif v>>8==4:w+=bound if v==0x400 else e.get('substitution_width',42)
    elif v>>8==0x1b:w-=v&255
    elif v>>8==0x1d:w+=v&255
  return max(wide,w),max(lines,line)
 def visible(e):return[(k,v)for k,v in project.norm(project.encode_entry(e,rv))if not(k=='CTR_FUNC'and v in (0x4d,0x52))]
 for ident,e in new.items():
  if '[[400]]'not in e['ru']:continue
  assert e.get('max_player_name_width')==81 and e.get('resolve_fixed_references');assert visible(e)==visible(old[ident]),'Wording/control changed '+ident
  project.validate_controls(ident,cat[ident]['tokens'],project.encode_entry(e,rv),e.get('literalize_word_fragment',False))
  before=measure(old[ident]);after=measure(e);assert after[0]<=e.get('max_width',156)and after[1]<=e.get('max_lines',3),(ident,after)
  rows.append({'id':ident,'before_max_width':before[0],'after_max_width':after[0],'after_lines':after[1],'text_rewrapped':old[ident]['ru']!=e['ru'],'fixed_coordinates':e.get('layout_profile')=='fixed_coordinates_unverified','before_over_width':before[0]>e.get('max_width',156)})
 report={'player_keyboard_chars_observed':9,'max_latin_keyboard_glyph_width':widest,'player_budget_px':bound,'records_checked':len(rows),'previous_overwide_records':sum(x['before_over_width']for x in rows),'text_rewrapped_records':sum(x['text_rewrapped']for x in rows),'other_records_unchanged':sum(old[i]==e for i,e in new.items()if i not in {x['id']for x in rows}),'wording_and_control_order_unchanged':True,'calculated_player_name_layout_passed':True,'scope':'All400 fields measured at81px; nine W typed/confirmed in a separate native test. Other04 fields, font changes and two fixed-coordinate contexts are not fully runtime verified. This is not a complete scene playthrough.','measurements':rows}
 a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k!='measurements'}))
if __name__=='__main__':main()
