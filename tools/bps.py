"""BPS1 writer for explicit source-copy/literal plans and checked standalone applier.

No original relocated assets are stored as literal patch payloads.
"""
import struct,zlib

def number(n):
    out=bytearray()
    while True:
        b=n&127;n>>=7
        if not n:out.append(b|128);return bytes(out)
        out.append(b);n-=1

def create(source,plan,metadata=b''):
    size=sum(n if isinstance(p,int) else len(p) for p,n in plan)
    patch=bytearray(b'BPS1'+number(len(source))+number(size)+number(len(metadata))+metadata)
    target=bytearray();relative=0;literal=0
    for item,length in plan:
        if isinstance(item,int):
            assert 0<=item and item+length<=len(source)
            if length==0:continue
            if item==len(target):patch+=number((length-1)<<2)
            else:
                patch+=number(((length-1)<<2)|2);delta=item-relative
                patch+=number((abs(delta)<<1)|int(delta<0));relative=item+length
            target+=source[item:item+length]
        else:
            assert len(item)==length
            if not item:continue
            patch+=number(((length-1)<<2)|1)+item;target+=item;literal+=length
    patch+=struct.pack('<II',zlib.crc32(source),zlib.crc32(target))
    patch+=struct.pack('<I',zlib.crc32(patch))
    assert apply(source,bytes(patch))==target
    return bytes(patch),bytes(target),literal

def apply(source,patch):
    assert patch[:4]==b'BPS1' and len(patch)>=19
    src_crc,dst_crc,patch_crc=struct.unpack('<III',patch[-12:])
    assert zlib.crc32(patch[:-4])==patch_crc,'Patch CRC mismatch'
    assert zlib.crc32(source)==src_crc,'Source CRC mismatch'
    i=4
    def read():
        nonlocal i
        n=0;shift=1
        for _ in range(10):
            assert i<len(patch)-12
            b=patch[i];i+=1;n+=(b&127)*shift
            if b&128:return n
            shift<<=7;n+=shift
        raise ValueError('Invalid BPS integer')
    src_size=read();dst_size=read();meta=read();assert src_size==len(source);i+=meta
    assert i<=len(patch)-12 and dst_size<=32*1024*1024
    out=bytearray();sr=0;tr=0
    while i<len(patch)-12:
        command=read();op=command&3;n=(command>>2)+1
        assert len(out)+n<=dst_size
        if op==0:
            assert len(out)+n<=len(source);out+=source[len(out):len(out)+n]
        elif op==1:
            assert i+n<=len(patch)-12;out+=patch[i:i+n];i+=n
        else:
            distance=read();delta=(distance>>1)*(-1 if distance&1 else 1)
            if op==2:
                sr+=delta;assert 0<=sr and sr+n<=len(source);out+=source[sr:sr+n];sr+=n
            else:
                tr+=delta;assert 0<=tr<len(out)
                for _ in range(n):out.append(out[tr]);tr+=1
    assert i==len(patch)-12 and len(out)==dst_size and zlib.crc32(out)==dst_crc
    return bytes(out)

if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('patch',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    assert not a.output.exists() and a.source.resolve()!=a.output.resolve()
    target=apply(a.source.read_bytes(),a.patch.read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(target)
    print('BPS source/patch/target CRC checks passed; wrote new private copy.')
