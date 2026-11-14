"""Prepare private Russian floating battle graphics from verified OAM material spans.

Only pixel data changes. Numeric/JP tiles, modifier icons, material geometry and
animation tables are preserved. Authored text is projected back through a compact
full-coverage material frame; the inverse composition is checked exactly.
"""
import argparse,collections,hashlib,json,struct
from pathlib import Path
from ffta_a7 import decode_archive,encode_literal_archive
FONT={
'А':'010/101/111/101/101','Б':'111/100/111/101/111','В':'110/101/110/101/110','Г':'111/100/100/100/100','Д':'011/011/011/111/101','Е':'111/100/110/100/111','Ж':'101/111/010/111/101','З':'110/001/010/001/110','И':'101/101/111/101/101','Й':'101/010/101/111/101','К':'101/110/100/110/101','Л':'011/101/101/101/101','М':'101/111/111/101/101','Н':'101/101/111/101/101','О':'010/101/101/101/010','П':'111/101/101/101/101','Р':'110/101/110/100/100','С':'011/100/100/100/011','Т':'111/010/010/010/010','У':'101/101/111/001/110','Ф':'010/111/111/010/010','Х':'101/101/010/101/101','Ц':'101/101/101/111/001','Ч':'101/101/111/001/001','Ш':'10101/10101/10101/10101/11111','Щ':'10101/10101/10101/11111/00001','Ы':'10001/10001/11001/10101/11001','Ь':'100/100/110/101/110','Я':'011/101/011/101/101',
'Ю':'10110/11001/11001/11001/10110',' ':'00/00/00/00/00','.':'0/0/0/0/1','!':'1/1/1/0/1','%':'101/001/010/100/101',
}
SIZES=[[(8,8),(16,16),(32,32),(64,64)],[(16,8),(32,8),(32,16),(64,32)],[(8,16),(8,32),(16,32),(32,64)]]
# source tile interval, Russian compact rendering. Names are display forms.
WORDS={2:[(0,4,'ЛЕЧЕНИЕ')],3:[(0,4,'СНЯТО')],4:[(0,4,'АТАКА')],5:[(0,4,'АТАКА')],6:[(0,4,'ЗАЩИТА')],7:[(0,4,'ЗАЩИТА')],8:[(0,4,'СКОР.')],9:[(0,3,'МЕДЛ.')],10:[(0,4,'СТОП')],11:[(0,3,'УСКОР.')],12:[(0,6,'НОКАУТ')],13:[(0,5,'СДВИГ')],14:[(0,4,'НОРМА'),(4,8,'НОРМА')],15:[(0,4,'КРИТ.'),(4,6,'РОСТ')],16:[(0,4,'В САМУЮ'),(4,8,'ТОЧКУ!')],17:[(0,6,'ПОЙМАН!')],18:[(0,3,'СКРЫТ')],19:[(0,4,'СЛОМАНО'),(4,8,'СЛОМАНО')],20:[(0,4,'КРИТИЧ.')],21:[(0,2,'МИМО')],22:[(0,6,'ОТРАВА')],23:[(0,4,'УРОВ.'),(5,8,'ВЫШЕ')],24:[(0,4,'МАГИЯ')],25:[(0,4,'МАГИЯ')]}

