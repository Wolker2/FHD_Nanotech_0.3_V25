"""Scoped DAT, source-shape and runtime-model regression checks. Not the game."""
import argparse, ast, copy, hashlib, importlib.util, json, re, sys, types
from pathlib import Path
from dat_codec import unpack, pack, walk, dump
from build_hotfix import node, params

def native_string(text):
    # TCodeAnalyzerEC.AppendText: \\n produces CRLF; no HTML conversion in RankText.
    return re.sub(r"\\(?:\\|n|\"|'|x[0-9a-fA-F]{1,4})", lambda m:
        '\r\n' if m[0]=='\\n' else chr(int(m[0][2:],16)) if m[0].startswith('\\x') else m[0][1:], text)

def load_model(baseline):
    tools = baseline / 'SOURCE/tools'
    support = types.ModuleType('inspect_models')
    support.HERE = baseline.parent; support.BASE = baseline.parent
    support.node = node; support.params = params
    sys.modules['inspect_models'] = support
    vm = types.ModuleType('script_harness'); vm.__file__ = str(tools / 'script_harness.py')
    source = (tools / 'script_harness.py').read_text()
    assert "a=('lit',t[1:-1])" in source
    source = source.replace("a=('lit',t[1:-1])", "a=('lit',native_string(t[1:-1]))")
    vm.__dict__['native_string'] = native_string
    sys.modules['script_harness'] = vm
    exec(compile(source, vm.__file__, 'exec'), vm.__dict__)
    sector = types.ModuleType('test_v7'); sector.__file__ = str(tools / 'test_v7.py')
    sys.modules['test_v7'] = sector
    exec(compile((tools / 'test_v7.py').read_text(), sector.__file__, 'exec'), sector.__dict__)
    ns = {'test_v7': sector, 'V8Host': None}
    for file, classname in [('test_v8.py','V8Host'),('test_v9.py','V9Host'),('test_v11.py','V11Host'),('test_v13.py','V13Host')]:
        tree = ast.parse((tools / file).read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname)
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(tools / file),'exec'),ns)
    class CurrentHost(ns['V13Host']):
        version = 'v14_hotfix'
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.schema_version = 11
        def call(self,name,args):
            # Enforce native getter/setter arities in the changed handlers.
            limits={'InterfaceImage':(2,3),'ShipCustomShipInfoData':(3,4),
                    'ShipCustomShipInfoTextData':(3,4),'ShipCustomShipInfoDescription':(2,3)}
            if name in limits:
                lo,hi=limits[name]; assert lo<=len(args)<=hi,(name,args)
            return super().call(name,args)
    return CurrentHost, sector, vm

def assert_safe_shape(vm, source):
    tree = vm.Parser(source).body()
    seen_code=False; names=set()
    for s in tree[1]:
        if s[0]=='declare':
            assert not seen_code,'declaration after a control-flow statement'
            assert s[2] not in names,'duplicate declaration'; names.add(s[2])
        else: seen_code=True
    def nested(s):
        if s[0]=='block':
            for a in s[1]: nested(a)
        elif s[0]=='if':
            assert s[2][0]=='block','unbraced conditional'
            nested(s[2])
            if s[3]: assert s[3][0]=='block'; nested(s[3])
        elif s[0]=='for':
            assert s[4][0]=='block'; nested(s[4])
        else: assert s[0]!='declare','nested declaration'
    for s in tree[1]:
        if s[0]!='declare': nested(s)

