"""Isolated native A7 decode of all combat popup tiles; not game progression."""
import argparse,struct,hashlib,json,subprocess,sys
from pathlib import Path

from ffta_a7 import decode_archive
CORE_SHA='3b5e74404a39b3b8b2a285843a4dcdbb3fc975e92fea8f9dd90bd6b98fb452e0'
def main():
 p=argparse.ArgumentParser()
 for k in ('rom','state','core','out-private','report'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();raw=a.rom.read_bytes();assert hashlib.sha256(a.core.read_bytes()).hexdigest()==CORE_SHA;ptr=struct.unpack_from('<I',raw,0xa8bbc)[0];blocks=decode_archive(raw,ptr-0x08000000);expected=b''.join(x['data']for x in blocks);assert len(blocks)==85 and len(expected)==5440
 original=a.state.read_bytes();s=bytearray(original);w=0x21000;assert struct.unpack_from('<I',s)[0]==0x0100000b;guard=b'CALENDAR-GUARD12';assert len(guard)==16
 s[w+0x3bff0:w+0x3c000]=guard;s[w+0x3c000:w+0x3d540]=b'\xcc'*5440;s[w+0x3d540:w+0x3d550]=guard
 stub=bytes.fromhex('014801210160fee7')+struct.pack('<I',0x0203f100);s[w+0x3f000:w+0x3f000+len(stub)]=stub;s[w+0x3f100:w+0x3f104]=bytes(4)
 for reg,value in [(0,ptr),(1,0x0203c000),(2,0),(3,0),(13,0x03007e00),(14,0x0203f001),(15,0x0800531a)]:struct.pack_into('<I',s,0x20+reg*4,value)
 struct.pack_into('<I',s,0x60,0xff);struct.pack_into('<II',s,0x2f8,0,0);struct.pack_into('<I',s,0x31c,struct.unpack_from('<I',s,0x31c)[0]&~13);struct.pack_into('<I',s,0x324,0);struct.pack_into('<H',s,0x608,0)
 for off in (0xba,0xc6,0xd2,0xde):struct.pack_into('<H',s,0x400+off,0)
 assert len(s)==len(original);a.out_private.mkdir(parents=True,exist_ok=True);state=a.out_private/'DO-NOT-PLAY.state';state.write_bytes(s)
 args=[sys.executable,str(Path(__file__).with_name('emulate.py')),str(a.rom),'--core',str(a.core),'--load-state',str(state),'--actions','3','--out',str(a.out_private/'run'),'--memory-out',str(a.out_private/'memory'),'--save-state',str(a.out_private/'after.state')];subprocess.run(args,check=True,capture_output=True,text=True)
 m=(a.out_private/'memory/map-02000000.bin').read_bytes();v=(a.out_private/'memory/map-06000000.bin').read_bytes();after=(a.out_private/'after.state').read_bytes();assert m[0x3c000:0x3d540]==expected and m[0x3bff0:0x3c000]==guard and m[0x3d540:0x3d550]==guard;assert struct.unpack_from('<I',m,0x3f100)[0]==1 and struct.unpack_from('<I',after,0x54)[0]==0x03007e00;assert v==original[0x1000:0x19000];assert a.state.read_bytes()==original
 report={'native_all_85_chunks_exact':True,'labels':24,'decoded_bytes':5440,'native_decoder':'0x08005318','source_pointer_fields':['0xa8bbc'],'rom_sha256':hashlib.sha256(raw).hexdigest(),'core_sha256':CORE_SHA,'guard_bytes_preserved':True,'input_state_unchanged':True,'vram_unchanged':True,'scope':'Isolated original A7 decoder for the full combat popup archive; not application of 24 effects in battle.'};a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
