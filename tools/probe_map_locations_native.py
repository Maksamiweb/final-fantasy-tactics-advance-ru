"""Isolated native A7 decoding of the full map archive and each30-place selector.

Does not unlock locations or claim a playthrough to all30 map positions.
"""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
from ffta_a7 import decode_archive
from prepare_map_locations import WIDTH_TABLE,OFFSET_TABLE
CORE_SHA='3b5e74404a39b3b8b2a285843a4dcdbb3fc975e92fea8f9dd90bd6b98fb452e0'
def main():
 p=argparse.ArgumentParser()
 for key in('rom','state','core','out-private','report'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(a.core.read_bytes()).hexdigest()==CORE_SHA;ptr=struct.unpack_from('<I',raw,0x36760)[0];assert ptr==struct.unpack_from('<I',raw,0x369a8)[0];blocks=[x['data']for x in decode_archive(raw,ptr-0x08000000)];codes=raw[WIDTH_TABLE:WIDTH_TABLE+30];offsets=struct.unpack_from('<30H',raw,OFFSET_TABLE);original=a.state.read_bytes();assert struct.unpack_from('<I',original)[0]==0x0100000b;results=[]
 cases=[('all',0,0,b''.join(blocks))]+[(str(i),offsets[i]//2,5+codes[i],b''.join(blocks[offsets[i]//2:offsets[i]//2+5+codes[i]]))for i in range(30)]
 for name,start,count,expected in cases:
  assert 0<len(expected)<0xb000;s=bytearray(original);w=0x21000;dst=0x30000;guard=b'MAPLABEL-GUARD16';assert len(guard)==16;s[w+dst-16:w+dst]=guard;s[w+dst:w+dst+len(expected)]=b'\xcc'*len(expected);s[w+dst+len(expected):w+dst+len(expected)+16]=guard
  stub=bytes.fromhex('014801210160fee7')+struct.pack('<I',0x0203f100);s[w+0x3f000:w+0x3f000+len(stub)]=stub;s[w+0x3f100:w+0x3f104]=bytes(4)
  for reg,value in [(0,ptr),(1,0x02030000),(2,start),(3,count),(13,0x03007e00),(14,0x0203f001),(15,0x0800531a)]:struct.pack_into('<I',s,0x20+reg*4,value)
  struct.pack_into('<I',s,0x60,0xff);struct.pack_into('<II',s,0x2f8,0,0);struct.pack_into('<I',s,0x31c,struct.unpack_from('<I',s,0x31c)[0]&~13);struct.pack_into('<I',s,0x324,0);struct.pack_into('<H',s,0x608,0)
  for off in(0xba,0xc6,0xd2,0xde):struct.pack_into('<H',s,0x400+off,0)
  out=a.out_private/name;out.mkdir(parents=True,exist_ok=True);state=out/'DO-NOT-PLAY.state';assert len(s)==len(original);state.write_bytes(s)
  subprocess.run([sys.executable,str(Path(__file__).with_name('emulate.py')),str(a.rom),'--core',str(a.core),'--load-state',str(state),'--actions','3','--out',str(out/'run'),'--memory-out',str(out/'memory'),'--save-state',str(out/'after.state')],check=True,capture_output=True)
  m=(out/'memory/map-02000000.bin').read_bytes();after=(out/'after.state').read_bytes();assert m[dst:dst+len(expected)]==expected and m[dst-16:dst]==guard and m[dst+len(expected):dst+len(expected)+16]==guard;assert struct.unpack_from('<I',m,0x3f100)[0]==1 and struct.unpack_from('<I',after,0x54)[0]==0x03007e00;assert after[0x1000:0x19000]==original[0x1000:0x19000];results.append({'selector':name,'start_chunk':start,'count_arg':count,'bytes':len(expected),'exact':True,'guards_and_stack_preserved':True})
 assert a.state.read_bytes()==original;r={'rom_sha256':hashlib.sha256(raw).hexdigest(),'core_sha256':CORE_SHA,'all_archive_and30_selectors_pass':True,'cases':results,'scope':'Isolated original A7 decoder for full archive and native start/count tables; no unlock/progression to all30 locations. Ordinary Sprohm/Giza views checked separately.'};a.report.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print('Native map archive and all30 selectors exact')
if __name__=='__main__':main()
