"""Match inventory SHA-1, size and CRC32 against a local No-Intro DAT mirror."""
import argparse,hashlib,json,re
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('inventory',type=Path);p.add_argument('dat',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();b=a.dat.read_bytes();txt=b.decode('utf-8');matches=[]
    for r in json.loads(a.inventory.read_text(encoding='utf-8')):
        blocks=[t.strip() for t in txt.split('game (') if re.search(r'\bsha1\s+'+r['sha1']+r'\b',t,re.I)]
        assert len(blocks)==1
        assert re.search(r'\bcrc\s+'+r['crc32']+r'\b',blocks[0],re.I)
        assert re.search(r'\bsize\s+'+str(r['size'])+r'\b',blocks[0])
        matches.append({'code':r['game_code'],'matches':blocks})
    a.out.write_text(json.dumps({'database_sha256':hashlib.sha256(b).hexdigest(),'matches':matches},indent=2));print('All three SHA-1/CRC32/size records match.')
if __name__=='__main__':main()
