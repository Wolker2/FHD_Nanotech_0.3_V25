"""Lossless DAT tree reader/writer based on supplied EC_BlockPar/EC_Data/EC_Buf.
Preserves sorted group metadata and UTF-16 string values. Validates CRC and size.
"""
import struct,zlib
from pathlib import Path

def cipher(data,seed):
    # Delphi div/mod truncate toward zero, including negative seeds.
    seed=struct.unpack('<i',struct.pack('<I',seed & 0xffffffff))[0]
    out=bytearray(data)
    for i in range(len(out)):
        hi=abs(seed)//127773 * (-1 if seed<0 else 1)
        lo=seed-hi*127773
        seed=lo*16807-hi*2836
        if seed<=0:seed+=2147483647
        out[i]^=(seed-1)&255
    return bytes(out)

class Reader:
    def __init__(self,b):self.b=b;self.p=0
    def take(self,n):
        assert 0<=n<=len(self.b)-self.p
        b=self.b[self.p:self.p+n];self.p+=n;return b
    def u32(self):return struct.unpack('<I',self.take(4))[0]
    def string(self):
        b=bytearray()
        while (x:=self.take(2))!=b'\0\0':b.extend(x)
        return b.decode('utf-16-le')
    def tree(self,cache=False):
        sort=None if cache else self.take(1)[0]
        assert sort in (None,0,1)
        entries=[]
        for _ in range(self.u32()):
            group=self.take(8) if sort else b''
            kind=self.take(1)[0];assert kind in (1,2)
            name=self.string()
            value=self.string() if kind==1 else self.tree(cache)
            entries.append([group,kind,name,value])
        return [sort,entries]

def serialize(tree,cache=False):
    sort,entries=tree
    b=bytearray(b'' if cache else bytes([sort]))
    b.extend(struct.pack('<I',len(entries)))
    for group,kind,name,value in entries:
        if sort:b.extend(group)
        b.extend(bytes([kind])+name.encode('utf-16-le')+b'\0\0')
        b.extend(value.encode('utf-16-le')+b'\0\0' if kind==1 else serialize(value,cache))
    return bytes(b)

def unpack(data,cache=False):
    key=0xea8f3f37 if cache else 0xb1e8c689
    for off in (0,8):
        crc,encoded_seed=struct.unpack_from('<II',data,off)
        compressed=cipher(data[off+8:],encoded_seed^key)
        if zlib.crc32(compressed)!=crc:continue
        assert compressed[:4]==b'ZL01'
        raw=zlib.decompress(compressed[8:])
        assert len(raw)==struct.unpack_from('<I',compressed,4)[0]
        reader=Reader(raw);tree=reader.tree(cache)
        assert reader.p==len(raw)
        assert serialize(tree,cache)==raw
        return tree,dict(offset=off,seed=encoded_seed^key,cache=cache,raw=raw)
    raise ValueError('DAT inner CRC mismatch')

def pack(tree,meta):
    raw=serialize(tree,meta['cache'])
    compressed=b'ZL01'+struct.pack('<I',len(raw))+zlib.compress(raw,9)
    key=0xea8f3f37 if meta['cache'] else 0xb1e8c689
    data=struct.pack('<II',zlib.crc32(compressed),meta['seed']^key)+cipher(compressed,meta['seed'])
    if meta['offset']:
        k1,k2=0x7db6c99d,0xc83fcbf3
        inner=struct.pack('<I',zlib.crc32(data)^k1)+data
        data=struct.pack('<II',len(data)^(k1^k2),zlib.crc32(inner)^k2)+data
    result,_=unpack(data,meta['cache']);assert result==tree
    return data

def walk(tree,prefix=''):
    for e in tree[1]:
        path=prefix+'.'+e[2] if prefix else e[2]
        yield path,e
        if e[1]==2:yield from walk(e[3],path)

def dump(tree,level=0):
    lines=[]
    for group,kind,name,value in tree[1]:
        if kind==1:lines.append('    '*level+name+'='+value)
        else:lines.extend(['    '*level+name+(' ^{' if value[0] else ' ~{'),dump(value,level+1),'    '*level+'}'])
    return '\n'.join(lines)

if __name__=='__main__':
    import sys
    p=Path(sys.argv[1]);tree,meta=unpack(p.read_bytes(),p.name=='CacheData.dat')
    Path(sys.argv[2]).write_text(dump(tree),encoding='utf-8')
