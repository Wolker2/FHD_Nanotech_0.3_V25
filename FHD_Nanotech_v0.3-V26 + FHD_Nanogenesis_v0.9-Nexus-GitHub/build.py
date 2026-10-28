#!/usr/bin/env python3
"""Build both Nanotech modules from editable config JSON and PNG atlas sources."""
from pathlib import Path
import argparse,hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'scripts'))
from dat_codec import encode as dat_encode
from artwork import AtlasReader,build_asset
PREFIX='Mods/FHD_MODS/'
def load(path):return json.loads(Path(path).read_text('utf-8'))
def hashes(files):return {name:hashlib.sha256(data).hexdigest()for name,data in sorted(files.items())}
def artwork_sources(root=ROOT):
    seen=set()
    for path in sorted((Path(root)/'source/graphics').glob('assets_*.json')):
        catalog=load(path);assert catalog['format']=='nanotech-artwork-catalog-v1'
        for name,data in catalog['files'].items():
            if name in seen:raise ValueError('Duplicate artwork: '+name)
            seen.add(name);yield name,data
def build(root=ROOT):
    root=Path(root);source=root/'source';files={}
    for module in load(source/'modules.json'):
        name=module['name'];folder=source/'modules'/name
        for path in sorted((folder/'CFG').rglob('*.json')):files[name+'/'+path.relative_to(folder).with_suffix('.dat').as_posix()]=dat_encode(load(path))
        assert module['metadata_encoding']=='utf-16le-bom'
        files[name+'/ModuleInfo.txt']=b'\xff\xfe'+(folder/'ModuleInfo.txt').read_bytes().decode('utf-8').encode('utf-16le')
    atlas=AtlasReader(source/'graphics')
    for name,data in artwork_sources(root):files[name]=build_asset(data,atlas)
    return files
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-original',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'dist/FHD_Nanotech-Nanogenesis-install.zip');a=p.parse_args();files=build()
    if a.verify_original:
        actual=hashes(files);expected=load(ROOT/'original-file-sha256.json')
        changed=sorted(n for n in actual.keys()|expected.keys()if actual.get(n)!=expected.get(n))
        if changed:raise SystemExit('Original-byte verification failed: '+', '.join(changed))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(PREFIX+name,(2026,1,1,0,0,0));info.external_attr=0o644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    print(json.dumps({'runtime_files':len(files),'original_bytes_verified':a.verify_original,'output':str(a.output)},indent=2))
if __name__=='__main__':main()