def material_frames(raw,ident):
 anim,material,start,size=struct.unpack_from('<IIHH',raw,0x3943fc+12*ident);base=material-0x08000000;first=struct.unpack_from('<I',raw,base)[0];assert first%4==0 and 0<first<1024
 offsets=struct.unpack_from('<'+'I'*(first//4),raw,base);assert list(offsets)==sorted(offsets)
 frames=[]
 for off in offsets:
  pos=base+off;count=struct.unpack_from('<H',raw,pos)[0];assert count<64;parts=[]
  for i in range(count):
   a,b,c=struct.unpack_from('<HHH',raw,pos+2+6*i);assert a>>14<3 and not a&0x2100
   w,h=SIZES[a>>14][b>>14];tile=c&1023;assert tile+w*h//64<=size//32
   x=b&511;x=x-512 if x>=256 else x;y=a&255;y=y-256 if y>=128 else y
   parts.append(dict(x=x,y=y,w=w,h=h,tile=tile,hflip=bool(b&0x1000),vflip=bool(b&0x2000),palette=c>>12))
  frames.append(parts)
 return start,size,frames

def mapping(parts,start):
 positions=collections.defaultdict(list);refs=set()
 for part in parts:
  for y in range(part['h']):
   for x in range(part['w']):
    tx=part['w']-1-x if part['hflip']else x;ty=part['h']-1-y if part['vflip']else y
    tile=start+part['tile']+(ty//8)*(part['w']//8)+tx//8;ref=tile*64+(ty%8)*8+tx%8
    positions[part['x']+x,part['y']+y].append(ref);refs.add(ref)
 return positions,refs

def make_bank(raw,repair_poison=False,preserve_knockout=False):
 original=b''.join(x['data']for x in decode_archive(raw,0x3bc898));assert len(original)==5440;pixels=[c for b in original for c in(b&15,b>>4)];authored=list(pixels);rows=[];allowed=set()
 for ident,groups in WORDS.items():
  start,size,frames=material_frames(raw,ident)
  for lo,hi,text in groups:
   selected=[[p for p in frame if lo<=p['tile'] and p['tile']+p['w']*p['h']//64<=hi]for frame in frames];allrefs=set().union(*(mapping(ps,start)[1]for ps in selected));assert allrefs
   candidates=[]
   for index,ps in enumerate(selected):
    pos,refs=mapping(ps,start)
    if refs!=allrefs:continue
    xs=[x for x,y in pos];ys=[y for x,y in pos];box=(min(xs),min(ys),max(xs)+1,max(ys)+1);
    label_width=sum(len(FONT[c].split('/')[0])+1 for c in text)-1
    if box[2]-box[0]>=label_width and box[3]-box[1]>=5:candidates.append(((box[3]-box[1])*10000+(box[2]-box[0]),index,pos,refs,box))
   assert candidates,('No full material anchor',ident,lo,hi)
   _,frame,pos,refs,box=min(candidates,key=lambda c:(c[0],-c[1]));assert not allowed&refs,('Shared text pixel across groups',ident);allowed|=refs
   # 3x5 authored letters with one-pixel black outline, original dominant body color.
   width=sum(len(FONT[c].split('/')[0])+1 for c in text)-1;ink=[];x=0
   for c in text:
    ink.extend((x+xx,y)for y,row in enumerate(FONT[c].split('/'))for xx,v in enumerate(row)if v=='1');x+=len(FONT[c].split('/')[0])+1
   body_color=collections.Counter(pixels[r]for r in refs if pixels[r]not in(0,1)).most_common(1)[0][0]
   options=[]
   for y0 in range(box[1],box[3]-4):
    for x0 in range(box[0],box[2]-width+1):
     body={(x+x0,y+y0)for x,y in ink}
     if not body<=pos.keys():continue
     desired={xy:0 for xy in pos}
     for x,y in body:
      for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
       if(x+dx,y+dy)in desired:desired[x+dx,y+dy]=1
     for xy in body:desired[xy]=body_color
     score=abs((x0+width/2)-(box[0]+box[2])/2)+abs((y0+2.5)-(box[1]+box[3])/2);options.append((score,desired,x0,y0))
   assert options,('Russian label cannot fit native material',ident,text,box,width)
   _,desired,x0,y0=min(options,key=lambda x:x[0]);trial={ref:0 for ref in refs}
   for xy,color in desired.items():
    if color:trial[pos[xy][0]]=color
   # First opaque OAM piece wins; zero is transparent.
   composed={xy:next((trial[r]for r in rr if trial[r]),0)for xy,rr in pos.items()}
   assert composed==desired,('Inverse material alias conflict',ident,text)
   for ref,color in trial.items():authored[ref]=color
   rows.append({'id':ident,'source_tiles':[lo,hi],'ru':text,'anchor_frame':frame,'native_bounds':box,'text_origin':[x0,y0],'source_pixel_count':len(refs),'body_color_index':body_color,'inverse_composition_exact':True})
 # Miss! reuses its s tile twice. Clear that repeated tile; keep original !.
 miss_start=material_frames(raw,21)[0]
 for ref in range((miss_start+2)*64,(miss_start+3)*64):authored[ref]=0;allowed.add(ref)
 level_start=material_frames(raw,23)[0]
 for ref in range((level_start+4)*64,(level_start+5)*64):authored[ref]=0;allowed.add(ref)
 if repair_poison:
  # Poison animates six separate 8x8 letters at changing, overlapping x/y.
  # A whole-word projection at one anchor splits letters in other frames.
  # Two independent glyphs fit the first two native letter slots in every frame.
  poison_start=material_frames(raw,22)[0]
  color=next(r['body_color_index']for r in rows if r['id']==22)
  for ref in range(poison_start*64,(poison_start+6)*64):authored[ref]=0;allowed.add(ref)
  for tile,c in enumerate('ЯД'):
   body={(x+1,y+1)for y,row in enumerate(FONT[c].split('/'))for x,v in enumerate(row)if v=='1'}
   for x,y in body:
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
     xx,yy=x+dx,y+dy
     if 0<=xx<8 and 0<=yy<8:authored[(poison_start+tile)*64+yy*8+xx]=1
   for x,y in body:authored[(poison_start+tile)*64+y*8+x]=color
  for row in rows:
   if row['id']==22:row.update(ru='ЯД',independent_letter_slots=True,all_animation_frames_review_required=True)
 if preserve_knockout:
  knockout_start,knockout_size,_=material_frames(raw,12)
  for ref in range(knockout_start*64,(knockout_start+knockout_size//32)*64):authored[ref]=pixels[ref]
  for row in rows:
   if row['id']==12:row.update(ru='KO',original_knockout_marker_preserved=True)
 result=bytes(authored[i]|authored[i+1]<<4 for i in range(0,len(authored),2));assert result[:10*32]==original[:10*32]and result[162*32:]==original[162*32:]
 assert all(a==b or i in allowed for i,(a,b)in enumerate(zip(pixels,authored)))
 return result,rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(raw).hexdigest()=='43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19';bank,rows=make_bank(raw);payload=encode_literal_archive([bank[i:i+64]for i in range(0,len(bank),64)]);assert b''.join(x['data']for x in decode_archive(payload))==bank;a.out_private.mkdir(parents=True,exist_ok=True);(a.out_private/'battle-ru.a7').write_bytes(payload);report={'source_archive':'0x3bc898','source_literal':'0xa8bbc','descriptors':'0x3943fc','word_groups':len(rows),'label_ids':24,'numeric_and_JP_tiles_unchanged':True,'modifier_icons_preserved':True,'material_and_animation_data_unchanged':True,'payload_bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'native_verified':False,'entries':rows};a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Prepared battle graphics',len(rows),'groups')
if __name__=='__main__':main()
