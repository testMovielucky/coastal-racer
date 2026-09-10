"""Original coastal art sample. Blender 5.2.1 LTS, no external generation.
blender --background --factory-startup --python-exit-code 1 --python tools/blender/coast_sample_v006.py
Separate reusable GLBs + authored sample layout + Blender review scene.
"""
import bpy, bmesh, math, json, hashlib, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
VERSION='v006'; SEED=909061
SRC=ROOT/'assets-source/blender/coast_sample'/VERSION
PRE=ROOT/'assets-source/previews/coast_sample'/VERSION
META=ROOT/'assets-source/metadata/coast_sample'/VERSION
OUT=ROOT/'public/assets/themes/coast'/('sample-'+VERSION)
BLEND=SRC/('coast_sample_'+VERSION+'.blend')
CAR=ROOT/'public/assets/cars/cr_sport_01/v006/cr_sport_01_v006.glb'
CAR_SHA='ada35c65b99507aa1f019be017b2c7d0ba3f9e222bc7e496686e13539c7c38dd'
assert hashlib.sha256(CAR.read_bytes()).hexdigest()==CAR_SHA
if BLEND.exists(): raise RuntimeError('Preserve existing version; create a new revision.')
for p in (SRC,PRE,META,OUT): p.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
prototypes=bpy.data.collections.new('ASSET_PROTOTYPES'); scene.collection.children.link(prototypes)
layout_coll=bpy.data.collections.new('COAST_REVIEW_LAYOUT'); scene.collection.children.link(layout_coll)
studio=bpy.data.collections.new('REVIEW_LIGHT_CAMERA'); scene.collection.children.link(studio)

def relocate(o,coll=prototypes):
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o)
    return o

def material(name,rough,metal=0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    vc=m.node_tree.nodes.new('ShaderNodeVertexColor'); vc.layer_name='Color'
    m.node_tree.links.new(vc.outputs['Color'],bs.inputs['Base Color'])
    return m

asphalt=material('Coast_Asphalt',.88)
mineral=material('Coast_Mineral',.82)
paint=material('Coast_Painted',.42,.10)
foliage=material('Coast_Foliage',.70)
water=material('Coast_Water',.27,.18)
metal=material('Coast_Metal',.32,.65)
SAND=(.70,.48,.24); CREAM=(.80,.76,.60); WHITE=(.91,.93,.89)
TEAL=(.012,.43,.46); CORAL=(.93,.16,.055); LEAF=(.028,.27,.065)

def mesh(name,verts,faces,mat,col,smooth=False,face_colors=None):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); prototypes.objects.link(o); me.materials.append(mat)
    attr=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for p in me.polygons:
        p.use_smooth=smooth
        color=face_colors[p.index] if face_colors else col
        for li in p.loop_indices: attr.data[li].color=(*color,1)
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    return o

def box(name,loc,size,mat,col,bevel=0):
    x,y,z=[v/2 for v in size]
    o=mesh(name,[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,col)
    o.location=loc
    if bevel:
        b=o.modifiers.new('Edge_radii','BEVEL'); b.width=bevel; b.segments=2
        n=o.modifiers.new('Weighted_normals','WEIGHTED_NORMAL'); n.keep_sharp=True
    return o

def sweep(name,points,radii,mat,col,sides=8):
    verts=[]
    for i,p in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        tangent.normalize(); a=tangent.cross(Vector((0,1,0)))
        if a.length<.01: a=tangent.cross(Vector((1,0,0)))
        a.normalize(); b=tangent.cross(a).normalized()
        for j in range(sides):
            verts.append(Vector(p)+radii[i]*(a*math.cos(j*2*math.pi/sides)+b*math.sin(j*2*math.pi/sides)))
    faces=[]
    for i in range(len(points)-1):
        for j in range(sides): faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces += [tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))]
    return mesh(name,verts,faces,mat,col,True)

def ellipsoid(name,loc,scale,mat,col):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,location=loc)
    o=relocate(bpy.context.object); o.name=name; o.scale=scale
    o.data.materials.append(mat)
    attr=o.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for v in attr.data: v.color=(*col,1)
    for p in o.data.polygons: p.use_smooth=True
    return o

exec(compile((ROOT/'tools/blender/coast_look_v006.py').read_text(encoding='utf-8-sig'), 'coast_look_v006.py', 'exec'))
tune_materials()

