"""Verify graphics decoding against a private read-only mGBA memory dump.

The report contains offsets/hashes only, never original graphic data.
"""
import argparse,hashlib,json,struct
from pathlib import Path
import project
from ffta_a7 import decode_archive

def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--memory',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    raw=a.rom.read_bytes();assert project.digest(raw)==project.SHA
    video=(a.memory/'map-06000000.bin').read_bytes();io=(a.memory/'map-04000000.bin').read_bytes()
    assert len(video)==0x18000 and len(io)==0x400
    chunks=decode_archive(raw,0x3a9ca4);decoded=b''.join(c['data']for c in chunks)
    match=decoded==video[0x8a40:0x8a40+len(decoded)]
    assert len(chunks)==33 and len(decoded)==2112 and match,'Use the documented ROM 0.8 status state'
    backgrounds=[]
    for i in range(4):
        cnt=struct.unpack_from('<H',io,8+i*2)[0]
        backgrounds.append({'bg':i,'control':hex(cnt),'char_base_vram_offset':hex(((cnt>>2)&3)*0x4000),
                            'map_vram_offset':hex(((cnt>>8)&31)*0x800),'size_code':cnt>>14})
    archives=[];offset=0
    while True:
        offset=raw.find(b'A7',offset)
        if offset<0:break
        try:
            found=decode_archive(raw,offset);data=b''.join(c['data']for c in found)
            archives.append({'offset':hex(offset),'chunks':len(found),'decoded_bytes':len(data),'decoded_sha256':hashlib.sha256(data).hexdigest()})
        except ValueError:pass
        offset+=2
    report={'clean_rom_sha256':project.SHA,'scope':'Known ROM 0.8 status-state memory, compared to clean USA graphics; no ROM changes',
            'format':'A7, dictionary types 0 and 3 only','local_code_provenance':['0x08005318','0x080051c4'],
            'verified_archive':{'rom_offset':'0x3a9ca4','chunks':33,'decoded_bytes':2112,'vram_offset':'0x8a40','exact_match':match,'sha256':hashlib.sha256(decoded).hexdigest()},
            'backgrounds':backgrounds,'decodable_archives':archives,'status_label_source_offsets_verified':False,
            'new_catalog_ids':0,'rom_or_patch_created':False}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'verified_graphics_bytes':len(decoded),'exact_match':match,'decodable_archives':len(archives),'rom_or_patch_created':False}))

if __name__=='__main__':main()
