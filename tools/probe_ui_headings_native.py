"""Execute all 32 nonempty native heading selectors in isolated mGBA states.

Calls the original loader/A7 decoder/VRAM transfer, including selector30's two
blocks. These frozen states are diagnostics, not gameplay or user save files.
"""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
from prepare_ui_headings import chunks,SELECTORS
CORE_SHA='3b5e74404a39b3b8b2a285843a4dcdbb3fc975e92fea8f9dd90bd6b98fb452e0'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for k in ('rom','state','core','out-private','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();assert sha(a.core)==CORE_SHA;original=a.state.read_bytes();assert struct.unpack_from('<I',original)[0]==0x0100000b
 a.out_private.mkdir(parents=True,exist_ok=True);data=chunks();rows=[];w=0x21000
 for index in range(1,33):
  s=bytearray(original);guard=b'HEADING-GUARD123';assert len(guard)==16
  s[w+0x3bff0:w+0x3c000]=guard;s[w+0x3c000:w+0x3c0c0]=b'\xcc'*192;s[w+0x3c0c0:w+0x3c0d0]=guard
  stub=bytes.fromhex('014801210160fee7')+struct.pack('<I',0x0203f100);s[w+0x3f000:w+0x3f000+len(stub)]=stub;s[w+0x3f100:w+0x3f104]=bytes(4)
  for reg,value in [(0,0x0203c000),(1,0),(2,index),(13,0x03007e00),(14,0x0203f001),(15,0x08018526)]:struct.pack_into('<I',s,0x20+reg*4,value)
  struct.pack_into('<I',s,0x60,0xff);struct.pack_into('<II',s,0x2f8,0,0);struct.pack_into('<I',s,0x31c,struct.unpack_from('<I',s,0x31c)[0]&~13);struct.pack_into('<I',s,0x324,0);struct.pack_into('<H',s,0x608,0)
  for off in (0xba,0xc6,0xd2,0xde):struct.pack_into('<H',s,0x400+off,0)
  assert len(s)==len(original);dest=a.out_private/str(index);dest.mkdir(exist_ok=True);state=dest/'DO-NOT-PLAY.state';state.write_bytes(s)
  args=[sys.executable,str(Path(__file__).with_name('emulate.py')),str(a.rom),'--core',str(a.core),'--load-state',str(state),'--actions','3','--out',str(dest/'run'),'--memory-out',str(dest/'memory'),'--save-state',str(dest/'after.state')]
  subprocess.run(args,check=True,capture_output=True,text=True);m=(dest/'memory/map-02000000.bin').read_bytes();v=(dest/'memory/map-06000000.bin').read_bytes();after=(dest/'after.state').read_bytes()
  assert struct.unpack_from('<I',m,0x3f100)[0]==1 and struct.unpack_from('<I',after,0x54)[0]==0x03007e00
  assert m[0x3bff0:0x3c000]==guard and m[0x3c0c0:0x3c0d0]==guard
  width,offset,chunk=SELECTORS[index];expected=data[chunk][offset*32:(offset+width)*32]if index!=30 else data[27][:96]+data[18][:96]
  assert len(expected)==width*32
  assert v[0x8000:0x8000+len(expected)]==expected,('Native VRAM mismatch',index)
  before=original[0x1000:0x19000];assert v[:0x8000]==before[:0x8000]and v[0x8000+len(expected):]==before[0x8000+len(expected):]
  rows.append({'selector':index,'chunk':chunk,'offset_tiles':offset,'width_tiles':width,'vram_exact':True,'vram_outside_span_unchanged':True,'scratch_guards_preserved':True,'returned':True})
 assert a.state.read_bytes()==original
 report={'passed':True,'selectors':32,'native_loader':'0x08018524','archive_decoder':'0x08005318','core_sha256':CORE_SHA,'rom_sha256':sha(a.rom),'input_state_sha256':hashlib.sha256(original).hexdigest(),'original_state_unchanged':True,'scope':'Native loader, authored A7, source selector dimensions and VRAM transfer. Frozen diagnostic states, no game progression or window positioning proof. Ordinary windows tested separately.','cases':rows}
 a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k!='cases'}))
if __name__=='__main__':main()

