"""Apply this project's experimental IPS with source and target SHA-256 validation."""
import argparse, hashlib, json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('patch',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    if a.output.resolve()==a.rom.resolve() or a.output.exists():raise SystemExit('Output must be a new file distinct from the source.')
    meta=json.loads(a.patch.with_name(a.patch.stem.replace('-cyrillic','-poc')+'.json').read_text(encoding='utf-8'))
    src=a.rom.read_bytes();patch=a.patch.read_bytes()
    assert hashlib.sha256(src).hexdigest()==meta['source_sha256'],'Wrong source ROM'
    assert hashlib.sha256(patch).hexdigest()==meta['patch_sha256'],'Wrong or altered patch'
    assert patch[:5]==b'PATCH';dst=bytearray(src);i=5
    while patch[i:i+3]!=b'EOF':
        assert i+5<=len(patch);off=int.from_bytes(patch[i:i+3],'big');n=int.from_bytes(patch[i+3:i+5],'big');i+=5
        assert n>0 and i+n<=len(patch) and off+n<=len(dst),'Invalid record'
        dst[off:off+n]=patch[i:i+n];i+=n
    assert i+3==len(patch)
    assert hashlib.sha256(dst).hexdigest()==meta['modified_sha256'],'Target hash mismatch'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(dst);print('Verified patch applied to new private ROM.')
if __name__=='__main__':main()
