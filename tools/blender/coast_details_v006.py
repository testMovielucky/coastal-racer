"""Original enrichment geometry and a locally computed water texture.
Executed in coast_sample_v006.py's namespace after its primitive helpers.
The user image is a visual reference only, never used as model/texture pixels.
"""
import numpy as np

def beam(name,a,b,width,mat,col):
    mid=(Vector(a)+Vector(b))*.5; delta=Vector(b)-Vector(a)
    o=box(name,mid,(width,width,delta.length),mat,col)
    o.rotation_euler=delta.to_track_quat('Z','Y').to_euler()
    return o

def blade(name,root,direction,length,width,lift,mat,col):
    # Broad curved folded blade; positive edge widths prevent zero-area faces.
    d=Vector(direction).normalized(); side=Vector((-d.y,d.x,0)).normalized()
    root=Vector(root); verts=[]
    for i,(u,w) in enumerate(((0,.02),(.52,1),(1,.012))):
        center=root+d*length*u+Vector((0,0,lift*math.sin(u*math.pi*.72)))
        verts.extend([center-side*width*w,center+Vector((0,0,width*.18*w)),center+side*width*w])
    faces=[]
    for j in range(2):
        faces.extend([(j*3,j*3+1,(j+1)*3+1,(j+1)*3),(j*3+1,j*3+2,(j+1)*3+2,(j+1)*3+1)])
    return mesh(name,verts,faces,mat,col,True)