assets={}; specs={}
def finish_asset(name,objects,description,colliders=None,connections=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        bpy.context.view_layer.objects.active=o
        for mod in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
        o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]; bpy.ops.object.join()
    o=bpy.context.object; o.name=name
    scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces)); bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges))
    bm.to_mesh(o.data); bm.free(); o.data.update()
    recolor_asset(o,name)
    root=bpy.data.objects.new(name+'_Root',None); prototypes.objects.link(root); o.parent=root
    root['asset_version']=VERSION; root['units']='metres'; root['seed']=SEED
    root['forward_blender']='-Y'; root['forward_gltf']='+Z'
    selected=[root,o]
    if connections:
        for label,pos in connections.items():
            marker=bpy.data.objects.new(name+'_'+label,None); prototypes.objects.link(marker); marker.parent=root; marker.location=pos
            marker['connection']=True; selected.append(marker)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected: obj.select_set(True)
    tune_materials()
    path=OUT/(name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_extras=True,export_cameras=False,export_lights=False,export_animations=False)
    specs[name]={'file':path.name,'description':description,'triangles':len(o.data.polygons),'materials':[m.name for m in o.data.materials],
                 'bounds_blender_m':{'min':[min(v.co[i] for v in o.data.vertices) for i in range(3)],'max':[max(v.co[i] for v in o.data.vertices) for i in range(3)]},
                 'connections_blender_m':connections or {},'colliders_blender':colliders or [],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    assets[name]=o
    for obj in selected: obj.hide_render=True; obj.hide_set(True)
    return o

exec(compile((ROOT/'tools/blender/coast_details_v006.py').read_text(encoding='utf-8-sig'), 'coast_details_v006.py', 'exec'))

# 8-metre straight road: exact flat contact surface, un-bevelled mating ends.
parts=[]
parts.append(box('Road_deck',(0,0,-.12),(8.4,8,.24),asphalt,(.145,.178,.191)))
for s in (-1,1):
    parts.append(box('Edge_line',(s*3.91,0,.003),(.13,8,.006),mineral,WHITE))
    parts.append(box('Road_margin',(s*4.17,0,.008),(.06,8,.016),mineral,(.28,.34,.35)))
for y in (-2,2): parts.append(box('Centre_dash',(0,y,.003),(.13,2,.006),mineral,WHITE))
finish_asset('road_straight_8m',parts,'8.4 m wide two-lane art sample; marking phase repeats every 4 m.',
             [{'shape':'box','center':[0,0,-.12],'size':[8.4,8,.24]}],{'Entry':[0,4,0],'Exit':[0,-4,0]})

# Raised promenade, with shallow real tile gaps over a continuous slab.
parts=[box('Walk_base',(0,0,.045),(2.4,8,.09),mineral,CREAM)]
for i in range(3):
    for j in range(8):
        col=tuple(c*(.93+.035*((i*7+j*3)%4)) for c in CREAM)
        parts.append(box('Walk_tile',(-.8+i*.8,-3.5+j,.104),(.783,.983,.035),mineral,col))
parts.append(box('Road_curb',(-1.12,0,.10),(.16,8,.20),mineral,WHITE))
parts.append(box('Beach_edge',(1.12,0,.025),(.16,8,.05),mineral,(.69,.65,.50)))
finish_asset('promenade_8m',parts,'2.4 m wide pale tiled promenade; curb faces local -X.',
             [{'shape':'box','center':[0,0,.06],'size':[2.4,8,.12]}],{'Entry':[0,4,.12],'Exit':[0,-4,.12]})

# Airy coastal railing, matching the reference's light posts and teal cap.
parts=[box('Barrier_footing',(0,0,.035),(.40,4,.07),mineral,WHITE),
       box('Barrier_lower_rail',(0,0,.50),(.14,4,.16),paint,WHITE),
       box('Barrier_teal_cap',(0,0,.79),(.20,4,.075),paint,TEAL)]
for y in (-1.85,0,1.85):
    parts.append(box('Barrier_post',(0,y,.41),(.14,.14,.78),paint,WHITE))
    parts.append(box('Barrier_post_cap',(0,y,.84),(.20,.20,.04),paint,TEAL))
finish_asset('barrier_4m',parts,'Open pale coastal railing with turquoise cap; 4 m repeat.',
             [{'shape':'box','center':[0,0,.4],'size':[.4,4,.8]}],{'Entry':[0,2,0],'Exit':[0,-2,0]})
# Narrow landscaped strip on the inland side. Gravel edging and large leaf
# clumps give a deliberately limited motif, leaving the road visually clear.
parts=[box('Land_base',(0,0,-.14),(3.4,8,.24),mineral,(.10,.31,.032)),
       box('Land_curb',(1.63,0,.045),(.14,8,.09),mineral,CREAM)]
for y in (-2.8,2.8):
    for j in range(7):
        angle=j*2*math.pi/7; length=.40+.05*(j%3)
        root=Vector((-.75,y,.0)); d=Vector((math.cos(angle),math.sin(angle),0))
        cross=Vector((-d.y,d.x,0))
        tip=root+d*length+Vector((0,0,.28+.05*(j%2)))
        v=[root,root+d*.25+cross*.07+Vector((0,0,.16)),tip,root+d*.25-cross*.07+Vector((0,0,.16)),root+d*.25+Vector((0,0,.20))]
        parts.append(mesh('Agave_leaf',v,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],foliage,(.11,.32,.22)))
