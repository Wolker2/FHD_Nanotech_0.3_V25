"""Remove Maloc_R from random selection; add native Dominator models 3/4."""
import copy,hashlib,json,shutil,struct,sys,zlib
from pathlib import Path
import numpy as np
from PIL import Image
from dat_codec import unpack,pack,dump
from build_hotfix import node,params,setcode,group_metadata
from build_v16 import ROOT,MODREL,source
from build_v17 import prop
sys.path.insert(0,str(ROOT/'tools_v25/modkit'))
from srhd_modkit.resources import inspect_pkg,inspect_hai,inspect_gai
from srhd_modkit.image_codec import encode_gi,decode_gi,RgbaImage

BASES={e:ROOT/f'work/v24_{e}'for e in ['release','test']}
VARIANTS={e:ROOT/f'work/v25_{e}'for e in ['release','test']}
COMMON=ROOT/'work/v25_common'
ORIGINAL=ROOT/'references25/SRHD_Modding/01_Game_Snapshot_Mixed/CFG_DATA_Extracted'
MODELS=[{'id':51+i,'series':s,'variant':v,'key':'FHDNTDom_'+s+str(v),'native':s+str(v),'graph':s+'.'+s[0]+str(v)}for i,(s,v)in enumerate((s,v)for s in ['Blazer','Keller','Terron']for v in [3,4])]

def rgba_frame(data,info,index):
    raw=data[info.frames[index].offset:info.frames[index].offset+info.frames[index].size]
    pixels=info.width*info.height
    assert len(raw)==pixels+1024 and info.palette_size==1024
    palette=np.frombuffer(raw[pixels:],dtype=np.uint8).reshape(256,4)[:,[2,1,0,3]].copy()
    palette[0,3]=0
    return Image.fromarray(palette[np.frombuffer(raw[:pixels],dtype=np.uint8).reshape(info.height,info.width)])

def gai(images,path):
    # Native GAI with independent ZL01 GI frames and the standard timing block.
    n=len(images);aux=struct.pack('<IIIHI',1,12,14,0,n)+b''.join(struct.pack('<II',i,70)for i in range(n))
    payload=[]
    for im in images:
        raw=encode_gi(RgbaImage(im.width,im.height,im.tobytes()),mode='2')
        payload.append(b'ZL01'+struct.pack('<I',len(raw))+zlib.compress(raw,9))
    header=bytearray(48);struct.pack_into('<4sI',header,0,b'gai\0',1)
    struct.pack_into('<III',header,16,images[0].width,images[0].height,n)
    offset=48+n*8;struct.pack_into('<II',header,32,offset,len(aux));offset+=len(aux);table=bytearray()
    for raw in payload:table.extend(struct.pack('<II',offset,len(raw)));offset+=len(raw)
    path.write_bytes(header+table+aux+b''.join(payload))

