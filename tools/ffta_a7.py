"""Read-only A7 graphics archive decoder, derived from USA 08005318/080051c4.

Only dictionary types 0 and 3 are implemented. No ROM writer.
"""
def decode_archive(data, base=0, max_output=0x100000):
    def be(p,n):
        if p<base or p+n>len(data):raise ValueError('Truncated archive')
        return int.from_bytes(data[p:p+n],'big')
    if data[base:base+2]!=b'A7':raise ValueError('Not A7')
    count=be(base+2,2)
    if not 0<count<=4096:raise ValueError('Invalid chunk count')
    header_end=8+4*count;dictionary=base+be(base+4,4)
    typ=be(dictionary,1);shift=be(dictionary+1,1)
    if typ not in (0,3) or shift>7:raise ValueError('Unsupported dictionary')
    fixed=be(dictionary+2,2) if typ==0 else None
    dict_start=dictionary+(4 if typ==0 else 2)
    if dictionary<base+header_end:raise ValueError('Dictionary overlaps header')
    offsets=[be(base+8+i*4,4) for i in range(count)]
    if offsets!=sorted(set(offsets)) or offsets[0]<header_end or base+offsets[-1]>=dictionary:
        raise ValueError('Invalid chunk offsets')
    mask=0xffff>>(shift+1);chunks=[];total=0
    for i,offset in enumerate(offsets):
        p=base+offset;end=base+offsets[i+1] if i+1<count else dictionary
        size=fixed
        if typ==3:size=be(p,2);p+=2
        if not size or total+size>max_output:raise ValueError('Invalid output size')
        out=bytearray()
        def take():
            nonlocal p
            if p>=end:raise ValueError('Truncated chunk')
            value=data[p];p+=1;return value
        while len(out)<size:
            cmd=take()
            if cmd&128:
                n=(cmd&127)+1
                if len(out)+n>size:raise ValueError('Literal exceeds output')
                for _ in range(n):out.append(take())
            else:
                n=(cmd>>(7-shift))+3;offset=((cmd<<8)|take())&mask
                if len(out)+n>size:raise ValueError('Dictionary copy exceeds output')
                start=dict_start+offset
                if start+n>len(data):raise ValueError('Truncated dictionary copy')
                out.extend(data[start:start+n])
        chunks.append({'source_offset':base+offsets[i],'consumed':p-(base+offsets[i]),'data':bytes(out)})
        total+=size
    return chunks

def encode_literal_archive(chunks):
    """Encode authored equal-size chunks without dictionary references; no ROM IO."""
    if not 0<len(chunks)<=4096:raise ValueError('Invalid chunk count')
    size=len(chunks[0])
    if not 0<size<=65535 or any(len(c)!=size for c in chunks):
        raise ValueError('Chunks must have the same nonzero size')
    payload=bytearray();offsets=[];header_size=8+4*len(chunks)
    for chunk in chunks:
        offsets.append(header_size+len(payload))
        for p in range(0,size,128):
            part=chunk[p:p+128];payload.append(128+len(part)-1);payload.extend(part)
    dictionary=header_size+len(payload)
    header=b'A7'+len(chunks).to_bytes(2,'big')+dictionary.to_bytes(4,'big')
    return header+b''.join(o.to_bytes(4,'big')for o in offsets)+payload+b'\0\5'+size.to_bytes(2,'big')
