"""Editable PNG atlas sources for lossless GI/GAI/HAI reconstruction.

PNG stores actual color/alpha/index/palette samples. JSON retains geometry,
RLE commands, sequence/delay data and typed headers, never compressed assets.
"""
from pathlib import Path
from collections import OrderedDict
import struct,zlib
import numpy as np
from PIL import Image
from gi_codec import decode as decode_gi,encode as encode_gi

class AtlasWriter:
    def __init__(self,folder):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.width=4096;self.height=3072;self.number=1;self.x=self.y=self.row=self.used=0
        self.pixels=np.zeros((self.height,self.width,4),dtype=np.uint8);self.files=[]
    def flush(self):
        if not self.used:return
        name='atlas_'+str(self.number).zfill(2)+'.png';path=self.folder/name
        temporary=path.with_suffix('.png.tmp')
        Image.fromarray(self.pixels[:self.used]).save(temporary,format='PNG',compress_level=6)
        temporary.replace(path)
        self.files.append({'file':name,'width':self.width,'height':self.used,'bytes':path.stat().st_size})
        print('ATLAS',name,path.stat().st_size,flush=True)
        self.number+=1;self.x=self.y=self.row=self.used=0;self.pixels.fill(0)
    def add(self,rgba):
        h,w=rgba.shape[:2];assert w<=self.width and h<=self.height,(w,h)
        if self.x+w>self.width:self.x=0;self.y+=self.row;self.row=0
        if self.y+h>self.height:self.flush()
        box=[self.x,self.y,w,h];self.pixels[self.y:self.y+h,self.x:self.x+w]=rgba
        self.x+=w;self.row=max(self.row,h);self.used=max(self.used,self.y+h)
        return {'atlas':'atlases/atlas_'+str(self.number).zfill(2)+'.png','box':box}

class AtlasReader:
    def __init__(self,folder):self.folder=Path(folder);self.cache=OrderedDict()
    def get(self,source):
        name=source['atlas']
        if name not in self.cache:
            with Image.open(self.folder/name)as image:self.cache[name]=np.array(image.convert('RGBA'))
            if len(self.cache)>3:self.cache.popitem(last=False)
        self.cache.move_to_end(name);x,y,w,h=source['box'];image=self.cache[name]
        assert x>=0 and y>=0 and x+w<=image.shape[1] and y+h<=image.shape[0]
        return image[y:y+h,x:x+w]

def samples_rgba(values,kind):
    a=np.asarray(values,dtype=np.uint32);out=np.zeros((len(a),4),dtype=np.uint8)
    if kind=='rgb565':
        out[:,0]=((a>>11)&31)*255//31;out[:,1]=((a>>5)&63)*255//63;out[:,2]=(a&31)*255//31;out[:,3]=255
    elif kind=='argb8888':
        out[:,0]=(a>>16)&255;out[:,1]=(a>>8)&255;out[:,2]=a&255;out[:,3]=a>>24
    elif kind=='transparency6':
        coverage=(63-a)*255//63;out[:,:3]=coverage[:,None];out[:,3]=255
    else:raise ValueError(kind)
    return out

