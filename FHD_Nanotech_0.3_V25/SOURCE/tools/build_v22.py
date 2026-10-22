"""Correct InterfacePos delta semantics and migrate saved V21 overrides."""
import copy,json,shutil
from dat_codec import unpack,pack,dump
from build_hotfix import node,params,setcode,group_metadata
from build_v16 import ROOT,MODREL,source,addcode
from build_v21 import TARGETS

BASES={e:ROOT/f'work/v21_{e}'for e in ['release','test']}
VARIANTS={e:ROOT/f'work/v22_{e}'for e in ['release','test']}
COMMON=ROOT/'work/v22_common'
DELTAS={1:((-2,-14,0),(-2,-14,0)),4:((-6,-31,0),(-6,-31,0)),5:((-7,-32,0),(-7,-32,0))}

MIGRATION="""
int nt_rhm_info=-1;
if(!Player()) { exit; }
nt_rhm_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_RH21');
if(nt_rhm_info>=0)
{
if(ShipCustomShipInfoTextData(Player(),nt_rhm_info,3)!='22')
{
InterfacePos('Ship','UpRH',0,0,0);
InterfacePos('Ship','DownRH',0,0,0);
ShipCustomShipInfoTextData(Player(),nt_rhm_info,1,'');
ShipCustomShipInfoTextData(Player(),nt_rhm_info,2,'0');
ShipCustomShipInfoTextData(Player(),nt_rhm_info,3,'22');
}
}
"""

RH="""
int nt_rh_tier=0;
int nt_rh_level=-1;
int nt_rh_info=-1;
int nt_rh_dx=0;
int nt_rh_dy=0;
dword nt_rh_hull=0;
if(CurrentForm()!='Ship') { exit; }
if(!Player()) { exit; }
ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.RemoteHoldMigration22'));
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
InterfacePos('Ship','UpRH',0,0,0);
InterfacePos('Ship','DownRH',0,0,0);
ShipCustomShipInfoTextData(Player(),nt_rh_info,1,'');
ShipCustomShipInfoTextData(Player(),nt_rh_info,2,'0');
}
}
exit;
}
if(nt_rh_info<0)
{
ShipAddCustomShipInfo(Player(),'FHDNT_RH21','NoShow');
nt_rh_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_RH21');
ShipCustomShipInfoTextData(Player(),nt_rh_info,3,'22');
}
if(nt_rh_tier==1) { nt_rh_dx=-2; nt_rh_dy=-14; }
if(nt_rh_tier==4) { nt_rh_dx=-6; nt_rh_dy=-31; }
if(nt_rh_tier==5) { nt_rh_dx=-7; nt_rh_dy=-32; }
if(ShipCustomShipInfoTextData(Player(),nt_rh_info,2)!='1' || ShipCustomShipInfoTextData(Player(),nt_rh_info,1)!=''+nt_rh_tier)
{
InterfacePos('Ship','UpRH',nt_rh_dx,nt_rh_dy,0);
InterfacePos('Ship','DownRH',nt_rh_dx,nt_rh_dy,0);
ShipCustomShipInfoTextData(Player(),nt_rh_info,1,''+nt_rh_tier);
ShipCustomShipInfoTextData(Player(),nt_rh_info,2,'1');
}
"""

def build():
    for edition,out in VARIANTS.items():
        base=BASES[edition]
        shutil.copytree(base/'Mods',out/'Mods',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.*'))
        lang,meta=unpack((base/MODREL/'CFG/Rus/Lang.dat').read_bytes())
        setcode(lang,'RemoteHoldButtons21',RH);addcode(lang,'RemoteHoldMigration22',MIGRATION)
        install=source(lang,'Install').replace('[FHDNT V21 ','[FHDNT V22 ')
        setcode(lang,'Install',install+"\nExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.RemoteHoldMigration22'));")
        group_metadata(lang);(out/MODREL/'CFG/Rus/Lang.dat').write_bytes(pack(lang,meta))
        mi=(base/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V21 ','V22 ')
        (out/MODREL/'ModuleInfo.txt').write_text(mi,encoding='utf-16')
        p=out/'SOURCE/CFG/Rus/Lang.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(lang)+'\n')
    COMMON.mkdir(parents=True,exist_ok=True)
    print(json.dumps({'version':'V22','editions':list(VARIANTS),'deltas':DELTAS,'saved_V21_migration':True}))

if __name__=='__main__':build()
