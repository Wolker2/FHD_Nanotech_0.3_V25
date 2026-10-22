"""Undo V15 frame changes outside level 20. Keep an exact pre-V15 renderer."""
import copy, hashlib, json, struct, sys
from pathlib import Path
from dat_codec import unpack, pack, walk, dump
from build_hotfix import node, params, setcode, group_metadata

ROOT=Path(__file__).resolve().parents[1]
MODREL=Path('Mods/FHD_MODS/FHD_Nanotech')
OUT=ROOT/'work/v16'
V13=ROOT/'work/v13'
V14=ROOT/'work/v14_hotfix'
V15=ROOT/'work/v15'

def source(t,name):return '\n'.join(e[3]for e in node(t,'FHDNT.Code.'+name)[1])
def addcode(t,name,text):
    node(t,'FHDNT.Code')[1].append([b'',2,name,[0,[]]])
    setcode(t,name,text)

def build():
    original,_=unpack((V14/MODREL/'CFG/Rus/Lang.dat').read_bytes())
    current,meta=unpack((V15/MODREL/'CFG/Rus/Lang.dat').read_bytes())
    old_frames=copy.deepcopy(node(original,'FHDNT.Code.FramesUI'))
    node(current,'FHDNT.Code')[1].append([b'',2,'FramesOriginal14',old_frames])
    parts=[('Ship','UseImage','2Use'),('Ship','PanelLeft','2LeftShort'),
           ('Ship','FHDNT_FrameBottom','2Bottom'),('Ship','FHDNT_FrameDSBg','2DSBg'),
           ('Ship','RightOpen','2Right'),('Ship','RHOpen','2RHBg'),
           ('Scaner','PanelLeft','2Left'),('Scaner','RightOpen','2Right')]
    only20="str nt_only20_form=CurrentForm();\n"
    for f,n,p in parts:
        overlay='FHDNT_Level20_'+f+'_'+p
        only20+=f"""
if(nt_only20_form=='{f}')
{{
if(InterfaceImage('{f}','{n}')!='GAI,Bm.FHDNTLevel20.{p}') InterfaceImage('{f}','{n}','GAI,Bm.FHDNTLevel20.{p}');
if(InterfaceState('{f}','{n}')!=1) InterfaceState('{f}','{n}',1);
if(InterfaceState('{f}','{overlay}')!=0) InterfaceState('{f}','{overlay}',0);
}}
"""
    addcode(current,'FramesLevel20Only16',only20)
    dispatch="""
str nt_scope_form=CurrentForm();
dword nt_scope_ship=0;
dword nt_scope_hull=0;
int nt_scope_level20=0;
str nt_scope_image='';
if(nt_scope_form!='Ship' && nt_scope_form!='Scaner') exit;
nt_scope_ship=FormCurShip();
if(nt_scope_ship)
{
nt_scope_hull=ShipItems(nt_scope_ship,0);
}
if(nt_scope_form=='Ship' && nt_scope_ship!=Player()) nt_scope_hull=0;
if(nt_scope_hull)
{
if(ItemExtraSpecialsCountByType(nt_scope_hull,FindBonusByNameInCfg('FHDNT_Mark'))==1)
{
if(ItemExtraSpecialsCountByType(nt_scope_hull,FindBonusByNameInCfg('FHDNT_Level'))==20) nt_scope_level20=1;
}
}
if(nt_scope_level20)
{
ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.FramesLevel20Only16'));
exit;
}
"""
    # Restore only our own level-20 image when leaving level 20. No Pos/Size
    # operations are introduced in the frame dispatcher or either renderer.
    for f,n,p in parts:
        dispatch+=f"""
if(nt_scope_form=='{f}')
{{
nt_scope_image=InterfaceImage('{f}','{n}');
if(findsubstr(nt_scope_image,'GAI,Bm.FHDNTLevel20.',0)==0)
{{
InterfaceImage('{f}','{n}','');
InterfaceState('{f}','{n}',-1);
}}
}}
"""
    dispatch+="ExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.FramesOriginal14'));"
    setcode(current,'FramesUI',dispatch)
    # Remove V15's unconditional additional cleanup of all eight geometries.
    # Retain only the existing portrait migration, not new frame settings.
    install=source(original,'Install').replace('[FHDNT V14]','[FHDNT V16]')
    install+="\nExecuteCodeFromString(GenerateCodeStringFromBlock('FHDNT.Code.PortraitUI13'));"
    setcode(current,'Install',install)
    assert node(current,'FHDNT.Code.FramesOriginal14')==node(original,'FHDNT.Code.FramesUI')
    group_metadata(current)
    out=OUT/MODREL;(out/'CFG/Rus').mkdir(parents=True,exist_ok=True)
    # Whole original Main.dat, not a recreated approximation of its geometry.
    (out/'CFG/Main.dat').write_bytes((V13/MODREL/'CFG/Main.dat').read_bytes())
    (out/'CFG/Rus/Lang.dat').write_bytes(pack(current,meta))
    (out/'ModuleInfo.txt').write_text((V15/MODREL/'ModuleInfo.txt').read_text(encoding='utf-16').replace('V15 TEST','V16 TEST'),encoding='utf-16')
    p=OUT/'SOURCE/CFG/Rus/Lang.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(dump(current)+'\n')
    print(json.dumps({'main_restored_exactly':True,'normal_frame_renderer':'Exact V14 copy','isolated_level20_renderer':True}))

if __name__=='__main__':build()
