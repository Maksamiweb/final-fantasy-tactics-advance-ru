"""Minimal libretro ctypes runner for local private ROM testing. Never sends ROM data."""
import argparse, ctypes as C, hashlib, json
from pathlib import Path
from PIL import Image

class Game(C.Structure):
    _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Info(C.Structure):
    _fields_=[('name',C.c_char_p),('version',C.c_char_p),('extensions',C.c_char_p),('fullpath',C.c_bool),('block_extract',C.c_bool)]
class Var(C.Structure):
    _fields_=[('key',C.c_char_p),('value',C.c_char_p)]

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--core',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--actions',default='600');p.add_argument('--load-state',type=Path);p.add_argument('--save-state',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    core=C.CDLL(str(a.core.resolve()));pixel=[0];frame=[None];keys=set();envlog=set();dirs=str(a.out.resolve()).encode();variables={}
    ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
    VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
    AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16);BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
    POLL=C.CFUNCTYPE(None);INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
    @ENV
    def env(cmd,ptr):
        if cmd in (9,30,31):C.cast(ptr,C.POINTER(C.c_char_p))[0]=dirs;return True
        if cmd==10:pixel[0]=C.cast(ptr,C.POINTER(C.c_int))[0];return pixel[0] in [0,1,2]
        if cmd==3:C.cast(ptr,C.POINTER(C.c_bool))[0]=False;return True
        if cmd==16:
            vs=C.cast(ptr,C.POINTER(Var));i=0
            while vs[i].key:
                val=vs[i].value.split(b'; ',1)[-1].split(b'|')[0];variables[vs[i].key]=val;i+=1
            return True
        if cmd==15:
            v=C.cast(ptr,C.POINTER(Var));v[0].value=variables.get(v[0].key);return bool(v[0].value)
        if cmd==17:C.cast(ptr,C.POINTER(C.c_bool))[0]=False;return True
        if cmd==18:C.cast(ptr,C.POINTER(C.c_bool))[0]=True;return True
        if cmd==39:C.cast(ptr,C.POINTER(C.c_uint))[0]=0x1ff;return True
        if cmd==47:C.cast(ptr,C.POINTER(C.c_uint))[0]=3;return True
        if cmd in (11,35):return True
        envlog.add(cmd);return False
    @VIDEO
    def video(data,w,h,pitch):
        if data:frame[0]=(C.string_at(data,pitch*h),w,h,pitch,pixel[0])
    audio=AUDIO(lambda l,r:None);batch=BATCH(lambda p,n:n);poll=POLL(lambda:None)
    inp=INPUT(lambda port,device,index,id:int(id in keys) if port==0 and device==1 else 0)
    for name,callback in [('environment',env),('video_refresh',video),('audio_sample',audio),('audio_sample_batch',batch),('input_poll',poll),('input_state',inp)]:
        getattr(core,'retro_set_'+name).argtypes=[type(callback)];getattr(core,'retro_set_'+name)(callback)
    core.retro_get_system_info.argtypes=[C.POINTER(Info)];info=Info();core.retro_get_system_info(C.byref(info));core.retro_init()
    rom=a.rom.read_bytes();buf=C.create_string_buffer(rom);game=Game(str(a.rom.resolve()).encode(),C.cast(buf,C.c_void_p),len(rom),None)
    core.retro_load_game.argtypes=[C.POINTER(Game)];core.retro_load_game.restype=C.c_bool
    assert core.retro_load_game(C.byref(game)),'load failed'
    core.retro_serialize_size.restype=C.c_size_t;core.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];core.retro_serialize.restype=C.c_bool
    core.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];core.retro_unserialize.restype=C.c_bool
    if a.load_state:
        state=a.load_state.read_bytes();sb=C.create_string_buffer(state);assert core.retro_unserialize(sb,len(state))
    buttons={'A':8,'B':0,'START':3,'SELECT':2,'UP':4,'DOWN':5,'LEFT':6,'RIGHT':7,'L':10,'R':11}
    count=0;captures=[]
    for step,act in enumerate(a.actions.split(',')):
        parts=act.split(':');n=int(parts[-1]);keys.clear()
        if len(parts)>1:keys.update(buttons[k] for k in parts[0].split('+'))
        for _ in range(n):core.retro_run();count+=1
        if frame[0]:
            raw,w,h,pitch,pf=frame[0]
            if pf==1:im=Image.frombytes('RGB',(w,h),raw,'raw','BGRX',pitch)
            else:
                pixels=[]
                for y in range(h):
                    for x in range(w):
                        v=int.from_bytes(raw[y*pitch+x*2:y*pitch+x*2+2],'little')
                        pixels.append((((v>>(11 if pf==2 else 10))&31)*255//31,((v>>5)&(63 if pf==2 else 31))*255//(63 if pf==2 else 31),(v&31)*255//31))
                im=Image.new('RGB',(w,h));im.putdata(pixels)
            dest=a.out/f'{step:02d}_{count}.png';im.save(dest);captures.append(dest.name)
    if a.save_state:
        n=core.retro_serialize_size();sb=C.create_string_buffer(n);assert core.retro_serialize(sb,n);a.save_state.write_bytes(sb.raw)
    result={'core':info.name.decode(),'version':info.version.decode(),'core_sha256':hashlib.sha256(a.core.read_bytes()).hexdigest(),'rom_sha256':hashlib.sha256(rom).hexdigest(),'frames':count,'actions':a.actions,'captures':captures,'unsupported_environment_commands':sorted(envlog),'pixel_format':pixel[0]}
    (a.out/'run.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    core.retro_unload_game();core.retro_deinit()
if __name__=='__main__':main()
