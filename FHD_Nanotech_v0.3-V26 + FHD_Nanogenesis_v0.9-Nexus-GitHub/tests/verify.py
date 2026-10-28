#!/usr/bin/env python3
"""Verify source-only reconstruction of all 525 files and resource references."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,platform,re,shutil,struct,sys,tempfile,zlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from build import build,hashes,load
from dat_codec import decode as dat_decode,encode as dat_encode
from gi_codec import decode as gi_decode
from artwork import HAI_FIELDS
def walk(block,prefix=''):
    for e in block['entries']:
        path=prefix+e['name'];yield path,e
        if e['kind']=='block':yield from walk(e['value'],path+'.')
def verify():
    checks=[]
    def check(condition,label):
        assert condition,label;checks.append(label)
    with tempfile.TemporaryDirectory()as folder:
        clean=Path(folder)
        for name in ['source','scripts']:shutil.copytree(ROOT/name,clean/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        files=build(clean)
    check(hashes(files)==load(ROOT/'original-file-sha256.json'),'All 525 runtime SHA-256 hashes match after isolated source-only rebuild')
    check(len(files)==525,'Exactly 525 original runtime files retained')
    counts=Counter(Path(n).suffix.lower()for n in files)
    check(counts==Counter({'.dat':6,'.gi':434,'.gai':51,'.hai':32,'.txt':2}),'All six configs, two metadata files and 517 graphics resources retained')
    check(not any(n.endswith(('.dll','.scr','.exe'))for n in files),'No DLL/SCR/EXE in supplied modules')
    nodes={};parameters=[];animation_frames=ship_frames=0;container_headers=[]
    for name,data in sorted(files.items()):
        suffix=Path(name).suffix.lower()
        if suffix=='.dat':
            fmt='cachedata'if name.endswith('CacheData.dat')else'blockpar';d=dat_decode(data,fmt)
            check(dat_encode(d)==data,'DAT complete parse/encode: '+name)
            for path,e in walk(d['root']):
                nodes[path]=e
                if e['kind']=='parameter':parameters.append((path,e['value']))
        elif suffix=='.gi':gi_decode(data)
        elif suffix=='.gai':
            assert data[:4]==b'gai\0';n=struct.unpack_from('<I',data,24)[0];animation_frames+=n
            for i in range(n):
                off,size=struct.unpack_from('<II',data,48+8*i)
                if not size:continue
                frame=data[off:off+size];assert frame[:4]==b'ZL01'
                raw=zlib.decompress(frame[8:]);assert len(raw)==struct.unpack_from('<I',frame,4)[0]
                gi_decode(raw)
        elif suffix=='.hai':
            h=dict(zip(HAI_FIELDS,struct.unpack_from('<13I',data)));ship_frames+=h['frame_count']
            assert h['magic']==0x04210420 and len(data)==52+h['frame_count']*h['frame_stride']
            assert h['bits_per_pixel']==8 and h['palette_bytes']==1024 and h['pitch_bytes']==h['width']
            container_headers.append(h)
    check(animation_frames==3156,'All 3156 compressed GI animation frames parsed and validated')
    check(ship_frames==2400,'All 2400 indexed HAI hull frames retained')
    check(len(container_headers)==32,'All indexed HAI container headers validated')
    # Resolve against Windows' case-insensitive namespace while preserving bytes.
    namespace={name.casefold()for name in files};references=[];missing=[]
    for path,value in parameters:
        normalized=value.replace('\\','/')
        if normalized.casefold().startswith('mods/fhd_mods/'):
            target=normalized[len('Mods/FHD_MODS/'):]
            present=target.casefold()in namespace
            if not present:present=any(n.startswith(target.casefold().rstrip('/')+'/')for n in namespace)
            references.append({'field':path,'target':target,'present':present})
            if not present:missing.append(references[-1])
    check(not missing,'All '+str(len(references))+' literal local resource paths resolve')
    for module,priority in [('FHD_Nanotech',5),('FHD_Nanogenesis',6)]:
        b=files[module+'/ModuleInfo.txt'];check(b[:2]==b'\xff\xfe','UTF-16LE BOM retained: '+module)
        check('Priority='+str(priority)in b[2:].decode('utf-16le'),'Module priority retained: '+module)
    check('Dependence=FHD_Nanotech'in files['FHD_Nanogenesis/ModuleInfo.txt'][2:].decode('utf-16le'),'Nanogenesis dependency on Nanotech retained')
    pngs=list((ROOT/'source/graphics/atlases').glob('*.png'));catalogs=list((ROOT/'source/graphics').glob('assets_*.json'))
    check(len(pngs)==45 and len(catalogs)==6,'Forty-five editable PNG atlases and six typed artwork catalogs')
    source_files=[p for p in ROOT.rglob('*')if p.is_file()and not any(x in ['.git','__pycache__','dist']for x in p.relative_to(ROOT).parts)]
    check(len(source_files)<=100,'Source repository contains at most 100 files')
    check(max(p.stat().st_size for p in source_files)<20*1024*1024,'Every individual source file is smaller than 20 MiB')
    return {'status':'passed','checks_passed':len(checks),'checks':checks,'runtime_sha256':hashes(files),
        'runtime_counts':dict(counts),'gai_frames':animation_frames,'hai_frames':ship_frames,
        'source_atlases':len(pngs),'source_catalogs':len(catalogs),'local_resource_references':len(references),'missing_resources':missing,
        'resource_paths':references,'original_runtime_files_excluded':0,'live_game_executed':False,
        'scope':'Exact source-only binary reconstruction, compressed frame parsing, indexed ship containers and static resource references. No live game interpreter, progression/UI/ship-preview/save behavior was executed.',
        'environment':{'python':platform.python_version(),'zlib':zlib.ZLIB_RUNTIME_VERSION,'Pillow':__import__('PIL').__version__,'numpy':__import__('numpy').__version__}}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path);a=p.parse_args();r=verify()
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:r[k]for k in ['status','checks_passed','gai_frames','hai_frames','local_resource_references','missing_resources']},indent=2))
