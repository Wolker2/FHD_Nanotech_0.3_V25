"""Build a two-file V14 test hotfix from the uploaded V13 directory."""
from pathlib import Path
import argparse, copy, hashlib, json, shutil, struct, sys

sys.path.insert(0, str(Path(__file__).parent))
from dat_codec import unpack, pack, dump, walk

def node(tree, path):
    for part in path.split('.'):
        tree = next(e[3] for e in tree[1] if e[1] == 2 and e[2] == part)
    return tree

def params(tree):
    return {e[2]: e[3] for e in tree[1] if e[1] == 1}

def setcode(tree, name, source):
    lines = [line.strip() for line in source.strip().splitlines() if line.strip()]
    node(tree, 'FHDNT.Code.' + name)[1] = [[b'', 1, f'{i:04d}', s] for i, s in enumerate(lines)]

def group_metadata(tree):
    if tree[0]:
        tree[1].sort(key=lambda e: e[2])
        totals = {}
        for e in tree[1]: totals[e[2]] = totals.get(e[2], 0) + 1
        seen = {}
        for e in tree[1]:
            i = seen.get(e[2], 0); seen[e[2]] = i + 1
            e[0] = struct.pack('<II', i, totals[e[2]] if i == 0 else 0)
    for e in tree[1]:
        if e[1] == 2: group_metadata(e[3])

PORTRAIT = """
int nt_portrait_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_UI04');
dword nt_portrait_hull=0;
int nt_portrait_skin=0;
str nt_portrait_path='';
if(CurrentForm()=='Ship')
{
if(FormCurShip()==Player())
{
nt_portrait_hull=ShipItems(Player(),0);
}
}
if(nt_portrait_hull)
{
if(ItemExtraSpecialsCountByType(nt_portrait_hull,FindBonusByNameInCfg('FHDNT_Mark'))==1)
{
nt_portrait_skin=ItemExtraSpecialsCountByType(nt_portrait_hull,FindBonusByNameInCfg('FHDNT_Skin'));
}
}
if(nt_portrait_skin<=0 || nt_portrait_skin>CT('FHDNT.Skins.Count'))
{
if(nt_portrait_info>=0)
{
if(ShipCustomShipInfoData(Player(),nt_portrait_info,2))
{
InterfaceImage('Ship','Ship3D',ShipCustomShipInfoTextData(Player(),nt_portrait_info,2));
ShipCustomShipInfoData(Player(),nt_portrait_info,2,0);
ShipCustomShipInfoTextData(Player(),nt_portrait_info,2,'');
}
}
exit;
}
if(nt_portrait_info<0)
{
ShipAddCustomShipInfo(Player(),'FHDNT_UI04','NoShow');
nt_portrait_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_UI04');
}
if(!ShipCustomShipInfoData(Player(),nt_portrait_info,2))
{
ShipCustomShipInfoTextData(Player(),nt_portrait_info,2,InterfaceImage('Ship','Ship3D'));
ShipCustomShipInfoData(Player(),nt_portrait_info,2,1);
}
nt_portrait_path=CT('FHDNT.Portraits13.'+nt_portrait_skin);
if(InterfaceImage('Ship','Ship3D')!=nt_portrait_path)
{
InterfaceImage('Ship','Ship3D',nt_portrait_path);
}
"""

TALENTS = r"""
int nt_talent_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_Supply042');
str nt_talent_text='';
str nt_talent_name='';
str nt_talent_effect='';
int nt_talent_marked=0;
dword nt_talent_hull=ShipItems(Player(),0);
int nt_talent_slot=0;
int nt_talent_choice=0;
if(nt_talent_info<0)
{
ShipAddCustomShipInfo(Player(),'FHDNT_Supply042','NoShow');
nt_talent_info=ShipFindCustomShipInfoByType(Player(),'FHDNT_Supply042');
}
if(nt_talent_hull)
{
if(ItemExtraSpecialsCountByType(nt_talent_hull,FindBonusByNameInCfg('FHDNT_Mark'))==1)
{
nt_talent_marked=1;
for(nt_talent_slot=1;nt_talent_slot<=4;nt_talent_slot=nt_talent_slot+1)
{
nt_talent_choice=ItemExtraSpecialsCountByType(nt_talent_hull,FindBonusByNameInCfg('FHDNT_Skill'+nt_talent_slot));
if(nt_talent_choice>=1 && nt_talent_choice<=20)
{
nt_talent_name=CT('FHDNT.Skills.'+nt_talent_choice+'.Name');
nt_talent_effect=CT('FHDNT.Skills.'+nt_talent_choice+'.Description');
if(findsubstr(nt_talent_effect,nt_talent_name+': ')==0)
{
nt_talent_effect=substr(nt_talent_effect,count(nt_talent_name)+2);
}
if(nt_talent_text!='')
{
nt_talent_text=nt_talent_text+'\n';
}
nt_talent_text=nt_talent_text+'<color=0,190,0>'+nt_talent_name+'</color>: '+nt_talent_effect;
}
}
}
}
ShipCustomShipInfoTextData(Player(),nt_talent_info,1,nt_talent_text);
ShipCustomShipInfoTextData(Player(),nt_talent_info,2,'');
if(nt_talent_marked)
{
ShipCustomShipInfoDescription(Player(),nt_talent_info,'<TextData1>');
}
else
{
ShipCustomShipInfoDescription(Player(),nt_talent_info,'NoShow');
}
"""

def build(baseline, output):
    baseline, output = Path(baseline), Path(output)
    modrel = Path('Mods/FHD_MODS/FHD_Nanotech')
    src, dst = baseline / modrel, output / modrel
    dst.mkdir(parents=True, exist_ok=True)
    tree, meta = unpack((src / 'CFG/Rus/Lang.dat').read_bytes())
    setcode(tree, 'PortraitUI13', PORTRAIT)
    setcode(tree, 'TalentInfo', TALENTS)
    for entry in node(tree, 'FHDNT.Code.Install')[1]:
        entry[3] = entry[3].replace('[FHDNT V13]', '[FHDNT V14]')
    group_metadata(tree)
    p = dst / 'CFG/Rus/Lang.dat'; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pack(tree, meta))
    text = (src / 'ModuleInfo.txt').read_text(encoding='utf-16').replace('V13', 'V14 TEST')
    (dst / 'ModuleInfo.txt').write_text(text, encoding='utf-16')
    source = output / 'SOURCE/CFG/Rus/Lang.txt'; source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(dump(tree) + '\n', encoding='utf-8')
    return tree

if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('baseline'); a.add_argument('output')
    args = a.parse_args(); build(args.baseline, args.output)
