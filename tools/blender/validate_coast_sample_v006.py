"""Static GLB, modular seam and real Blender import checks. No game-code writes."""
import bpy, json, struct, hashlib, math, numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'public/assets/themes/coast/sample-v006'
META=ROOT/'assets-source/metadata/coast_sample/v006'
layout=json.loads((OUT/'sample_layout.json').read_text(encoding='utf8'))
assert layout['seed']==909061 and layout['road']['width_m']==8.4
assert layout['road']['sample_length_m']==40
reports={}; all_materials=set(); total_bytes=0; unique_triangles=0
for name,spec in layout['assets'].items():
    path=OUT/spec['file']; raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==spec['sha256']
    magic,ver,sz=struct.unpack_from('<4sII',raw)
    assert magic==b'glTF' and ver==2 and sz==len(raw)
    jlen,jtyp=struct.unpack_from('<II',raw,12); assert jtyp==0x4e4f534a
    g=json.loads(raw[20:20+jlen]); blen,btyp=struct.unpack_from('<II',raw,20+jlen); assert btyp==0x004e4942
    binary=raw[28+jlen:28+jlen+blen]
    if name=='water_8m':
        assert len(g.get('textures',[]))==1 and len(g.get('images',[]))==1
        assert 'uri' not in g['images'][0] and g['images'][0]['mimeType']=='image/png'
        view=g['bufferViews'][g['images'][0]['bufferView']]
        payload=binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
        assert payload[:8]==bytes([137,80,78,71,13,10,26,10])
        width,height=struct.unpack_from('>II',payload,16)
        assert width==1024 and height==1024
        assert g['materials'][0].get('pbrMetallicRoughness',{}).get('baseColorTexture') is not None or any('baseColorTexture' in m.get('pbrMetallicRoughness',{}) for m in g['materials'])
    else:
        assert not g.get('textures') and not g.get('images')
    assert not any('uri' in b for b in g.get('buffers',[]))
    assert not g.get('animations') and not g.get('cameras')
    def access(idx):
        a=g['accessors'][idx]; v=g['bufferViews'][a['bufferView']]
        fmt,size={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']]
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        stride=v.get('byteStride',size*width); start=v.get('byteOffset',0)+a.get('byteOffset',0)
        assert start+(a['count']-1)*stride+size*width<=len(binary)
        return [struct.unpack_from('<'+fmt*width,binary,start+i*stride) for i in range(a['count'])]
    triangles=0; primitive_count=0; degenerates=0; positions=[]
    for mesh in g['meshes']:
        for p in mesh['primitives']:
            primitive_count+=1; assert p.get('mode',4)==4
            pos=access(p['attributes']['POSITION']); normals=access(p['attributes']['NORMAL']); col=access(p['attributes']['COLOR_0'])
            assert all(math.isfinite(v) for xyz in pos for v in xyz)
            assert all(abs(Vector(n).length-1)<.01 for n in normals)
            assert len(col)==len(pos)
            ids=[v[0] for v in access(p['indices'])]; assert len(ids)%3==0 and max(ids)<len(pos)
            triangles+=len(ids)//3
            for i in range(0,len(ids),3):
                a,b,c=[Vector(pos[ids[i+j]]) for j in range(3)]
                if (b-a).cross(c-a).length<1e-10: degenerates+=1
            positions+=pos
    assert degenerates==0,(name,degenerates)
    assert triangles==spec['triangles'],(name,triangles,spec['triangles'])
    node_names=[n.get('name') for n in g['nodes']]
    assert name in node_names and name+'_Root' in node_names
    assert len(node_names)==len(set(node_names))
    for label,pos in spec['connections_blender_m'].items():
        nd=next(n for n in g['nodes'] if n.get('name')==name+'_'+label)
        expected=(pos[0],pos[2],-pos[1])
        assert all(abs(a-b)<1e-6 for a,b in zip(nd['translation'],expected))
    # Exported positions: glTF Z = -Blender Y. Compare exact end perimeter
    # coordinate sets in X/Y at both ends (no camera-based seam claim).
    seam=None
    if spec['connections_blender_m']:
        half=abs(spec['connections_blender_m']['Entry'][1])
        ends=[]
        for side in (-1,1):
            ends.append({(round(p[0],5),round(p[1],5)) for p in positions if abs(p[2]-side*half)<1e-5})
        assert ends[0] and ends[0]==ends[1],(name,'different mating profiles',len(ends[0]),len(ends[1]))
        seam={'matching_end_profiles':True,'profile_vertex_positions':len(ends[0]),'length_m':half*2}
    mats=[m['name'] for m in g['materials']]; all_materials.update(mats)
    reports[name]={'triangles':triangles,'bytes':len(raw),'materials':mats,'material_count':len(mats),'primitives':primitive_count,'degenerate_triangles':degenerates,'end_seam':seam,'sha256':spec['sha256']}
    total_bytes+=len(raw); unique_triangles+=triangles

# Actual import of every module in a clean scene; ensure the engine format is
# consumable rather than trusting the file extension or the export log alone.
for name,spec in layout['assets'].items():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(OUT/spec['file']))
    nodes=list(bpy.context.scene.objects)
    assert any(o.name==name+'_Root' for o in nodes)
    meshes=[o for o in nodes if o.type=='MESH']
    assert len(meshes)==1,(name,len(meshes))
    for o in meshes: o.data.calc_loop_triangles()
    assert sum(len(o.data.loop_triangles) for o in meshes)==reports[name]['triangles']
    reports[name]['blender_import']=True
    if name=='water_8m':
        imported_images=[n.image for o in meshes for m in o.data.materials for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
        assert any(tuple(img.size)==(1024,1024) for img in imported_images)
        image=next(img for img in imported_images if tuple(img.size)==(1024,1024))
        source_image=bpy.data.images.load(str(ROOT/'assets-source/blender/coast_sample/v006/textures/water_pattern_1024.png'),check_existing=False)
        actual=np.empty(1024*1024*4,dtype=np.float32); expected=np.empty_like(actual)
        image.pixels.foreach_get(actual); source_image.pixels.foreach_get(expected)
        error=float(np.max(np.abs(actual-expected)))
        seam_error=float(np.max(np.abs(actual.reshape(1024,1024,4)[0]-actual.reshape(1024,1024,4)[-1])))
        assert error<1/255 and seam_error<1/255,(error,seam_error)
        reports[name]['embedded_texture_matches_source_max_error']=error
        reports[name]['texture_repeat_row_max_error']=seam_error

assert len(all_materials)<=6,all_materials
assert unique_triangles<=16000,unique_triangles
sample_triangles=sum(reports[p['asset']]['triangles'] for p in layout['placements'])
assert sample_triangles<=50000,sample_triangles
for placement in layout['placements']:
    if placement['asset'] in ('palm_a','bollard','rock_cluster','agave_cluster','flower_cluster','beach_umbrella','beach_lounger','lifeguard_tower'):
        assert abs(placement['position_blender_m'][0])>4.5
road_positions=sorted(p['position_blender_m'][1] for p in layout['placements'] if p['asset']=='road_straight_8m')
assert road_positions==[-16,-8,0,8,16]
assert all(abs(b-a-8)<1e-8 for a,b in zip(road_positions,road_positions[1:]))
car=ROOT/layout['review_car']['path']; assert hashlib.sha256(car.read_bytes()).hexdigest()==layout['review_car']['sha256']
report={'asset_set':'coast_sample','version':'v006','scenario':layout['scenario'],'seed':layout['seed'],'blender':bpy.app.version_string,
        'unique_geometry_triangles':unique_triangles,'sample_environment_triangles':sample_triangles,'sample_with_car_triangles':sample_triangles+21114,
        'module_glb_total_bytes':total_bytes,'unique_environment_materials':sorted(all_materials),'texture_count':1,'texture_resolution':[1024,1024],'asset_count':len(reports),'placement_count':len(layout['placements']),
        'assets':reports,'checks':{'binary_accessors_indices_colors_normals':True,'no_external_assets':True,'zero_degenerate_triangles':True,'module_connections':True,'road_adjacency':True,'decor_outside_road':True,'car_unchanged':True,'blender_import_all_modules':True},
        'not_verified':['human artistic approval','Babylon rendering','physics collider integration','iPhone/iPad performance']}
(META/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))






