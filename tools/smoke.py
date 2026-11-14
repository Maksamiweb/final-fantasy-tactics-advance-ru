"""Replay boot, opening, name confirmation and tutorial options. Captures require visual QA.

Save-states are local test checkpoints; this does NOT validate in-game saves.
"""
import argparse,json,subprocess,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--core',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    stages=[
        ('boot','1800,START:1,240,A:1,3600,START:1,240,A:1,3600,A:8,240,A:8,240,A:8,240',1),
        ('name',','.join(['A:8,180']*40),20),
        ('confirm',','.join(['B:8,20']*5)+',START:8,60,LEFT:8,30,A:8,600',1),
        ('tutorial',','.join(['A:8,180']*40),20),
        ('help','600,A:8,120,A:8,120,A:8,120,A:8,120,START:8,120',1),
        ('options','B:8,60,START:8,60,DOWN:8,30,A:8,120',1),
    ]
    previous=None;results=[]
    for name,actions,every in stages:
        args=[sys.executable,str(Path(__file__).with_name('emulate.py')),str(a.rom),'--core',str(a.core),'--out',str(a.out/name),'--actions',actions,'--capture-every',str(every),'--save-state',str(a.out/(name+'.state'))]
        if previous:args+=['--load-state',str(previous)]
        completed=subprocess.run(args,check=True,capture_output=True,text=True)
        result=json.loads(completed.stdout);results.append({'stage':name,**result});previous=a.out/(name+'.state');print(name,'completed',flush=True)
    assert len({r['rom_sha256'] for r in results})==1,'ROM changed during test'
    (a.out/'smoke.json').write_text(json.dumps({'visual_review_required':True,'in_game_save_tested':False,'stages':results},indent=2))
if __name__=='__main__':main()
