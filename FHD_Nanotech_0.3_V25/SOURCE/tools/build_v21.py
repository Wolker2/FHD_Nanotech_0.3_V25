"""One common core and GUI for RELEASE/TEST; move only three tiers' RH arrows."""
import copy,json,re,shutil
from pathlib import Path
from dat_codec import unpack,pack,dump,walk
from build_hotfix import node,params,setcode,group_metadata
from build_v16 import ROOT,MODREL,source,addcode
from build_v17 import prop

BASE=ROOT/'work/v19'
COMMON=ROOT/'work/v21_common'
VARIANTS={'release':ROOT/'work/v21_release','test':ROOT/'work/v21_test'}
DEBUG={'FHDNT_Test','FHDNT_StorageButton17','FHDNT_NewTestHull'}|{f'FHDNT_Choose{i}'for i in range(21)}
TARGETS={1:((299,260,-1),(299,283,-1)),4:((295,243,-1),(295,266,-1)),5:((294,242,-1),(294,265,-1))}

def gated(s,level=False):
    m=re.match(r'^(?:(?:dword|int|str)\s+[^;]+;\s*)*',s)
    p=m.end();condition="CT('FHDNT.Build')!='TEST'"
    if level:condition+=" || CT('FHDNT.LevelSelection')!=1"
    return s[:p]+f'\nif({condition}) {{ exit; }}\n'+s[p:]

RH_CODE="""
int nt_rh_tier=0;
int nt_rh_level=-1;
int nt_rh_info=-1;
int nt_rh_x=0;
int nt_rh_up=0;
int nt_rh_down=0;
int nt_rh_old_down_y=0;
dword nt_rh_hull=0;
if(CurrentForm()!='Ship') { exit; }
if(!Player()) { exit; }
if(FormCurShip()==Player())
{
nt_rh_hull=ShipItems(Player(),0);
if(nt_rh_hull)
{
if(ItemExtraSpecialsCountByType(nt_rh_hull,FindBonusByNameInCfg('FHDNT_Mark'))==1)
{
nt_rh_level=ItemExtraSpecialsCountByType(nt_rh_hull,FindBonusByNameInCfg('FHDNT_Level'));
if(nt_rh_level>=0 && nt_rh_level<5) { nt_rh_tier=1; }
if(nt_rh_level>=15 && nt_rh_level<20) { nt_rh_tier=4; }
if(nt_rh_level==20) { nt_rh_tier=5; }
}
}
}
nt_rh_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_RH21');
if(nt_rh_tier==0)
{
if(nt_rh_info>=0)
{
if(ShipCustomShipInfoTextData(Player(),nt_rh_info,2)=='1')
{
nt_rh_old_down_y=ShipCustomShipInfoTextData(Player(),nt_rh_info,1);
InterfacePos('Ship','UpRH',ShipCustomShipInfoData(Player(),nt_rh_info,1),ShipCustomShipInfoData(Player(),nt_rh_info,2),-1);
InterfacePos('Ship','DownRH',ShipCustomShipInfoData(Player(),nt_rh_info,3),nt_rh_old_down_y,-1);
ShipCustomShipInfoTextData(Player(),nt_rh_info,2,'0');
}
}
exit;
}
if(nt_rh_info<0)
{
ShipAddCustomShipInfo(Player(),'FHDNT_RH21','NoShow');
nt_rh_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_RH21');
}
if(ShipCustomShipInfoTextData(Player(),nt_rh_info,2)!='1')
{
ShipCustomShipInfoData(Player(),nt_rh_info,1,UICheckElement('Ship','UpRH','PosX'));
ShipCustomShipInfoData(Player(),nt_rh_info,2,UICheckElement('Ship','UpRH','PosY'));
ShipCustomShipInfoData(Player(),nt_rh_info,3,UICheckElement('Ship','DownRH','PosX'));
ShipCustomShipInfoTextData(Player(),nt_rh_info,1,''+UICheckElement('Ship','DownRH','PosY'));
ShipCustomShipInfoTextData(Player(),nt_rh_info,2,'1');
}
if(nt_rh_tier==1) { nt_rh_x=299; nt_rh_up=260; nt_rh_down=283; }
if(nt_rh_tier==4) { nt_rh_x=295; nt_rh_up=243; nt_rh_down=266; }
if(nt_rh_tier==5) { nt_rh_x=294; nt_rh_up=242; nt_rh_down=265; }
if(UICheckElement('Ship','UpRH','PosX')!=nt_rh_x || UICheckElement('Ship','UpRH','PosY')!=nt_rh_up)
{
InterfacePos('Ship','UpRH',nt_rh_x,nt_rh_up,-1);
}
if(UICheckElement('Ship','DownRH','PosX')!=nt_rh_x || UICheckElement('Ship','DownRH','PosY')!=nt_rh_down)
{
InterfacePos('Ship','DownRH',nt_rh_x,nt_rh_down,-1);
}
"""

