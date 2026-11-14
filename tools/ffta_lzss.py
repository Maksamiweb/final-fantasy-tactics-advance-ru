"""Bounded reader for the BE-size stream consumed by USA function 0800543c.

This is distinct from BIOS LZ77 and A7 dictionary archives. No ROM writer.
"""
def decompress(data,offset=0,max_output=0x40000):
    if offset<0 or offset+4>len(data):raise ValueError('Truncated header')
    size=int.from_bytes(data[offset:offset+4],'big')
    if not 0<size<=max_output:raise ValueError('Invalid size')
    p=offset+4;out=bytearray()
    def take():
        nonlocal p
        if p>=len(data):raise ValueError('Truncated stream')
        value=data[p];p+=1;return value
    while len(out)<size:
        cmd=take();distance=None;fill=None
        if cmd&0x80:
            n=((cmd>>3)&15)+3;distance=(((cmd&7)<<8)|take())+1
        elif cmd&0x40:
            n=(cmd&63)+1
            if len(out)+n>size:raise ValueError('Literal exceeds size')
            for _ in range(n):out.append(take())
            continue
        elif cmd&0x20:n=(cmd&31)+2;fill=0
        elif cmd&0x10:
            b=take();n=((b&0xc0)>>2|(cmd&15))+4;distance=((b&63)<<8|take())+1
        elif cmd==2:n=take()+3;fill=0
        elif cmd==1:n=take()+3;fill=255
        elif cmd==0:
            n=take()+5;distance=(take()<<8|take())+1
        else:raise ValueError('Unsupported command')
        if len(out)+n>size:raise ValueError('Command exceeds size')
        if distance is not None:
            if distance>len(out):raise ValueError('Invalid backward distance')
            for _ in range(n):out.append(out[-distance])
        else:out.extend(bytes([fill])*n)
    return bytes(out),p-offset

def compress(data):
    """Encode with bounded match search and a shortest-packet dynamic program.

    The match search keeps the last 256 candidates per three-byte key. This is
    not a proof of globally minimum compressed size. No ROM IO is performed.
    """
    from collections import defaultdict,deque
    if not 0<len(data)<=0x40000:raise ValueError('Invalid size')
    n=len(data);matches=[];positions=defaultdict(lambda:deque(maxlen=256))
    for i in range(n):
        best=[(0,0),(0,0),(0,0)]
        key=data[i:i+3]
        for j in reversed(positions[key]):
            distance=i-j
            if distance>65536:break
            high=min(260,n-i);low=3
            while low<high:
                mid=(low+high+1)//2
                if data[i:i+mid]==data[j:j+mid]:low=mid
                else:high=mid-1
            for group,limit,cap in [(0,2048,18),(1,16384,67),(2,65536,260)]:
                length=min(low,cap)
                if distance<=limit and length>best[group][0]:best[group]=(length,distance)
            if all(length>=min(cap,n-i) for (length,_),cap in zip(best,[18,67,260])):break
        matches.append(best)
        if len(key)==3:positions[key].append(i)
    cost=[0]*(n+1);chosen=[None]*n
    for i in range(n-1,-1,-1):
        options=[]
        for length in range(1,min(64,n-i)+1):options.append((1+length+cost[i+length],length,'literal',0))
        if data[i]in (0,255):
            run=1
            while run<min(258,n-i) and data[i+run]==data[i]:run+=1
            if data[i]==0:
                for length in range(2,min(33,run)+1):options.append((1+cost[i+length],length,'zero',0))
            for length in range(3,run+1):options.append((2+cost[i+length],length,'fill',data[i]))
        for (maxlen,distance),minimum,kind,packet in zip(matches[i],[3,4,5],['near','far','long'],[2,3,4]):
            for length in range(minimum,maxlen+1):options.append((packet+cost[i+length],length,kind,distance))
        chosen[i]=min(options,key=lambda o:(o[0],-o[1]));cost[i]=chosen[i][0]
    out=bytearray(n.to_bytes(4,'big'));i=0
    while i<n:
        _,length,kind,distance=chosen[i]
        if kind=='literal':out.append(0x40+length-1);out.extend(data[i:i+length])
        elif kind=='zero':out.append(0x20+length-2)
        elif kind=='fill':out.extend([2 if distance==0 else 1,length-3])
        else:
            d=distance-1
            if kind=='near':out.extend([0x80|((length-3)<<3)|(d>>8),d&255])
            elif kind=='far':out.extend([0x10|((length-4)&15),((length-4)&48)<<2|(d>>8),d&255])
            else:out.extend([0,length-5,d>>8,d&255])
        i+=length
    return bytes(out)