def validate(baseline, output):
    baseline, output = Path(baseline), Path(output)
    original,_=unpack((baseline/'Mods/FHD_MODS/FHD_Nanotech/CFG/Rus/Lang.dat').read_bytes())
    file=output/'Mods/FHD_MODS/FHD_Nanotech/CFG/Rus/Lang.dat'
    current,meta=unpack(file.read_bytes()); assert unpack(pack(current,meta))[0]==current
    assert (output/'SOURCE/CFG/Rus/Lang.txt').read_text()==dump(current)+'\n'
    old={p:e[3] for p,e in walk(original) if e[1]==1}
    now={p:e[3] for p,e in walk(current) if e[1]==1}
    changed={p for p in old.keys()|now.keys() if old.get(p)!=now.get(p)}
    assert all(p.startswith(('FHDNT.Code.PortraitUI13.','FHDNT.Code.TalentInfo.','FHDNT.Code.Install.')) for p in changed)
    assert sum(p.startswith('FHDNT.Code.Install.') for p in changed)==1
    Host,sector,vm=load_model(baseline)
    h=Host(seed=12)
    old_portrait=''.join(e[3] for e in node(original,'FHDNT.Code.PortraitUI13')[1])
    assert old_portrait[843:].startswith('nt_portrait_path=')
    try: assert_safe_shape(vm,old_portrait)
    except AssertionError: pass
    else: raise AssertionError('Old unsafe structure must be detected')
    for name in ('PortraitUI13','TalentInfo'): assert_safe_shape(vm,h.source[name])
    h.startup(); shop,item=h.stock()[0];h.shops[shop].remove(item);h.held=[item,100];h.form='Ship'
    h.images[('Ship','Ship3D')]='GI,Bm.OtherMod.Portrait'
    h.run('PortraitUI13')
    info=h.info('FHDNT_UI04')
    assert h.infos[info]['text'][2]=='GI,Bm.OtherMod.Portrait'
    for skin,allowed in params(node(current,'FHDNT.Skins.Allowed')).items():
        if allowed!='1':continue
        h.extra[(item,'FHDNT_Skin')]=int(skin);h.run('PortraitUI13')
        assert h.images[('Ship','Ship3D')]==h.lang['FHDNT.Portraits13.'+skin]
        assert h.infos[info]['text'][2]=='GI,Bm.OtherMod.Portrait'
    h.held=[100,item];h.run('PortraitUI13')
    assert h.images[('Ship','Ship3D')]=='GI,Bm.OtherMod.Portrait' and h.infos[info]['data'][2]==0
    h.images[('Ship','Ship3D')]='GI,Bm.ChangedLater';h.run('PortraitUI13')
    assert h.images[('Ship','Ship3D')]=='GI,Bm.ChangedLater'
    h.held=[item,100];h.images.pop(('Ship','Ship3D'));h.run('PortraitUI13')
    for form in ('RuinsTalk','EquipmentShop','StarMap','Scaner'):
        h.form=form;h.run('PortraitUI13');assert ('Ship','Ship3D') not in h.images
    h.form='Ship';h.form_ship=2;h.run('PortraitUI13');assert ('Ship','Ship3D') not in h.images
    h.form_ship=1
    for skin in (0,-1,int(h.lang['FHDNT.Skins.Count'])+1):
        h.extra[(item,'FHDNT_Skin')]=skin;h.run('PortraitUI13');assert ('Ship','Ship3D') not in h.images
    h.extra[(item,'FHD_WormholeV2_Core')]=1
    h.extra[(100,'FHD_WormholeV2_EngineCore')]=1
    for level in (*range(21),0,20):
        h.run('TestLevel',{'h':item,'target':level})
        assert h.extra.get((item,'FHDNT_Level'),0)==level
        assert h.form=='Ship' and h.closed==0
        assert h.extra[(item,'FHD_WormholeV2_Core')]==1
        assert h.extra[(100,'FHD_WormholeV2_EngineCore')]==1
        assert h.items[item]['series']==1 and h.items[item]['name'].endswith(' [WH]')
    main,_=unpack((baseline/'Mods/FHD_MODS/FHD_Nanotech/CFG/Main.dat').read_bytes())
    controls={}
    def visit(t):
        p=params(t)
        if p.get('Name'):controls[p['Name']]=t
        for e in t[1]:
            if e[1]==2:visit(e[3])
    visit(node(main,'ML.Ship'))
    for name,n in controls.items():
        for e in n[1]:
            if e[1]==2 and e[2]=='OnPressCode':
                h.ast['button:'+name]=vm.Parser(''.join(x[3] for x in e[3][1])).body()
    for name,modal in [('FHDNT_OpenSkills','FHDNT_SkillPicker'),('FHDNT_Test','FHDNT_LevelPicker03')]:
        h.run('button:'+name)
        assert h.uistates[('Ship',modal)]==1 and h.form=='Ship' and h.closed==0
        h.uistates[('Ship',modal)]=0;h.run('ModalInput')
    for choice in (1,8,15,20):h.run('button:FHDNT_SkillChoice'+str(choice))
    h.run('TalentInfo');info=h.info('FHDNT_Supply042');text=h.infos[info]['text'][1]
    rows=text.split('\r\n');assert len(rows)==4 and '<br>' not in text
    for row,choice in zip(rows,(1,8,15,20)):
        name=h.lang[f'FHDNT.Skills.{choice}.Name']
        effect=h.lang[f'FHDNT.Skills.{choice}.Description'].removeprefix(name+': ')
        assert row==f'<color=0,190,0>{name}</color>: {effect}'
    for slot,value in enumerate((0,21,-1,1),1):h.extra[(item,'FHDNT_Skill'+str(slot))]=value
    h.run('TalentInfo');assert '\r\n' not in h.infos[info]['text'][1]
    h.held=[100,item];h.run('TalentInfo')
    assert h.infos[info]['text'][1]=='' and h.infos[info]['description']=='NoShow'
    sector.SectorHost=Host;result=sector.tests();assert result['status']=='PASS'
    runtime=list((output/'Mods').rglob('*'))
    runtime=[p.relative_to(output/'Mods/FHD_MODS/FHD_Nanotech').as_posix() for p in runtime if p.is_file()]
    assert set(runtime)=={'CFG/Rus/Lang.dat','ModuleInfo.txt'}
    report={'status':'PASS','scope':'DAT validation, source compatibility rules and actual scripts executed with mocked APIs; not the Windows game compiler or renderer',
            'old_error_position':843,'old_error_token':'nt_portrait_path','old_structure_rejected':True,
            'script_blocks_parsed':len(h.ast)-sum(k.startswith('button:') for k in h.ast),
            'runtime_files_changed':sorted(runtime),'checks':[
                'Portrait and talent handlers declare locals first and brace every conditional body',
                '21 allowed portraits, previous override restored, default override cleared, repeated calls, ordinary hull, foreign ship, non-Ship forms and invalid skin IDs',
                'All levels 0-20 and downgrades, actual open/choice button handlers keep the Ship screen open',
                'Four selected talents, native CRLF line breaks, green names, unchanged effects; empty and invalid slots; ordinary hull clears text',
                'Wormhole bonus and [WH] name suffix survive level changes; non-Nanotech series untouched',
                'Only PortraitUI13, TalentInfo and the startup version message change inside Lang.dat; Main.dat and CacheData.dat supplied by V13 remain untouched'],
            'sector_regression':result,'game_test_required':True}
    reports=output/'reports';reports.mkdir(exist_ok=True)
    (reports/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'status':report['status'],'script_blocks':report['script_blocks_parsed'],'sector_scenarios':len(result['passed']),'changed_files':runtime},ensure_ascii=False))
    return report

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('baseline');a.add_argument('output');v=a.parse_args()
    validate(v.baseline,v.output)
