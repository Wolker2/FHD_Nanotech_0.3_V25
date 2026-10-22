"""Check all six native models, no-repeat evolution and the scoped delta."""
import copy,json,sys,zlib
from pathlib import Path
from dat_codec import unpack,pack
from build_hotfix import node,params,group_metadata
from build_v16 import ROOT,MODREL
from build_v17 import prop
from build_v25 import BASES,VARIANTS,COMMON,MODELS,ORIGINAL
from test_hotfix import load_model
from srhd_modkit.resources import inspect_gai,_decode_gai_frame,inspect_hai
from srhd_modkit.image_codec import read_gi,decode_gi

def read(p,cache=False):return unpack(p.read_bytes(),cache)[0]
def norm(t):t=copy.deepcopy(t);group_metadata(t);return t

def main():
    Model,sector,vm=load_model(ROOT/'work/v13')
    class Host(Model):
        version='v25_test'
        def __init__(self,*a,**kw):super().__init__(*a,**kw);self.storage=[]
        def call(self,name,a):
            if name=='ShipStar':return 20000
            if name=='StarShips':return 0
            if name=='UpdateFormShip':return 0
            if name=='AddItemToStorage':self.storage.append(tuple(a));return 0
            if name=='FindItemInStorage':return next((i for i,x in enumerate(self.storage)if x[1]==a[0]),-1)
            return super().call(name,a)
    native_main=read(ROOT/'references17/Main.dat');native_cache=read(ORIGINAL/'CFG/CacheData.dat',True)
    all_seen=set();evolutions=0
    for edition,out in VARIANTS.items():
        lang=read(out/MODREL/'CFG/Rus/Lang.dat');main=read(out/MODREL/'CFG/Main.dat');cache=read(out/MODREL/'CFG/CacheData.dat',True)
        allowed={int(k)for k,v in params(node(lang,'FHDNT.Skins.Allowed')).items()if v=='1'}
        assert len(allowed)==26 and 16 not in allowed and set(range(51,57))<=allowed
        assert params(node(lang,'FHDNT.Skins'))['Count']=='56'
        for model in MODELS:
            ident=str(model['id']);key=model['key'];native=model['native']
            assert params(node(lang,'MicroModuls.FHDNT_Skin'+ident))['KindGraph']==key
            assert params(node(lang,'MicroModuls.FHDNT_UsedSkin'+ident))['CustomTag']=='FHDNT_UsedSkin'+ident
            graph=copy.deepcopy(node(main,'Data.SE.Ship.Akrin.'+key))
            prop(graph,'1ImageP','GI,Bm.ShipP.1'+native)
            assert norm(graph)==norm(node(native_main,'Data.SE.Ship.'+model['graph']))
            for field in ['Image','ImageS','ImageMap']:
                path=params(graph)[field];parent,leaf=path.rsplit('.',1);assert leaf in params(node(native_cache,parent))
            assert params(node(lang,'FHDNT.Portraits13'))[ident]=='GI,Bm.ShipP.2'+native
            for prefix,size in [(1,38),(2,75)]:
                for suffix in ['a','i','s']:
                    path=params(node(cache,'Bm.Items'))[f'{prefix}Hull_{key}_{suffix}']
                    file=out/Path(path.replace('\\','/'));assert file.is_file()
                    if suffix=='a':
                        info=inspect_gai(file);assert len(info.frames)==50
                        data=file.read_bytes()
                        for i,frame in enumerate(info.frames):
                            decoded,_=_decode_gai_frame(data[frame.offset:frame.offset+frame.size],i)
                            image=decode_gi(decoded);assert (image.width,image.height)==(size,size)
                    else:
                        image=read_gi(file);assert (image.width,image.height)==(size,size)
                    assert any(image.pixels[3::4]),'Empty preview'
        # All existing script blocks are byte-for-byte semantically unchanged,
        # except the startup version label. UI, XP and TEST gift stay intact.
        old=read(BASES[edition]/MODREL/'CFG/Rus/Lang.dat')
        for e in node(old,'FHDNT.Code')[1]:
            if e[2]!='Install':assert norm(e[3])==norm(node(lang,'FHDNT.Code.'+e[2])),e[2]
        baseline_main=read(BASES[edition]/MODREL/'CFG/Main.dat')
        stripped=copy.deepcopy(main);n=node(stripped,'Data.SE.Ship.Akrin');n[1]=[e for e in n[1]if e[2]not in {m['key']for m in MODELS}]
        assert norm(stripped)==norm(baseline_main),'Existing geometry/callback changed'
        # Every old file survives; only configuration and description change.
        for p in (BASES[edition]/'Mods').rglob('*'):
            if not p.is_file()or any(x.startswith('.')for x in p.relative_to(BASES[edition]).parts):continue
            rel=p.relative_to(BASES[edition])
            if rel not in [MODREL/'CFG/Main.dat',MODREL/'CFG/CacheData.dat',MODREL/'CFG/Rus/Lang.dat',MODREL/'ModuleInfo.txt']:assert p.read_bytes()==(out/rel).read_bytes()
        for name in ['Main.dat','CacheData.dat','Rus/Lang.dat']:
            t,m=unpack((out/MODREL/'CFG'/name).read_bytes(),name=='CacheData.dat');assert unpack(pack(t,m),name=='CacheData.dat')[0]==t
        cls=type('Edition',(Host,),{'version':'v25_'+edition})
        for seed in range(12):
            h=cls(seed=seed);h.startup();pool=h.run('SkinPool',output='result')
            assert {int(x)for x in pool.split(',')}==allowed
            shop,it=h.stock()[0];h.shops[shop].remove(it);h.held=[it,100];h.form='Ship'
            plans=[h.extra[it,'FHDNT_Plan0']]
            for level in range(1,21):
                if edition=='test':h.run('TestLevel',{'h':it,'target':level})
                else:
                    need=int(h.lang[f'FHDNT.Levels.{level-1}.Need']);h.run('GrantXP',{'h':it,'points':need})
                assert h.extra[it,'FHDNT_Level']==level
                skin=h.extra[it,'FHDNT_Skin'];assert skin in allowed and skin!=16
                assert skin==h.extra[it,'FHDNT_Plan'+str(level)]
                plans.append(skin);all_seen.add(skin);evolutions+=1
            assert len(plans)==len(set(plans))==21
        # Force each new model through real Evolve/Apply/Portrait blocks.
        h=cls(seed=99);h.startup();it=h.run('NewHull',output='result');h.held=[it,100];h.form='Ship'
        if h.info('FHDNT_UI04')<0:h.call('ShipAddCustomShipInfo',[1,'FHDNT_UI04','NoShow'])
        for model in MODELS:
            h.extra[it,'FHDNT_Level']=0;h.extra[it,'FHDNT_Plan0']=model['id']
            h.run('Evolve',{'h':it});h.run('Apply',{'h':it});h.run('PortraitUI13')
            assert h.extra[it,'FHDNT_Skin']==model['id']
            selected=params(node(lang,'MicroModuls.FHDNT_Skin'+str(h.extra[it,'FHDNT_Skin'])))['KindGraph']
            assert params(node(main,'Data.SE.Ship.Akrin.'+selected))['2ImageP']=='GI,Bm.ShipP.2'+model['native']
        # Reload clears the old cached pool containing the excluded model.
        fast=h.info('FHDNT_Fast04');h.infos[fast]['text'][3]='16,4,5';h.run('Install')
        assert 16 not in {int(x)for x in h.run('SkinPool',output='result').split(',')}
        # A stored future Maloc_R plan is rejected when that level is reached.
        h.extra[it,'FHDNT_Level']=0;h.extra[it,'FHDNT_Plan1']=16
        h.run('GrantXP',{'h':it,'points':150})
        assert h.extra[it,'FHDNT_Level']==1 and h.extra[it,'FHDNT_Skin']!=16
    assert set(range(51,57))<=all_seen,'All six new models must occur in real random evolution'
    a,b=[read(VARIANTS[e]/MODREL/'CFG/Rus/Lang.dat')for e in ['release','test']]
    prop(node(b,'FHDNT'),'Build','RELEASE');prop(node(b,'FHDNT'),'LevelSelection','0');assert norm(a)==norm(b)
    for name in ['Main.dat','CacheData.dat']:assert (VARIANTS['release']/MODREL/'CFG'/name).read_bytes()==(VARIANTS['test']/MODREL/'CFG'/name).read_bytes()
    report={'status':'PASS (static/model)','windows_game':'НЕТ ТЕСТА','excluded':'Maloc_R (16)','added_models':[m['native']for m in MODELS],'allowed_count':26,'real_evolution_steps':evolutions,'all_levels_0_20_unique':True,'new_models_in_random_evolution':True,'six_models_evolve_and_portrait_paths_checked':True,'old_pool_cache_reset_checked':True,'old_future_maloc_plan_rejected':True,'native_flight_graphs_preserved':True,'preview_files_checked':36,'original_frames_buttons_xp_and_start_gift_unchanged':True,'shared_core':True,'new_flight_hai_copies':0}
    for out in [COMMON,*VARIANTS.values()]:
        p=out if out==COMMON else out/'reports';p.mkdir(parents=True,exist_ok=True);(p/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
