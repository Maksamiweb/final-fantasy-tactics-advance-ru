"""Fetch public tool code only. No game or translation assets are downloaded."""
import argparse, hashlib, io, json, urllib.request, zipfile
from pathlib import Path
REV='cd32ebce88bb26cae030115d5538c1d01a0772f3'
FILES=['ffta_sect.py','ffta_charset.py','ffta_parser.py','ffta_font.py','ffta_modifier.py','readme.md','LICENSE','charset_us.json']
def main():
    p=argparse.ArgumentParser();p.add_argument('destination',type=Path);p.add_argument('--emulator',action='store_true');a=p.parse_args();a.destination.mkdir(parents=True,exist_ok=True);manifest={}
    for name in FILES:
        data=urllib.request.urlopen(f'https://raw.githubusercontent.com/BSoD123456/ffta_us_cn/{REV}/{name}',timeout=40).read()
        (a.destination/name).write_bytes(data);manifest[name]=hashlib.sha256(data).hexdigest()
    if a.emulator:
        data=urllib.request.urlopen('https://buildbot.libretro.com/nightly/windows/x86_64/latest/mgba_libretro.dll.zip',timeout=40).read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            dll=z.read('mgba_libretro.dll');(a.destination/'mgba_libretro.dll').write_bytes(dll)
            manifest['mgba_libretro.dll']=hashlib.sha256(dll).hexdigest()
    (a.destination/'manifest.json').write_text(json.dumps({'parser_revision':REV,'sha256':manifest},indent=2))
    print('Fetched tool sources; parser GPL-3.0, mGBA MPL-2.0. Emulator nightly is unpinned; compare SHA-256 with reports/toolchain.json.')
if __name__=='__main__':main()
