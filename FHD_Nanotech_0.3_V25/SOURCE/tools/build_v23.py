"""Apply the approved XP balance to the shared V22 core."""
import copy,json,shutil
from dat_codec import unpack,pack,dump
from build_hotfix import node,params,setcode,group_metadata
from build_v16 import ROOT,MODREL,source,addcode
from build_v17 import prop

BASES={e:ROOT/f'work/v22_{e}'for e in ['release','test']}
VARIANTS={e:ROOT/f'work/v23_{e}'for e in ['release','test']}
COMMON=ROOT/'work/v23_common'
BALANCE={
    'Dominator':{0:2500,1:250,2:200,3:150,4:100,5:80,6:300,7:60},
    'Klissan':{1:170,2:125,3:95,4:75,5:55},
    'Pirate':dict(enumerate([55,70,80,100,125,150,200,250])),
    'Warrior':dict(enumerate([55,70,80,100,125,150,200,250])),
    'Ranger':dict(enumerate([45,60,70,90,100,125,150,200])),
    'Transport':dict(enumerate([20,30,40,50,60,70,80,90])),
    'Machpella':1500,
}
REWARD="""
int result=0;
int nt_reward_rank=max(0,min(7,rank));
if(tag=='Machpella') { result=CT('FHDNT.XP23.Machpella'); exit; }
if(tag=='Klissan1') { result=CT('FHDNT.XP23.Klissan.1'); exit; }
if(tag=='Klissan2') { result=CT('FHDNT.XP23.Klissan.2'); exit; }
if(tag=='Klissan3') { result=CT('FHDNT.XP23.Klissan.3'); exit; }
if(tag=='Klissan4') { result=CT('FHDNT.XP23.Klissan.4'); exit; }
if(tag=='Klissan5') { result=CT('FHDNT.XP23.Klissan.5'); exit; }
if(tag=='Smuggler') { result=CT('FHDNT.XP23.Pirate.'+nt_reward_rank); exit; }
if(kind==t_Kling)
{
if(subtype>=0 && subtype<=7) { result=CT('FHDNT.XP23.Dominator.'+subtype); }
exit;
}
if(kind==t_Pirate) { result=CT('FHDNT.XP23.Pirate.'+nt_reward_rank); exit; }
if(kind==t_Warrior) { result=CT('FHDNT.XP23.Warrior.'+nt_reward_rank); exit; }
if(kind==t_Ranger) { result=CT('FHDNT.XP23.Ranger.'+nt_reward_rank); exit; }
if(kind==t_Transport) { result=CT('FHDNT.XP23.Transport.'+nt_reward_rank); }
"""
# Record a rank while the victim pointer is still valid. Award only after the
# confirmed PlayerKillsShip event, through the existing duplicate guard.
CAPTURE="""
dword nt_capture_victim=0;
dword nt_capture_hull=0;
int nt_capture_kind=-1;
int nt_capture_rank=0;
int nt_capture_info=-1;
str nt_capture_key='';
str nt_capture_pending='';
if(!Player()) { exit; }
if(ScriptItemActShip()!=Player()) { exit; }
nt_capture_hull=ShipItems(Player(),0);
if(!nt_capture_hull) { exit; }
if(ItemExtraSpecialsCountByType(nt_capture_hull,FindBonusByNameInCfg('FHDNT_Mark'))!=1) { exit; }
nt_capture_victim=ScriptItemActObject1();
if(!nt_capture_victim || nt_capture_victim==Player()) { exit; }
nt_capture_kind=ShipTypeN(nt_capture_victim);
if(nt_capture_kind!=t_Ranger && nt_capture_kind!=t_Pirate && nt_capture_kind!=t_Warrior && nt_capture_kind!=t_Transport) { exit; }
if(nt_capture_kind==t_Pirate || ShipType(nt_capture_victim)=='Smuggler')
{ nt_capture_rank=GetShipPirateRank(nt_capture_victim); }
else { nt_capture_rank=ShipRank(nt_capture_victim); }
nt_capture_rank=max(0,min(7,nt_capture_rank));
nt_capture_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_XP23');
if(nt_capture_info<0)
{
ShipAddCustomShipInfo(Player(),'FHDNT_XP23','NoShow');
nt_capture_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_XP23');
}
nt_capture_key='|'+CurTurn()+':'+Id(ShipStar(nt_capture_victim))+':'+Id(nt_capture_victim)+':'+nt_capture_rank+'|';
nt_capture_pending=ShipCustomShipInfoTextData(Player(),nt_capture_info,1);
if(findsubstr(nt_capture_pending,nt_capture_key)!=0)
{ ShipCustomShipInfoTextData(Player(),nt_capture_info,1,nt_capture_key+nt_capture_pending); }
"""
# Explosion damage uses a separate engine path without an attacker fatal event.
# One local-system snapshot per turn supplies ranks for that path; fatal-hit
# metadata takes priority. No galaxy-wide scans or modifications of NPCs.
CACHE="""
dword nt_cache_hull=0;
dword nt_cache_star=0;
dword nt_cache_ship=0;
int nt_cache_info=-1;
int nt_cache_i=0;
int nt_cache_kind=-1;
int nt_cache_rank=0;
str nt_cache_scope='';
str nt_cache_list='';
if(!Player()) { exit; }
nt_cache_hull=ShipItems(Player(),0);
if(!nt_cache_hull) { exit; }
if(ItemExtraSpecialsCountByType(nt_cache_hull,FindBonusByNameInCfg('FHDNT_Mark'))!=1) { exit; }
nt_cache_star=ShipStar(Player());
if(!nt_cache_star) { exit; }
nt_cache_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_XP23');
if(nt_cache_info<0)
{
ShipAddCustomShipInfo(Player(),'FHDNT_XP23','NoShow');
nt_cache_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_XP23');
}
nt_cache_scope=''+CurTurn()+':'+Id(nt_cache_star);
if(force!=1 && ShipCustomShipInfoTextData(Player(),nt_cache_info,3)==nt_cache_scope) { exit; }
for(nt_cache_i=0;nt_cache_i<StarShips(nt_cache_star);nt_cache_i=nt_cache_i+1)
{
nt_cache_ship=StarShips(nt_cache_star,nt_cache_i);
if(!nt_cache_ship || nt_cache_ship==Player()) { continue; }
nt_cache_kind=ShipTypeN(nt_cache_ship);
if(nt_cache_kind!=t_Ranger && nt_cache_kind!=t_Pirate && nt_cache_kind!=t_Warrior && nt_cache_kind!=t_Transport) { continue; }
if(nt_cache_kind==t_Pirate || ShipType(nt_cache_ship)=='Smuggler')
{ nt_cache_rank=GetShipPirateRank(nt_cache_ship); }
else { nt_cache_rank=ShipRank(nt_cache_ship); }
nt_cache_rank=max(0,min(7,nt_cache_rank));
nt_cache_list=nt_cache_list+'|'+CurTurn()+':'+Id(nt_cache_star)+':'+Id(nt_cache_ship)+':'+nt_cache_rank+'|';
}
if(force==1)
{
ShipCustomShipInfoTextData(Player(),nt_cache_info,1,nt_cache_list+ShipCustomShipInfoTextData(Player(),nt_cache_info,1));
}
else
{
ShipCustomShipInfoTextData(Player(),nt_cache_info,2,nt_cache_list);
ShipCustomShipInfoTextData(Player(),nt_cache_info,3,nt_cache_scope);
}
"""

