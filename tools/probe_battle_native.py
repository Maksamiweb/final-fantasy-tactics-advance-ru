"""Isolated native battle-table branch probe, not a playable battle/save.

Starts after the allocator at each LDR r1, runs the original decoder and branch
completion, then returns to a marker loop. No ROM, user save or input state edits.
Only pinned USA/mGBA layouts are supported. Input ID16 has no dynamic arguments.
"""
import argparse,contextlib,hashlib,io,json,struct,subprocess,sys
from pathlib import Path
import project
CORE_SHA='3b5e74404a39b3b8b2a285843a4dcdbb3fc975e92fea8f9dd90bd6b98fb452e0'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for k in ('rom','source-rom','state','core','upstream','translation','catalog','out-private','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();assert sha(a.core)==CORE_SHA and sha(a.source_rom)==project.SHA
 original=a.state.read_bytes();assert struct.unpack_from('<I',original)[0]==0x0100000b
 a.out_private.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(a.upstream.resolve()));import ffta_sect as parser
 with contextlib.redirect_stdout(io.StringIO()):obj=parser.c_ffta_sect_text_buf(bytes([0]),0);obj.parse_size(None,1);obj.parse()
 chars=json.loads((a.upstream/'charset_us.json').read_text(encoding='utf8'))[0];rev={v:int(k)for k,v in reversed(list(chars.items()))if len(v)==1};rev.update({c:project.COUNT+i for i,c in enumerate(project.ALPHABET)})
 translated=next(e for e in json.loads(a.translation.read_text(encoding='utf8'))['entries']if e['id']=='pages:battle/16')
 source=json.loads(a.catalog.read_text(encoding='utf8'))['entries']['pages:battle/16']
 rows=[]
 for variant,rom,tokens in [('source',a.source_rom,source['tokens']),('russian',a.rom,project.encode(translated['ru'],rev))]:
  expected=bytes(obj._encode(tokens));assert len(expected)<128
  # The native decoder expands half-width source glyphs into full token form.
  expected=bytes(obj._encode([('CHR_FULL',v)if k.startswith('CHR')else(k,v)for k,v in tokens]))
  for name,flag,pc in [('mask-7fff',0x8000,0x080274a4),('mask-3fff',0x4000,0x08027440)]:
   w=0x21000;s=bytearray(original);s[w+0x3c000:w+0x3c600]=bytes(0x600)
   struct.pack_into('<I',s,w+0x3c094,0x0203c300);struct.pack_into('<I',s,w+0x3c500,0x0203c400);struct.pack_into('<H',s,w+0x3c40c,flag|16)
   guard=b'BATTLE-GUARD-123';s[w+0x3c0f0:w+0x3c100]=guard;s[w+0x3c200:w+0x3c210]=guard;s[w+0x3c100:w+0x3c200]=b'\xcc'*256
   stub=bytes.fromhex('014801210160fee7')+struct.pack('<I',0x0203f100);s[w+0x3f000:w+0x3f000+len(stub)]=stub;s[w+0x3f100:w+0x3f104]=bytes(4)
   struct.pack_into('<I',s,0x19000+0x7d20,0x0203f001)
   for reg,value in [(0,0x0203c100),(6,0),(7,0x0203c000),(8,0x0203c080),(9,0x0203c500),(13,0x03007d00),(14,0x0203f001),(15,pc+2)]:struct.pack_into('<I',s,0x20+reg*4,value)
   struct.pack_into('<I',s,0x60,0xff);struct.pack_into('<II',s,0x2f8,0,0);struct.pack_into('<I',s,0x31c,struct.unpack_from('<I',s,0x31c)[0]&~13);struct.pack_into('<I',s,0x324,0);struct.pack_into('<H',s,0x608,0)
   for off in (0xba,0xc6,0xd2,0xde):struct.pack_into('<H',s,0x400+off,0)
   dest=a.out_private/(variant+'-'+name);dest.mkdir(exist_ok=True);state=dest/'DO-NOT-PLAY.state';assert len(s)==len(original),'Diagnostic state length changed'
   state.write_bytes(s)
   args=[sys.executable,str(Path(__file__).with_name('emulate.py')),str(rom),'--core',str(a.core),'--load-state',str(state),'--actions','3','--out',str(dest/'run'),'--memory-out',str(dest/'memory'),'--save-state',str(dest/'after.state')]
   completed=subprocess.run(args,check=True,capture_output=True,text=True);m=(dest/'memory/map-02000000.bin').read_bytes();after=(dest/'after.state').read_bytes()
   assert struct.unpack_from('<I',m,0x3f100)[0]==1,'Branch did not return'
   assert struct.unpack_from('<I',after,0x54)[0]==0x03007d24,'Wrong restored stack'
   assert m[0x3c080:0x3c084]==bytes.fromhex('02001800')and struct.unpack_from('<I',m,0x3c300)[0]==16
   assert m[0x3c0f0:0x3c100]==guard and m[0x3c200:0x3c210]==guard
   actual=m[0x3c100:0x3c100+len(expected)];assert actual==expected,(variant,name,actual.hex(),expected.hex())
   assert m[0x3c100+len(expected):0x3c180]==b'\xcc'*(128-len(expected))
   rows.append({'variant':variant,'branch':name,'native_entry':hex(pc),'rom_sha256':sha(rom),'output_exact':True,'bytes':len(expected),'return_marker':1,'guards_preserved':True,'state_mode_and_masked_id_correct':True,'core_run':json.loads(completed.stdout)})
 assert a.state.read_bytes()==original
 report={'scope':'Isolated original LDR/decoder/completion branch execution. Allocator and prefix formatting intentionally bypassed; not gameplay, rendering, dynamic substitutions, battle timing or save compatibility. No ROM changed.','id':'pages:battle/16','russian_text':translated['ru'],'source_text':source['source'],'core_sha256':CORE_SHA,'input_state_sha256':hashlib.sha256(original).hexdigest(),'input_state_unchanged':True,'cases':rows,'passed':True}
 a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':True,'cases':len(rows),'scope':report['scope']}))
if __name__=='__main__':main()
