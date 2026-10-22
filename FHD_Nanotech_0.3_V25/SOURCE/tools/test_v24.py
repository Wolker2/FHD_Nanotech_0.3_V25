"""Execute actual new-game/load hooks and check delivery exactly once."""
import copy,json
from dat_codec import unpack,pack
from build_hotfix import node,params,group_metadata
from build_v16 import ROOT,MODREL,source
from build_v17 import prop
from build_v24 import BASES,VARIANTS,COMMON
from test_hotfix import load_model,assert_safe_shape

def read(p):return unpack(p.read_bytes())[0]
def norm(t):t=copy.deepcopy(t);group_metadata(t);return t

def main():
    Model,sector,vm=load_model(ROOT/'work/v13')
    class GiftHost(Model):
        version='v24_test'
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw);self.storage=[];self.storage_accepts=True;self.factory_fails=False;self.create_calls=0
            main=read(ROOT/'work'/self.version/MODREL/'CFG/Main.dat')
            for label,path in [('new','BV.OnStart.0DayScripts'),('load','BV.OnLoad.Runtime')]:
                self.ast[label]=vm.Parser('\n'.join(v for k,v in sorted(params(node(main,path)).items()))).body()
        def call(self,name,a):
            if name=='AddItemToStorage':
                if self.storage_accepts:self.storage.append(tuple(a))
                return 0 # Native procedure returns no success flag.
            if name=='FindItemInStorage':return next((i for i,x in enumerate(self.storage)if x[1]==a[0]),-1)
            if name=='ExecuteCodeFromString'and a[0]=='NewHull':
                self.create_calls+=1
                if self.factory_fails:return 0
            if name=='ShipStar':return 20000
            if name=='StarShips':return 0
            return super().call(name,a)
    h=GiftHost(seed=12);h.turn=61;h.run('new')
    assert len(h.storage)==1 and h.create_calls==1
    planet,it=h.storage[0]
    assert planet==h.currentplanet and h.held==[100]
    assert h.extra[it,'FHDNT_Mark']==1 and h.extra.get((it,'FHDNT_Level'),0)==0
    info=h.info('FHDNT_StartGift24');assert h.infos[info]['data'][1]==2 and h.infos[info]['data'][2]==it
    for _ in range(5):h.run('load');h.run('new');h.run('TryStartGift24')
    assert len(h.storage)==1 and h.create_calls==1
    # Selling/moving/removing the gift never grants a replacement.
    h.storage=[];h.currentplanet+=1;h.turn+=20;h.run('load');h.run('TryStartGift24');assert not h.storage and h.create_calls==1
    # Existing TEST saves never receive a gift on load or through Dispatch.
    old=GiftHost(seed=12);old.turn=100;old.run('load');old.form='StarMap';old.action=10;old.run('Dispatch')
    assert old.info('FHDNT_StartGift24')<0 and old.storage==[]
    # Planet initialization can be delayed. Pending state survives loading and
    # is completed through the ordinary dispatcher without opening Ship UI.
    d=GiftHost(seed=12);start_planet=d.currentplanet;d.currentplanet=0;d.turn=61;d.run('new')
    assert not d.storage and d.infos[d.info('FHDNT_StartGift24')]['data'][1]==1
    d.run('load');d.currentplanet=start_planet;d.form='StarMap';d.action=10;d.run('Dispatch')
    assert len(d.storage)==1 and d.form=='StarMap'
    d.run('Dispatch');assert len(d.storage)==1
    # Factory/storage failure leaves a pending marker, frees failed objects,
    # throttles retry for one turn, and marks done only after storage accepts.
    for failure in ['factory','storage']:
        f=GiftHost(seed=12);f.turn=61;original_items=set(f.items)
        if failure=='factory':f.factory_fails=True
        else:f.storage_accepts=False
        f.run('new');assert not f.storage and f.infos[f.info('FHDNT_StartGift24')]['data'][1]==1
        assert set(f.items)==original_items
        attempts=f.create_calls;f.run('TryStartGift24');assert f.create_calls==attempts
        f.factory_fails=False;f.storage_accepts=True;f.turn+=1;f.run('TryStartGift24')
        assert len(f.storage)==1 and f.infos[f.info('FHDNT_StartGift24')]['data'][1]==2
    class Release(GiftHost):version='v24_release'
    r=Release(seed=12);r.run('new');r.run('load');r.run('StartTestGift24');r.run('TryStartGift24')
    assert not r.storage and r.info('FHDNT_StartGift24')<0 and r.create_calls==0
    assert_safe_shape(vm,h.source['StartTestGift24']);assert_safe_shape(vm,h.source['TryStartGift24'])
    for s in h.source.values():vm.Parser(s).body()
    lr,lt=[read(VARIANTS[e]/MODREL/'CFG/Rus/Lang.dat')for e in ['release','test']]
    prop(node(lt,'FHDNT'),'Build','RELEASE');prop(node(lt,'FHDNT'),'LevelSelection','0');assert norm(lr)==norm(lt)
    assert (VARIANTS['release']/MODREL/'CFG/Main.dat').read_bytes()==(VARIANTS['test']/MODREL/'CFG/Main.dat').read_bytes()
    for edition,out in VARIANTS.items():
        before=read(BASES[edition]/MODREL/'CFG/Rus/Lang.dat');after=read(out/MODREL/'CFG/Rus/Lang.dat')
        for e in node(before,'FHDNT.Code')[1]:
            if e[2]not in ['Install','Dispatch']:assert norm(e[3])==norm(node(after,'FHDNT.Code.'+e[2])),e[2]
        # Only the new-game startup key differs in Main; OnLoad and every UI
        # element/callback remain identical to V23.
        bm=read(BASES[edition]/MODREL/'CFG/Main.dat');am=read(out/MODREL/'CFG/Main.dat')
        n=node(am,'BV.OnStart.0DayScripts');n[1]=[e for e in n[1]if e[2]!='91_FHDNT_Gift24'];assert norm(am)==norm(bm)
        for p in (BASES[edition]/'Mods').rglob('*'):
            if p.is_file()and all(not x.startswith('.')for x in p.relative_to(BASES[edition]).parts):
                rel=p.relative_to(BASES[edition])
                if rel not in [MODREL/'CFG/Main.dat',MODREL/'CFG/Rus/Lang.dat',MODREL/'ModuleInfo.txt']:assert p.read_bytes()==(out/rel).read_bytes()
        for name in ['Main.dat','Rus/Lang.dat']:
            t,m=unpack((out/MODREL/'CFG'/name).read_bytes());assert unpack(pack(t,m))[0]==t
    report={'status':'PASS (static/model)','windows_game':'НЕТ ТЕСТА','new_game_exactly_one_test_gift':True,'start_turn_61_checked':True,'level_zero_random_skin_factory_unchanged':True,'reload_and_repeated_hooks_no_duplicates':True,'old_saves_no_automatic_gift':True,'delayed_planet_and_retry_checked':True,'no_release_gift':True,'xp_frames_supply_and_ui_unchanged':True,'shared_core':True,'runtime_files_changed':['CFG/Main.dat','CFG/Rus/Lang.dat','ModuleInfo.txt']}
    for out in [COMMON,*VARIANTS.values()]:
        p=out if out==COMMON else out/'reports';p.mkdir(parents=True,exist_ok=True);(p/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
