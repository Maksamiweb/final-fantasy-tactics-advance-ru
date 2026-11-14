"""Conservative lexical inventory. Never declare a resource unreachable or translated.

Reports only IDs and hashes, never a public source-text dump. Unknown original font
glyphs and Japanese annotations remain distinct from blank/placeholder records.
"""
import argparse,collections,json,re
from pathlib import Path

def classify(source):
    visible=re.sub(r'\[\[[^]]*\]\]','',source).strip()
    if visible.casefold()in {'dummy','-','????','(---)','xxxx','(not used)'}or visible.startswith('CRN_'):return 'placeholder_or_reserved'
    if visible.startswith('カット'):return 'japanese_cut_label_candidate'
    if re.search(r'[ぁ-ヿ一-龯]',visible):
        if re.match(r'^\s*\[\[40\]\]\[\[42\]\]',source):return 'japanese_after_end_marker_candidate'
        return 'japanese_dialogue_candidate'
    if re.search(r'[A-Za-z]',visible):return 'latin_text_candidate'
    if re.search(r'\[\[U[0-9A-Fa-f]+\]\]',source):return 'unmapped_glyph_content'
    if not visible:return 'empty_or_control_only'
    if re.search(r'\[\[51[0-9A-Fa-f]+\]\]',source):return 'dynamic_name_and_punctuation'
    return 'symbol_numeric_or_punctuation_only'

def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--translation',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    catalog=json.loads(a.catalog.read_text(encoding='utf-8'))['entries'];translated=json.loads(a.translation.read_text(encoding='utf-8'))['entries'];ids={e['id']for e in translated};assert len(ids)==len(translated)
    counts=collections.Counter();all_counts=collections.Counter();records=[]
    for ident,e in catalog.items():
        category=classify(e['source']);all_counts[category]+=1
        if ident in ids:continue
        counts[category]+=1;records.append({'id':ident,'category':category,'source_sha256':e['source_sha256']})
    report={'catalog_records':len(catalog),'authored_records':len(ids),'remaining_records':len(records),'all_catalog_lexical_categories':dict(all_counts),'remaining_lexical_categories':dict(counts),'remaining_records_by_category':records,'scope':'Lexical classification, not runtime reachability. Japanese copy/annotation/cut-label candidates and unmapped glyphs require source-font and call-site investigation. Coverage of Latin candidates excludes graphical text, undeclared encodings and mixed Japanese resources. Blank/symbol/placeholder records are not counted as newly translated.','rom_or_patch_created':False}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items()if k not in ('remaining_records_by_category','scope')}))
if __name__=='__main__':main()
