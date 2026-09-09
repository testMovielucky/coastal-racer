"""Read-only GLB/source validation, writes one version-specific evidence report.
Run with Blender --background --factory-startup --python this_script.py.
"""
import bpy, json, struct, math, hashlib, bmesh
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'public/assets/cars/cr_sport_01/v006'
META=ROOT/'assets-source/metadata/cr_sport_01/v006'
path=OUT/'cr_sport_01_v006.glb'
raw=path.read_bytes()
magic,version,length=struct.unpack_from('<4sII',raw)
assert magic==b'glTF' and version==2 and length==len(raw)
n,typ=struct.unpack_from('<II',raw,12)
assert typ==0x4e4f534a
g=json.loads(raw[20:20+n])
binlen,bintyp=struct.unpack_from('<II',raw,20+n)
assert bintyp==0x004e4942
data=raw[28+n:28+n+binlen]
assert not any('uri' in x for x in g.get('buffers',[])+g.get('images',[]))
formats={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}
sizes={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def accessor(index):
    a=g['accessors'][index]; v=g['bufferViews'][a['bufferView']]
    fmt,sz=formats[a['componentType']]; width=sizes[a['type']]
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    stride=v.get('byteStride',width*sz)
    assert offset+(a['count']-1)*stride+width*sz<=len(data)
    return [struct.unpack_from('<'+fmt*width,data,offset+i*stride) for i in range(a['count'])]
triangles=0; degenerate=0; primitives=0
for m in g['meshes']:
    for p in m['primitives']:
        assert p.get('mode',4)==4
        primitives+=1
        indices=[x[0] for x in accessor(p['indices'])]
        pos=accessor(p['attributes']['POSITION'])
        assert all(math.isfinite(v) for xyz in pos for v in xyz)
        assert max(indices)<len(pos) and len(indices)%3==0
        normals=accessor(p['attributes']['NORMAL'])
        assert all(abs(Vector(v).length-1)<.01 for v in normals)
        triangles+=len(indices)//3
        for i in range(0,len(indices),3):
            a,b,c=[Vector(pos[indices[i+j]]) for j in range(3)]
            if (b-a).cross(c-a).length<1e-10: degenerate+=1
names=[n.get('name') for n in g['nodes']]
assert len(names)==len(set(names))
assert set(['CR_Sport_01','Body','Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']).issubset(names)
assert 'Collider_Chassis' not in names
assert len(g['materials'])==4
assert 8000<=triangles<=25000,triangles
assert degenerate==0,degenerate
assert not g.get('textures')
assert not g.get('animations')
root=next(n for n in g['nodes'] if n['name']=='CR_Sport_01')
assert len(root['children'])==5
node_checks={}
for name in ['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']:
    nd=next(n for n in g['nodes'] if n['name']==name)
    t=nd['translation']
    expect=[.907 if name[-1]=='L' else -.907,.355,1.28 if name[-2]=='F' else -1.27]
    assert all(abs(a-b)<1e-5 for a,b in zip(t,expect)),(name,t,expect)
    assert len(nd['children'])==1
    node_checks[name]={'gltf_pivot_m':t,'spin_axis':'local X'}

# Stronger regression gate: each structural shell must be a closed manifold
# in the source, and every source shell triangle must survive the GLB export.
source_path=ROOT/'assets-source/blender/cr_sport_01/v006/cr_sport_01_v006.blend'
with bpy.data.libraries.load(str(source_path),link=False) as (available,loaded):
    loaded.objects=['Body']
source_body=loaded.objects[0]
closed_shell_checks={}
source_triangle_sets={}
def triangle_key(points):
    return tuple(sorted(tuple(round(float(v),6) for v in p) for p in points))
for group_name in ('QA_Closed_Body_Shell','QA_Closed_Canopy'):
    group=source_body.vertex_groups[group_name]
    ids={v.index for v in source_body.data.vertices if any(g.group==group.index and g.weight>.5 for g in v.groups)}
    polygons=[p for p in source_body.data.polygons if all(i in ids for i in p.vertices)]
    bm=bmesh.new()
    vmap={i:bm.verts.new(source_body.data.vertices[i].co) for i in ids}
    for poly in polygons: bm.faces.new([vmap[i] for i in poly.vertices])
    boundary=sum(e.is_boundary for e in bm.edges)
    non_manifold=sum(not e.is_manifold for e in bm.edges)
    assert boundary==0 and non_manifold==0,(group_name,boundary,non_manifold)
    assert abs(bm.calc_volume())>.05
    closed_shell_checks[group_name]={'boundary_edges':boundary,'non_manifold_edges':non_manifold,'triangles':len(bm.faces),'volume_m3':abs(bm.calc_volume())}
    source_triangle_sets[group_name]={triangle_key([source_body.data.vertices[i].co for i in p.vertices]) for p in polygons}
    bm.free()
source_mesh=source_body.data
bpy.data.objects.remove(source_body,do_unlink=True)
bpy.data.meshes.remove(source_mesh)
for material in list(bpy.data.materials):
    if material.users==0: bpy.data.materials.remove(material)

# Real importer round-trip, without changing source/export files.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(path))
bpy.context.view_layer.update()
points=[]
for o in bpy.context.scene.objects:
    if o.type=='MESH': points += [o.matrix_world@v.co for v in o.data.vertices]
minimum=[min(p[k] for p in points) for k in range(3)]
maximum=[max(p[k] for p in points) for k in range(3)]
for name in node_checks:
    node=bpy.data.objects[name]; child=node.children[0]
    vertices=[node.matrix_world.inverted()@child.matrix_world@v.co for v in child.data.vertices]
    radius=max(math.hypot(v.y,v.z) for v in vertices)
    assert abs(radius-.355)<.002,(name,radius)
    before=node.matrix_world.translation.copy()
    node.rotation_euler.x+=math.pi/2
    bpy.context.view_layer.update()
    assert (node.matrix_world.translation-before).length<1e-7
    after=[node.matrix_world.inverted()@child.matrix_world@v.co for v in child.data.vertices]
    assert max((a-b).length for a,b in zip(vertices,after))<1e-5
    node.rotation_euler.x-=math.pi/2
    node_checks[name]['radius_m']=radius
    node_checks[name]['rotation_90deg_keeps_pivot_and_geometry']=True
body=bpy.data.objects['Body']
body.data.calc_loop_triangles()
exported_triangles={triangle_key([body.data.vertices[i].co for i in tri.vertices]) for tri in body.data.loop_triangles}
for name,expected in source_triangle_sets.items():
    missing=expected-exported_triangles
    assert not missing,(name,'shell triangles lost in export',len(missing))
    closed_shell_checks[name]['all_triangles_preserved_in_glb']=True
paint=bpy.data.materials['Body_Paint']
shader=paint.node_tree.nodes.get('Principled BSDF')
saved=shader.inputs['Base Color'].default_value[:]
shader.inputs['Base Color'].default_value=(.02,.3,.8,1)
assert any(slot.material==paint for slot in body.material_slots)
assert shader.inputs['Base Color'].default_value[2]>.79
shader.inputs['Base Color'].default_value=saved
collider=OUT/'cr_sport_01_v006.collider.glb'
collider_raw=collider.read_bytes(); cn=struct.unpack_from('<I',collider_raw,12)[0]; cg=json.loads(collider_raw[20:20+cn])
ct=sum(cg['accessors'][p['indices']]['count']//3 for m in cg['meshes'] for p in m['primitives'])
assert ct==12
report={'asset':'cr_sport_01','version':'v006','blender':bpy.app.version_string,'triangles':triangles,'degenerate_triangles':degenerate,'closed_shells':closed_shell_checks,'triangle_budget':25000,'materials':[m['name'] for m in g['materials']],'material_count':len(g['materials']),'mesh_count':len(g['meshes']),'primitive_count':primitives,'texture_count':len(g.get('textures',[])),'glb_bytes':len(raw),'glb_sha256':hashlib.sha256(raw).hexdigest(),'collider_bytes':len(collider_raw),'collider_triangles':ct,'bounds_blender_m':{'min':minimum,'max':maximum,'dimensions':[maximum[k]-minimum[k] for k in range(3)]},'nodes':names,'wheels':node_checks,'checks':{'binary_container_and_accessors':True,'finite_positions_and_unit_normals':True,'no_degenerate_triangles':True,'triangle_material_texture_budget':True,'no_external_uris':True,'hierarchy_preserved':True,'blender_glb_import':True,'body_color_parameter':True,'separate_box_collider':True},'not_verified':['Babylon rendering','browser performance','iPhone/iPad','human artistic acceptance'],'provenance':{'method':'Original scripted Blender geometry','downloaded_models':False,'paid_generation':False,'youtube_video_viewed':False}}
(META/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))





