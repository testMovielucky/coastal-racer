"""Original Coastal Racer sport coupe. Blender 5.2.1; metres, front -Y, up Z.
Run: blender --background --factory-startup --python tools/blender/cr_sport_01_v006.py
Outputs are versioned; refuse an existing blend. No external assets or dependencies.
"""
import bpy, math, json, sys, hashlib, bmesh
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'v006'
SRC = ROOT / 'assets-source/blender/cr_sport_01' / VERSION
PREVIEW = ROOT / 'assets-source/previews/cr_sport_01' / VERSION
META = ROOT / 'assets-source/metadata/cr_sport_01' / VERSION
OUT = ROOT / 'public/assets/cars/cr_sport_01' / VERSION
BLEND = SRC / 'cr_sport_01_v006.blend'
if BLEND.exists():
    raise RuntimeError('Version already exists. Preserve it and create a new version.')
for p in (SRC, PREVIEW, META, OUT): p.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
car = bpy.data.collections.new('CAR_EXPORT')
scene.collection.children.link(car)
studio = bpy.data.collections.new('STUDIO_NOT_EXPORTED')
scene.collection.children.link(studio)

def move(obj, coll=car):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj

def material(name, color, metal, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    m.diffuse_color = (*color, 1)
    return m

paint = material('Body_Paint', (0.80, .065, .004), .40, .30)
paint.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value = .32
trim = material('Rubber_Trim', (.016, .021, .028), .05, .56)
glass = material('Glass_Dark', (.025, .065, .085), .48, .16)
detail = material('Detail_VertexColor', (.65, .7, .75), .65, .28)
vc = detail.node_tree.nodes.new('ShaderNodeVertexColor')
vc.layer_name = 'Color'
detail.node_tree.links.new(vc.outputs['Color'], detail.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
materials = [paint, trim, glass, detail]

def mesh(name, verts, faces, mat=paint, color=None, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    o = bpy.data.objects.new(name, data)
    car.objects.link(o)
    data.materials.append(mat)
    if color:
        attr = data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for v in attr.data: v.color = (*color, 1)
    for f in data.polygons: f.use_smooth = smooth
    # Recalculate normals for custom closed surfaces and strips.
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    o.select_set(False)
    return o

def bevel(o, width=.018, segments=1):
    mod = o.modifiers.new('Small manufactured edge radii', 'BEVEL')
    mod.width, mod.segments = width, segments
    mod = o.modifiers.new('Weighted surface normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    return o

def box(name, loc, size, mat, radius=.012, color=None):
    x,y,z = [v/2 for v in size]
    verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    o=mesh(name,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,color)
    o.location=loc
    if radius: bevel(o,radius)
    return o

def line(name, points, radius, mat, color=None, sides=4):
    # Explicit swept polygon tube, no runtime curves.
    verts=[]
    for i,point in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        tangent.normalize()
        a=tangent.cross(Vector((0,0,1)))
        if a.length<.01: a=tangent.cross(Vector((0,1,0)))
        a.normalize(); b=tangent.cross(a).normalized()
        for j in range(sides):
            v=Vector(point)+radius*(a*math.cos(j*2*math.pi/sides)+b*math.sin(j*2*math.pi/sides))
            verts.append(v)
    faces=[]
    for i in range(len(points)-1):
        for j in range(sides): faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces += [tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))]
    return mesh(name,verts,faces,mat,color,True)

# Hand-designed continuous longitudinal profiles. The hood flows into broad
# fenders; actual open arches are part of the mesh, not black painted circles.
profile=[(-2.13,.77,.55),(-1.96,.91,.65),(-1.55,.97,.75),(-1.27,.98,.80),(-.85,.925,.75),(-.35,.885,.73),(.35,.91,.77),(.9,.99,.84),(1.26,1.015,.86),(1.65,.985,.80),(2.04,.90,.73),(2.13,.86,.68)]
def interp(y, idx):
    for i,(a,b) in enumerate(zip(profile,profile[1:])):
        if a[0]<=y<=b[0]:
            prev=profile[max(0,i-1)]; nxt=profile[min(len(profile)-1,i+2)]
            span=b[0]-a[0]; t=(y-a[0])/span
            ma=(b[idx]-prev[idx])/(b[0]-prev[0])*span
            mb=(nxt[idx]-a[idx])/(nxt[0]-a[0])*span
            return (2*t**3-3*t*t+1)*a[idx]+(t**3-2*t*t+t)*ma+(-2*t**3+3*t*t)*b[idx]+(t**3-t*t)*mb
    return profile[0 if y<0 else -1][idx]
def arch(y):
    value=.22
    for cy in (-1.28,1.27):
        d=abs(y-cy)
        if d<.418: value=max(value,.355+math.sqrt(.418**2-d*d))
    return value
# One continuous watertight body ring with integrated arch returns, inner
# wheel-well walls and underfloor. End caps use the exact surface perimeter.
ys=sorted(set(round(y,7) for y in
    [-2.13+i*4.26/144 for i in range(145)]+[p[0] for p in profile]+
    [c-.418*math.cos(j*math.pi/48) for c in (-1.28,1.27) for j in range(49)]+
    [c+d for c in (-1.28,1.27) for d in (-.41801,.41801)]))
verts=[]
ring_size=20
for y in ys:
    w,h=interp(y,1),interp(y,2)
    low=arch(y)
    right=[(0,y,h-.025)]
    for t,dz in [(.35,-.015),(.68,0),(.89,.018),(1,-.025)]:
        right.append((w*t,y,h+dz))
    right += [(w*1.008,y,max(low+.025,h-.09)),
              (w*.99,y,low), (w-.035,y,low-.010),
              (w-.25,y,low-.018), (w-.25,y,.18), (0,y,.18)]
    ring=right+[(-x,yy,z) for x,yy,z in reversed(right[1:-1])]
    assert len(ring)==ring_size
    verts.extend(ring)
faces=[]
for i in range(len(ys)-1):
    for j in range(ring_size):
        faces.append((i*ring_size+j,i*ring_size+(j+1)%ring_size,
                      (i+1)*ring_size+(j+1)%ring_size,(i+1)*ring_size+j))
faces += [tuple(reversed(range(ring_size))),
          tuple((len(ys)-1)*ring_size+j for j in range(ring_size))]
hull=mesh('Body_shell_closed',verts,faces,paint,smooth=True)
# Leave hidden underfloor and wheel-well wall normals flat, preventing their
# shading from bleeding into the polished fender.
for poly in hull.data.polygons:
    if poly.index >= (len(ys)-1)*ring_size or poly.index%ring_size in (7,8,9,10,11,12):
        poly.use_smooth=False
def tag_closed(obj,group_name):
    group=obj.vertex_groups.new(name=group_name)
    group.add(list(range(len(obj.data.vertices))),1.0,'REPLACE')
tag_closed(hull,'QA_Closed_Body_Shell')
for s in (-1,1):
    box('Aero_rocker', (s*.903,0,.227),(.085,1.57,.094),trim,.015)
    line('Rocker_paint_edge',[(s*.93,-.78,.28),(s*.91,.3,.28),(s*.96,.81,.32)],.018,paint)

# Closed canopy: roof, both window sides, end closures and underside share
# vertices. Lower glazing is embedded into the hull to prevent daylight gaps.
cab=[(-.87,.72,.729),(-.29,.60,1.135),(.12,.605,1.19),(.57,.585,1.18),(.92,.64,1.015),(1.42,.76,.806)]
verts=[]
for y,w,h in cab:
    for t in (-1,-.7,0,.7,1): verts.append((w*t,y,h+.025*(1-t*t)))
    lower_z=min(interp(y,2)-.055,h-.018)
    verts.extend([(.80,y,lower_z),(-.80,y,lower_z)])
faces=[]
for i in range(len(cab)-1):
    for j in range(7): faces.append((i*7+j,i*7+(j+1)%7,(i+1)*7+(j+1)%7,(i+1)*7+j))
faces += [tuple(reversed(range(7))),tuple((len(cab)-1)*7+j for j in range(7))]
canopy=mesh('Canopy_closed',verts,faces,glass,smooth=True)
canopy.data.materials.append(paint)
for poly in canopy.data.polygons:
    row,j=divmod(poly.index,7)
    if (row in (1,2) and j<4) or j==5: poly.material_index=1
    if j>=4: poly.use_smooth=False
tag_closed(canopy,'QA_Closed_Canopy')
for s in (-1,1):
    side=[(s*.72,-.87,.729),(s*.60,-.29,1.135),(s*.605,.12,1.19),(s*.585,.57,1.18),(s*.64,.92,1.015),(s*.76,1.42,.806),(s*.80,.67,interp(.67,2)-.027)]
    line('Window_surround',side+[side[0]],.022,paint)
    line('Quarter_pillar',[(s*.60,.61,1.125),(s*.78,.72,.807)],.026,paint)
    points=[(s*.922,-.68,.70),(s*.928,-.64,.42),(s*.914,-.4,.31),(s*.916,.53,.32),(s*.95,.67,.62)]
    line('Door_shutline',points,.005,trim,sides=4)
    # The previous protruding black side intake and its blade are removed.
    box('Flush_handle',(s*.919,.33,.716),(.017,.17,.025),trim,.008)
    line('Mirror_stalk',[(s*.73,-.65,.84),(s*.98,-.61,.86)],.023,trim)
    box('Mirror_shell',(s*1.027,-.60,.876),(.20,.24,.105),paint,.037)
    box('Mirror_glass',(s*1.025,-.472,.877),(.146,.009,.060),glass,.012)

# Hood panel seams and extractors follow the low, tapered bonnet.
for s in (-1,1):
    line('Hood_panel_gap',[(s*.50,-1.98,.655),(s*.48,-1.6,.74),(s*.44,-1.05,.765),(s*.57,-.88,.758)],.0045,trim,sides=4)
    for j in range(3):
        o=box('Hood_extractor',(s*.59,-1.12+j*.066,.779),(.19,.024,.011),trim,.006)
    # Narrow lamps lie on sloping nose, with deliberate vertical end signature.
    def lamp_point(x,y,offset=.008):
        t=x/interp(y,1)
        dz=.018 if t<.89 else .018-(t-.89)/.11*.043
        return (s*x,y,interp(y,2)+dz+offset)
    patch=[lamp_point(.47,-2.085),lamp_point(.73,-2.062),lamp_point(.84,-1.89),lamp_point(.64,-1.95)]
    mesh('Inset_headlight_housing',patch,[(0,1,2,3)],trim)
    line('Front_LED',[lamp_point(.50,-2.065,.016),lamp_point(.72,-2.044,.016),lamp_point(.81,-1.919,.016)],.012,detail,(.68,.91,1))
    mesh('Front_corner_duct',[(s*.48,-2.14,.30),(s*.77,-2.14,.29),(s*.74,-2.14,.442),(s*.53,-2.14,.45)],[(0,1,2,3)],trim)
mesh('Front_intake',[(-.38,-2.144,.31),(.38,-2.144,.31),(.32,-2.144,.454),(-.32,-2.144,.454)],[(0,1,2,3)],trim)
for x in (-.25,-.125,0,.125,.25): box('Grille_fin',(x,-2.166,.36),(.016,.017,.12),trim,.003)
line('Front_splitter',[(-.88,-1.94,.237),(-.76,-2.17,.22),(0,-2.195,.211),(.76,-2.17,.22),(.88,-1.94,.237)],.028,trim)

# Rear view is the primary composition: dark full-width recess, paired red
# signatures, floating lip, recessed centre and a finned diffuser.
box('Tail_graphic_recess',(0,2.137,.579),(1.65,.035,.163),trim,.03)
for s in (-1,1):
    pts=[(s*.12,2.168,.62),(s*.61,2.166,.62),(s*.78,2.153,.596)]
    line('Tail_LED_upper',pts,.018,detail,(1,.012,.018))
    line('Tail_LED_lower',[(s*.29,2.169,.553),(s*.60,2.167,.553),(s*.77,2.154,.574)],.012,detail,(1,.022,.015))
    box('Wing_support',(s*.60,1.89,.794),(.038,.17,.14),trim,.012)
    line('Exhaust_rim',[(s*.61+.071*math.cos(a*2*math.pi/20),2.10,.326+.041*math.sin(a*2*math.pi/20)) for a in range(21)],.01,detail,(.35,.39,.43))
    box('Exhaust_dark',(s*.61,2.085,.326),(.142,.02,.075),trim,.029)
box('Diffuser_recess',(0,2.08,.28),(1.50,.20,.13),trim,.024)
for x in (-.49,-.25,0,.25,.49):
    box('Diffuser_fin',(x,2.095,.216),(.024,.30,.135),trim,.005)
wing=box('Rear_lip_aero',(0,1.956,.886),(1.79,.265,.050),paint,.022)
wing.rotation_euler.x=math.radians(-7)
for s in (-1,1): box('Wing_end',(s*.878,1.951,.899),(.028,.27,.079),trim,.011)
for j in range(5):
    y=1.49+j*.066
    box('Rear_deck_vent',(0,y,interp(y,2)+.01),(.92,.027,.015),trim,.006)

# Wheels: lathed tyre shoulder, rim barrel, sculpted spokes, brake rotor.
wheel_nodes=[]
def lathe(name, center, profile, mat, color=None, segments=32):
    verts=[]
    for x,r in profile:
        for j in range(segments):
            a=j*2*math.pi/segments
            verts.append((center[0]+x,center[1]+r*math.sin(a),center[2]+r*math.cos(a)))
    faces=[]
    for i in range(len(profile) if len(profile)>2 else 1):
        nxt=(i+1)%len(profile)
        for j in range(segments): faces.append((i*segments+j,i*segments+(j+1)%segments,nxt*segments+(j+1)%segments,nxt*segments+j))
    if len(profile)==2:
        faces.extend([tuple(reversed(range(segments))),tuple(segments+j for j in range(segments))])
    return mesh(name,verts,faces,mat,color,True)
for s,side in [(-1,'R'),(1,'L')]:
    for cy,axle in [(-1.28,'F'),(1.27,'R')]:
        center=(s*.907,cy,.355)
        node=bpy.data.objects.new('Wheel_'+axle+side,None); car.objects.link(node); node.location=center
        node['spin_axis']='local X'; node['radius_m']=.355
        wheel_nodes.append(node)
        before=set(car.objects)
        prof=[(-.135,.262),(-.135,.305),(-.12,.334),(-.09,.35),(-.06,.355),(.06,.355),(.09,.35),(.12,.334),(.135,.305),(.135,.262)]
        lathe('Tyre_'+axle+side,center,prof,trim)
        # Outer face at signed lateral offset.
        lathe('Alloy_barrel_'+axle+side,center,[(s*x,r) for x,r in [(-.11,.255),(.105,.255),(.137,.267),(.143,.263),(.143,.242),(.125,.232),(.10,.23)]],detail,(.52,.60,.67))
        lathe('Brake_disc_'+axle+side,center,[(s*.075,.065),(s*.075,.211),(s*.09,.211),(s*.09,.065)],detail,(.20,.24,.28))
        lathe('Hub_'+axle+side,center,[(s*.10,.001),(s*.10,.06),(s*.16,.06),(s*.167,.043),(s*.167,.001)],detail,(.32,.40,.46),32)
        for j in range(5):
            a=j*2*math.pi/5+.12
            def coord(rad,ang,depth): return (center[0]+s*depth,cy+rad*math.sin(ang),.355+rad*math.cos(ang))
            shape=[(.052,a-.33),(.23,a-.13),(.247,a+.065),(.105,a+.28),(.052,a+.34)]
            verts=[coord(r,t,d) for d in (.102,.153) for r,t in shape]
            faces=[(4,3,2,1,0),(5,6,7,8,9)]+[(k,(k+1)%5,(k+1)%5+5,k+5) for k in range(5)]
            bevel(mesh('Swept_spoke',verts,faces,detail,(.65,.73,.79)),.006,1)
            # Small fastener geometry on hub.
            pt=coord(.042,a,.172)
            lathe('Lug',pt,[(-.003,.009),(.003,.009)],trim,segments=8)
        box('Brake_caliper',(center[0]+s*.087,cy+.158,.355),(.045,.075,.18),paint,.016)
        for obj in set(car.objects)-before:
            obj.parent=node
            obj.matrix_parent_inverse=node.matrix_world.inverted()

# Collapse static components to one named body; preserve wheel pivots as nodes
# with one multi-material mesh under each. Apply bevels before export.
bpy.context.view_layer.update()
for obj in list(car.objects):
    if obj.type=='MESH':
        bpy.context.view_layer.objects.active=obj
        for mod in list(obj.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
def join_objects(objects,name,origin):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects: o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
    obj=bpy.context.object; obj.name=name
    scene.cursor.location=origin
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    return obj
body=join_objects([o for o in car.objects if o.type=='MESH' and o.parent is None],'Body',(0,0,0))
for node in wheel_nodes:
    join_objects([o for o in car.objects if o.parent==node],node.name+'_Mesh',node.location)
# Remove collapsed bevel triangles and freeze an explicit game topology.
for obj in car.objects:
    if obj.type=='MESH':
        bm=bmesh.new(); bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bmesh.ops.dissolve_degenerate(bm,dist=1e-7,edges=list(bm.edges))
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(obj.data); bm.free(); obj.data.update()
root=bpy.data.objects.new('CR_Sport_01',None); car.objects.link(root)
root['asset_version']=VERSION; root['units']='metres'; root['front_blender']='-Y'; root['front_gltf']='+Z'
body.parent=root
for node in wheel_nodes: node.parent=root
collider=box('Collider_Chassis',(0,0,.58),(1.76,3.94,.76),trim,0)
collider.parent=root; collider.display_type='WIRE'; collider.hide_render=True
collider['role']='physics_proxy'; collider['shape']='box'; collider['render']=False
scene.cursor.location=(0,0,0)
bpy.context.view_layer.update()

def export(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_extras=True,export_cameras=False,export_lights=False,export_materials='EXPORT',export_normals=True,export_texcoords=True,export_animations=False)
export(OUT/'cr_sport_01_v006.glb',[o for o in car.objects if o!=collider])
export(OUT/'cr_sport_01_v006.collider.glb',[root,collider])
collider.hide_set(True)

# Neutral studio, no downloaded HDRI; preview stage never enters the GLB.
floor_mat=material('Studio_floor',(.055,.080,.095),.12,.5)
floor=box('Studio_floor',(0,0,-.055),(200,200,.1),floor_mat,0); move(floor,studio)
scene.world.color=(.18,.18,.18)
scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.23,.29,.36,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.5
def area(name,loc,power,color,size,target=(0,0,.4)):
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size; d.color=color
    o=bpy.data.objects.new(name,d); studio.objects.link(o); o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Key_softbox',(2,-3,6),1150,(1,.89,.77),5)
area('Cool_fill',(-4,-1,3),1000,(.58,.77,1),4)
area('Rear_rim',(1,4,4),1500,(1,.72,.45),3)
area('Top_strip',(-1,1,6),850,(1,1,1),3)
camdata=bpy.data.cameras.new('Review_camera'); camera=bpy.data.objects.new('Review_camera',camdata); studio.objects.link(camera); scene.camera=camera
scene.render.engine='CYCLES'; scene.cycles.samples=40; scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-.3
views={'front':((4.8,-7.8,3.1),(0,-.15,.55),55),'rear':((-4.6,7.6,2.8),(0,.25,.55),55),'side':((7.8,0,1.7),(0,0,.57),54),'gameplay':((2.6,6.9,4.3),(0,-.25,.45),51)}
camera.location=views['gameplay'][0]
camera.rotation_euler=(Vector(views['gameplay'][1])-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.lens=51
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
for name,(pos,target,lens) in views.items():
    camera.location=pos; camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler(); camera.data.lens=lens
    scene.render.filepath=str(PREVIEW/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print('ASSET_COMPLETE',str(BLEND),flush=True)