def build():
    COMMON.mkdir(parents=True,exist_ok=True)
    for edition,out in VARIANTS.items():
        base=BASES[edition]
        shutil.copytree(base/'Mods',out/'Mods',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.*'))
        lang,meta=unpack((base/MODREL/'CFG/Rus/Lang.dat').read_bytes())
        xp=[1,[]]
        for name,values in BALANCE.items():
            if isinstance(values,dict):xp[1].append([b'',2,name,[1,[[b'',1,str(k),str(v)]for k,v in values.items()]]])
            else:xp[1].append([b'',1,name,str(values)])
        node(lang,'FHDNT')[1].append([b'',2,'XP23',xp])
        for name,s in [('KillReward23',REWARD),('CaptureKillRank23',CAPTURE),('CacheKillRanks23',CACHE)]:addcode(lang,name,s)
        infos=node(lang,'ShipInfo.AddInfo.CustomInfos')
        infos[1].append([b'',2,'FHDNT_XP23',[1,[[b'',1,k,v]for k,v in {'Description':'NoShow','Icon':'0','Name':''}.items()]]])
        runtime=node(lang,'ShipInfo.AddInfo.CustomInfos.FHDNT_Runtime04')
        prop(runtime,'OnActCodeTypes',params(runtime)['OnActCodeTypes']+',t_OnDealingFatalDamage,t_OnWeaponShot,t_OnMissileHittingObject')
        callback="""if(ScriptItemActionType(t_OnDealingFatalDamage))
{ ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.CaptureKillRank23')); }
else if(ScriptItemActionType(t_OnWeaponShot) || ScriptItemActionType(t_OnMissileHittingObject))
{
if(ScriptItemActShip()==Player() && ObjectType(ScriptItemActObject1())==6)
{ ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.CacheKillRanks23'),'force',1); }
}
else { ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.Dispatch')); }"""
        node(runtime,'OnActCode')[1]=[[b'',1,f'{i:04d}',s]for i,s in enumerate(callback.splitlines())]
        tick=source(lang,'Tick')
        start=tick.index('if(nt_type==t_Kling)');end=tick.index('nt_total_points=nt_total_points+nt_points;')
        reward="""
nt_xp_rank=0;
nt_xp_prefix='|'+nt_day+':'+GalaxyEventData(nt_i,1)+':'+GalaxyEventData(nt_i,2)+':';
nt_xp_rank_found=0;
nt_xp_best=2147483647;
for(nt_xp_r=0;nt_xp_r<=7;nt_xp_r=nt_xp_r+1)
{
nt_xp_pos=findsubstr(nt_xp_pending,nt_xp_prefix+nt_xp_r+'|');
if(nt_xp_pos>=0 && nt_xp_pos<nt_xp_best)
{ nt_xp_rank=nt_xp_r; nt_xp_rank_found=1; nt_xp_best=nt_xp_pos; }
}
if(!nt_xp_rank_found)
{
for(nt_xp_r=0;nt_xp_r<=7;nt_xp_r=nt_xp_r+1)
{
if(findsubstr(nt_xp_cache,nt_xp_prefix+nt_xp_r+'|')>=0)
{ nt_xp_rank=nt_xp_r; break; }
}
}
nt_points=ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.KillReward23'),'kind',nt_type,'subtype',nt_sub,'tag',GalaxyEventsTextData(nt_i,2),'rank',nt_xp_rank);
"""
        tick=tick[:start]+reward+tick[end:]
        anchor='for(nt_i=GalaxyEvents()-1;nt_i>=0;nt_i=nt_i-1)'
        setup="""
int nt_xp_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_XP23');
int nt_xp_rank=0;
int nt_xp_r=0;
int nt_xp_rank_found=0;
int nt_xp_pos=0;
int nt_xp_best=0;
str nt_xp_prefix='';
str nt_xp_pending='';
str nt_xp_cache='';
if(nt_xp_info>=0)
{
nt_xp_pending=ShipCustomShipInfoTextData(Player(),nt_xp_info,1);
nt_xp_cache=ShipCustomShipInfoTextData(Player(),nt_xp_info,2);
}
"""
        # Keep every declaration at the start, retaining original initializers
        # in their original execution order after the early guards.
        tick=tick.replace(anchor,setup+'\n'+anchor)
        decl=[];body=[]
        import re
        for line in tick.splitlines():
            m=re.fullmatch(r'(int|str|dword) (\w+)=(.*);',line.strip())
            if m:
                typ,name,value=m.groups();decl.append(f"{typ} {name}="+("'';"if typ=='str'else'0;'));body.append(name+'='+value+';')
            else:body.append(line)
        tick='\n'.join(decl+body)
        tick=tick.replace("ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.SeedMarkets'));", "if(nt_xp_info>=0) { ShipCustomShipInfoTextData(Player(),nt_xp_info,1,''); }\nExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.CacheKillRanks23'),'force',0);\nExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.SeedMarkets'));")
        setcode(lang,'Tick',tick)
        install=source(lang,'Install').replace('[FHDNT V22 ','[FHDNT V23 ')
        setcode(lang,'Install',install+"\nExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.CacheKillRanks23'),'force',0);")
        group_metadata(lang);(out/MODREL/'CFG/Rus/Lang.dat').write_bytes(pack(lang,meta))
        mi=(base/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V22 ','V23 ')
        (out/MODREL/'ModuleInfo.txt').write_text(mi,encoding='utf-16')
        p=out/'SOURCE/CFG/Rus/Lang.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(lang)+'\n')
    (COMMON/'balance.json').write_text(json.dumps(BALANCE,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'version':'V23','editions':list(VARIANTS),'balance':BALANCE}))

if __name__=='__main__':build()
