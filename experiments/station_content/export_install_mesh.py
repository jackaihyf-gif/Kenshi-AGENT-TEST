"""Bake back faces for native default building materials, not a runtime hook."""
import bpy,sys,types,json
from pathlib import Path
p=Path('D:/JACK/KenshiArmorMod');o=p/'research/station_install_20261103';o.mkdir(exist_ok=True)
sys.path.insert(0,str(p/'tools/native'));m=types.ModuleType('station_addon');m.__path__=[str(p/'tools/kenshi_io_blender-main/4.4')];sys.modules['station_addon']=m
from station_addon import ogre_importer,ogre_exporter
class Op:
 def report(self,*a):print(*a)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
assert ogre_importer.load(Op(),bpy.context,str(p/'research/station_candidate_20261103/jack_station_candidate.mesh'),create_materials=False)=={'FINISHED'}
ob=next(x for x in bpy.context.scene.objects if x.type=='MESH');old=ob.data
verts=[tuple(v.co)for v in old.vertices];faces=[list(f.vertices)for f in old.polygons];uv=old.uv_layers.active
face_uv=[[tuple(uv.data[i].uv)for i in f.loop_indices]for f in old.polygons]
front_triangles=sum(len(f)-2 for f in faces);count=len(verts)
mesh=bpy.data.meshes.new('JACK_Assembly_Station_DoubleSided')
mesh.from_pydata(verts+verts,[],faces+[[i+count for i in reversed(f)]for f in faces]);mesh.update()
layer=mesh.uv_layers.new(name='UVMap')
all_uv=face_uv+[list(reversed(u))for u in face_uv]
for f,coords in zip(mesh.polygons,all_uv):
 f.use_smooth=True
 for i,value in zip(f.loop_indices,coords):layer.data[i].uv=value
ob.data=mesh;ob.name='jack_t60_assembly_station'
mesh.materials.clear();mesh.materials.append(bpy.data.materials.new('JACK_Assembly_Station'))
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
target=o/'jack_t60_assembly_station.mesh';assert not target.exists()
assert ogre_exporter.save(Op(),bpy.context,str(target),tangent_format='FLIPPED',export_skeleton=False)=={'FINISHED'}
report={'front_triangles':front_triangles,'two_sided_triangles':front_triangles*2,'reason':'open source shell; native default building shader backface culling','geometry_scale_unchanged':True,'no_runtime_material_hook':True}
(o/'mesh_build.json').write_text(json.dumps(report,indent=2));print('INSTALL_MESH_READY',report)