def make_assets():
    COMMON.mkdir(parents=True,exist_ok=True)
    pkg=inspect_pkg(ORIGINAL/'DATA/ships.pkg')
    by_name={e.name.lower():e for e in pkg.entries}
    extracted=ROOT/'references25/native_assets';extracted.mkdir(parents=True,exist_ok=True)
    assetroot=COMMON/'preview_assets';assetroot.mkdir(exist_ok=True)
    report=[];sheet=Image.new('RGBA',(6*160,190),(15,23,31,255))
    from PIL import ImageDraw
    for col,model in enumerate(MODELS):
        native=model['native'];entry=by_name[native.lower()+'.hai'];raw=pkg.decompress(entry)
        path=extracted/(native+'.hai');path.write_bytes(raw);info=inspect_hai(path)
        assert info.frame_count>=50
        frames=[rgba_frame(raw,info,i)for i in range(50)]
        for prefix,size in [(1,38),(2,75)]:
            small=[im.resize((size,size),Image.Resampling.LANCZOS)for im in frames]
            stem=f'{prefix}Hull_'+model['key']
            gai(small,assetroot/(stem+'_a.gai'))
            for suffix in ['i','s']:
                (assetroot/(stem+'_'+suffix+'.gi')).write_bytes(encode_gi(RgbaImage(size,size,small[0].tobytes()),mode='2'))
        portrait=pkg.decompress(by_name['2'+native.lower()+'.gi'])
        (extracted/('2'+native+'.gi')).write_bytes(portrait)
        p=decode_gi(portrait);im=Image.frombytes('RGBA',(p.width,p.height),p.pixels)
        im.thumbnail((150,140));sheet.alpha_composite(im,(col*160+(160-im.width)//2,10))
        ImageDraw.Draw(sheet).text((col*160+8,155),native,fill=(230,240,255))
        report.append({**model,'source':'data/Ship/'+native+'.hai','sha256':hashlib.sha256(raw).hexdigest(),'source_frames':info.frame_count,'shop_preview_frames':50,'portrait':'data/ShipP/2'+native.lower()+'.gi','portrait_sha256':hashlib.sha256(portrait).hexdigest()})
    sheet.save(COMMON/'models_preview.png')
    (COMMON/'native_assets.json').write_text(json.dumps(report,indent=2)+'\n')

def build():
    make_assets()
    native_main,_=unpack((ROOT/'references17/Main.dat').read_bytes())
    native_cache,_=unpack((ORIGINAL/'CFG/CacheData.dat').read_bytes(),True)
    native_ship=params(node(native_cache,'Bm.Ship'));native_portraits=params(node(native_cache,'Bm.ShipP'))
    for edition,out in VARIANTS.items():
        base=BASES[edition]
        shutil.copytree(base/'Mods',out/'Mods',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.*'))
        main,mm=unpack((base/MODREL/'CFG/Main.dat').read_bytes())
        lang,lm=unpack((base/MODREL/'CFG/Rus/Lang.dat').read_bytes())
        cache,cm=unpack((base/MODREL/'CFG/CacheData.dat').read_bytes(),True)
        if not any(e[1]==2 and e[2]=='Items'for e in node(cache,'Bm')[1]):
            node(cache,'Bm')[1].append([b'',2,'Items',[None,[]]])
        prop(node(lang,'FHDNT.Skins.Allowed'),'16','0');prop(node(lang,'FHDNT.Skins'),'Count','56')
        specials=node(lang,'MicroModuls')
        for model in MODELS:
            ident=str(model['id']);key=model['key'];native=model['native']
            prop(node(lang,'FHDNT.Skins'),ident,key);prop(node(lang,'FHDNT.Skins.Allowed'),ident,'1')
            prop(node(lang,'FHDNT.Portraits13'),ident,'GI,Bm.ShipP.2'+native)
            # Assert that every vanilla animation and portrait reference exists.
            assert native in native_ship and native+'s'in native_ship and '2'+native in native_portraits
            graph=copy.deepcopy(node(native_main,'Data.SE.Ship.'+model['graph']))
            prop(graph,'1ImageP','GI,Bm.ShipP.2'+native)
            node(main,'Data.SE.Ship.Akrin')[1].append([b'',2,key,graph])
            special=copy.deepcopy(node(lang,'MicroModuls.FHDNT_Skin50'))
            prop(special,'CustomTag','FHDNT_Skin'+ident);prop(special,'KindGraph',key)
            specials[1].append([b'',2,'FHDNT_Skin'+ident,special])
            used=copy.deepcopy(node(lang,'MicroModuls.FHDNT_UsedSkin50'));prop(used,'CustomTag','FHDNT_UsedSkin'+ident)
            specials[1].append([b'',2,'FHDNT_UsedSkin'+ident,used])
            file_info=[1,[]]
            for prefix in [1,2]:
                for suffix in ['a','i','s']:
                    filename=f'{prefix}Hull_{key}_{suffix}.'+('gai'if suffix=='a'else'gi')
                    rel='Mods\\FHD_MODS\\FHD_Nanotech\\DATA\\Image\\DominatorPreview\\'+filename
                    prop(node(cache,'Bm.Items'),f'{prefix}Hull_{key}_{suffix}',rel)
                    if prefix==2:file_info[1].append([b'',1,suffix,rel])
            node(lang,'FHDNT.Skins.Files')[1].append([b'',2,ident,file_info])
        setcode(lang,'Install',source(lang,'Install').replace('[FHDNT V24 ','[FHDNT V25 '))
        for name,t,m in [('Main.dat',main,mm),('Rus/Lang.dat',lang,lm),('CacheData.dat',cache,cm)]:
            group_metadata(t);(out/MODREL/'CFG'/name).write_bytes(pack(t,m))
            p=out/'SOURCE/CFG'/name.replace('.dat','.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(t)+'\n')
        shutil.copytree(COMMON/'preview_assets',out/MODREL/'DATA/Image/DominatorPreview',dirs_exist_ok=True)
        mi=(base/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V24 ','V25 ')
        (out/MODREL/'ModuleInfo.txt').write_text(mi,encoding='utf-16')
    print(json.dumps({'version':'V25','excluded':'Maloc_R (16)','added':[m['native']for m in MODELS],'allowed_skins':26,'new_preview_files':36,'flight_HAI_files_copied':0}))

if __name__=='__main__':build()