finish_asset('inland_strip_8m',parts,'3.4 m planted verge, reserved decor outside the driveable road.',[],{'Entry':[0,4,0],'Exit':[0,-4,0]})

# Beach strip. Periodic shoreline and identical cross-sections at y=±4 avoid
# cracks when neighbouring modules meet. Local X=0 starts at the promenade.
def shore_x(y): return 7.0+.32*math.cos(y*math.pi/4)+.10*math.cos(y*math.pi/2)
verts=[]; faces=[]; colors=[]
for j in range(33):
    y=-4+j*.25; shore=shore_x(y)
    ring=[(0,y,-.015),(1.6,y,-.04),(shore-1.5,y,-.15),(shore-.55,y,-.225),(shore,y,-.28),(shore+.8,y,-.39)]
    verts.extend(ring)
for j in range(32):
    for k in range(5):
        faces.append((j*6+k,j*6+k+1,(j+1)*6+k+1,(j+1)*6+k))
        colors.append([(.77,.58,.34),(.77,.58,.34),(.67,.49,.27),(.48,.41,.25),(.21,.49,.39)][k])
parts=[mesh('Beach_surface',verts,faces,mineral,SAND,True,colors)]
# Rocks are now reusable independent clustered assets.
finish_asset('beach_8m',parts,'8 m long sand-to-shallows transition, periodic matching shore profile.',[],{'Entry':[0,4,-.015],'Exit':[0,-4,-.015]})

build_rich_water()
lush_palm()

# Small coastal furniture accent; helps scale without expanding to buildings.
parts=[box('Bollard_foot',(0,0,.035),(.32,.32,.07),mineral,CREAM,.035),
       box('Bollard_post',(0,0,.38),(.12,.12,.70),metal,(.10,.19,.20),.022),
       box('Bollard_band',(0,0,.62),(.132,.132,.12),paint,WHITE,.008),
       box('Bollard_cap',(0,0,.76),(.15,.15,.05),paint,TEAL,.015)]
finish_asset('bollard',parts,'Promenade bollard, no electric light or runtime effect.',
             [{'shape':'box','center':[0,0,.40],'size':[.16,.16,.80]}])

make_enrichment_assets()

# Author a bounded 40 m review composition from reusable prototypes.
placements=[]
def place(asset,pos,rotation=0,scale=1):
    src=assets[asset]; o=src.copy(); o.data=src.data; o.parent=None
    layout_coll.objects.link(o); o.name=asset+'_Instance_%02d'%len(placements)
    o.location=pos; o.rotation_euler.z=rotation; o.scale=(scale,scale,scale)
    o.hide_render=False; o.hide_set(False)
    placements.append({'asset':asset,'position_blender_m':list(pos),'rotation_z_radians':rotation,'uniform_scale':scale})
    return o
for y in (-16,-8,0,8,16):
    place('road_straight_8m',(0,y,0))
    place('promenade_8m',(5.7,y,0))
    place('inland_strip_8m',(-5.9,y,0))
    place('beach_8m',(6.9,y,0))
    place('water_8m',(6.9,y,0))
for y in range(-18,20,4): place('barrier_4m',(4.44,y,0))
for pos,rot,scale in [((7.8,-13,-.04),.4,1.04),((8.1,3,-.04),2.7,1.0),((-6.0,-5,-.01),1.2,1.08),((-6.1,13,-.01),3.7,.94),((8.0,16,-.04),5.0,.87)]:
    place('palm_a',pos,rot,scale)
