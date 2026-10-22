"""Minimal V16 overlay: native click guard, hover aliases, warehouse button."""
import copy, json, shutil
from pathlib import Path
from dat_codec import unpack, pack, dump
from build_hotfix import node, params, setcode, group_metadata
from build_v16 import ROOT, MODREL, source, addcode

BASE=ROOT/'work/v16'
OUT=ROOT/'work/v17'
HITPATH=(('ML',0),('Ship',0),('Panel',0),('Panel',3))
MAINPATH=HITPATH[:-1]

def at(t,path):
    for name,index in path:
        t=[e[3] for e in t[1] if e[1]==2 and e[2]==name][index]
    return t

def prop(t,k,v):
    for e in t[1]:
        if e[1]==1 and e[2]==k:e[3]=v;return
    t[1].append([b'',1,k,v])

def control(t,name):
    if params(t).get('Name')==name:return t
    for e in t[1]:
        if e[1]==2:
            r=control(e[3],name)
            if r is not None:return r

def guard(name,pos,size):
    values=dict(Active='False',MouseBlocking='False',MouseBlockingTest='False',Name=name,
                Pos=pos,Size=size,PosAutoCorrection='True',
                PosAutoCorrectionXCoef='0.5',PosAutoCorrectionYCoef='0.5')
    return [1,[[b'',1,k,v] for k,v in values.items()]]

WAREHOUSE="""
dword nt_storage_planet=0;
dword nt_storage_hull=0;
if(!Player()) { exit; }
if(CurrentForm()!='Ship') { exit; }
if(FormCurShip()!=Player()) { exit; }
nt_storage_planet=GetShipPlanet(Player());
if(!nt_storage_planet)
{
SFT('Для выдачи корпуса на склад нужно находиться на планете');
exit;
}
nt_storage_hull=ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.NewHull'),'result');
if(!nt_storage_hull) { exit; }
AddItemToStorage(nt_storage_planet,nt_storage_hull);
SFT('Новый Nanotech уровня 0 добавлен на склад текущей планеты');
UpdateFormShip();
"""

def build():
    main,mm=unpack((BASE/MODREL/'CFG/Main.dat').read_bytes())
    cache,cm=unpack((ROOT/'work/v15'/MODREL/'CFG/CacheData.dat').read_bytes(),True)
    lang,lm=unpack((BASE/MODREL/'CFG/Rus/Lang.dat').read_bytes())
    # The native close handler checks direct children by rectangle. This covers
    # exactly the union of Compl0/1/2, independent of animated frame alpha.
    at(main,HITPATH)[1].append([b'',2,'Panel',guard('FHDNT_ConfigHit17','426,37,8','70,26')])
    at(main,HITPATH)[1].append([b'',2,'Panel',guard('FHDNT_StorageHit17','331,727,8','152,20')])
    button=copy.deepcopy(control(main,'FHDNT_Test'))
    for k,v in dict(Name='FHDNT_StorageButton17',Caption='Корпус на склад',Pos='331,727,-2',
                    Active='False',PosAutoCorrection='True',PosAutoCorrectionXCoef='0.5',PosAutoCorrectionYCoef='0.5').items():prop(button,k,v)
    node(button,'OnPressCode')[1]=[[b'',1,'0000',"ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.AddWarehouse17'));"]]
    at(main,MAINPATH)[1].append([b'',2,'GraphButton',button])
    formcache=node(cache,'Bm.FormShip2')
    for mode in (1,2):
        key=f'{mode}AI_1001'
        assert key+'L' not in params(formcache)
        formcache[1].append([b'',1,key+'L',params(formcache)[key]])
    addcode(lang,'AddWarehouse17',WAREHOUSE)
    ui=source(lang,'UI')
    for condition in ("if(CurrentForm()!='Ship')", "if(FormCurShip()!=Player())"):
        anchor=condition+'\n{'
        assert ui.count(anchor)==1
        ui=ui.replace(anchor,anchor+"\nInterfaceState('Ship','FHDNT_StorageButton17',0);")
    marker="dword nt_hull=ShipItems(Player(),0);"
    assert ui.count(marker)==1
    ui=ui.replace(marker,"if(GetShipPlanet(Player())) { InterfaceState('Ship','FHDNT_StorageButton17',3); } else { InterfaceState('Ship','FHDNT_StorageButton17',0); }\n"+marker)
    setcode(lang,'UI',ui)
    setcode(lang,'Install',source(lang,'Install').replace('[FHDNT V16]','[FHDNT V17]'))
    for filename,t,meta in [('Main.dat',main,mm),('CacheData.dat',cache,cm),('Rus/Lang.dat',lang,lm)]:
        group_metadata(t)
        p=OUT/MODREL/'CFG'/filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(pack(t,meta))
        p=OUT/'SOURCE/CFG'/filename.replace('.dat','.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(t)+'\n')
    (OUT/MODREL/'ModuleInfo.txt').write_text((BASE/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V16 TEST','V17 TEST'),encoding='utf-16')
    print(json.dumps({'built':'V17','graphics_changed':False,'frame_code_changed':False,'runtime_files':4}))

if __name__=='__main__':build()
