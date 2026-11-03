"""Local content candidates. Preserve current files and all recipe/tech IDs."""
from pathlib import Path
import ast,copy,hashlib,json,shutil,struct,xml.etree.ElementTree as ET

P=Path('D:/JACK/KenshiArmorMod');G=Path('D:/steam/steamapps/common/Kenshi')
O=Path(__file__).resolve().parent;PACKAGE=O/'candidate'
assert not PACKAGE.exists(),'Never overwrite an earlier content candidate'
reader=P.parent/'kenshi_armour_audit/read_data.py';ns={'struct':struct};tree=ast.parse(reader.read_text('utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))],type_ignores=[]),str(reader),'exec'),ns)
Reader=ns['Reader'];u=lambda n:struct.pack('<I',n&0xffffffff)
def string(s):b=s.encode('utf8');return u(len(b))+b
def header(path):
 r=Reader(path);assert r.val('i')==16;r.val('i')
 for _ in range(4):r.s()
 r.val('i');return r.b[:r.o]
def encode(records,prefix):
 b=prefix+u(len(records))
 for r in records:
  b+=u(0)+u(r['type'])+u(0)+string(r['name'])+string(r['id'])+u(r['flags'])
  for ty,fmt in enumerate(('?','f','i','3f','4f','s','s')):
   fields=[(k,v)for k,v in r['fields'].items()if r['field_types'][k]==ty];b+=u(len(fields))
   for k,v in fields:b+=string(k)+(string(v)if fmt=='s'else struct.pack('<'+fmt,*v)if fmt in ('3f','4f')else struct.pack('<'+fmt,v))
  b+=u(len(r['refs']))
  for k,refs in r['refs'].items():
   b+=string(k)+u(len(refs))
   for sid,values in refs.items():b+=string(sid)+struct.pack('<3i',*values)
  b+=u(0)
 return b
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def setfield(r,k,v):
 assert k in r['field_types']
 ty=r['field_types'][k]
 r['fields'][k]=struct.unpack('<f',struct.pack('<f',v))[0]if ty==1 else v
def snapshot(mod):
 p=G/'mods'/mod/(mod+'.mod');rows=list(Reader(p).records());prefix=header(p)
 assert encode(rows,prefix)==p.read_bytes(),'Writer must reproduce original bytes before changes'
 return p,rows,prefix

energy,ers,eh=snapshot('JACK_EnergyWeapons');craft,crs,ch=snapshot('JACK_WastelandCraft')
original_e=copy.deepcopy(ers);original_c=copy.deepcopy(crs)
for r in ers:
 if r['id']in ['200-JACK_EnergyWeapons.mod','210-JACK_EnergyWeapons.mod']:
  assert r['fields']['stackable']==1;setfield(r,'stackable',100)
expected_e=copy.deepcopy(original_e)
for r in expected_e:
 if r['id']in ['200-JACK_EnergyWeapons.mod','210-JACK_EnergyWeapons.mod']:r['fields']['stackable']=100
assert ers==expected_e
assert next(r for r in ers if r['id']=='110-JACK_EnergyWeapons.mod')['fields']['shoot sound']==1

vanilla={}
for file in ['gamedata.base','Newwworld.mod','Dialogue.mod','rebirth.mod']:
 ns['merge'](vanilla,list(Reader(G/'data'/file).records()),file)
part=copy.deepcopy(vanilla['2100-gamedata.base']);mat=copy.deepcopy(vanilla['2032-gamedata.base'])
for r,sid,name in [(part,'220-JACK_WastelandCraft.mod','T60 assembly station frame'),(mat,'221-JACK_WastelandCraft.mod','T60 assembly station surface')]:
 assert all(old['id']!=sid for old in crs);r.pop('sources',None);r.update(id=sid,name=name,flags=2147483650)
setfield(part,'phs or mesh','./mods/JACK_WastelandCraft/meshes/jack_t60_assembly_station.mesh')
setfield(part,'xml collision','./mods/JACK_WastelandCraft/physics/jack_t60_assembly_station.xml')
part['refs']={'material':{mat['id']:[0,100,0]}}
for key,suffix in [('texture map','d'),('normal map','n'),('metalness map','m')]:setfield(mat,key,'./mods/JACK_WastelandCraft/textures/station_'+suffix+'.dds')
setfield(mat,'scaffolding tex scale',4.0)
building=next(r for r in crs if r['id']=='200-JACK_WastelandCraft.mod')
assert building['refs']['parts']=={'2100-gamedata.base':[0,100,0]}
building['refs']['parts']={part['id']:[0,100,0]}
setfield(building,'scale',1.0);setfield(building,'building height',26.00225067138672)
setfield(building,'Description','用于动力装甲装配的专用工位。承重立柱与夹臂固定机体，底部导轨为装配和搬运留出空间。')
crs.extend([part,mat])
# Every pre-existing gameplay record and unlock/cost remains unchanged except the visual station record.
for before,after in zip(original_c,crs):
 if before['id']!='200-JACK_WastelandCraft.mod':assert before==after,(before['id'],'unrelated crafting change')
assert building['refs']['functionality']==next(r for r in original_c if r['id']==building['id'])['refs']['functionality']

for mod,rows,prefix in [('JACK_EnergyWeapons',ers,eh),('JACK_WastelandCraft',crs,ch)]:
 dest=PACKAGE/mod;dest.mkdir(parents=True);f=dest/(mod+'.mod');f.write_bytes(encode(rows,prefix));assert list(Reader(f).records())==rows
backup=O/'backup';backup.mkdir();shutil.copy2(energy,backup/energy.name);shutil.copy2(craft,backup/craft.name)
base=PACKAGE/'JACK_WastelandCraft'
for directory in ['meshes','physics','textures','materials']:(base/directory).mkdir()
shutil.copy2(O/'jack_t60_assembly_station.mesh',base/'meshes/jack_t60_assembly_station.mesh')
for suffix in ['d','n','m']:
 shutil.copy2(P/f'research/station_candidate_20261103/optimized/with_mips/station_{suffix}.dds',base/f'textures/station_{suffix}.dds')

# Generic PhysX scene settings are retained, all old geometry/actors replaced by authored boxes.
xml=ET.parse(G/'data/buildings/crafting/smithy_armour.xml');collection=xml.getroot().find('NxuPhysicsCollection');collection.set('id','JACK_T60_Assembly_Station')
scene=collection.find('NxSceneDesc');actor=copy.deepcopy(scene.find('NxActorDesc'))
for old in list(scene):
 if old.tag=='NxActorDesc':scene.remove(old)
boxes=[('post_left',[-7.5,10.6,13],[1.1,1.3,13]),('post_right',[7.5,10.6,13],[1.1,1.3,13]),
 ('rail_left',[-7.5,0,.4],[1.1,12.8,.4]),('rail_right',[7.5,0,.4],[1.1,12.8,.4]),
 ('rear_brace',[0,10.4,4.5],[6.4,.8,.65]),('arm_left',[-5,2,24.4],[1,8.4,1.1]),('arm_right',[5,2,24.4],[1,8.4,1.1])]
for i,(name,center,half)in enumerate(boxes):
 a=copy.deepcopy(actor);a.set('id','JACK_Actor_'+str(i));a.set('name',name)
 a.find('globalPose').text='1 0 0  0 1 0  0 0 1  '+' '.join(str(v)for v in center)
 box=a.find('NxBoxShapeDesc');box.set('dimensions',' '.join(str(v)for v in half))
 shape=box.find('NxShapeDesc');shape.set('name',name);shape.find('localPose').text='1 0 0  0 1 0  0 0 1  0 0 0'
 insert_at=next((j for j,node in enumerate(scene)if node.tag=='NxActorGroupPair'),len(scene))
 scene.insert(insert_at,a)
f=base/'physics/jack_t60_assembly_station.xml';xml.write(f,encoding='utf8',xml_declaration=True)
assert len(ET.parse(f).findall('.//NxActorDesc'))==7
assert all(a.get('hasBody')=='false'for a in ET.parse(f).findall('.//NxActorDesc'))
assert all(not(all(abs(point[j]-center[j])<=half[j]for j in range(3)))for point in [(0,-10,1),(0,0,1),(0,0,18)]for _,center,half in boxes)
(O/'collision_boxes.json').write_text(json.dumps({'coordinate_system':'PhysX XML/Blender Z-up; same convention as inspected native template','boxes':boxes,'central_sample_points_clear':True,'actual_navigation_verified':False},indent=2),encoding='utf8')
(base/'materials/jack_assembly_station.material').write_text('''material JACK_Assembly_Station
{
 technique { pass {
 vertex_program_ref Object_VP {}
 fragment_program_ref Object_FP {}
 texture_unit diffuseMap { texture ./mods/JACK_WastelandCraft/textures/station_d.dds }
 texture_unit normalMap { texture ./mods/JACK_WastelandCraft/textures/station_n.dds }
 texture_unit metalnessMap { texture ./mods/JACK_WastelandCraft/textures/station_m.dds }
 } }
}
''',encoding='utf8')
manifest={'energy_before_sha256':sha(energy),'craft_before_sha256':sha(craft),'ammo_stackable':[1,100],
 'ammo_charges_weights_and_recipes_unchanged':True,'gauss_native_sound_preserved':True,'existing_tech_and_functionality_records_unchanged':True,
 'station':{'building_id':building['id'],'part_id':part['id'],'material_id':mat['id'],'triangles':15184,'physics_static_boxes':7,'scale':1.0,'building_height':26.00225067138672},
 'files':{f.relative_to(PACKAGE).as_posix():sha(f)for f in PACKAGE.rglob('*')if f.is_file()},'installed':False,'game_verified':False}
(O/'validation.json').write_text(json.dumps(manifest,indent=2),encoding='utf8');print(json.dumps({'files':len(manifest['files']),'ammo_stackable':100,'collision_boxes':7,'station_new_ids':[part['id'],mat['id']]}))
