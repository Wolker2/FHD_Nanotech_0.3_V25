"""V18: native-aware guards, isolated UI blocks, and Wormhole parent fix."""
import copy, json, shutil
from pathlib import Path
from dat_codec import unpack, pack, dump
from build_hotfix import node, params, setcode, group_metadata
from build_v16 import ROOT, MODREL, source
from build_v17 import at, control, prop, guard, HITPATH, MAINPATH

BASE=ROOT/'work/v17'
OUT=ROOT/'work/v18'
WHBASE=ROOT/'research18/wormhole/FHD_Wormhole'
WHREL=Path('Mods/FHD_MODS/FHD_Wormhole')
LEFTPATH=MAINPATH+(('Panel',1),('Panel',1),('Panel',0))

def ensure(t,path):
    for name,index in path:
        es=[e for e in t[1] if e[1]==2 and e[2]==name]
        while len(es)<=index:
            e=[b'',2,name,[1,[]]];t[1].append(e);es.append(e)
        t=es[index][3]
    return t

def wrap(t,name,kind,child):t[1].append([b'',2,name,[1,[[b'',2,kind,child]]]])

WAREHOUSE="""
dword nt_storage_planet=0;
dword nt_storage_hull=0;
int nt_storage_index=-1;
if(!Player()) { exit; }
if(CurrentForm()!='Ship') { exit; }
if(FormCurShip()!=Player()) { exit; }
nt_storage_planet=GetShipPlanet(Player());
if(!nt_storage_planet)
{
MessageBox('Для выдачи корпуса на склад нужно находиться на планете');
exit;
}
nt_storage_hull=ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.NewHull'),'result');
if(!nt_storage_hull)
{
SFT('[FHDNT V18] не удалось создать корпус для склада');
MessageBox('Не удалось создать Nanotech. Проверьте установку ресурсов мода.');
exit;
}
AddItemToStorage(nt_storage_planet,nt_storage_hull);
nt_storage_index=FindItemInStorage(nt_storage_hull);
if(nt_storage_index<0)
{
FreeItem(nt_storage_hull);
SFT('[FHDNT V18] корпус не принят складом');
MessageBox('Не удалось добавить корпус на склад текущей планеты');
exit;
}
InterfaceState('Ship','FHDNT_LevelPicker03',0);
ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.ModalInput'));
SFT('Новый Nanotech уровня 0 добавлен на склад текущей планеты');
UpdateFormShip();
"""

def build():
    main,mm=unpack((BASE/MODREL/'CFG/Main.dat').read_bytes())
    lang,lm=unpack((BASE/MODREL/'CFG/Rus/Lang.dat').read_bytes())
    # Unknown block names are namespaces: native LoadConfiguredChildren recurses
    # through them with the SAME owner. This avoids merging GraphButton[0] with
    # CustomBridgeInto and its native callback/visibility changes.
    owner=at(main,MAINPATH)
    button=copy.deepcopy(control(main,'FHDNT_StorageButton17'))
    owner[1][:]=[e for e in owner[1] if not(e[1]==2 and params(e[3]).get('Name')=='FHDNT_StorageButton17')]
    prop(button,'MouseBlocking','True')
    wrap(owner,'FHDNT_StorageUI18','GraphButton',button)
    for name in ['FHDNT_ConfigHit17','FHDNT_StorageHit17']:
        prop(control(main,name),'Active','True')
    # Change only hit testing, keeping native images, captions, callbacks and
    # geometry. Rect accepts the caption pixels even where image alpha is zero.
    for index in range(3):
        prop(ensure(main,LEFTPATH+(('GraphButton',index),)),'KindHit','Rect')
    create=control(main,'FHDNT_NewTestHull')
    prop(create,'Caption','Создать корпус на склад')
    node(create,'OnPressCode')[1]=[[b'',1,'0000',"ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.AddWarehouse17'));"]]
    setcode(lang,'AddWarehouse17',WAREHOUSE)
    setcode(lang,'NewTestHull',"ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.AddWarehouse17'));")
    ui=source(lang,'UI')
    old="InterfaceState('Ship','FHDNT_Test',3); InterfaceState('Ship','FHDNT_NewTestHull',0);"
    assert ui.count(old)==1
    ui=ui.replace(old,"InterfaceState('Ship','FHDNT_Test',3);\nif(GetShipPlanet(Player())) { InterfaceState('Ship','FHDNT_NewTestHull',3); } else { InterfaceState('Ship','FHDNT_NewTestHull',2); }")
    setcode(lang,'UI',ui)
    setcode(lang,'Install',source(lang,'Install').replace('[FHDNT V17]','[FHDNT V18]'))
    # Wormhole's child controls used to inherit Forsage.Active, which the game
    # sets false whenever the viewed hull lacks an afterburner slot. Keep the
    # same local origin/depth, graphics, control names, and original scripts in
    # an independent sibling panel. Native Forsage remains entirely native.
    wh,wm=unpack((WHBASE/'CFG/Main.dat').read_bytes())
    left=at(wh,LEFTPATH);old_forsage=at(wh,LEFTPATH+(('Panel',0),))
    controls=[copy.deepcopy(e) for e in old_forsage[1] if e[1]==2 and params(e[3]).get('Name','').startswith('FHDWormhole')]
    assert len(controls)==4
    independent=guard('FHDWormholePanel18','6,201,-1','53,215')
    # Its parent is already centered by the native layout; no extra correction.
    independent[1][:]=[e for e in independent[1] if not e[2].startswith('PosAutoCorrection')]
    prop(independent,'Active','True');independent[1].extend(controls)
    left[1][:]=[e for e in left[1] if not(e[1]==2 and e[3] is old_forsage)]
    wrap(left,'FHDWormhole_UI18','Panel',independent)
    whhit=guard('FHDWormholeHit18','205,406,8','17,17');prop(whhit,'Active','True')
    wrap(ensure(wh,HITPATH),'FHDWormhole_ClickGuard18','Panel',whhit)
    for rel,t,meta in [(MODREL/'CFG/Main.dat',main,mm),(MODREL/'CFG/Rus/Lang.dat',lang,lm),(WHREL/'CFG/Main.dat',wh,wm)]:
        group_metadata(t);p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(pack(t,meta))
        p=OUT/'SOURCE'/rel.with_suffix('.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(t)+'\n')
    p=OUT/MODREL/'CFG/CacheData.dat';shutil.copyfile(BASE/MODREL/'CFG/CacheData.dat',p)
    (OUT/MODREL/'ModuleInfo.txt').write_text((BASE/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V17 TEST','V18 TEST'),encoding='utf-16')
    print(json.dumps({'built':'V18','frame_images_and_geometry_changed':False,'wormhole_main_only':True}))

if __name__=='__main__':build()
