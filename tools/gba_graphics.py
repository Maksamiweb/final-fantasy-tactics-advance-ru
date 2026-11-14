"""Bounded GBA BIOS LZ77/RLE readers for private graphics research; no ROM writer.

Format reference: GBATEK BIOS decompression functions, linked in the research report.
"""
def decompress(data,offset=0,max_output=0x40000):
    if offset<0 or offset+4>len(data):raise ValueError('Truncated header')
    typ=data[offset];size=int.from_bytes(data[offset+1:offset+4],'little')
    if typ not in (0x10,0x30)or not 0<size<=max_output:raise ValueError('Unsupported type or size')
    p=offset+4;out=bytearray()
    def take():
        nonlocal p
        if p>=len(data):raise ValueError('Truncated stream')
        value=data[p];p+=1;return value
    while len(out)<size:
        flags=take()
        if typ==0x30:
            count=(flags&127)+(3 if flags&128 else 1)
            if flags&128:out.extend(bytes([take()])*min(count,size-len(out)))
            else:
                for _ in range(count):
                    value=take()
                    if len(out)<size:out.append(value)
        else:
            for bit in range(7,-1,-1):
                if len(out)>=size:break
                if flags&(1<<bit):
                    hi=take();lo=take();count=(hi>>4)+3;distance=((hi&15)<<8|lo)+1
                    if distance>len(out):raise ValueError('Invalid backward reference')
                    for _ in range(min(count,size-len(out))):out.append(out[-distance])
                else:out.append(take())
    return bytes(out),p-offset

def literal_lz(data):
    if not 0<len(data)<1<<24:raise ValueError('Invalid size')
    out=bytearray(b'\x10'+len(data).to_bytes(3,'little'))
    for p in range(0,len(data),8):out.append(0);out.extend(data[p:p+8])
    return bytes(out)
