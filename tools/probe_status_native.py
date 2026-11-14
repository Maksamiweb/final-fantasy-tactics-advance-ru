"""Run the existing native decompressor and BIOS transfer in a diagnostic state.

No ROM changes. Diagnostic states overwrite scratch RAM and freeze the game;
they are NOT playable saves. Only the pinned ROM 0.8/core are supported.
"""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
from PIL import Image
from ffta_lzss import decompress
from prepare_status_graphics import LABELS

ROM_SHA='d9775a5ef83c68a17bd86be9251d96d33b5735ffc0df487e58919db9470db166'
CORE_SHA='3b5e74404a39b3b8b2a285843a4dcdbb3fc975e92fea8f9dd90bd6b98fb452e0'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--test-rom',type=Path,required=True);p.add_argument('--core',type=Path,required=True)
    p.add_argument('--status-state',type=Path,required=True);p.add_argument('--payload',type=Path,required=True);p.add_argument('--expected-bank',type=Path,required=True)
    p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--capture',type=Path);a=p.parse_args()
    assert sha(a.test_rom.read_bytes())==ROM_SHA and sha(a.core.read_bytes())==CORE_SHA
    original_state_sha=sha(a.status_state.read_bytes());payload=a.payload.read_bytes();expected=a.expected_bank.read_bytes()
    decoded,used=decompress(payload);assert decoded==expected and len(expected)==7264 and used==len(payload)
    assert len(payload)<0x10000
    a.out_private.mkdir(parents=True,exist_ok=True)
    baseline=a.out_private/'baseline';run=a.out_private/'run';baseline_state=baseline/'baseline.state';after_state=run/'after.state'
    assert a.status_state.resolve()not in (baseline_state.resolve(),after_state.resolve())
    runner=Path(__file__).with_name('emulate.py')
    def emulate(state,out,after,frames):
        subprocess.run([sys.executable,str(runner),str(a.test_rom),'--core',str(a.core),'--load-state',str(state),'--actions',str(frames),
                        '--out',str(out),'--memory-out',str(out/'memory'),'--save-state',str(after)],check=True,capture_output=True,text=True)
    emulate(a.status_state,baseline,baseline_state,1)
    state=bytearray(baseline_state.read_bytes());assert struct.unpack_from('<I',state)[0]==0x0100000b
    # Verify documented state offsets against independent memory-map dumps.
    for offset,length,name in [(0x1000,0x18000,'06000000'),(0x19000,0x8000,'03000000'),(0x21000,0x40000,'02000000')]:
        assert state[offset:offset+length]==(baseline/'memory'/('map-'+name+'.bin')).read_bytes()
    wram=0x21000;guard=b'GBA-GFX-GUARD!!!'
    state[wram+0x10000:wram+0x10000+len(payload)]=payload
    state[wram+0x18000:wram+0x18000+len(expected)]=b'\xcc'*len(expected)
    state[wram+0x18000-len(guard):wram+0x18000]=guard
    state[wram+0x18000+len(expected):wram+0x18000+len(expected)+len(guard)]=guard
    # Thumb return stub: CpuFastSet(WRAM output, VRAM+9280, 199*8 words),
    # write marker=1, then branch to itself. Literal pool is at +0x18.
    stub=bytes.fromhex('05480649c722d2000cdf054801210160fee7c04600000000')+struct.pack('<III',0x02018000,0x06009280,0x0200f100)
    state[wram+0xf000:wram+0xf000+len(stub)]=stub
    state[wram+0xf100:wram+0xf104]=b'\0'*4
    for reg,value in [(0,0x02018000),(1,0x02010000),(13,0x03007e00),(14,0x0200f001),(15,0x0800543e)]:
        struct.pack_into('<I',state,0x20+reg*4,value)
    struct.pack_into('<I',state,0x60,0xff) # Thumb system mode, IRQ/FIQ disabled
    struct.pack_into('<II',state,0x2f8,0,0) # refresh the decode/fetch pipeline
    flags=struct.unpack_from('<I',state,0x31c)[0]&~13
    struct.pack_into('<I',state,0x31c,flags);struct.pack_into('<I',state,0x324,0)
    struct.pack_into('<H',state,0x400+0x208,0) # IME
    for off in (0xba,0xc6,0xd2,0xde):struct.pack_into('<H',state,0x400+off,0)
    diagnostic=a.out_private/'diagnostic-DO-NOT-PLAY.state';diagnostic.write_bytes(state)
    emulate(diagnostic,run,after_state,3)
    memory=(run/'memory/map-02000000.bin').read_bytes();video=(run/'memory/map-06000000.bin').read_bytes();after=after_state.read_bytes()
    baseline_video=(baseline/'memory/map-06000000.bin').read_bytes()
    assert memory[0x18000:0x18000+len(expected)]==expected
    assert memory[0x18000-len(guard):0x18000]==guard and memory[0x18000+len(expected):0x18000+len(expected)+len(guard)]==guard
    assert int.from_bytes(memory[0xf100:0xf104],'little')==1
    assert memory[0x10000:0x10000+len(payload)]==payload
    assert struct.unpack_from('<I',after,0x54)[0]==0x03007e00 and struct.unpack_from('<I',after,0x5c)[0]==0x0200f012
    assert video[0x9280:0xab60]==expected[:199*32]
    assert video[:0x9280]==baseline_video[:0x9280] and video[0xab60:]==baseline_video[0xab60:]
    assert sha(a.status_state.read_bytes())==original_state_sha and sha(a.test_rom.read_bytes())==ROM_SHA
    before_image=Image.open(baseline/'00_1.png').convert('RGB');after_image=Image.open(run/'00_3.png').convert('RGB')
    assert before_image.size==after_image.size==(240,160)
    changed_pixels=outside_pixels=0
    for y in range(160):
        for x in range(240):
            if before_image.getpixel((x,y))!=after_image.getpixel((x,y)):
                changed_pixels+=1
                if not any(x0<=x<x1 and y0<=y<y1 for _,_,(x0,y0,x1,y1)in LABELS):outside_pixels+=1
    assert changed_pixels and outside_pixels==0,'Unexpected native-screen differences'
    if a.capture:
        a.capture.parent.mkdir(parents=True,exist_ok=True);a.capture.write_bytes((run/'00_3.png').read_bytes())
    report={'rom_sha256':ROM_SHA,'core_sha256':CORE_SHA,'original_status_state_sha256':original_state_sha,
            'native_function':'0x0800543c','input_ram':'0x02010000','output_ram':'0x02018000',
            'payload_bytes':len(payload),'native_decoded_bytes':len(expected),'native_output_sha256':sha(expected),
            'native_output_exact':True,'guards_preserved':True,'stack_restored':True,'return_marker':1,
            'vram_prefix_tiles':199,'vram_prefix_exact':True,'vram_outside_prefix_unchanged':True,
            'changed_screen_pixels':changed_pixels,'changed_screen_pixels_outside_label_rectangles':outside_pixels,
            'native_render_captured':bool(a.capture),'rom_or_patch_created':False,'original_rom_and_state_unchanged':True,
            'scope':'Isolated native codec and renderer probe using scratch RAM in a diagnostic state. No normal loader, gameplay, other-window or save-compatibility proof.'}
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))

if __name__=='__main__':main()
