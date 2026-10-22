"""One TEST-only warehouse hull, armed exclusively by the new-game hook."""
import json,shutil
from dat_codec import unpack,pack,dump
from build_hotfix import node,setcode,group_metadata
from build_v16 import ROOT,MODREL,source,addcode
from build_v17 import prop
BASES={e:ROOT/f'work/v23_{e}'for e in ['release','test']}
VARIANTS={e:ROOT/f'work/v24_{e}'for e in ['release','test']}
COMMON=ROOT/'work/v24_common'

START="""
int nt_gift_info=-1;
if(CT('FHDNT.Build')!='TEST') { exit; }
if(!Player()) { exit; }
nt_gift_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_StartGift24');
if(nt_gift_info<0)
{
ShipAddCustomShipInfo(Player(),'FHDNT_StartGift24','NoShow',1,0,0);
}
ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.TryStartGift24'));
"""
TRY="""
int nt_gift_info=-1;
int nt_gift_index=-1;
dword nt_gift_planet=0;
dword nt_gift_hull=0;
if(CT('FHDNT.Build')!='TEST') { exit; }
if(!Player()) { exit; }
nt_gift_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_StartGift24');
if(nt_gift_info<0) { exit; }
if(ShipCustomShipInfoData(Player(),nt_gift_info,1)!=1) { exit; }
nt_gift_planet=GetShipPlanet(Player());
if(!nt_gift_planet) { exit; }
if(CurTurn()<ShipCustomShipInfoData(Player(),nt_gift_info,3)) { exit; }
nt_gift_hull=ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.NewHull'),'result');
if(!nt_gift_hull)
{
ShipCustomShipInfoData(Player(),nt_gift_info,3,CurTurn()+1);
exit;
}
AddItemToStorage(nt_gift_planet,nt_gift_hull);
nt_gift_index=FindItemInStorage(nt_gift_hull);
if(nt_gift_index<0)
{
FreeItem(nt_gift_hull);
ShipCustomShipInfoData(Player(),nt_gift_info,3,CurTurn()+1);
SFT('[FHDNT TEST] склад не принял стартовый корпус');
exit;
}
ShipCustomShipInfoData(Player(),nt_gift_info,1,2);
ShipCustomShipInfoData(Player(),nt_gift_info,2,Id(nt_gift_hull));
ShipCustomShipInfoData(Player(),nt_gift_info,3,Id(nt_gift_planet));
SFT('[FHDNT TEST] стартовый Nanotech добавлен на склад');
"""

def build():
    COMMON.mkdir(parents=True,exist_ok=True)
    for edition,out in VARIANTS.items():
        base=BASES[edition]
        shutil.copytree(base/'Mods',out/'Mods',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.*'))
        main,mm=unpack((base/MODREL/'CFG/Main.dat').read_bytes())
        lang,lm=unpack((base/MODREL/'CFG/Rus/Lang.dat').read_bytes())
        prop(node(main,'BV.OnStart.0DayScripts'),'91_FHDNT_Gift24',"ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.StartTestGift24'));")
        addcode(lang,'StartTestGift24',START);addcode(lang,'TryStartGift24',TRY)
        node(lang,'ShipInfo.AddInfo.CustomInfos')[1].append([b'',2,'FHDNT_StartGift24',[1,[[b'',1,k,v]for k,v in {'Description':'NoShow','Icon':'0','Name':''}.items()]]])
        dispatch=source(lang,'Dispatch')
        anchor='if(nt_dispatch_action==t_OnPlayerUseMM)';assert dispatch.count(anchor)==1
        setcode(lang,'Dispatch',dispatch.replace(anchor,"ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.TryStartGift24'));\n"+anchor))
        setcode(lang,'Install',source(lang,'Install').replace('[FHDNT V23 ','[FHDNT V24 '))
        for name,t,m in [('Main.dat',main,mm),('Rus/Lang.dat',lang,lm)]:
            group_metadata(t);(out/MODREL/'CFG'/name).write_bytes(pack(t,m))
            p=out/'SOURCE/CFG'/name.replace('.dat','.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(t)+'\n')
        mi=(base/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V23 ','V24 ')
        (out/MODREL/'ModuleInfo.txt').write_text(mi,encoding='utf-16')
    print(json.dumps({'version':'V24','editions':list(VARIANTS),'gift':'One level-0 Nanotech in player storage at the starting planet, TEST new games only'}))

if __name__=='__main__':build()
