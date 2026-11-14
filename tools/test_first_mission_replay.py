"""Explicit first-mission acceptance replay on a private copy of the early save.

Checks all condition-table consumers and the 300-gil fee. Captures need visual
review for the translated objective and the actual revised story lines.
"""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path
from test_shop_replay import SAVE_SHA

def main():
    p=argparse.ArgumentParser()
    for key in ('rom','battery','core','out-private','report'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();rom=a.rom.read_bytes();battery=a.battery.read_bytes();assert hashlib.sha256(battery).hexdigest()==SAVE_SHA
    fields=(0x13d98,0x13de0,0x13e34,0x13e98);pointers=[struct.unpack_from('<I',rom,off)[0]for off in fields]
    assert len(set(pointers))==1 and pointers[0]!=0x084b83a0,'A condition loader still uses the original English table'
    assert 0<=pointers[0]-0x08000000<len(rom)
    a.out_private.mkdir(parents=True,exist_ok=True);copy=a.out_private/'input-copy.sav';assert copy.resolve()!=a.battery.resolve();copy.write_bytes(battery)
    stages=[];runner=Path(__file__).with_name('emulate.py')
    def run(name,actions,previous=None):
        args=[sys.executable,str(runner),str(a.rom),'--core',str(a.core),'--sram-in',str(copy),'--out',str(a.out_private/name),'--actions',actions,'--save-state',str(a.out_private/(name+'.state')),'--memory-out',str(a.out_private/name/'memory')]
        if previous:args+=['--load-state',str(a.out_private/(previous+'.state'))]
        completed=subprocess.run(args,check=True,capture_output=True,text=True);stages.append({'stage':name,**json.loads(completed.stdout)})
    run('world','600,START:8,180,START:8,180,A:8,180,A:8,180,A:8,180')
    run('pub','A:8,120,A:8,240','world');run('list','DOWN:8,30,A:8,180','pub');run('detail','A:8,180','list')
    run('tutorial-initial','A:8,180,A:8,180','detail');run('goal','A:8,180,A:8,180,A:8,180,A:8,180','tutorial-initial')
    run('accept-prompt','A:8,180','goal');run('paid','A:8,180','accept-prompt');run('story','A:8,180,A:8,180,A:8,180,A:8,180','paid')
    memory=(a.out_private/'paid/memory/map-02000000.bin').read_bytes();gil=struct.unpack_from('<I',memory,0x1f64)[0];assert gil==4700,'First-mission fee not paid'
    assert a.battery.read_bytes()==battery and copy.read_bytes()==battery
    report={'rom_sha256':hashlib.sha256(rom).hexdigest(),'source_battery_sha256':SAVE_SHA,'source_battery_unchanged':True,'fresh_boot_and_battery_load':True,'condition_pointer_fields':[hex(x)for x in fields],'shared_new_condition_table':hex(pointers[0]),'mission_fee':300,'remaining_gil':gil,'visual_review_required':True,'scope':'One early mission acceptance and opening dialogue. Not a completed mission, crystal/Jagd playthrough or every condition branch.','stages':stages}
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in report.items()if k!='stages'}))

if __name__=='__main__':main()
