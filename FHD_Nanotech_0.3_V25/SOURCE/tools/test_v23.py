"""XP table, native event contract, save continuity and scoped regressions."""
import copy,json,re
from dat_codec import unpack,pack
from build_hotfix import node,params,group_metadata
from build_v16 import ROOT,MODREL,source
from build_v17 import prop
from build_v23 import BASES,VARIANTS,COMMON
from test_hotfix import load_model,assert_safe_shape

def read(p):return unpack(p.read_bytes())[0]
def normalized(t):t=copy.deepcopy(t);group_metadata(t);return t

def main():
    Model,sector,vm=load_model(ROOT/'work/v13')
    table=(ROOT/'upload/FHD_Nanotech_XP_Table_RU.txt').read_text(encoding='utf-8-sig')
    rank_rows=[list(map(int,m))for m in re.findall(r'^\s*([0-7])\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*$',table,re.M)]
    assert len(rank_rows)==8
    ordinary={k:[row[i]for row in rank_rows]for k,i in [('Pirate',1),('Warrior',2),('Ranger',3),('Transport',4)]}
    def named(name):return int(re.search(r'^'+re.escape(name)+r'\s*\|\s*(\d+)',table,re.M)[1])
    dom=[named(n)for n in ['Блазер (главный)','Эквентор','Ургант','Смерш','Менок','Штип','Бертор','Клиг']]
    klissan=[named(n)for n in ['Эгемон','Нондус','Катаури','Рогит','Мутенок']]
    machpella=named('Махпелла (главная)')

    class XPHost(Model):
        version='v23_test'
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw)
            self.constants.update({'t_OnDealingFatalDamage':90,'t_OnWeaponShot':91,'t_OnMissileHittingObject':92})
            self.victims={};self.events=[];self.target=0;self.actor=1;self.awards=[];self.rank_reads=[];self.real_grant=False
            self.star=20000
            lang=read(ROOT/'work'/self.version/MODREL/'CFG/Rus/Lang.dat')
            cb='\n'.join(e[3]for e in node(lang,'ShipInfo.AddInfo.CustomInfos.FHDNT_Runtime04.OnActCode')[1])
            self.ast['runtime_callback']=vm.Parser(cb).body()
        def call(self,name,a):
            if name=='ExecuteCodeFromString' and a[0]=='GrantXP':
                b=dict(zip(a[1::2],a[2::2]));self.awards.append(b['points'])
                if not self.real_grant:return 0
            if name=='ScriptItemActionType':return int(self.action==a[0]) if a else self.action
            if name=='ScriptItemActShip':return self.actor
            if name=='ScriptItemActObject1':return self.target
            if name=='ShipStar':return self.star
            if name=='ObjectType':return 6 if a[0]==900000 else 5 if a[0]in self.victims else 0
            if name=='StarShips':
                live=[v for v,d in self.victims.items()if d['alive']]
                return live[a[1]] if len(a)>1 else len(live)
            if name=='ShipTypeN':return self.victims[a[0]]['kind']
            if name=='ShipType':return self.victims[a[0]]['tag']
            if name in ['ShipRank','GetShipPirateRank']:
                d=self.victims[a[0]];assert d['alive'],'Dereferenced a dead ship'
                assert d['kind'] in [self.constants['t_'+k]for k in ordinary],'Rank API on a non-normal ship'
                self.rank_reads.append((name,a[0]))
                return d['pirate_rank' if name=='GetShipPirateRank'else'rank']
            if name=='GalaxyEvents':return len(self.events)
            if name=='GalaxyEventDate':return self.events[a[0]]['day']
            if name=='GalaxyEventType':return self.events[a[0]]['event']
            if name=='GalaxyEventData':return self.events[a[0]]['data'][a[1]]
            if name=='GalaxyEventsTextData':return self.events[a[0]]['text'][a[1]]
            return super().call(name,a)
        def victim(self,kind,rank=0,tag='',subtype=0,pirate_rank=None):
            v=80000+len(self.victims)
            self.victims[v]={'kind':self.constants.get('t_'+kind,13),'rank':rank,'pirate_rank':rank if pirate_rank is None else pirate_rank,'tag':tag,'subtype':subtype,'alive':True}
            return v
        def kill(self,v,fatal=True,event='PlayerKillsShip'):
            d=self.victims[v]
            if fatal:
                self.action=90;self.target=v;self.run('runtime_callback')
            self.events.append({'day':self.turn,'event':event,'data':[d['kind'],self.star,v,1,100,d['subtype']],'text':['Name','Full name',d['tag']]})
            d['alive']=False
        def equipped(self):
            self.startup();shop,it=self.stock()[0];self.shops[shop].remove(it);self.held=[it,100];self.form='Ship';self.turn=1
            return it
        def points(self,kind,subtype,tag,rank):return self.run('KillReward23',{'kind':self.constants.get('t_'+kind,13),'subtype':subtype,'tag':tag,'rank':rank})
    cases=0
    for edition in VARIANTS:
        cls=type('EditionHost',(XPHost,),{'version':'v23_'+edition});h=cls(seed=12);it=h.equipped()
        for kind,rewards in ordinary.items():
            for rank,expected in enumerate(rewards):
                assert h.points(kind,7,'',rank)==expected
                # Native pirates use PirateRank, other normal ships use Rank.
                v=h.victim(kind,rank if kind!='Pirate' else 7-rank,subtype=7,pirate_rank=rank if kind=='Pirate'else 7-rank)
                h.kill(v);h.run('Tick');assert h.awards[-1]==expected,(edition,kind,rank,h.awards)
                count=len(h.awards);h.run('Tick');assert len(h.awards)==count
                cases+=1
        for i,expected in enumerate(dom):
            assert h.points('Kling',i,'',7)==expected
            v=h.victim('Kling',subtype=i);h.kill(v);h.run('Tick');assert h.awards[-1]==expected;cases+=1
        # The three series share boss subtype 0.
        for boss in ['Blazer','Keller','Terron']:assert h.points('Kling',0,'',0)==2500
        for i,expected in enumerate(klissan,1):
            for kind in ['Kling','Transport','Warrior']:
                assert h.points(kind,0,'Klissan'+str(i),7)==expected
            v=h.victim('Kling',tag='Klissan'+str(i),subtype=0);h.kill(v);h.run('Tick');assert h.awards[-1]==expected;cases+=1
        v=h.victim('Station',tag='Machpella');h.kill(v);h.run('Tick');assert h.awards[-1]==machpella;cases+=1
        for rank,expected in enumerate(ordinary['Pirate']):
            v=h.victim('Transport',7-rank,tag='Smuggler',pirate_rank=rank)
            h.kill(v);h.run('Tick');assert h.awards[-1]==expected;cases+=1
        # Professions/custom presentation do not change the Ranger category;
        # diplomats/liners remain Transports and use the same rank scale.
        for tag in ['RangerPirate','RangerWarrior','RangerTrader','FemRanger']:
            assert h.points('Ranger',0,tag,7)==200
        for tag in ['Diplomat','Liner','Transport']:
            assert h.points('Transport',0,tag,7)==90
        for subtype in [-1,8,99]:assert h.points('Kling',subtype,'',7)==0
        for tag in ['Handler','KB','Unknown']:assert h.points('Station',0,tag,7)==0
        assert h.points('Pirate',0,'',-1)==55 and h.points('Pirate',0,'',99)==250
        # Multiple kills in a tick, same-event duplicates and unrelated events.
        h.events=[];h.turn+=1;h.awards=[]
        for kind,rank in [('Ranger',3),('Warrior',7),('Transport',6)]:h.kill(h.victim(kind,rank))
        h.events.append(copy.deepcopy(h.events[0]));h.kill(h.victim('Pirate',7),event='PartnerKillsShip')
        h.run('Tick');assert h.awards==[90+250+80]
        assert h.infos[h.info('FHDNT_XP23')]['text'][1]==''
        # Save/reload keeps pending metadata, event cursor and accrued XP.
        h.turn+=1;h.kill(h.victim('Pirate',0,pirate_rank=6))
        saved=copy.deepcopy(h.infos);extra=copy.deepcopy(h.extra);old_awards=list(h.awards)
        h.run('Install');assert h.extra==extra and h.infos[h.info('FHDNT_XP23')]['text'][1]==saved[h.info('FHDNT_XP23')]['text'][1]
        h.run('Tick');assert h.awards==old_awards+[200]
        h.run('Install');h.run('Tick');assert h.awards==old_awards+[200]
        # Explosions use cached live ranks, never dereference the dead victim.
        h.turn+=1;v=h.victim('Warrior',6);h.run('CacheKillRanks23',{'force':0});reads=len(h.rank_reads)
        h.run('CacheKillRanks23',{'force':0});assert len(h.rank_reads)==reads
        h.kill(v,fatal=False);h.run('Tick');assert h.awards[-1]==200
        # A later fatal snapshot overrides a start-of-turn rank snapshot.
        h.turn+=1;v=h.victim('Ranger',1);h.run('CacheKillRanks23',{'force':0});h.victims[v]['rank']=6
        h.kill(v);h.run('Tick');assert h.awards[-1]==150
        # Item detonations refresh live ranks immediately, including ships
        # spawned after the turn snapshot and several explosions before Tick.
        h.turn+=1;h.run('CacheKillRanks23',{'force':0});before=list(h.awards)
        v=h.victim('Warrior',7);h.action=91;h.target=900000;h.run('runtime_callback')
        assert h.awards==before
        h.kill(v,fatal=False)
        v=h.victim('Transport',0,tag='Smuggler',pirate_rank=5)
        h.action=92;h.target=900000;h.run('runtime_callback');h.kill(v,fatal=False)
        h.run('Tick');assert h.awards==before+[250+150]
        h.turn+=1;v=h.victim('Ranger',7)
        for rank in [7,1,6,1]:
            h.victims[v]['rank']=rank;h.action=91;h.target=900000;h.run('runtime_callback')
        h.kill(v,fatal=False);h.run('Tick');assert h.awards[-1]==60
        # Normal shots neither scan the system nor dispatch Tick/UI work.
        v=h.victim('Ranger',0);h.target=v;h.action=91;reads=len(h.rank_reads);ticks=h.blocks['Tick']
        h.run('runtime_callback');assert len(h.rank_reads)==reads and h.blocks['Tick']==ticks
        # No awards on ordinary hulls, no metadata capture for another attacker.
        h.held=[100,it];h.turn+=1;before=list(h.awards);h.kill(h.victim('Pirate',7));h.run('Tick');assert h.awards==before
        h.held=[it,100];h.actor=2;h.target=h.victim('Pirate',7);h.action=90
        pending=h.infos[h.info('FHDNT_XP23')]['text'][1];h.run('runtime_callback');assert h.infos[h.info('FHDNT_XP23')]['text'][1]==pending
        h.actor=1
        # Actual GrantXP retains balances and thresholds, including multi-level
        # rewards and a capped level 20. Nothing changes the progression table.
        needs=[int(h.lang[f'FHDNT.Levels.{level}.Need'])for level in range(21)]
        expected_needs=[150]+[int(x)for x in re.findall(r'^\s*\d+\s*\|\s*(\d+)\s*$',table.split('5. ПОРОГИ')[1],re.M)]+[0]
        assert needs==expected_needs and sum(needs[1:20])==32490 and sum(needs[:20])==32640
        h.real_grant=True;h.extra[it,'FHDNT_Level']=1;h.extra[it,'FHDNT_XP']=149
        h.run('GrantXP',{'h':it,'points':2500})
        level=1;xp=2649
        while xp>=needs[level] and level<20:xp-=needs[level];level+=1
        assert h.extra[it,'FHDNT_Level']==level and h.extra[it,'FHDNT_XP']==xp
        h.run('GrantXP',{'h':it,'points':sum(needs)})
        assert h.extra[it,'FHDNT_Level']==20 and h.extra[it,'FHDNT_XP']==0
        for name in ['KillReward23','CaptureKillRank23','CacheKillRanks23']:assert_safe_shape(vm,h.source[name])
        for s in h.source.values():vm.Parser(s).body()
    release,test=[read(VARIANTS[e]/MODREL/'CFG/Rus/Lang.dat')for e in ['release','test']]
    prop(node(test,'FHDNT'),'Build','RELEASE');prop(node(test,'FHDNT'),'LevelSelection','0');assert normalized(test)==normalized(release)
    for edition,out in VARIANTS.items():
        before=read(BASES[edition]/MODREL/'CFG/Rus/Lang.dat');after=read(out/MODREL/'CFG/Rus/Lang.dat')
        for e in node(before,'FHDNT.Code')[1]:
            if e[2]not in ['Tick','Install']:assert normalized(e[3])==normalized(node(after,'FHDNT.Code.'+e[2])),e[2]
        assert normalized(node(before,'FHDNT.Levels'))==normalized(node(after,'FHDNT.Levels'))
        for p in (BASES[edition]/'Mods').rglob('*'):
            if p.is_file() and all(not x.startswith('.')for x in p.relative_to(BASES[edition]).parts):
                rel=p.relative_to(BASES[edition])
                if rel not in [MODREL/'CFG/Rus/Lang.dat',MODREL/'ModuleInfo.txt']:assert p.read_bytes()==(out/rel).read_bytes(),rel
        t,m=unpack((out/MODREL/'CFG/Rus/Lang.dat').read_bytes());assert unpack(pack(t,m))[0]==t
    report={'status':'PASS (static/model)','windows_game':'НЕТ ТЕСТА','reward_and_rank_event_cases':cases,'approved_attachment_used_as_expected_values':True,'rank_api_on_dead_or_non_normal_ships':False,'duplicate_awards':False,'pending_ranks_and_progress_survive_reload':True,'explosion_rank_snapshot_checked':True,'new_spawn_and_repeated_item_explosions_checked':True,'ordinary_shots_do_not_scan_system':True,'thresholds_and_ui_unchanged':True,'shared_core':True,'runtime_files_changed':['CFG/Rus/Lang.dat','ModuleInfo.txt'],'native_event_contract':'aNormalShip.ProcessShipKill: numeric data[5] is subtype; text[2] is TypeNameOverrideKey; ranks captured before death','fallback':'Nonstandard scripted kills bypassing combat hooks and all live snapshots use rank 0; the journal does not contain a rank.'}
    for out in [COMMON,*VARIANTS.values()]:
        p=out if out==COMMON else out/'reports';p.mkdir(parents=True,exist_ok=True);(p/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
