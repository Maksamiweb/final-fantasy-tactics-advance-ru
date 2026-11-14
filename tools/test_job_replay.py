"""Explicit native job/ability replay on private copies of the reported battery.

The report records inputs and asserts battery isolation/gil. Screenshots must be
reviewed for job identity, assigned ability and layout; this is not a full game test.
"""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
from test_shop_replay import SAVE_SHA

def main():
    p=argparse.ArgumentParser()
    for name in ('rom','battery','core','out-private','report'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();battery=a.battery.read_bytes();assert hashlib.sha256(battery).hexdigest()==SAVE_SHA
    a.out_private.mkdir(parents=True,exist_ok=True);copy=a.out_private/'input-copy.sav';assert copy.resolve()!=a.battery.resolve();copy.write_bytes(battery)
    stages=[];runner=Path(__file__).with_name('emulate.py')
    def run(name,actions,previous=None,battery_in=None,battery_out=None):
        out=a.out_private/name;state=a.out_private/(name+'.state')
        args=[sys.executable,str(runner),str(a.rom),'--core',str(a.core),'--sram-in',str(battery_in or copy),'--out',str(out),'--actions',actions,'--save-state',str(state),'--memory-out',str(out/'memory')]
        if previous:args+=['--load-state',str(a.out_private/(previous+'.state'))]
        if battery_out:args+=['--sram-out',str(battery_out)]
        result=subprocess.run(args,check=True,capture_output=True,text=True);stages.append({'stage':name,**json.loads(result.stdout)})
    boot='600,START:8,180,START:8,180,A:8,180,A:8,180,A:8,180'
    run('world',boot);run('roster','START:8,120,A:8,120','world');run('unit-menu','A:8,120','roster')
    run('abilities','DOWN:8,30,A:8,120','unit-menu');run('details','R:8,120','abilities');run('detail-help','SELECT:8,120','details')
    run('ability-list','A:8,120','abilities');run('item-set','A:8,120','ability-list');run('after-set','B:8,120','item-set')
    run('jobs','DOWN:8,20,A:8,120','after-set');run('thief','RIGHT:8,240,A:8,360,B:8,180','jobs');run('exit-units','B:8,120,B:8,120','thief')
    run('save-prompt','START:8,120,DOWN:8,20,DOWN:8,20,A:8,120,A:8,120,A:8,120','exit-units')
    written=a.out_private/'jobs-and-item.sav';run('saved','LEFT:8,30,A:8,300,A:8,120','save-prompt',battery_out=written)
    assert written.read_bytes()!=battery
    run('reloaded',boot,battery_in=written);run('reloaded-roster','START:8,120,A:8,120','reloaded',battery_in=written)
    run('reloaded-unit','A:8,120','reloaded-roster',battery_in=written);run('reloaded-abilities','DOWN:8,30,A:8,120','reloaded-unit',battery_in=written)
    run('restored-soldier','A:8,120,LEFT:8,240,A:8,360,B:8,180','thief')
    run('numou-unit','DOWN:8,30,A:8,120','roster');run('ukrot','DOWN:8,20,DOWN:8,20,A:8,120,LEFT:8,180','numou-unit')
    run('viera-unit','DOWN:8,30,RIGHT:8,30,A:8,120','roster');run('fencer','DOWN:8,20,DOWN:8,20,A:8,120,RIGHT:8,180','viera-unit')
    memory=(a.out_private/'reloaded/memory/map-02000000.bin').read_bytes();gil=struct.unpack_from('<I',memory,0x1f64)[0];assert gil==5000
    assert copy.read_bytes()==battery and a.battery.read_bytes()==battery
    assert len({r['rom_sha256']for r in stages})==1
    report={'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),'source_battery_sha256':SAVE_SHA,'source_battery_unchanged':True,'game_battery_written_and_fresh_booted':True,'reload_gil':gil,'visual_review_required':True,'visual_review_scope':['Soldier->Thief','secondary Item assigned','Thief and Item retained after fresh battery boot','back to Soldier','Fencer/Beastmaster abbreviation frames','ability slot/list/detail/help text'],'scope':'Pinned early save, three races and selected screens; AP acquisition, advanced unlocks and all battle effects are not tested.','stages':stages}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k not in ('stages','visual_review_scope')}))

if __name__=='__main__':main()