for y in (-16,-8,0,8,16): place('bollard',(6.6,y,.12))

place_enrichment(place)

# Accepted car is loaded unchanged for the review scene only, never re-exported.
before=set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(CAR))
car_objects=set(scene.objects)-before
car_collection=bpy.data.collections.new('ACCEPTED_CAR_V006_REVIEW_ONLY'); scene.collection.children.link(car_collection)
for o in car_objects: relocate(o,car_collection)
car_root=next(o for o in car_objects if o.name=='CR_Sport_01')
car_root.location=(-1.85,11.0,.011)

layout={'schema_version':1,'asset_version':VERSION,'seed':SEED,'scenario':'coast-art-sample-40m','units':'metres',
        'axes':{'blender':{'forward':'-Y','up':'+Z'},'gltf':{'forward':'+Z','up':'+Y'},'blender_to_gltf_position':'(x,y,z) -> (x,z,-y)'},
        'road':{'width_m':8.4,'sample_length_m':40,'module_length_m':8,'top_z_blender_m':0,'entry_blender':[0,20,0],'exit_blender':[0,-20,0],
                'decor_exclusion_blender':{'min':[-4.2,-20,0],'max':[4.2,20,5]}},
        'assets':specs,'placements':placements,
        'review_car':{'path':str(CAR.relative_to(ROOT)).replace('\\','/'),'sha256':CAR_SHA,'position_blender_m':list(car_root.location),'exported_with_environment':False},
        'status':'awaiting_artistic_review','not_implemented':['track generator','race physics','browser integration','animated water','device performance measurement']}
(OUT/'sample_layout.json').write_text(json.dumps(layout,indent=2),encoding='utf8')
(META/'asset_inventory.json').write_text(json.dumps(layout,indent=2),encoding='utf8')

# Local daylight studio; large water plane is review backdrop, not an asset.
backdrop_water=material('Review_Backdrop_Water',.25,.18)
bg=box('Review_ocean_backdrop',(15,0,-.42),(2000,2000,.08),backdrop_water,(.002,.23,.43)); relocate(bg,studio)
scene.world.use_nodes=True; nt=scene.world.node_tree
nt.nodes.get('Background').inputs[0].default_value=(.32,.60,.87,1)
nt.nodes.get('Background').inputs[1].default_value=.50
def light(name,kind,loc,power,color,target,size=0):
    data=bpy.data.lights.new(name,kind); data.energy=power; data.color=color
    if kind=='AREA': data.shape='DISK'; data.size=size
    else: data.angle=math.radians(3)
    o=bpy.data.objects.new(name,data); studio.objects.link(o); o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
light('Coastal_sun','SUN',(-12,-8,20),3.0,(1,.91,.75),(0,0,0))
light('Sky_softbox','AREA',(2,3,17),1400,(.64,.83,1),(0,0,0),12)
camera_data=bpy.data.cameras.new('Coast_review_camera'); camera=bpy.data.objects.new('Coast_review_camera',camera_data); studio.objects.link(camera); scene.camera=camera
scene.render.engine='CYCLES'; scene.cycles.samples=48; scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG'; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=.15
tune_review(scene)
views={'overview':{'pos':(-31,37,30),'target':(5,0,.3),'ortho':57,'size':(1600,1100)},
       'gameplay':{'pos':(.8,20.5,9.8),'target':(-.9,7.4,.3),'lens':42,'size':(1080,1440)},
       'coast_detail':{'pos':(21,15,10),'target':(7.4,3,.9),'lens':45,'size':(1500,1050)},
       'tower_detail':{'pos':(16,-16,6.5),'target':(10.6,-7.5,1.75),'lens':48,'size':(1400,1100)},
       'gameplay_composed':{'pos':(-10,24,14),'target':(2,7,.5),'lens':42,'size':(1600,1000)}}
def view(params):
    camera.location=params['pos']; camera.rotation_euler=(Vector(params['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO' if 'ortho' in params else 'PERSP'
    if 'ortho' in params: camera_data.ortho_scale=params['ortho']
    else: camera_data.lens=params['lens']
    scene.render.resolution_x,scene.render.resolution_y=params['size']
view(views['overview'])
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
for name,params in views.items():
    view(params); scene.render.filepath=str(PRE/(name+'.png')); bpy.ops.render.render(write_still=True)
assert hashlib.sha256(CAR.read_bytes()).hexdigest()==CAR_SHA
print('COAST_SAMPLE_COMPLETE',str(BLEND),flush=True)