def make_water_texture():
    n=1024
    u,v=np.meshgrid(np.linspace(0,1,n,dtype=np.float32),np.linspace(0,1,n,dtype=np.float32))
    # Periodic jittered Voronoi field creates organic light-cell edges.
    xx=u*31+.29*np.sin(v*math.tau*3)+.16*np.sin(u*math.tau*4)
    yy=v*14+.20*np.sin(u*math.tau*3)+.16*np.sin(v*math.tau*2)
    ix=np.floor(xx); iy=np.floor(yy)
    first=np.full_like(u,100); second=np.full_like(u,100)
    for oy in (-1,0,1):
        for ox in (-1,0,1):
            cx=ix+ox; cy=iy+oy
            hx=np.mod(np.sin(np.mod(cx,31)*127.1+np.mod(cy,14)*311.7)*43758.5453,1)
            hy=np.mod(np.sin(np.mod(cx,31)*269.5+np.mod(cy,14)*183.3)*43758.5453,1)
            dist=(xx-cx-.2-hx*.6)**2+(yy-cy-.2-hy*.6)**2
            second=np.minimum(second,np.maximum(first,dist)); first=np.minimum(first,dist)
    edge=np.exp(-((np.sqrt(second)-np.sqrt(first))/.038)**2)
    knots=np.array([0,.035,.20,.55,1],dtype=np.float32)
    palette=np.array([[.025,.68,.48],[.002,.59,.54],[.001,.33,.53],[.002,.23,.43],[.002,.23,.43]],dtype=np.float32)
    rgb=np.stack([np.interp(u,knots,palette[:,i]) for i in range(3)],axis=-1)
    light=edge*(.36*np.exp(-u*3)+.065)*(1-u)**.8
    ripple=.95+.05*np.sin(xx*2.5+np.cos(yy*2.4))
    rgb=rgb*ripple[:,:,None]
    rgb=rgb*(1-light[:,:,None])+np.array([.42,.91,.88])*light[:,:,None]
    phase=.018*np.sin(v*math.tau*2)+.010*np.cos(v*math.tau*5)
    wash=np.exp(-((u-.035-phase)/.025)**2)
    wash2=.50*np.exp(-((u-.105-phase*.65)/.018)**2)
    crest=np.exp(-((u-.012-phase*.42)/.0034)**2)
    grain=.5+.5*np.sin(u*math.tau*130+.9*np.sin(v*math.tau*11))*np.sin(v*math.tau*53+.6*np.sin(u*math.tau*17))
    foam=np.clip(edge*(wash+wash2)*.95+crest*.88+(wash*.6+wash2*.35)*np.maximum(0,(grain-.60)/.4),0,1)
    rgb=rgb*(1-foam[:,:,None])+np.array([.93,.98,.94])*foam[:,:,None]
    # Generated 8-bit colour pixels are sRGB; explicitly encode the linear
    # palette so Blender and glTF sample the same bright tropical colours.
    rgb=np.where(rgb<=.0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
    pixels=np.ones((n,n,4),dtype=np.float32); pixels[:,:,:3]=rgb
    pixels[-1]=pixels[0]  # exact matching pixel rows for the modular seam
    assert np.max(np.abs(pixels[-1]-pixels[0]))==0
    img=bpy.data.images.new('Coast_WaterPattern_1024',width=n,height=n,alpha=True)
    img.pixels.foreach_set(pixels.ravel()); img.update()
    texture_dir=SRC/'textures'; texture_dir.mkdir(exist_ok=True)
    img.filepath_raw=str(texture_dir/'water_pattern_1024.png'); img.file_format='PNG'; img.save(); img.pack()
    nodes=water.node_tree.nodes; links=water.node_tree.links
    tex=nodes.new('ShaderNodeTexImage'); tex.image=img; tex.extension='REPEAT'; tex.interpolation='Linear'
    links.new(tex.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
    nodes.get('Principled BSDF').inputs['Roughness'].default_value=.25
    return img

def build_rich_water():
    make_water_texture()
    verts=[]; faces=[]; uv=[]
    # 32 rows have exactly the same y-period as the road/shore modules.
    for j in range(33):
        y=-4+j*.25; shore=shore_x(y)+.10
        for k in range(25):
            t=k/24; x=shore+(25-shore)*t
            z=-.285+.011*math.sin(t*math.pi*6)*math.cos(y*math.pi/4)
            verts.append((x,y,z)); uv.append((t,j/32))
    for j in range(32):
        for k in range(24): faces.append((j*25+k,j*25+k+1,(j+1)*25+k+1,(j+1)*25+k))
    surface=mesh('Water_textured_surface',verts,faces,water,(1,1,1),True)
    layer=surface.data.uv_layers.new(name='WaterUV')
    for p in surface.data.polygons:
        for li in p.loop_indices: layer.data[li].uv=uv[surface.data.loops[li].vertex_index]
    parts=[surface]
    # Delicate irregular edge of breaking foam, generated as real geometry.
    vv=[]
    for j in range(129):
        y=-4+j/16; x=shore_x(y)+.085+.055*math.cos(y*math.pi*2)
        w=.026+.027*(.5+.5*math.sin(y*math.pi*5))
        vv += [(x,y,-.276),(x+w,y,-.276)]
    ff=[(j*2,j*2+1,(j+1)*2+1,(j+1)*2) for j in range(128)]
    parts.append(mesh('Organic_foam_edge',vv,ff,mineral,(.88,.97,.92)))
    finish_asset('water_8m',parts,'Static water; locally generated packed 1024px caustic/foam texture, periodic in Y.',[],{'Entry':[0,4,-.285],'Exit':[0,-4,-.285]})

def lush_palm():
    parts=[]
    def trunk(t): return Vector((.55*t*t,.16*math.sin(t*math.pi/2),5.8*t))
    parts.append(sweep('Tapered_palm_trunk',[trunk(i/18) for i in range(19)],[.24-.105*i/18 for i in range(19)],mineral,(.37,.235,.095),10))
    for i in range(1,19):
        t=i/20; c=trunk(t); r=.244-.105*t
        parts.append(sweep('Palm_ring',[c-Vector((0,0,.014)),c+Vector((0,0,.014))],[r,r-.001],mineral,(.27,.17,.06),10))
    top=trunk(1)
    parts.append(ellipsoid('Palm_crown',top+Vector((0,0,.06)),(.22,.24,.31),foliage,(.19,.30,.025)))
    for k in range(3):
        a=k*math.tau/3
        parts.append(ellipsoid('Coconut',top+Vector((.19*math.cos(a),.19*math.sin(a),-.12)),(.14,.16,.18),mineral,(.29,.21,.055)))
    for frond in range(10):
        angle=frond*math.tau/10+.07*(frond%2)
        d=Vector((math.cos(angle),math.sin(angle),0)); cross=Vector((-d.y,d.x,0))
        length=2.65+.22*(frond%3); lift=1.15+.4*(frond%2); drop=1.15+.15*(frond%3)
        def rachis(t): return top+d*length*t+Vector((0,0,.14+lift*math.sin(t*math.pi*.9)-drop*t*t))
        parts.append(sweep('Palm_frond_spine',[rachis(i/12) for i in range(13)],[.035*(1-i/13)+.002 for i in range(13)],foliage,(.26,.39,.035),5))
        verts=[]; faces=[]; colors=[]
        for j in range(1,15):
            t=j/16; center=rachis(t)
            for sign in (-1,1):
                direction=(cross*sign+d*.30).normalized()
                span=1.06*math.sin(math.pi*t)**.65
                width=.165*math.sin(math.pi*t)**.45
                start=len(verts)
                for u,w in ((0,.05),(.52,1),(1,.008)):
                    c=center+direction*span*u+Vector((0,0,-.25*u*u-.06*t*u))
                    verts.extend([c-d*width*w,c+Vector((0,0,.045*w)),c+d*width*w])
                for seg in range(2):
                    for side in range(2):
                        q=start+seg*3+side
                        faces.append((q,q+1,q+4,q+3))
                        colors.append([(.04,.24,.025),(.095,.33,.022),(.16,.37,.018)][(j+frond+side)%3])
        parts.append(mesh('Broad_curved_leaflets',verts,faces,foliage,LEAF,True,colors))
    finish_asset('palm_a',parts,'Full pennate palm with broad curved leaflets; no alpha cards.',[{'shape':'capsule','start':[0,0,0],'end':[.55,.16,5.8],'radius':.25}])

def make_enrichment_assets():
    # Faceted limestone group, including a large silhouette anchor and pebbles.
    parts=[]
    for i,(p,s) in enumerate([((0,0,.40),(.68,.53,.63)),((.65,.20,.18),(.42,.34,.31)),((-.50,.36,.14),(.35,.29,.28)),((.31,-.57,.08),(.21,.24,.17)),((-.60,-.25,.07),(.22,.20,.15))]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2 if i==0 else 1,radius=1,location=p)
        o=relocate(bpy.context.object); o.name='Coastal_limestone'; o.scale=s
        o.rotation_euler=(.14*i,.2*i,.45*i); o.data.materials.append(mineral)
        attr=o.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
        for poly in o.data.polygons:
            c=[(.67,.59,.43),(.75,.68,.51),(.60,.55,.42)][(poly.index+i)%3]
            for li in poly.loop_indices: attr.data[li].color=(*c,1)
        parts.append(o)
    finish_asset('rock_cluster',parts,'Original faceted limestone and pebble group.')

    parts=[]
    for ring,(count,length,lift) in enumerate(((9,.72,.48),(6,.53,.68))):
        for i in range(count):
            a=i*math.tau/count+.4*ring
            parts.append(blade('Agave_lance',(0,0,.015),(math.cos(a),math.sin(a),0),length,.095,lift,foliage,[(.055,.25,.105),(.14,.36,.095),(.23,.42,.08)][i%3]))
    # A low grass tuft beside the main rosette.
    for i in range(7):
        a=i*math.tau/7
        parts.append(blade('Dune_grass',(.60,.22,0),(math.cos(a),math.sin(a),0),.30,.024,.32,foliage,(.32,.40,.055)))
    finish_asset('agave_cluster',parts,'Two-scale fleshy rosette and dune grass cluster.')

    parts=[]
    for i in range(7):
        a=i*math.tau/7; c=(.32*math.cos(a),.28*math.sin(a),.09)
        for j in range(3):
            ang=a+j*1.5
            parts.append(blade('Shrub_leaf',c,(math.cos(ang),math.sin(ang),0),.39,.095,.22,foliage,[(.03,.22,.04),(.08,.32,.04),(.14,.37,.055)][j]))
        tip=Vector(c)+Vector((.12*math.cos(a),.12*math.sin(a),.45+.08*(i%2)))
        parts.append(sweep('Flower_stem',[c,tip],[.012,.008],foliage,(.18,.30,.03),4))
        for j in range(5):
            ang=j*math.tau/5
            base=tip+Vector((.055*math.cos(ang),.055*math.sin(ang),.01))
            v=[tip,base+Vector((.045*math.cos(ang+.6),.045*math.sin(ang+.6),.005)),base+Vector((.065*math.cos(ang),.065*math.sin(ang),.025)),base+Vector((.045*math.cos(ang-.6),.045*math.sin(ang-.6),.005))]
            parts.append(mesh('Coral_flower_petal',v,[(0,1,2,3)],paint,(.95,.16,.028)))
    finish_asset('flower_cluster',parts,'Compact green shrub with small coral flowers, not road obstacles.')

    # Striped beach umbrella, 8 alternating cloth panels and visible ribs.
    parts=[sweep('Umbrella_pole',[(0,0,0),(0,0,2.36)],[.034,.027],metal,(.68,.73,.69),10)]
    verts=[]; faces=[]; colors=[]
    segments=32
    for r,z in ((.018,2.37),(.48,2.30),(1.0,2.10),(1.30,1.95)):
        for j in range(segments):
            a=j*math.tau/segments
            verts.append((r*math.cos(a),r*math.sin(a),z-.045*math.sin(j*math.pi/4)**2*(r/1.3)))
    for ring in range(3):
        for j in range(segments):
            faces.append((ring*segments+j,ring*segments+(j+1)%segments,(ring+1)*segments+(j+1)%segments,(ring+1)*segments+j))
            colors.append(TEAL if (j//4)%2 else WHITE)
    parts.append(mesh('Eight_panel_canopy',verts,faces,paint,TEAL,True,colors))
    for j in range(8):
        a=j*math.tau/8
        parts.append(sweep('Umbrella_rib',[(0,0,2.34),(.50*math.cos(a),.50*math.sin(a),2.26),(1.27*math.cos(a),1.27*math.sin(a),1.93)],[.016,.013,.009],metal,(.73,.76,.70),4))
    finish_asset('beach_umbrella',parts,'Turquoise and white eight-panel umbrella, 2.6 m diameter.')

    parts=[]
    for s in (-1,1):
        pts=[(s*.32,-.86,.30),(s*.32,.22,.34),(s*.32,.87,1.0)]
        parts.append(sweep('Chair_side_rail',pts,[.027]*3,metal,(.80,.84,.78),6))
        parts.append(beam('Chair_leg',(s*.32,-.71,.02),(s*.32,.34,.42),.045,metal,(.78,.81,.75)))
        parts.append(beam('Chair_leg',(s*.32,.57,.02),(s*.32,-.38,.31),.045,metal,(.78,.81,.75)))
    parts.append(mesh('Teal_canvas',[(-.285,-.84,.315),(.285,-.84,.315),(.285,.22,.355),(-.285,.22,.355),(-.285,.85,.99),(.285,.85,.99)],[(0,1,2,3),(3,2,5,4)],paint,TEAL))
    for y,z in [(-.84,.305),(.84,.975)]: parts.append(beam('Chair_crossbar',(-.32,y,z),(.32,y,z),.040,metal,(.78,.81,.75)))
    finish_asset('beach_lounger',parts,'Folded beach chaise with teal canvas and pale frame.')

    # Lifeguard hut on stilts, pale trim, stairs, open platform and striped roof.
    parts=[]
    for x in (-.66,.66):
        for y in (-.66,.66): parts.append(box('Tower_stilt',(x,y,.76),(.10,.10,1.52),paint,TEAL))
    for x in (-.66,.66):
        parts.append(beam('Stilt_brace',(x,-.66,.25),(x,.66,1.33),.060,paint,TEAL))
    for y in (-.66,.66):
        parts.append(beam('Stilt_brace',(-.66,y,.25),(.66,y,1.33),.060,paint,TEAL))
    parts.append(box('Tower_platform',(0,0,1.46),(2.12,2.12,.12),paint,WHITE))
    for x in (-.69,.69):
        for y in (-.69,.69): parts.append(box('Hut_frame',(x,y,2.32),(.085,.085,1.68),paint,WHITE))
    # Three sides and a front door/windows, using opaque inset glazing.
    for s in (-1,1):
        parts.append(box('Hut_side_panel',(s*.69,0,1.91),(.045,1.36,.73),paint,TEAL))
        parts.append(box('Hut_side_window',(s*.695,0,2.64),(.027,1.18,.62),paint,(.055,.25,.30)))
        for y in (-.34,.34): parts.append(box('Window_mullion',(s*.717,y,2.64),(.045,.035,.64),paint,WHITE))
        parts.append(box('Window_sill',(s*.717,0,2.30),(.06,1.35,.05),paint,WHITE))
    parts.append(box('Hut_back',(0,.69,2.30),(1.36,.045,1.55),paint,TEAL))
    parts.append(box('Hut_front_lower',(-.39,-.69,1.90),(.55,.045,.72),paint,TEAL))
    parts.append(box('Hut_door',(.27,-.69,2.23),(.64,.047,1.38),paint,(.023,.32,.35)))
    parts.append(box('Hut_front_window',(-.39,-.718,2.64),(.53,.025,.62),paint,(.055,.25,.30)))
    parts.append(box('Door_handle',(.49,-.73,2.25),(.028,.028,.13),metal,(.7,.72,.65)))
    for x in (-1,1):
        for y in (-1,0,1): parts.append(box('Deck_baluster',(x,y,1.86),(.047,.047,.73),paint,WHITE))
        parts.append(beam('Deck_side_rail',(x,-1,2.24),(x,1,2.24),.060,paint,TEAL))
    parts.append(beam('Deck_back_rail',(-1,1,2.24),(1,1,2.24),.060,paint,TEAL))
    for a,b in [((-1,-1,2.24),(-.40,-1,2.24)),((.40,-1,2.24),(1,-1,2.24))]: parts.append(beam('Deck_front_rail',a,b,.06,paint,TEAL))
    for i in range(7):
        y=-2.54+i*.235; z=.14+i*.22
        parts.append(box('Stair_tread',(0,y,z),(.70,.275,.075),paint,TEAL))
    for s in (-1,1):
        parts.append(beam('Stair_stringer',(s*.38,-2.72,.025),(s*.38,-.96,1.43),.075,paint,WHITE))
        parts.append(beam('Stair_handrail',(s*.45,-2.56,.88),(s*.45,-1.0,2.24),.04,paint,WHITE))
    # Eight triangular painted roof wedges, closed with an underside.
    perimeter=[(-1.06,-1.06,3.13),(0,-1.06,3.13),(1.06,-1.06,3.13),(1.06,0,3.13),(1.06,1.06,3.13),(0,1.06,3.13),(-1.06,1.06,3.13),(-1.06,0,3.13)]
    rv=perimeter+[(0,0,3.73)]
    rf=[(j,(j+1)%8,8) for j in range(8)]+[tuple(reversed(range(8)))]
    parts.append(mesh('Striped_pyramid_roof',rv,rf,paint,TEAL,False,[TEAL if j%2 else WHITE for j in range(8)]+[WHITE]))
    for j in range(4):
        a=perimeter[j*2]; b=perimeter[((j+1)*2)%8]; parts.append(beam('Roof_fascia',a,b,.065,paint,TEAL))
    # Original orange rescue board leaning beside the hut.
    board=ellipsoid('Rescue_board',(1.12,.35,1.10),(.095,.26,1.04),paint,CORAL)
    board.rotation_euler.y=-.16; parts.append(board)
    bpy.ops.mesh.primitive_torus_add(major_segments=20,minor_segments=6,location=(.79,-1.065,1.97),rotation=(math.pi/2,0,0),major_radius=.18,minor_radius=.042)
    ring=relocate(bpy.context.object); ring.name='Lifebuoy'; ring.data.materials.append(paint)
    attr=ring.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for poly in ring.data.polygons:
        c=WHITE if (poly.index//6)%5==0 else CORAL
        for li in poly.loop_indices: attr.data[li].color=(*c,1)
    parts.append(ring)
    finish_asset('lifeguard_tower',parts,'3.73 m original striped lifeguard hut, stilts, braces, stairs and rescue board.',[{'shape':'box','center':[0,0,1.9],'size':[2.12,2.12,3.8]}])

def place_enrichment(place):
    for p,r,s in [((10.3,-15,-.05),.6,1.1),((9.2,-1.4,-.06),1.8,.8),((10.7,14.0,-.05),3.0,1.15),((-6.2,-16,0),.7,.8),((-6.1,5,0),2.0,.65),((-6.5,17,0),4.0,.95)]:
        place('rock_cluster',p,r,s*1.12)
    for i,(x,y,s) in enumerate([(8.2,-18,.85),(9.3,-12,1.0),(8.2,-6,.75),(10.6,0,1.1),(8.0,6,.8),(10.2,16,.9),(-6.0,-18,1.0),(-6.6,-10,.75),(-6.0,-1,1.0),(-6.2,6,.7),(-6.2,17,1.0)]):
        place('agave_cluster',(x,y,-.025),i*.91,s*1.4)
    for i,(x,y) in enumerate([(8.3,-10),(9.1,1),(-6.0,-12),(-6.2,2),(-6.0,16)]):
        place('flower_cluster',(x,y,-.01),i*1.7,1.22 if x>0 else 1.35)
    # Low grouped planting ties each palm to the sand/grass instead of leaving
    # isolated bare trunks; all placements remain outside the road corridor.
    for i,(x,y,z) in enumerate([(7.8,-13,-.04),(8.1,3,-.04),(-6.0,-5,-.01),(-6.1,13,-.01),(8.0,16,-.04)]):
        place('agave_cluster',(x+.55,y+.20,z),i*1.35,.55)
    place('lifeguard_tower',(10.6,-7.5,-.07),math.radians(-20),1)
    place('beach_umbrella',(10.0,8.4,-.07),.1,1)
    for x in (9.35,10.75): place('beach_lounger',(x,9.55,-.07),math.radians(-15),1)




