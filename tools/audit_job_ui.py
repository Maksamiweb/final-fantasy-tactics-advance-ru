"""Screen job/ability labels, description layout and source prerequisite counts.

Static estimates do not replace native checks of every job/late ability window.
"""
import argparse,json,re
from pathlib import Path
import project

def prerequisite_numbers(text,source=False):
    if source:return [int(x)for x in re.findall(r'A-ability\s*x(\d+)',text)]
    return [int(x)for x in re.findall(r'(\d+)\s*[АA]-умен',text)]

def main():
    ap=argparse.ArgumentParser()
    for name in ('catalog','translation','charset','rom','font','report'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();cat=json.loads(a.catalog.read_text(encoding='utf8'))['entries'];entries={e['id']:e for e in json.loads(a.translation.read_text(encoding='utf8'))['entries']}
    cs=json.loads(a.charset.read_text(encoding='utf8'))[0];reverse={v:int(k)for k,v in reversed(list(cs.items()))if len(v)==1};reverse.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
    raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA
    widths=raw[project.WIDTH:project.WIDTH+project.COUNT]+project.glyphs(a.font)[1]+project.compact_glyphs(a.font)[1]
    def measure(text,entry):
        size=0;unknown=[]
        for kind,value in project.encode_entry({**entry,'ru':text},reverse):
            if kind.startswith('CHR'):size+=widths[value]
            elif value==0x52:size+=4
            elif value>>8==0x1b:size-=value&255
            elif value>>8==0x1d:size+=value&255
            elif value>>8==0x51:
                fixed=entries.get(f'words:refer/{value&255}')
                if fixed:size+=measure(fixed['ru'],fixed)[0]
                else:size+=42;unknown.append(hex(value))
            elif value>>8==4:size+=42;unknown.append(hex(value))
        return size,unknown
    labels=[];descriptions=[];issues=[];prerequisites=[]
    for ident,e in entries.items():
        label_limit=None
        if ident.startswith('words:content/')and 1<=int(ident.split('/')[-1])<124:label_limit=88
        elif ident.startswith('words:battle/')and 106<=int(ident.split('/')[-1])<=575:label_limit=78
        elif ident in {f'words:system/{i}'for i in (49,50,51,53)}:label_limit=88
        if label_limit:
            width,_=measure(e['ru'],e);labels.append({'id':ident,'width_px':width,'limit_px':label_limit})
            if width>label_limit:issues.append({'id':ident,'reason':'label too wide','width_px':width})
        if ident.startswith(('fx_text/17/','fx_text/18/','fx_text/19/','fx_text/22/')):
            project.validate_controls(ident,cat[ident]['tokens'],project.encode_entry(e,reverse),e.get('literalize_word_fragment',False))
            boxes=[x for x in re.split(r'\[\[(?:4F|40|42)\]\]',e['ru'])if x];unknown=[];sizes=[]
            for box in boxes:
                for line in box.split('\n'):
                    n,u=measure(line,e);sizes.append(n);unknown+=u
            count=max((x.count('\n')+1 for x in boxes),default=0)
            item={'id':ident,'max_width_px':max(sizes,default=0),'max_lines':count,'dynamic_fields':unknown};descriptions.append(item)
            if item['max_width_px']>e.get('max_width',156)or count>e.get('max_lines',3):issues.append({**item,'reason':'description layout'})
            if ident.startswith('fx_text/22/'):
                original=prerequisite_numbers(cat[ident]['source'],True)
                if original:
                    translated=prerequisite_numbers(e['ru']);prerequisites.append({'id':ident,'source_counts':original,'translated_counts':translated})
                    if original!=translated:issues.append({'id':ident,'reason':'job prerequisite counts changed'})
    report={'labels_checked':len(labels),'description_records_checked':len(descriptions),'prerequisite_profiles_checked':len(prerequisites),'issues':issues,'labels':labels,'descriptions':descriptions,'prerequisites':prerequisites,'scope':'78/88px conservative label budgets; source-relative description budgets and prerequisite numbers. Dynamic 04 uses provisional 42px. Prerequisite class-name identity and actual unlock behavior require contextual/native review.','rom_created':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k in ('labels_checked','description_records_checked','prerequisite_profiles_checked','issues')}))
    assert len(labels)==594 and not issues,'Job/ability UI audit failed'

if __name__=='__main__':main()
