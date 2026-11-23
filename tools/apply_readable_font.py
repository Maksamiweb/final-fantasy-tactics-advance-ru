"""Apply the OFL bitmap overlay after building the pinned audit-1.26 base."""
from pathlib import Path
import hashlib, argparse
p=argparse.ArgumentParser(); p.add_argument('base'); p.add_argument('output'); a=p.parse_args()
base=Path(a.base).read_bytes()
assert hashlib.sha256(base).hexdigest()=='51b50b198e094cfd0274908b89150a675c9a5c3f39ac408907da4ef049981a75', 'Expected audit-1.26'
glyphs=(Path(__file__).resolve().parents[1]/'font/readable/glyphs.bin').read_bytes()
assert len(glyphs)==18432
result=base[:0x1063380]+glyphs+base[0x1067b80:]
assert hashlib.sha256(result).hexdigest()=='5fa7a4ff38506c6e35539286475ae84b46f67c18465fec68b43212402638a43c'
out=Path(a.output)
assert not out.exists(), 'Choose a new output file'
out.write_bytes(result)
print('audit-1.27 written; text pointers and advance widths unchanged')
