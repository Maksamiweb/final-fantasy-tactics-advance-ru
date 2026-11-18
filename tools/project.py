"""USA-only private catalog and append-only resource builder. Python 3.10+, Pillow.

Source text stays in a private catalog; public translations contain only authored Russian.
"""
import argparse,collections,contextlib,hashlib,io,json,re,struct,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import bps

SHA='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19'
FONT=0x433330;WIDTH=0x4966b0;COUNT=3175
ALPHABET='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя«»—–№…'
TAG=re.compile(r'\[\[(U[0-9A-Fa-f]+|[0-9A-Fa-f]+|EOS)\]\]')

def digest(data):return hashlib.sha256(data).hexdigest()
def norm(tokens):return [('CHR',v) if k.startswith('CHR_') else (k,v) for k,v in tokens]
def semantic_hash(tokens):return digest(json.dumps(norm(tokens),separators=(',',':')).encode())
def structural(tokens):return [(k,v) for k,v in tokens if not k.startswith('CHR') and not (k=='CTR_FUNC' and v in (0x4d,0x52))]

# USA descriptions form English words using shared names plus suffixes:
# Remedi + es, and Dark Knight + sword. Only these pinned records are literalized.
WORD_FRAGMENT_HASHES={
    'fx_text/17/39':'adf975569819c1b2ec85a5409d7663df911e07d7ae74a79b152c97e6bec499fd',
    'fx_text/17/212':'b3a769f8fcebf92c14a7f17d8d13490f4101d938becb19fe8c2755bd60276350',
    'fx_text/21/40':'84c19ccd54bd5beebb289abe43992462d02578b25b9a9a761afe0f73aa8c87e8',
}
WORD_FRAGMENT_REFERENCES={'fx_text/17/39':0x5105,'fx_text/17/212':0x5105,'fx_text/21/40':0x5137}
WORD_FRAGMENT_SUFFIXES={'fx_text/17/39':[206,220],'fx_text/17/212':[206,220],'fx_text/21/40':[220,224,216,219,205]}

def validate_controls(ident,source,translated,literalize_word_fragment=False):
    expected=structural(source)
    if literalize_word_fragment:
        assert ident in WORD_FRAGMENT_HASHES,'Word-fragment exception is not allowed here'
        assert semantic_hash(source)==WORD_FRAGMENT_HASHES[ident],'Word-fragment source changed'
        normalized=norm(source)
        reference=('CTR_FUNC',WORD_FRAGMENT_REFERENCES[ident]);suffix=WORD_FRAGMENT_SUFFIXES[ident]
        pos=normalized.index(reference)
        assert normalized[pos+1:pos+1+len(suffix)]==[('CHR',v)for v in suffix],'Expected source-language suffix'
        assert expected.count(reference)==1
        expected=[t for t in expected if t!=reference]
    assert structural(translated)==expected,ident+' structural controls changed'
    validate_choice_prompt_lines(ident,source,translated)
    if ident=='fx_text/9/2':validate_level_suffix(source,translated)

def validate_level_suffix(source,translated):
    # Native empty-skill branch consumes five display tokens after418. A shorter
    # localized /Lvl. suffix eats the following line break (observed in game).
    def length(tokens):
        tokens=[tuple(t)for t in tokens]
        first=tokens.index(('CTR_FUNC',0x418))+1
        last=tokens.index(('CTR_FUNC',0x41a),first)
        tail=tokens[first:last]
        assert all(k.startswith('CHR') or (k=='CTR_FUNC' and v==0x52)for k,v in tail)
        return len(tail)
    assert length(source)==length(translated),'Mission skill-level suffix must retain native display-token count'

def validate_choice_prompt_lines(ident,source,translated):
    # Native confirmations size the prompt from the source layout. An extra
    # wrapped line can move Yes/No below the box (observed in save overwrite).
    def positions(tokens):
        line=0;result=[]
        for kind,value in tokens:
            if kind!='CTR_FUNC':continue
            if value in (0x40,0x42,0x4f):line=0
            elif value==0x4d:line+=1
            elif value>>8==0x32:result.append(line)
        return result
    before=positions(source);after=positions(translated)
    assert len(before)==len(after),ident+' choice count changed'
    assert all(b<=a for a,b in zip(before,after)),ident+' extra prompt line hides choice row'

def additional_fixed_page_consumers(old_offset,raw):
    if old_offset==0x4c3e60:
        fields=[]
        for pc,at in ((0x548cc,0x5493c),(0x65be2,0x65c18),(0x6debe,0x6df5c)):
            op=struct.unpack_from('<H',raw,pc)[0]
            assert op&0xff00==0x4900 and ((pc+4)&~3)+(op&255)*4==at
            assert struct.unpack_from('<I',raw,at)[0]==0x084c3e60
            fields.append(at)
        return fields
    if old_offset!=0x4c3798:return []
    fields=[]
    for pc,at in ((0x4ecf4,0x4ed3c),(0x4fc00,0x4fd14),(0x50116,0x50134)):
        op=struct.unpack_from('<H',raw,pc)[0]
        assert op&0xff00==0x4900 and ((pc+4)&~3)+(op&255)*4==at
        assert struct.unpack_from('<I',raw,at)[0]==0x084c3798
        fields.append(at)
    return fields

def encoded_text_limit(ident,source_bytes):
    # Native tavern/help records already reach 970 bytes in the verified USA ROM.
    # Larger help translations may use their own native extent, never an arbitrary cap.
    return max(512,source_bytes) if ident.startswith('fx_text/8/') else 512

def uncompressed_text_flags(flags):
    # Only bits 0/1 select alternate encoding/compression. Upper metadata is
    # used by the native renderer: dropping 0x1800 blanks item help page two.
    return flags & 0xfffc

def additional_page_consumers(name,old_offset,raw):
    # The USA condition loader has four branches loading the same page table.
    # init_info describes only the first. Keep an explicit, source-pinned list;
    # never scan and replace arbitrary matching words in the ROM.
    consumers={
        'condi':(0x4b83a0,((0x13dcc,0x13de0),(0x13e26,0x13e34),(0x13e6e,0x13e98))),
        'battle':(0x497418,((0x27440,0x27484),(0x274a4,0x274dc))),
    }
    if name not in consumers:return []
    expected,branches=consumers[name]
    assert old_offset==expected,'Unexpected native '+name+' table'
    fields=[]
    for instruction,literal in branches:
        op=struct.unpack_from('<H',raw,instruction)[0]
        assert op&0xff00==0x4900,'Expected Thumb LDR r1 literal'
        assert ((instruction+4)&~3)+(op&255)*4==literal,'Page literal moved'
        assert struct.unpack_from('<I',raw,literal)[0]==old_offset+0x08000000,'Page source pointer changed'
        fields.append(literal)
    return fields