EDITION="""
if(CT('FHDNT.Build')!='TEST' || CT('FHDNT.LevelSelection')!=1)
{
InterfaceState('Ship','FHDNT_Test',0);
InterfaceState('Ship','FHDNT_LevelPicker03',0);
}
if(CT('FHDNT.Build')!='TEST')
{
InterfaceState('Ship','FHDNT_StorageButton17',0);
InterfaceState('Ship','FHDNT_NewTestHull',0);
}
ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.ModalInput'));
"""

def build():
    main,mm=unpack((BASE/MODREL/'CFG/Main.dat').read_bytes())
    lang,lm=unpack((BASE/MODREL/'CFG/Rus/Lang.dat').read_bytes())
    addcode(lang,'RemoteHoldButtons21',RH_CODE);addcode(lang,'EditionUI21',EDITION)
    info=[1,[[b'',1,k,v]for k,v in {'Description':'NoShow','Icon':'0','Name':''}.items()]]
    node(lang,'ShipInfo.AddInfo.CustomInfos')[1].append([b'',2,'FHDNT_RH21',info])
    frames=source(lang,'FramesUI');anchor="str nt_scope_image='';";assert frames.count(anchor)==1
    setcode(lang,'FramesUI',frames.replace(anchor,anchor+"\nExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.RemoteHoldButtons21'));"))
    for name in ['TestLevel','AddWarehouse17','NewTestHull']:setcode(lang,name,gated(source(lang,name),name=='TestLevel'))
    for path,e in walk(main):
        if e[1]!=2:continue
        name=params(e[3]).get('Name','')
        if name in DEBUG:
            cb=node(e[3],'OnPressCode');s='\n'.join(x[3]for x in cb[1])
            s=gated(s,name=='FHDNT_Test' or name.startswith('FHDNT_Choose'))
            cb[1]=[[b'',1,f'{i:04d}',line.strip()]for i,line in enumerate(s.strip().splitlines())if line.strip()]
            if name in {'FHDNT_Test','FHDNT_NewTestHull','FHDNT_StorageButton17'}:prop(e[3],'Active','False')
    ui=source(lang,'UI')
    ui=ui.replace("if(GetShipPlanet(Player())) { InterfaceState('Ship','FHDNT_StorageButton17',3); }", "if(CT('FHDNT.Build')=='TEST' && GetShipPlanet(Player())) { InterfaceState('Ship','FHDNT_StorageButton17',3); }")
    ui=ui.replace("InterfaceState('Ship','FHDNT_Test',3);", "if(CT('FHDNT.Build')=='TEST' && CT('FHDNT.LevelSelection')==1) { InterfaceState('Ship','FHDNT_Test',3); } else { InterfaceState('Ship','FHDNT_Test',0); }")
    ui=ui.replace("if(GetShipPlanet(Player())) { InterfaceState('Ship','FHDNT_NewTestHull',3); } else { InterfaceState('Ship','FHDNT_NewTestHull',2); }", "if(CT('FHDNT.Build')=='TEST' && GetShipPlanet(Player())) { InterfaceState('Ship','FHDNT_NewTestHull',3); } else { InterfaceState('Ship','FHDNT_NewTestHull',0); }")
    setcode(lang,'UI',"ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.EditionUI21'));\n"+ui)
    install=source(lang,'Install').replace("SFT('[FHDNT V19] загружен');","SFT('[FHDNT V21 '+CT('FHDNT.Build')+'] загружен');")
    assert '[FHDNT V19]'not in install
    setcode(lang,'Install',install+"\nExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.EditionUI21'));")
    group_metadata(main);group_metadata(lang);COMMON.mkdir(parents=True,exist_ok=True)
    (COMMON/'Main.dat').write_bytes(pack(main,mm));(COMMON/'Lang.txt').write_text(dump(lang)+'\n')
    for edition,out in VARIANTS.items():
        shutil.copytree(BASE/'Mods',out/'Mods',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.*'))
        own=copy.deepcopy(lang);prop(node(own,'FHDNT'),'Build','TEST'if edition=='test'else'RELEASE');prop(node(own,'FHDNT'),'LevelSelection','1'if edition=='test'else'0');group_metadata(own)
        (out/MODREL/'CFG/Main.dat').write_bytes(pack(main,mm));(out/MODREL/'CFG/Rus/Lang.dat').write_bytes(pack(own,lm))
        mi=(BASE/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V19 SLIM TEST','V21 '+edition.upper())
        (out/MODREL/'ModuleInfo.txt').write_text(mi,encoding='utf-16')
        for filename,t in [('Main.txt',main),('Rus/Lang.txt',own)]:
            p=out/'SOURCE/CFG'/filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(t)+'\n')
    print(json.dumps({'version':'V21','editions':list(VARIANTS),'tier_positions':TARGETS,'shared_main_dat':True}))

if __name__=='__main__':build()
