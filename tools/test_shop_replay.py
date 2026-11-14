"""Explicit integration replay for the private reported save (not unittest discovery).

Reads the battery file, runs only private copies/checkpoints, never saves over it.
The pinned save starts in Sprohm with 5000 gil. Different saves need new actions.
"""
import argparse,hashlib,json,struct,subprocess,sys
from pathlib import Path

SAVE_SHA='6b1b12709caec36889a538572b42b3e02bde665e77197801beec218a3c7a4094'

def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--battery',type=Path,required=True);p.add_argument('--core',type=Path,required=True);p.add_argument('--out-private',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--check-save',action='store_true',help='Overwrite a private battery copy through the game and fresh-boot it');a=p.parse_args()
    battery=a.battery.read_bytes();assert hashlib.sha256(battery).hexdigest()==SAVE_SHA
    a.out_private.mkdir(parents=True,exist_ok=True);private_battery=a.out_private/'input-copy.sav'
    assert private_battery.resolve()!=a.battery.resolve();private_battery.write_bytes(battery)
    runner=Path(__file__).with_name('emulate.py');stages=[]
    def run(name,actions,previous=None,battery_in=None,battery_out=None):
        out=a.out_private/name;state=a.out_private/(name+'.state')
        args=[sys.executable,str(runner),str(a.rom),'--core',str(a.core),'--actions',actions,'--out',str(out),'--memory-out',str(out/'memory'),'--save-state',str(state)]
        # A serialized core checkpoint is not proof that battery storage was
        # restored; supply the battery explicitly whenever testing writes.
        args+=['--sram-in',str(battery_in or private_battery)]
        if previous:args+=['--load-state',str(previous)]
        if battery_out:args+=['--sram-out',str(battery_out)]
        result=subprocess.run(args,check=True,capture_output=True,text=True)
        stages.append({'stage':name,**json.loads(result.stdout)})
        return state,out
    world,_=run('world','600,START:8,180,START:8,180,A:8,180,A:8,180,A:8,180')
    buy,buy_out=run('buy','A:8,180,DOWN:8,20,A:8,240,A:8,240',world)
    io=(buy_out/'memory/map-04000000.bin').read_bytes();video=(buy_out/'memory/map-06000000.bin').read_bytes()
    assert struct.unpack_from('<H',io,0x10)[0]==0x88,'Replay did not reach shop'
    assert sum(b!=0 for b in video[:0x4000])>5000,'Shop background disappeared'
    assert sum(b!=0 for b in video[0x10000:])>5000,'Shop sprite graphics disappeared'
    run('next-category','RIGHT:8,120',buy)
    purchased,purchased_out=run('purchase','A:8,90,A:8,90,A:8,180',buy)
    def gil(out):return struct.unpack_from('<I',(out/'memory/map-02000000.bin').read_bytes(),0x1f64)[0]
    assert gil(purchased_out)==4500,'Bronze Helm purchase not completed'
    menu,_=run('after-purchase','A:8,120,B:8,180',purchased)
    sell,_=run('sell','DOWN:8,20,A:8,240',menu)
    sold,sold_out=run('sale','A:8,90,A:8,90,A:8,180,A:8,120,B:8,120',sell)
    assert gil(sold_out)==4750,'Bronze Helm sale not completed'
    left,_=run('leave','DOWN:8,20,DOWN:8,20,A:8,240,A:8,180',sold)
    saved_gil=None
    if a.check_save:
        confirm,_=run('overwrite-prompt','B:8,120,START:8,120,DOWN:8,20,DOWN:8,20,A:8,120,A:8,120,A:8,120',left)
        written=a.out_private/'after-trade.sav'
        run('save-complete','LEFT:8,30,A:8,300,A:8,120',confirm,battery_out=written)
        assert written.read_bytes()!=battery,'Game did not write changed battery data'
        reloaded,reload_out=run('fresh-reload','600,START:8,180,START:8,180,A:8,180,A:8,180,A:8,180',battery_in=written)
        saved_gil=gil(reload_out);assert saved_gil==4750,'Trade result not preserved after save and fresh boot'
        reopened,reopen_out=run('shop-after-reload','A:8,180,DOWN:8,20,A:8,240,A:8,240',reloaded,battery_in=written)
        assert gil(reopen_out)==4750
        io=(reopen_out/'memory/map-04000000.bin').read_bytes()
        assert struct.unpack_from('<H',io,0x10)[0]==0x88,'Shop not reopened after reload'
        roster,_=run('roster','START:8,120,A:8,120',reloaded,battery_in=written)
        inventory,_=run('inventory','START:8,120',roster,battery_in=written)
        run('inventory-help','SELECT:8,120',inventory,battery_in=written)
        run('inventory-categories','UP:8,60,RIGHT:8,120,RIGHT:8,120,RIGHT:8,120',inventory,battery_in=written)
        sort,_=run('sort-prompt','START:8,120',inventory,battery_in=written)
        run('sort-auto','A:8,120',sort,battery_in=written)
    assert private_battery.read_bytes()==battery
    report={'battery_sha256':SAVE_SHA,'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),
            'fresh_boot_and_battery_load':True,'shop_background_present':True,'category_switch_replayed':True,
            'purchase_gil':4500,'sale_gil':4750,'source_battery_unchanged':a.battery.read_bytes()==battery,
            'game_save_after_transaction_tested':a.check_save,'fresh_reload_gil':saved_gil,
            'scope':'One Sprohm shop and recorded categories; --check-save also exercises overwrite/fresh load, reopening shop and representative inventory/help/sort. Screenshots require visual review; not every item/window or full gameplay.',
            'stages':stages}
    a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items()if k!='stages'}))

if __name__=='__main__':main()
