"""Render/check the curated glossary; never perform substring replacement in ROM text."""
import argparse,collections,json,re,sys
from pathlib import Path

def clean(value):return re.sub(r'\s+',' ',value).strip().casefold()
def check_labels(registry,catalog,translations):
    accepted=collections.defaultdict(list);count=0;conflicts=[]
    for e in registry['entries']:
        if e['decision']=='accepted':accepted[e['en'].casefold()].append(e)
    for t in translations:
        source=catalog[t['id']]['source']
        if '[[' in source or '\n' in source:continue
        candidates=[e for e in accepted.get(source.casefold(),[]) if t['id'] not in e.get('excluded_rom_ids',[])]
        if not candidates:continue
        allowed={clean(e['ru']) for e in candidates}|{clean(e['short_ru']) for e in candidates if e['short_ru'] and ('short_ru_ids' not in e or t['id'] in e['short_ru_ids'])}
        count+=1
        if clean(t['ru']) not in allowed:conflicts.append({'id':t['id'],'term_ids':[e['term_id'] for e in candidates],'actual_ru':t['ru'],'expected_ru':sorted(allowed)})
    return count,conflicts

def main():
    p=argparse.ArgumentParser();p.add_argument('--glossary',type=Path,required=True);p.add_argument('--catalog',type=Path);p.add_argument('--translation',type=Path);p.add_argument('--markdown',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    r=json.loads(a.glossary.read_text(encoding='utf-8'));sources=r['sources'];entries=r['entries'];ids=set();keys=set()
    labels={'official_other_title':'официальная форма другой части','attested':'зафиксировано во вторичном источнике','project_choice':'решение проекта','proposal':'предложение'}
    for e in entries:
        assert e['term_id'] not in ids;ids.add(e['term_id']);key=(e['category'],e['en'].casefold());assert key not in keys;keys.add(key)
        assert e['evidence'] in labels and e['decision'] in ('accepted','review')
        assert all(s in sources for s in e['source_ids'])
        if e['evidence']=='official_other_title':assert any(sources[s]['kind']=='official_platform' for s in e['source_ids'])
        if e['evidence']=='proposal':assert e['decision']=='review'
    lines=['# Словарь Final Fantasy для проекта FFTA','',f"Версия {r['version']}; проверка источников 30.10.2026. Всего {len(entries)} терминологических карточек. Это не универсальный официальный русский словарь.",'','Правила и ограничения: [TERMINOLOGY_POLICY.md](TERMINOLOGY_POLICY.md). `review` означает, что вариант требует дополнительной проверки до окончательной фиксации. Альтернативы перечисляются для распознавания, а не для свободного чередования в переводе.','']
    for category in sorted({e['category'] for e in entries}):
        lines += [f'## {category}','','| Оригинал | Вариант проекта | Статус | Другие варианты / замечание | Источники |','|---|---|---|---|---|']
        for e in entries:
            if e['category']!=category:continue
            alt='; '.join(e['alternatives_ru']);note=' '.join(x for x in [alt,e['note']] if x)
            refs=', '.join(f"[{s}]({sources[s]['url']})" if sources[s].get('url') else s for s in e['source_ids'])
            lines.append(f"| {e['en']} | {e['ru']} | {labels[e['evidence']]} / {e['decision']} | {note} | {refs} |")
        lines.append('')
    lines += ['## Как читались источники','']
    for sid,s in sources.items():
        lines += [f"- {sid}: {s['title']}. Тип: {s['kind']}; доступ: {s['access']}. {s.get('scope','')}"]
    a.markdown.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report={'term_count':len(entries),'decisions':dict(collections.Counter(e['decision'] for e in entries)),'evidence':dict(collections.Counter(e['evidence'] for e in entries)),'exact_label_checks':0,'conflicts':[],'scope':'Exact named-label checks only; prose, inflection and semantic identity require editorial review.'}
    if a.catalog and a.translation:
        cat=json.loads(a.catalog.read_text(encoding='utf-8'))['entries'];translations=json.loads(a.translation.read_text(encoding='utf-8'))['entries']
        report['exact_label_checks'],report['conflicts']=check_labels(r,cat,translations)
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))
    if report['conflicts']:sys.exit(1)
if __name__=='__main__':main()