def validate_ui_headings(raw,payload):
    from prepare_ui_headings import chunks,SELECTORS
    from ffta_a7 import decode_archive
    assert [x['data']for x in decode_archive(payload)]==chunks(),'Unexpected authored UI heading payload'
    expected=b''.join(bytes((*row,0))for row in SELECTORS)
    assert raw[0x36d6e4:0x36d6e4+len(expected)]==expected,'UI selector metadata changed'
    for pc,literal in ((0x18542,0x1857c),(0x18584,0x185b0)):
        op=struct.unpack_from('<H',raw,pc)[0]
        assert op&0xff00==0x4800 and ((pc+4)&~3)+(op&255)*4==literal,'UI archive loader changed'
        assert struct.unpack_from('<I',raw,literal)[0]==0x083d5070,'UI source pointer changed'
    return (0x1857c,0x185b0)

def load(rom,upstream):
    sys.path.insert(0,str(upstream.resolve()));import ffta_sect as s
    raw=rom.read_bytes();assert digest(raw)==SHA,'Only verified clean USA supported'
    with contextlib.redirect_stdout(io.StringIO()):root=s.load_rom_us(str(rom))
    charset=json.loads((upstream/'charset_us.json').read_text(encoding='utf-8'))[0]
    return s,raw,root,{int(k):v for k,v in charset.items()}

def records(s,root):
    found={}
    def descend(obj,path,parent=None,index=None):
        if obj is None:return
        if isinstance(obj,s.c_ffta_sect_text_line):found[path]={'obj':obj.text,'line':obj,'parent':parent,'index':index};return
        if isinstance(obj,s.c_ffta_sect_text_buf):found[path]={'obj':obj,'line':None,'parent':parent,'index':index};return
        if isinstance(obj,s.c_ffta_sect_tab_ref):
            for i in range(obj.tsize):
                try:descend(obj[i],path+'/'+str(i),obj,i)
                except Exception as error:raise ValueError(path+'/'+str(i)+': '+str(error)) from error
    for name,obj in root.tabs.items():
        if name not in ('s_text','fx_text','pages','words'):continue
        if isinstance(obj,dict):
            for sub,t in obj.items():descend(t,name+':'+sub)
        else:descend(obj,name)
    return found

def text(tokens,charset):
    out=[]
    for k,v in tokens:
        if k.startswith('CHR'):out.append(charset.get(v,f'[[U{v:X}]]'))
        elif k=='CTR_EOS':out.append('[[EOS]]')
        elif v==0x52:out.append(' ')
        elif v==0x4d:out.append('\n')
        else:out.append(f'[[{v:X}]]')
    return ''.join(out)

def encode(txt,reverse):
    out=[];pos=0
    while pos<len(txt):
        tag=TAG.match(txt,pos)
        if tag:
            val=tag.group(1)
            if val.startswith('U'):
                glyph=int(val[1:],16)
                if not 0<=glyph<COUNT:raise ValueError('Raw glyph must refer to the original font')
                out.append(('CHR_FULL',glyph))
            else:out.append(('CTR_EOS',0) if val=='EOS' else ('CTR_FUNC',int(val,16)))
            pos=tag.end();continue
        c=txt[pos];pos+=1
        if c==' ':out.append(('CTR_FUNC',0x52))
        elif c=='\n':out.append(('CTR_FUNC',0x4d))
        else:
            if c not in reverse:raise ValueError('Unsupported character '+repr(c))
            out.append(('CHR_FULL',reverse[c]))
    return out

