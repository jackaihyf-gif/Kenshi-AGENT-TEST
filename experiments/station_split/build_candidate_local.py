import ast,copy,hashlib,json,pathlib,struct
ROOT=pathlib.Path(r'D:/steam/steamapps/common/Kenshi'); OUT=pathlib.Path(__file__).resolve().parent
src=pathlib.Path(r'D:/JACK/kenshi_armour_audit/read_data.py'); tree=ast.parse(src.read_text('utf8').replace("errors='replace'","errors='surrogateescape'")); ns={'struct':struct};exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,(ast.ClassDef,ast.FunctionDef))],type_ignores=[]),str(src),'exec'),ns); Reader=ns['Reader'];merge=ns['merge']
def u(x):return struct.pack('<I',x&0xffffffff)
def s(x):
 b=x.encode('utf8',errors='surrogateescape');return u(len(b))+b
def encode(rows,prefix):
 data=prefix+u(len(rows))
 for r in rows:
  data+=u(0)+u(r['type'])+u(0)+s(r['name'])+s(r['id'])+u(r['flags'])
  for kind,fmt in enumerate(('?','f','i','3f','4f','s','s')):
   fs=[(k,v) for k,v in r['fields'].items() if r['field_types'][k]==kind];data+=u(len(fs))
   for k,v in fs:
    data+=s(k)
    if fmt=='s':data+=s(v)
    elif fmt in ('3f','4f'):data+=struct.pack('<'+fmt,*v)
    else:data+=struct.pack('<'+fmt,v)
  data+=u(len(r['refs']))
  for k,refs in r['refs'].items():
   data+=s(k)+u(len(refs))
   for target,v in refs.items():data+=s(target)+struct.pack('<3i',*v)
  data+=u(0)
 return data
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'mods/JACK_WastelandCraft/JACK_WastelandCraft.mod'; assert sha(source)=='fe8e8e9490c48b814c5a9740f0c25751059aa15d3dc43d145570eee7b6ca7b6c'
rd=Reader(source);assert rd.val('i')==16;rd.val('i')
for _ in range(4):rd.s()
rd.val('i');prefix=rd.b[:rd.o]
old=list(Reader(source).records());assert len(old)==24 and encode(old,prefix)==source.read_bytes()
rows=copy.deepcopy(old);db={r['id']:r for r in rows}; own=lambda n:f'{n}-JACK_WastelandCraft.mod'; energy=lambda n:f'{n}-JACK_EnergyWeapons.mod'
for n,t in zip((400,410,420,430,440,450,460),(6,6,3,8,8,1,1)):db[own(n)]['fields']['production time']=t
for n,t in ((100,12.),(110,14.)):db[energy(n)]['fields']['craft time hrs']=t
f=db[own(110)];f['fields']['production mult']=1.
for sid in (energy(200),energy(210),own(450),own(460)):del f['refs']['item crafts'][sid]
db[own(210)]['refs']['item crafts']={own(450):[50,0,0],own(460):[50,0,0]}
db[own(310)]['refs']['enable buildings'][own(500)]=[0,0,0]
ammo=copy.deepcopy(f);ammo['id']=own(510);ammo['name']='弹药装配';ammo['fields']['production mult']=2.;ammo['refs']['item crafts']={energy(200):[50,0,0],energy(210):[50,0,0]};ammo['refs'].pop('crossbow crafts');ammo['refs'].pop('consumes',None)
bench=copy.deepcopy(db[own(100)]);bench['id']=own(500);bench['name']='弹药装配台';bench['fields']['building group']='';bench['fields']['Description']='用于装配能量武器弹药。';bench['fields']['power output']=-10;bench['fields']['build materials']=4;bench['refs']['functionality']={own(510):[0,0,0]};bench['refs']['construction']={'42159-gamedata.base':[4,0,0],'579-gamedata.base':[2,0,0]}
rows.extend([ammo,bench]);candidate=OUT/'JACK_WastelandCraft.mod.candidate';candidate.write_bytes(encode(rows,prefix));assert list(Reader(candidate).records())==rows
# Full load order and unresolved references comparison.
files=[ROOT/'data'/n for n in ('gamedata.base','Newwworld.mod','Dialogue.mod','rebirth.mod')];available={p.name:p for p in pathlib.Path(r'D:/steam/steamapps/workshop/content/233860').rglob('*.mod')};available.update({p.name:p for p in (ROOT/'mods').rglob('*.mod')});enabled=[x for x in (ROOT/'data/mods.cfg').read_text(encoding='utf-8-sig').splitlines() if x.strip()];missing=[x for x in enabled if x not in available];assert not missing;files += [available[x] for x in enabled];before={};after={}
for p in files:
 rr=list(Reader(p).records());merge(before,copy.deepcopy(rr),p.name);merge(after,copy.deepcopy(rows if p==source else rr),p.name)
def unresolved(d):return {(sid,key,target) for sid,r in d.items() for key,refs in r['refs'].items() for target in refs if target and target not in d}
new_unresolved=unresolved(after)-unresolved(before);assert not new_unresolved,new_unresolved
assert set(after[own(110)]['refs']['item crafts'])=={own(n) for n in (400,410,420,430,440)}
assert set(after[own(210)]['refs']['item crafts'])=={own(450),own(460)}
assert set(after[own(510)]['refs']['item crafts'])=={energy(200),energy(210)}
assert all(rows[i]==old[i] for i in range(21,24))
mixed=[{'id':r['id'],'name':r['name'],'refs':{k:list(r['refs'][k])[:3] for k in ('armour crafts','item crafts')}} for r in before.values() if r['type']==62 and r['fields'].get('function')==10 and 'armour crafts' in r['refs'] and 'item crafts' in r['refs']]
report={'source_sha256':sha(source),'candidate_sha256':sha(candidate),'energy_sha256':sha(ROOT/'mods/JACK_EnergyWeapons/JACK_EnergyWeapons.mod'),'records_before':len(old),'records_after':len(rows),'enabled_mods':len(enabled),'loaded_files':len(files),'new_unresolved_references':len(new_unresolved),'mixed_load_order_examples_not_vanilla_proof':mixed[:10],'storage_records_unchanged':True,'roundtrip_byte_exact':True,'candidate_readback_exact':True,'new_building_uses_existing_part':'96181-Newwworld.mod','candidate_only':True,'old_research_save_effect':'unverified','gameplay':'unverified'}
orig=ast.parse(src.read_text('utf8')); plain={'struct':struct};exec(compile(ast.Module(body=[x for x in orig.body if isinstance(x,(ast.ClassDef,ast.FunctionDef))],type_ignores=[]),str(src),'exec'),plain); decoded={r['id']:r for r in plain['Reader'](candidate).records()}; assert decoded[own(500)]['name']=='弹药装配台' and decoded[own(500)]['fields']['Description']=='用于装配能量武器弹药。' and decoded[own(510)]['name']=='弹药装配'; assert all('�' not in v for v in (decoded[own(500)]['name'],decoded[own(500)]['fields']['Description'],decoded[own(510)]['name']));report['new_chinese_utf8_verified']=True;report['mixed_example_attribution']='2931 armour crafts is vanilla; item crafts added by 2333.mod; runtime support unverified'
(OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=True,indent=2),'utf8');print(json.dumps(report,ensure_ascii=True))