def rgba_samples(image,kind):
    p=image.astype(np.uint32)
    if kind=='rgb565':return (((p[...,0]*31+127)//255)<<11)|(((p[...,1]*63+127)//255)<<5)|((p[...,2]*31+127)//255)
    if kind=='argb8888':return (p[...,3]<<24)|(p[...,0]<<16)|(p[...,1]<<8)|p[...,2]
    if kind=='transparency6':return 63-(p[...,0]*63+127)//255
    raise ValueError(kind)

def export_gi(data,atlas):
    d=decode_gi(data)
    for layer in d['layers']:
        if 'pixels'in layer:
            l,t,r,b=layer['bounds'];image=samples_rgba(layer.pop('pixels'),layer['pixel_format']).reshape(b-t,r-l,4)
            layer['source']=atlas.add(image)
        elif layer.get('commands'):
            commands=layer.pop('commands');width,height=layer['width'],layer['height']
            image=np.zeros((height,width,4),dtype=np.uint8)
            values=[v for c in commands for v in c.get('pixels',[])];pixels=samples_rgba(values,layer['pixel_format'])
            encoded=[];x=y=pos=0
            for cmd in commands:
                if 'end_row'in cmd:encoded.append(cmd['end_row']);y+=1;x=0
                elif 'skip'in cmd:encoded.append(cmd['skip']);x+=cmd['skip']
                else:
                    n=len(cmd['pixels']);assert y<height and x+n<=width
                    encoded.append(128+n);image[y,x:x+n]=pixels[pos:pos+n];x+=n;pos+=n
            assert y==height and pos==len(pixels)
            layer['rle_commands']=encoded;layer['source']=atlas.add(image)
    return d

def build_gi(source,atlas):
    d={**source,'layers':[]}
    for item in source['layers']:
        layer=dict(item);d['layers'].append(layer)
        if 'source'not in layer:continue
        pixels=rgba_samples(atlas.get(layer.pop('source')),layer['pixel_format'])
        if 'rle_commands'not in layer:layer['pixels']=pixels.reshape(-1).tolist();continue
        commands=layer.pop('rle_commands');result=[];x=y=0
        for cmd in commands:
            if cmd in [0,128]:result.append({'end_row':cmd});y+=1;x=0
            elif cmd<128:result.append({'skip':cmd});x+=cmd
            else:
                n=cmd-128;assert y<pixels.shape[0] and x+n<=pixels.shape[1]
                result.append({'pixels':pixels[y,x:x+n].tolist()});x+=n
        layer['commands']=result
    return encode_gi(d)

def export_gai(data,atlas):
    assert data[:4]==b'gai\0';h=struct.unpack_from('<11I',data,4)
    version,left,top,right,bottom,count,flags,seq_offset,seq_size,*reserved=h
    d={'format':'nanotech-gai-atlas-v1','version':version,'bounds':[left,top,right,bottom],'playback_flags':flags,'reserved':reserved,'sequences':[],'frames':[]}
    if seq_offset:
        table=data[seq_offset:seq_offset+seq_size];n=struct.unpack_from('<I',table)[0]
        for i in range(n):
            aux,off=struct.unpack_from('<II',table,4+8*i);assert off>=aux and (off-aux)%2==0
            auxiliary=list(struct.unpack_from('<'+'H'*((off-aux)//2),table,aux));length=struct.unpack_from('<I',table,off)[0]
            frames=[list(struct.unpack_from('<II',table,off+4+8*j))for j in range(length)]
            assert all(0<=a<count for a,b in frames)
            d['sequences'].append({'auxiliary_u16':auxiliary,'frames':frames})
    for i in range(count):
        off,size=struct.unpack_from('<II',data,48+8*i)
        if not size:d['frames'].append(None);continue
        compressed=data[off:off+size];assert compressed[:4]==b'ZL01'
        raw=zlib.decompress(compressed[8:]);assert len(raw)==struct.unpack_from('<I',compressed,4)[0]
        assert zlib.compress(raw,9)==compressed[8:]
        d['frames'].append(export_gi(raw,atlas))
    return d

def build_gai(d,atlas):
    seq=d['sequences'];table=bytearray(struct.pack('<I',len(seq))+bytes(8*len(seq)))if seq else bytearray()
    for i,s in enumerate(seq):
        aux=len(table);table.extend(struct.pack('<'+'H'*len(s['auxiliary_u16']),*s['auxiliary_u16']));off=len(table)
        table.extend(struct.pack('<I',len(s['frames'])))
        for frame,delay in s['frames']:table.extend(struct.pack('<II',frame,delay))
        struct.pack_into('<II',table,4+8*i,aux,off)
    frames=[]
    for frame in d['frames']:
        if frame is None:frames.append(b'');continue
        raw=build_gi(frame,atlas);frames.append(b'ZL01'+struct.pack('<I',len(raw))+zlib.compress(raw,9))
    offset=48+8*len(frames);header=struct.pack('<4s11I',b'gai\0',d['version'],*d['bounds'],len(frames),d['playback_flags'],offset if table else 0,len(table),*d['reserved'])
    offset+=len(table);directory=bytearray()
    for frame in frames:directory.extend(struct.pack('<II',offset if frame else 0,len(frame)));offset+=len(frame)
    return header+directory+table+b''.join(frames)

HAI_FIELDS=['magic','width','height','pitch_bytes','frame_count','frame_stride','has_palette','bits_per_pixel','red_mask','green_mask','blue_mask','alpha_mask','palette_bytes']
def export_hai(data,atlas):
    h=dict(zip(HAI_FIELDS,struct.unpack_from('<13I',data)))
    assert h['magic']==0x04210420 and h['bits_per_pixel']==8 and h['has_palette']==1 and h['palette_bytes']==1024
    w,ht,n,stride=h['pitch_bytes'],h['height'],h['frame_count'],h['frame_stride']
    assert w==h['width'] and stride==w*ht+1024 and len(data)==52+n*stride
    cols=10;rows=(n+cols-1)//cols;indices=np.zeros((rows*ht,cols*w,4),dtype=np.uint8);palettes=np.zeros((n,256,4),dtype=np.uint8)
    for i in range(n):
        at=52+i*stride;plane=np.frombuffer(data[at:at+w*ht],dtype=np.uint8).reshape(ht,w);y,x=divmod(i,cols)
        target=indices[y*ht:(y+1)*ht,x*w:(x+1)*w];target[:,:,:3]=plane[:,:,None];target[:,:,3]=255
        palettes[i]=np.frombuffer(data[at+w*ht:at+stride],dtype=np.uint8).reshape(256,4)
    return {'format':'nanotech-hai-atlas-v1','header':h,'columns':cols,'indices':atlas.add(indices),'palettes':atlas.add(palettes)}

def build_hai(d,atlas):
    h=d['header'];out=bytearray(struct.pack('<13I',*[h[k]for k in HAI_FIELDS]));indices=atlas.get(d['indices']);palettes=atlas.get(d['palettes']);w,ht=h['pitch_bytes'],h['height']
    for i in range(h['frame_count']):
        y,x=divmod(i,d['columns']);out.extend(indices[y*ht:(y+1)*ht,x*w:(x+1)*w,0].tobytes());out.extend(palettes[i].tobytes())
    return bytes(out)

def build_asset(d,atlas):
    kind=d['format']
    if kind=='srhd-gi012-json-v1':return build_gi(d,atlas)
    if kind=='nanotech-gai-atlas-v1':return build_gai(d,atlas)
    if kind=='nanotech-hai-atlas-v1':return build_hai(d,atlas)
    raise ValueError(kind)