def glyphs(font_path):
    assert digest(font_path.read_bytes())=='9cc831490532009bae2b3ce0d39c62adfc889060beb421593bfd9d2396d0f10a','Unexpected font'
    font=ImageFont.truetype(str(font_path),13)
    bitmaps=[];widths=[];sheet=Image.new('RGB',(16*20,32*5),'#e6e3c8');draw=ImageDraw.Draw(sheet)
    for i,c in enumerate(ALPHABET):
        im=Image.new('L',(16,16));d=ImageDraw.Draw(im);d.text((0,-2),c,font=font,fill=255,stroke_width=0)
        box=im.getbbox();assert box and box[2]<=15
        # Monochrome body plus a one-pixel shadow, matching palette roles in the original.
        body=[[im.getpixel((x,y))>=100 for x in range(16)] for y in range(16)]
        pixels=[[3 if body[y][x] else (2 if x>0 and y>0 and body[y-1][x-1] else 0) for x in range(16)] for y in range(16)]
        values=[pixels[y][tile*8+x] for tile in range(2) for y in range(16) for x in range(8)]
        bitmaps.append(bytes(values[j]|values[j+1]<<4 for j in range(0,256,2)))
        widths.append(min(15,box[2]+1))
        x=(i%20)*16;y=(i//20)*32
        for yy in range(16):
            for xx in range(16):
                if pixels[yy][xx]:sheet.putpixel((x+xx,y+yy),(0,0,0) if pixels[yy][xx]==3 else (120,120,120))
        draw.text((x,y+16),c,font=font,fill='black')
    return b''.join(bitmaps),bytes(widths),sheet

def compact_glyphs(font_path):
    """Same-height condensed Cyrillic for bounded UI name buffers, separate slots."""
    assert digest(font_path.read_bytes())=='9cc831490532009bae2b3ce0d39c62adfc889060beb421593bfd9d2396d0f10a'
    font=ImageFont.truetype(str(font_path),13);bitmaps=[];widths=[]
    sheet=Image.new('RGB',(16*20,32*5),'#e6e3c8');draw=ImageDraw.Draw(sheet)
    for i,c in enumerate(ALPHABET):
        source=Image.new('L',(16,16));ImageDraw.Draw(source).text((0,-2),c,font=font,fill=255)
        box=source.getbbox();assert box
        target_width=max(1,round(box[2]*0.65))
        mask=source.crop((0,0,box[2],16)).resize((target_width,16),Image.Resampling.LANCZOS)
        body=[[x<target_width and mask.getpixel((x,y))>=85 for x in range(16)]for y in range(16)]
        pixels=[[3 if body[y][x]else 2 if x and y and body[y-1][x-1]else 0 for x in range(16)]for y in range(16)]
        values=[pixels[y][tile*8+x]for tile in range(2)for y in range(16)for x in range(8)]
        bitmaps.append(bytes(values[j]|values[j+1]<<4 for j in range(0,256,2)));widths.append(target_width+1)
        xx=(i%20)*16;yy=(i//20)*32
        for y in range(16):
            for x in range(16):
                if pixels[y][x]:sheet.putpixel((xx+x,yy+y),(0,0,0)if pixels[y][x]==3 else(120,120,120))
        draw.text((xx,yy+16),c,font=font,fill='black')
    return b''.join(bitmaps),bytes(widths),sheet

def encode_entry(entry,reverse):
    tokens=encode(entry['ru'],reverse);profile=entry.get('font_profile','normal')
    assert profile in ('normal','compact_ui'),'Unknown font profile'
    if profile=='compact_ui':
        tokens=[(k,v+len(ALPHABET)if k.startswith('CHR')and COUNT<=v<COUNT+len(ALPHABET)else v)for k,v in tokens]
    return tokens

def fixed_name_widths(entries,reverse,widths):
    result={}
    for entry in entries:
        if not entry['id'].startswith('words:refer/'):continue
        size=0
        for kind,value in encode_entry(entry,reverse):
            if kind.startswith('CHR'):size+=widths[value]
            elif kind=='CTR_FUNC' and value==0x52:size+=4
            elif kind=='CTR_FUNC' and value>>8==0x1b:size-=value&255
            elif kind=='CTR_FUNC' and value>>8==0x1d:size+=value&255
            else:raise ValueError('Fixed name contains unresolved control: '+entry['id'])
        result[int(entry['id'].split('/')[-1])]=size
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['extract','build']);p.add_argument('--rom',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--catalog',type=Path);p.add_argument('--translation',type=Path);p.add_argument('--font',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--private-rom',type=Path);p.add_argument('--status-graphics',type=Path,help='Pinned native-tested status LZSS stream, optional');p.add_argument('--ui-heading-graphics',type=Path,help='Authored UI A7 heading archive, optional');p.add_argument('--mission-graphics',type=Path,help='Private mission RANK/PAGE LZSS stream, optional');p.add_argument('--roster-graphics',type=Path,help='Private roster hint LZSS stream, optional');p.add_argument('--calendar-graphics',type=Path,help='Authored month A7 archive, optional');p.add_argument('--world-hud-graphics',type=Path,help='Private treasury/day LZSS stream, optional');p.add_argument('--world-button-graphics',type=Path,help='Private world LAW/Info LZSS stream, optional');p.add_argument('--battle-popup-graphics',type=Path,help='Private floating combat A7 archive, optional');p.add_argument('--equipment-button-graphics',type=Path,help='Private equipment button LZSS stream, optional');p.add_argument('--ability-type-graphics',type=Path,help='Private ability type A7 archive, optional');p.add_argument('--law-panel-graphics',type=Path,help='Private duplicate law heading LZSS stream, optional');p.add_argument('--map-location-graphics',type=Path,help='Authored30-place A7 archive and native layout tables, optional');p.add_argument('--battle-goal-graphics',type=Path,help='Private battle objective archive/header directory');p.add_argument('--battle-result-graphics',type=Path,help='Authored battle/mission result archive directory');p.add_argument('--save-counter-graphics',type=Path,help='Private save-slot completed-mission LZSS');p.add_argument('--banner-font',type=Path,help='Pinned local bold italic font for battle captions');p.add_argument('--map-alert-graphics',type=Path,help='Private Engage and Mission caption streams');p.add_argument('--title-menu-graphics',type=Path,help='Authored raw title-screen menu OBJ labels');p.add_argument('--title-credit-graphics',type=Path,help='Private BG title credits graphics/map');p.add_argument('--title-heading-font',type=Path,help='Local serif font for Russian edition caption');p.add_argument('--title-credit-font',type=Path,help='Local upright font for larger translation credit');p.add_argument('--ready-caption-graphics',type=Path,help='Private160x24 Russian Get Ready caption');p.add_argument('--word-layout',type=Path,help='Build report fixing word addresses and reserved byte lengths');a=p.parse_args()
    s,raw,root,charset=load(a.rom,a.upstream);items=records(s,root)
    if a.command=='extract':
        catalog={k:{'source':text(v['obj'].tokens,charset),'source_sha256':semantic_hash(v['obj'].tokens),'offset':hex(v['obj'].real_offset),'tokens':v['obj'].tokens} for k,v in items.items()}
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'rom_sha256':SHA,'entries':catalog},indent=2,ensure_ascii=False),encoding='utf-8');print('Private catalog records:',len(items));return
    assert a.private_rom and a.font and a.translation
    assert a.private_rom.resolve()!=a.rom.resolve()
    entries=json.loads(a.translation.read_text(encoding='utf-8'))['entries']
    for e in entries:
        assert e['id'] in items,e['id'];assert semantic_hash(items[e['id']]['obj'].tokens)==e['source_sha256'],e['id']+' source changed'
    terminology_path=Path(__file__).resolve().parent.parent/'translation/TERMINOLOGY.json'
    terminology_checks=0
    if terminology_path.exists():
        from terminology import check_labels
        registry=json.loads(terminology_path.read_text(encoding='utf-8'))
        label_catalog={k:{'source':text(v['obj'].tokens,charset)} for k,v in items.items()}
        terminology_checks,conflicts=check_labels(registry,label_catalog,entries)
        assert not conflicts,'Accepted terminology conflict: '+json.dumps(conflicts,ensure_ascii=True)
    newglyphs,newwidths,sheet=glyphs(a.font);compact_sheet=None
    if any(e.get('font_profile')=='compact_ui'for e in entries):
        extra,extra_widths,compact_sheet=compact_glyphs(a.font)
        newglyphs+=extra;newwidths+=extra_widths
    reverse={}
    for k,v in charset.items():
        if len(v)==1 and v not in reverse:reverse[v]=k
    reverse.update({c:COUNT+i for i,c in enumerate(ALPHABET)})
    encoded={};tokens={};layout=[]
    allwidths=raw[WIDTH:WIDTH+COUNT]+newwidths
    fixed_names=fixed_name_widths(entries,reverse,allwidths)
    for e in entries:
        ts=encode_entry(e,reverse);old=items[e['id']]['obj'].tokens
        validate_controls(e['id'],old,ts,e.get('literalize_word_fragment',False))
        if 'max_chars' in e:
            assert sum(k.startswith('CHR') or (k=='CTR_FUNC' and v==0x52) for k,v in ts)<=e['max_chars'],e['id']+' character cap exceeded'
        tokens[e['id']]=ts;encoded[e['id']]=bytes(items[e['id']]['obj']._encode(ts))
        byte_limit=encoded_text_limit(e['id'],items[e['id']]['obj'].raw_len)
        assert len(encoded[e['id']])<=byte_limit,e['id']+' exceeds source-scoped encoded byte limit'
        # Width includes known dynamic-field budgets. Unknown substitutions fail layout review explicitly.
        limit=e.get('max_width',156);maxlines=e.get('max_lines',3);linewidth=0;lines=1;warnings=[];widest=0
        for k,v in ts:
            if k=='CTR_FUNC' and f'{v:04X}' in e.get('dynamic_widths',{}):linewidth+=e['dynamic_widths'][f'{v:04X}']
            elif k.startswith('CHR'):linewidth+=allwidths[v]
            elif k=='CTR_FUNC' and v==0x52:linewidth+=4
            elif (e.get('font_profile')=='compact_ui' or e.get('max_player_name_width')is not None or e.get('measure_control_offsets')) and k=='CTR_FUNC' and v>>8==0x1b:linewidth-=v&255
            elif (e.get('font_profile')=='compact_ui' or e.get('max_player_name_width')is not None or e.get('measure_control_offsets')) and k=='CTR_FUNC' and v>>8==0x1d:linewidth+=v&255
            elif k=='CTR_FUNC' and v==0x4d:widest=max(widest,linewidth);linewidth=0;lines+=1
            elif k=='CTR_FUNC' and v in (0x4f,0x40,0x42):
                widest=max(widest,linewidth)
                if lines>maxlines:warnings.append('too many lines')
                linewidth=0;lines=1
            elif k=='CTR_FUNC' and (v>>8 in (0x51,0x04) or v==0x400):
                linewidth+=fixed_names.get(v&255,e.get('substitution_width',42))if e.get('resolve_fixed_references')and v>>8==0x51 else e.get('max_player_name_width',e.get('substitution_width',42))if v==0x400 else e.get('substitution_width',42)
        widest=max(widest,linewidth)
        if widest>limit:warnings.append('line too wide')
        if lines>maxlines:warnings.append('too many lines')
        layout.append({'id':e['id'],'max_measured_width':widest,'limit':limit,'warnings':warnings,'profile':e.get('layout_profile','dialogue'),'runtime_verified':e.get('runtime_verified',False)})
    assert all(not x['warnings'] for x in layout),'Layout validation failed: '+json.dumps([x for x in layout if x['warnings']],ensure_ascii=True)
    # A story page may have several owner-table aliases (for example 0 and 60).
    # Relocating their shared page intentionally changes every alias of a line.
    shared_lines={}
    for ident,ts in list(tokens.items()):
        item=items[ident]
        if item['line'] is None:continue
        key=(item['parent'].real_offset,item['index'])
        if key in shared_lines:assert norm(shared_lines[key])==norm(ts),'Conflicting shared-page translations: '+ident
        shared_lines[key]=ts
    affected_aliases=[]
    for ident,item in items.items():
        if item['line'] is None:continue
        key=(item['parent'].real_offset,item['index'])
        if ident not in tokens and key in shared_lines:
            tokens[ident]=shared_lines[key];affected_aliases.append(ident)
    # An append-only plan retains all source bytes; only explicitly inventoried pointers change.
    writes={};append=[];tail=len(raw);relocations=[]
    word_slots={}
    if a.word_layout:
        baseline=json.loads(a.word_layout.read_text(encoding='utf8'))
        word_slots={entry['id']:entry for entry in baseline['relocations'] if entry.get('kind')=='word'}
        assert all(entry['kind']=='word' for entry in word_slots.values())
    def push(item,n=None):
        nonlocal tail
        if n is None:n=len(item)
        at=tail;append.append((item,n));tail+=n;return at
    def align(n=4):
        if tail%n:push(bytes(n-tail%n))
    def put(off,data):
        assert 0<=off and off+len(data)<=len(raw)
        if off in writes:assert writes[off]==data
        writes[off]=bytes(data)
    font_start=tail;push(FONT,COUNT*128);push(newglyphs);align();width_start=tail;push(WIDTH,COUNT);push(newwidths);align()
    for old,new,expected in [(FONT,font_start,[0x13474]),(WIDTH,width_start,[0x13480,0x13a7c])]:
        hits=[];start=0;needle=struct.pack('<I',old+0x8000000)
        while True:
            i=raw.find(needle,start)
            if i<0:break
            hits.append(i);start=i+1
        assert hits==expected,('Pointer references changed',old,hits)
        for off in hits:put(off,struct.pack('<I',new+0x8000000))
    pages=collections.defaultdict(dict)
    for ident,data in encoded.items():
        item=items[ident]
        if item['line'] is None:
            align(2)
            reserved=len(data)
            if word_slots:
                slot=word_slots[ident]
                assert tail==int(slot['new_offset'],16),ident+' stable word address changed'
                reserved=slot['bytes']
                assert len(data)<=reserved,ident+' exceeds reserved word slot'
            at=push(data+bytes(reserved-len(data)))
            put(item['parent'].real_offset+item['index']*4,struct.pack('<I',at+0x8000000))
            relocations.append({'id':ident,'new_offset':hex(at),'bytes':len(data),'reserved_bytes':reserved,'kind':'word'})
        else:pages[item['parent'].real_offset][ident]=data
    for changes in pages.values():
        first=items[next(iter(changes))];page=first['parent'];align();base=tail
        offsets=[];parts=[];relative=page.tsize*2;paths={items[k]['index']:k for k in changes}
        for idx in range(page.tsize):
            if relative%2:parts.append((b'\0',1));relative+=1
            assert relative<=65535,'16-bit page limit exceeded'
            offsets.append(relative);line=page[idx]
            if idx in paths:
                payload=struct.pack('<H',uncompressed_text_flags(line.U16(0)))+encoded[paths[idx]];parts.append((payload,len(payload)));relative+=len(payload)
            else:parts.append((line.real_offset,line.raw_len));relative+=line.raw_len
        push(struct.pack('<'+'H'*len(offsets),*offsets))
        for part,n in parts:push(part,n)
        align()
        # Locate the original owner table rather than scanning and replacing arbitrary ROM values.
        fields=[]
        def owner(obj):
            if isinstance(obj,dict):
                for x in obj.values():owner(x)
            elif isinstance(obj,s.c_ffta_sect_tab_ref) and not isinstance(obj,s.c_ffta_sect_text_page):
                for i in range(obj.tsize):
                    sub=obj[i]
                    if sub is not None and sub.real_offset==page.real_offset:
                        if isinstance(obj,s.c_ffta_sect_tab_ref_addr):value=base+0x8000000
                        else:value=base-obj.real_offset+getattr(obj,'_tab_ref_sub_offset',0)
                        fields.append((obj.real_offset+i*obj._TAB_WIDTH,value,obj._TAB_WIDTH))
                    elif isinstance(sub,s.c_ffta_sect_tab_ref) and not isinstance(sub,s.c_ffta_sect_text_page):owner(sub)
        for name in ('s_text','fx_text'):owner(root.tabs[name])
        for name,t in root.tabs['pages'].items():
            if t.real_offset==page.real_offset:
                off=root.init_info['pages:'+name][0];fields.append((off,base+0x8000000,4))
                fields.extend((off,base+0x8000000,4)for off in additional_page_consumers(name,page.real_offset,raw))
        fields.extend((off,base+0x8000000,4)for off in additional_fixed_page_consumers(page.real_offset,raw))
        assert fields,'Page owner missing'
        for off,value,n in fields:put(off,value.to_bytes(n,'little'))
        relocations.append({'ids':list(changes),'old_page':hex(page.real_offset),'new_page':hex(base),'size':tail-base,'lines':page.tsize,'pointer_fields':[hex(f[0]) for f in fields]})
    graphics_report=None
    if a.status_graphics:
        from ffta_lzss import decompress
        payload=a.status_graphics.read_bytes()
        status_variants={'17b01550928240cb62bb0dc37fe6093b138ce3c940af7cba32f416bcaef1e175':('0dfe5b36582ab20de1ae95ec9da2f3a55542e68ed71b4653116558a8e0fe275c',12),'bcd082a266e61e07e2f80b376e56b75ceff96ce56697380c97fad3b14b1cf725':('7b6aab711b6942c8d4e2f83fff53c9c72cca3a5a0794f50d48bafa11ee8c7c84',16),'2e21e6b2a151408517264197ee42ee32f0042fcc8f284bcbb5d94e2ea1236637':('2c76fa7f3b374a004d5f53061bd610bb42087ff344a20ce5fca971ebfd15f508',15),'5329198614cab66eb6b8ecac9022de397303f8de2326701717706effec19f01c':('7c29d742c487755f157c024ea4be6cbf5d73865c18fc1ce3f63f20cb885dc48c',13)}
        assert digest(payload)in status_variants,'Unexpected pinned status payload'
        expected_status_hash,status_label_count=status_variants[digest(payload)]
        before,old_used=decompress(raw,0x3b4214);after,new_used=decompress(payload)
        assert old_used==4000 and len(before)==len(after)==7264 and new_used==len(payload)<=old_used
        assert digest(before)=='be047764271a4255375cfd95608c2824bbb649fe768fd021086e0f0c8cd8185d'
        assert digest(after)==expected_status_hash
        assert after[199*32:]==before[199*32:],'Status bank tail changed'
        put(0x3b4214,payload)
        graphics_report={'offset':'0x3b4214','payload_bytes':len(payload),'previous_stream_bytes':old_used,
                         'payload_sha256':digest(payload),'decoded_sha256':digest(after),'labels':status_label_count,'EQUIP_translated':False,'number_sign_translated':status_label_count>=13,'equipment_hints_translated':status_label_count>=15,'master_translated':status_label_count>=16}
    ability_type_report=None
    if a.ability_type_graphics:
        from ffta_a7 import decode_archive
        from prepare_ability_types import chunks
        payload=a.ability_type_graphics.read_bytes()
        assert [x['data']for x in decode_archive(payload)]==chunks(raw)
        for pc,field in ((0x7bdca,0x7bdf0),(0x7bf9a,0x7bff8),(0x8c606,0x8c628)):
            op=struct.unpack_from('<H',raw,pc)[0]
            assert op&0xff00==0x4800 and ((pc+4)&~3)+(op&255)*4==field
            assert struct.unpack_from('<I',raw,field)[0]==0x083c5744
        align();at=push(payload)
        for field in (0x7bdf0,0x7bff8,0x8c628):put(field,struct.pack('<I',at+0x08000000))
        ability_type_report={'source_archive':'0x3c5744','new_archive':hex(at),'pointer_fields':['0x7bdf0','0x7bff8','0x8c628'],'sha256':digest(payload),'labels':4}
    battle_popup_report=None
    if a.battle_popup_graphics:
        from ffta_a7 import decode_archive
        from prepare_battle_graphics import make_bank
        expected,battle_entries=make_bank(raw)
        repaired_poison,repaired_entries=make_bank(raw,repair_poison=True)
        preserved_knockout,knockout_entries=make_bank(raw,repair_poison=True,preserve_knockout=True)
        payload=a.battle_popup_graphics.read_bytes()
        decoded_popup=b''.join(x['data']for x in decode_archive(payload))
        assert decoded_popup in (expected,repaired_poison,preserved_knockout)
        if decoded_popup==repaired_poison:battle_entries=repaired_entries
        if decoded_popup==preserved_knockout:battle_entries=knockout_entries
        pc=0xa8b88;field=0xa8bbc;op=struct.unpack_from('<H',raw,pc)[0]
        assert op&0xff00==0x4800 and ((pc+4)&~3)+(op&255)*4==field
        assert struct.unpack_from('<I',raw,field)[0]==0x083bc898
        align();at=push(payload);put(field,struct.pack('<I',at+0x08000000))
        battle_popup_report={'source_archive':'0x3bc898','new_archive':hex(at),'pointer_field':hex(field),'sha256':digest(payload),'word_groups':len(battle_entries),'labels':24,'material_and_animation_data_unchanged':True}
    calendar_graphics_report=None
    if a.calendar_graphics:
        from ffta_a7 import decode_archive
        from prepare_calendar_graphics import chunks
        payload=a.calendar_graphics.read_bytes();assert [x['data']for x in decode_archive(payload)] in (chunks(),chunks(True))
        for pc,field,reg in ((0x35d14,0x35dd0,1),(0x57c36,0x57c80,0)):
            op=struct.unpack_from('<H',raw,pc)[0]
            assert op&0xff00==0x4800+reg*0x100 and ((pc+4)&~3)+(op&255)*4==field
            assert struct.unpack_from('<I',raw,field)[0]==0x083acd68
        align();at=push(payload)
        for field in (0x35dd0,0x57c80):put(field,struct.pack('<I',at+0x08000000))
        calendar_graphics_report={'source':'0x3acd68','new_archive':hex(at),'sha256':digest(payload),'months':5,'authored_chunks':30,'pointer_fields':['0x35dd0','0x57c80']}
    equipment_button_report=None
    if a.equipment_button_graphics:
        from ffta_lzss import decompress
        from prepare_equipment_buttons import translated_bank,SOURCE_OFFSET
        source,used=decompress(raw,SOURCE_OFFSET);assert used==1176
        payload=a.equipment_button_graphics.read_bytes();decoded,consumed=decompress(payload)
        assert decoded in (translated_bank(source),translated_bank(source,True)) and consumed==len(payload) and len(payload)<=used
        put(SOURCE_OFFSET,payload)
        equipment_button_report={'offset':hex(SOURCE_OFFSET),'payload_bytes':len(payload),'sha256':digest(payload),'labels':['СПР.','СНЯТЬ','ТЮРЬМА','ЗАДАН.']}
    world_button_report=None
    if a.world_button_graphics:
        from ffta_lzss import decompress
        from prepare_world_buttons import translated_bank,SOURCE_OFFSET
        source,used=decompress(raw,SOURCE_OFFSET);assert used==1676
        payload=a.world_button_graphics.read_bytes();decoded,consumed=decompress(payload)
        assert decoded==translated_bank(source) and consumed==len(payload) and len(payload)<=used
        put(SOURCE_OFFSET,payload)
        world_button_report={'offset':hex(SOURCE_OFFSET),'payload_bytes':len(payload),'sha256':digest(payload),'labels':['ЗАК.','СПР.']}
    battle_goal_report=None
    if a.battle_goal_graphics:
        from ffta_a7 import decode_archive
        from prepare_battle_goals import make_goals
        assert a.banner_font
        expected,headers,goal_rows=make_goals(raw,a.banner_font)
        payload=(a.battle_goal_graphics/'goals.a7').read_bytes();assert [x['data']for x in decode_archive(payload)]==expected
        assert (a.battle_goal_graphics/'headers.bin').read_bytes()==headers
        pc=0x8f9b0;field=0x8fa70;op=struct.unpack_from('<H',raw,pc)[0]
        assert op&0xff00==0x4800 and ((pc+4)&~3)+(op&255)*4==field and struct.unpack_from('<I',raw,field)[0]==0x083c1834
        op=struct.unpack_from('<H',raw,0x2b8f8)[0]
        assert op&0xff00==0x4c00 and ((0x2b8f8+4)&~3)+(op&255)*4==0x2b94c and struct.unpack_from('<I',raw,0x2b94c)[0]==0x083bef08
        align();at=push(payload);put(field,struct.pack('<I',at+0x08000000));put(0x3bef08,headers)
        battle_goal_report={'source_archive':'0x3c1834','new_archive':hex(at),'pointer_field':hex(field),'raw_header_span':'0x3bef08..0x3bf307','labels':6,'headers':2,'sha256':digest(payload)}
    ready_caption_report=None
    if a.ready_caption_graphics:
        from prepare_ready_caption import translated_bank,SOURCE
        from ffta_lzss import decompress
        assert a.title_heading_font
        payload=a.ready_caption_graphics.read_bytes();decoded,used=decompress(payload)
        assert decoded==translated_bank(a.title_heading_font) and used==len(payload) and len(payload)<=1019
        original,old_size=decompress(raw,SOURCE);assert len(original)==1920 and old_size==1019
        put(SOURCE,payload)
        ready_caption_report={'source':hex(SOURCE),'bytes':len(payload),'ru':'ГОТОВЬТЕСЬ!','decoded_bytes':1920}
    battle_result_report=None
    if a.battle_result_graphics:
        from ffta_a7 import decode_archive
        from prepare_battle_results import make_results
        assert a.banner_font
        main,bg,result_tables,result_rows,_=make_results(raw,a.banner_font)
        result_archives=[]
        for filename,expected,old,fields in (
            ('results-main.a7',main,0x083bf308,((0x90adc,0x90b90),(0x90c18,0x90ccc),(0x90d54,0x90e04),(0x90e90,0x90f40))),
            ('results-bg.a7',bg,0x083c05e8,((0x90ae8,0x90b94),(0x90c24,0x90cd0),(0x90d60,0x90e08),(0x90e9c,0x90f44)))):
            payload=(a.battle_result_graphics/filename).read_bytes();assert [x['data']for x in decode_archive(payload)]==expected
            for pc,field in fields:
                op=struct.unpack_from('<H',raw,pc)[0]
                assert op&0xff00==0x4800 and ((pc+4)&~3)+(op&255)*4==field and struct.unpack_from('<I',raw,field)[0]==old
            align();at=push(payload)
            for pc,field in fields:put(field,struct.pack('<I',at+0x08000000))
            result_archives.append({'file':filename,'new_archive':hex(at),'sha256':digest(payload),'pointer_fields':[hex(f)for pc,f in fields]})
        for at,data in result_tables:put(at,data)
        battle_result_report={'labels':4,'glyph_slots_per_label':12,'object_counts_unchanged':[15,14,10,11],'material_tables':[hex(at)for at,data in result_tables],'archives':result_archives}
    title_credit_report=None
    if a.title_credit_graphics:
        from prepare_title_credits import make_art
        assert a.title_heading_font and a.banner_font
        supplied=((a.title_credit_graphics/'graphics.bin').read_bytes(),(a.title_credit_graphics/'map.bin').read_bytes())
        variants=[make_art(raw,a.title_heading_font,a.banner_font,dark)for dark in(False,True)]
        if a.title_credit_font:variants.append(make_art(raw,a.title_heading_font,a.title_credit_font,False,True))
        matches=[v for v in variants if supplied==v[:2]]
        assert len(matches)==1,'Unexpected title credits graphics'
        graphics,title_map,title_credit_report=matches[0]
        for pc,field,register,expected in ((0x135d86,0x135e40,0,0x08960ec0),(0x135d8a,0x135e48,2,0x1cd4),(0x135dc2,0x135e68,0,0x08957d28)):
            op=struct.unpack_from('<H',raw,pc)[0]
            assert op&0xff00==0x4800+register*256 and ((pc+4)&~3)+(op&255)*4==field and struct.unpack_from('<I',raw,field)[0]==expected
        align();at=push(graphics);put(0x135e40,struct.pack('<I',at+0x08000000));put(0x135e48,struct.pack('<I',len(graphics)//2))
        align();at=push(title_map);put(0x135e68,struct.pack('<I',at+0x08000000))
    title_menu_report=None
    if a.title_menu_graphics:
        from prepare_title_menu import make_art
        title_menu_report=[]
        variants=[make_art(a.font),make_art(a.font,True)]
        actual=[(offset,(a.title_menu_graphics/(hex(offset)+'.bin')).read_bytes())for offset,_ in variants[0]]
        assert actual in variants,'Unexpected title menu graphics'
        for offset,expected in actual:
            data=(a.title_menu_graphics/(hex(offset)+'.bin')).read_bytes()
            assert data==expected
            put(offset,data)
            title_menu_report.append({'offset':hex(offset),'bytes':len(data),'sha256':digest(data)})
    map_alert_report=None
    if a.map_alert_graphics:
        from prepare_map_alerts import translated_banks
        from ffta_lzss import decompress
        map_alert_report=[]
        variants=[translated_banks(raw,repair)for repair in(False,True,2,3)]
        actual={offset:decompress((a.map_alert_graphics/(hex(offset)+'.lzss')).read_bytes())[0]for offset in variants[0]}
        assert actual in variants,'Unexpected map alert graphics'
        for offset,expected in actual.items():
            source,used=decompress(raw,offset)
            payload=(a.map_alert_graphics/(hex(offset)+'.lzss')).read_bytes()
            decoded,consumed=decompress(payload)
            assert decoded==expected and consumed==len(payload) and len(payload)<=used
            put(offset,payload)
            map_alert_report.append({'offset':hex(offset),'bytes':len(payload),'sha256':digest(payload)})
    save_counter_report=None
    if a.save_counter_graphics:
        from ffta_lzss import decompress
        from prepare_save_counter import translated_bank,SOURCE
        source,used=decompress(raw,SOURCE);assert used==580
        payload=a.save_counter_graphics.read_bytes();decoded,consumed=decompress(payload)
        assert decoded==translated_bank(source) and consumed==len(payload) and len(payload)<=used
        put(SOURCE,payload)
        save_counter_report={'offset':hex(SOURCE),'payload_bytes':len(payload),'sha256':digest(payload),'changed_decoded_span':[0,320],'labels':['ЗАДАНИЙ','ПРОЙДЕНО']}
    map_location_report=None
    if a.map_location_graphics:
        from ffta_a7 import decode_archive
        from prepare_map_locations import make_asset,WIDTH_TABLE,OFFSET_TABLE
        blocks,codes,offsets,map_rows,_=make_asset(raw,entries,a.font)
        payload=a.map_location_graphics.read_bytes();assert [x['data']for x in decode_archive(payload)]==blocks
        for pc,field in ((0x36710,0x36760),(0x36942,0x369a8)):
            op=struct.unpack_from('<H',raw,pc)[0]
            assert op&0xff00==0x4800 and ((pc+4)&~3)+(op&255)*4==field
            assert struct.unpack_from('<I',raw,field)[0]==0x083ab42c
        align();at=push(payload)
        for field in (0x36760,0x369a8):put(field,struct.pack('<I',at+0x08000000))
        put(WIDTH_TABLE,codes);put(OFFSET_TABLE,offsets)
        map_location_report={'source_archive':'0x3ab42c','new_archive':hex(at),'pointer_fields':['0x36760','0x369a8'],'width_table':hex(WIDTH_TABLE),'offset_table':hex(OFFSET_TABLE),'sha256':digest(payload),'labels':30,'chunks':len(blocks),'all_pixels_authored':True,'geometry_classes':5}
    law_panel_report=None
    if a.law_panel_graphics:
        from ffta_lzss import decompress
        from prepare_law_headings import translated_bank,SOURCE_OFFSET
        source,used=decompress(raw,SOURCE_OFFSET);assert used==542
        payload=a.law_panel_graphics.read_bytes();decoded,consumed=decompress(payload)
        assert decoded==translated_bank(source) and consumed==len(payload) and len(payload)<=used
        put(SOURCE_OFFSET,payload)
        law_panel_report={'offset':hex(SOURCE_OFFSET),'payload_bytes':len(payload),'sha256':digest(payload),'labels':['ЗАПРЕТ','БОНУС']}
    world_hud_report=None
    if a.world_hud_graphics:
        from ffta_lzss import decompress
        from prepare_world_hud import translated_bank,SOURCE_OFFSET
        source,used=decompress(raw,SOURCE_OFFSET);assert used==1295
        payload=a.world_hud_graphics.read_bytes();decoded,consumed=decompress(payload)
        assert decoded in tuple(translated_bank(source,law,clean)for law in(False,True)for clean in(False,True)) and consumed==len(payload) and len(payload)<=used
        put(SOURCE_OFFSET,payload)
        world_hud_report={'offset':hex(SOURCE_OFFSET),'payload_bytes':len(payload),'sha256':digest(payload),'labels':['КАЗНА','ДН.']+(['ЗАПРЕТ','БОНУС']if decoded in (translated_bank(source,True),translated_bank(source,True,True))else[])}
    roster_graphics_report=None
    if a.roster_graphics:
        from ffta_lzss import decompress
        from prepare_roster_graphics import translated_bank,SOURCE_OFFSET
        source,used=decompress(raw,SOURCE_OFFSET);assert used==582
        payload=a.roster_graphics.read_bytes();decoded,consumed=decompress(payload)
        assert decoded==translated_bank(source) and consumed==len(payload) and len(payload)<=used
        put(SOURCE_OFFSET,payload)
        roster_graphics_report={'offset':hex(SOURCE_OFFSET),'payload_bytes':len(payload),'sha256':digest(payload),'labels':['СМЕНА','ПРЕДМЕТЫ','СОРТ.']}
    mission_graphics_report=None
    if a.mission_graphics:
        from ffta_lzss import decompress
        from prepare_mission_graphics import translated_bank,SOURCE_OFFSET
        source,used=decompress(raw,SOURCE_OFFSET);assert used==1629
        payload=a.mission_graphics.read_bytes();decoded,consumed=decompress(payload)
        assert decoded in (translated_bank(source),translated_bank(source,True)) and consumed==len(payload) and len(payload)<=used
        put(SOURCE_OFFSET,payload)
        mission_graphics_report={'offset':hex(SOURCE_OFFSET),'payload_bytes':len(payload),'source_consumed_bytes':used,'sha256':digest(payload),'labels':['КАЗНА','СПР.','РАНГ','СТР.'],'changed_decoded_spans':['0x20..0x11f','0x280..0x2df','0x5e0..0x6bf']}
    ui_graphics_report=None
    if a.ui_heading_graphics:
        payload=a.ui_heading_graphics.read_bytes();fields=validate_ui_headings(raw,payload)
        align();at=push(payload)
        for field in fields:put(field,struct.pack('<I',at+0x08000000))
        ui_graphics_report={'source_archive':'0x3d5070','new_archive':hex(at),'pointer_fields':[hex(x)for x in fields],'payload_bytes':len(payload),'sha256':digest(payload),'authored_chunks':30,'native_selectors':32,'all_pixels_authored':True}
    assert tail<=32*1024*1024,'GBA ROM capacity exceeded'
    plan=[];pos=0
    for off,data in sorted(writes.items()):
        assert off>=pos,'Overlapping writes'
        if off>pos:plan.append((pos,off-pos))
        plan.append((data,len(data)));pos=off+len(data)
    plan.append((pos,len(raw)-pos));plan+=append
    patch,target,literal=bps.create(raw,plan,b'FFTA USA Russian development build; not a complete translation')
    assert target[:0xc0]==raw[:0xc0]
    # Appending the first page removes the smallest-relative-offset count heuristic.
    # Preserve the independently inventoried root count instead of reading text as pointers.
    moved={int(r['old_page'],16):r['size'] for r in relocations if 'old_page' in r}
    class CountedSub(s.c_ffta_sect_text_sub):
        def parse_size(self,top,alignment):
            s.c_ffta_sect.parse_size(self,None,alignment)
            # Sparse relocated children need not remain inside the old group's extent.
            # Their count and individual bounds come from the verified source schema.
            self.tsize=self.source_table.tsize
            self._tab_ref_size=[]
            for i in range(self.tsize):
                old=self.source_table[i];size=moved.get(old.real_offset,old.sect_top)
                offset=self.get_entry(i)
                assert offset>=self.tsize*self._TAB_WIDTH,'Nested text pointer overlaps its owner table'
                assert size is not None and self.real_offset+offset+size<=len(target),'Nested text pointer exceeds ROM'
                self._tab_ref_size.append(size)
    class CountedStory(s.c_ffta_sect_text):
        def parse_size(self,top,alignment):
            s.c_ffta_sect.parse_size(self,None,alignment)
            self.tsize=root.tabs['s_text'].tsize
            self._tab_ref_size=self._guess_size(None,False)
            for i in range(self.tsize):
                old=root.tabs['s_text'][i]
                self._tab_ref_size[i]=moved.get(old.real_offset,old.sect_top)
        def get_ref(self,idx):
            old=root.tabs['s_text'][idx]
            if isinstance(old,s.c_ffta_sect_text_sub):
                offset=self.get_entry(idx);sub=self.sub(offset,cls=CountedSub);sub.source_table=old
                self._init_ref(sub,idx,offset);return sub
            return super().get_ref(idx)
    rebuilt_info=root.init_info.copy()
    rebuilt_info['s_text']=(root.init_info['s_text'][0],CountedStory)
    try:
        with contextlib.redirect_stdout(io.StringIO()):rebuilt=s.c_ffta_sect_rom(target,0).setup(rebuilt_info,len(target))
    except Exception:
        for name,info in root.init_info.items():
            try:s.c_ffta_sect_rom(target,0).setup({name:info},len(target))
            except Exception as err:print('Invalid rebuilt table',name,str(err))
        raise
    rebuilt_items=records(s,rebuilt);assert rebuilt_items.keys()==items.keys()
    for ident,item in items.items():
        expected=tokens.get(ident,item['obj'].tokens)
        assert norm(rebuilt_items[ident]['obj'].tokens)==norm(expected),'Roundtrip failed '+ident
        if item['line'] is not None:
            flags=item['line'].U16(0)
            expected_flags=uncompressed_text_flags(flags)if ident in tokens else flags
            assert rebuilt_items[ident]['line'].U16(0)==expected_flags,'Text header metadata changed '+ident
    a.out.mkdir(parents=True,exist_ok=True);a.private_rom.parent.mkdir(parents=True,exist_ok=True);a.private_rom.write_bytes(target)
    (a.out/'ffta-usa-ru-development.bps').write_bytes(patch)
    sheet.save(a.out/'russian-glyphs.png')
    if compact_sheet is not None:compact_sheet.save(a.out/'russian-glyphs-compact.png')
    report={'source_sha256':SHA,'target_sha256':digest(target),'bps_sha256':digest(patch),'source_size':len(raw),'target_size':len(target),'patch_size':len(patch),'literal_patch_bytes':literal,'original_glyphs_preserved':True,'added_glyphs':len(ALPHABET),'new_font_offset':hex(font_start),'new_width_offset':hex(width_start),'updated_pointer_offsets':[hex(o) for o in sorted(writes)],'translated_records':len(entries),'catalog_records':len(items),'all_records_roundtrip_pass':True,'bps_self_apply_pass':True,'layout':layout,'relocations':relocations}
    report['terminology_label_checks']=terminology_checks
    report['affected_shared_page_aliases']=affected_aliases
    report['native_help_size_allowances']=[{'id':e['id'],'encoded_bytes':len(encoded[e['id']]),'native_bytes':items[e['id']]['obj'].raw_len}for e in entries if len(encoded[e['id']])>512]
    report['status_graphics']=graphics_report
    report['ui_heading_graphics']=ui_graphics_report
    report['mission_graphics']=mission_graphics_report
    report['roster_graphics']=roster_graphics_report
    report['ability_type_graphics']=ability_type_report
    report['battle_popup_graphics']=battle_popup_report
    report['calendar_graphics']=calendar_graphics_report
    report['battle_goal_graphics']=battle_goal_report
    report['battle_result_graphics']=battle_result_report
    report['ready_caption_graphics']=ready_caption_report
    report['save_counter_graphics']=save_counter_report
    report['map_alert_graphics']=map_alert_report
    report['title_menu_graphics']=title_menu_report
    report['title_credit_graphics']=title_credit_report
    report['map_location_graphics']=map_location_report
    report['law_panel_graphics']=law_panel_report
    report['world_hud_graphics']=world_hud_report
    report['equipment_button_graphics']=equipment_button_report
    report['world_button_graphics']=world_button_report
    report['compact_ui_glyphs']=len(ALPHABET)if compact_sheet is not None else 0
    report['added_glyphs']=len(newwidths)
    report['text_header_metadata_preserved']=True
    report['translated_headers_with_upper_metadata']=sum(items[k]['line'] is not None and bool(items[k]['line'].U16(0)&0xff00)for k in tokens)
    (a.out/'build.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ('layout','relocations')},ensure_ascii=True))
if __name__=='__main__':main()

