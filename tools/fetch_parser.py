"""Fetch only pinned parser code/character mapping, never a ROM or translation dump."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
REV='cd32ebce88bb26cae030115d5538c1d01a0772f3'
EXPECTED={'ffta_sect.py':'dd1d04163573da5c8197d28e7d2d19f7df7623c682d6c311575fa0cc6c3c5b54','charset_us.json':'7ce1e76bc5b17ea77bfc8934a55de4f479f379cf9f89ec8ede2a9961cda2dcc7'}
def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);manifest={}
    for name in ['ffta_sect.py','charset_us.json','LICENSE']:
        raw=urllib.request.urlopen(f'https://raw.githubusercontent.com/BSoD123456/ffta_us_cn/{REV}/{name}',timeout=40).read();h=hashlib.sha256(raw).hexdigest()
        if name in EXPECTED:assert h==EXPECTED[name]
        (a.out/name).write_bytes(raw);manifest[name]=h
    (a.out/'manifest.json').write_text(json.dumps({'revision':REV,'sha256':manifest},indent=2));print('Pinned GPL-3.0 parser fetched; no ROM data downloaded.')
if __name__=='__main__':main()
