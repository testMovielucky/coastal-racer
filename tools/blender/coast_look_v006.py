"""Color/material-only revision. Shared by lookdev and reproducible build.
All RGB values below are scene-linear. No geometry or accepted-car edits.
"""
import bpy

def recolor_asset(obj, asset_name):
    colors=obj.data.color_attributes.get('Color')
    if not colors:
        return
    for poly in obj.data.polygons:
        mat=obj.data.materials[poly.material_index].name
        for li in poly.loop_indices:
            r,g,b,a=colors.data[li].color
            if mat=='Coast_Asphalt':
                r,g,b=.060,.075,.088
            elif mat=='Coast_Foliage':
                r,g,b=r*.74,min(g*1.12,.65),b*.62
            elif mat=='Coast_Painted':
                if g>r*2 and b>r*2:
                    r,g,b=.003,.38,.48
                elif r>g*2 and r>b*2:
                    r,g,b=min(r, .88),g*.55,b*.40
            elif mat=='Coast_Mineral':
                if asset_name=='beach_8m' and r>g and g>b:
                    r,g,b=r*.98,g*.89,b*.63
                elif asset_name=='inland_strip_8m' and g>r*2:
                    r,g,b=.12,.32,.012
                elif asset_name in ('palm_a','rock_cluster') and r>g>b:
                    r,g,b=r*.94,g*.90,b*.73
            colors.data[li].color=(r,g,b,a)

def tune_materials():
    settings={
        'Coast_Asphalt':(.82,0), 'Coast_Mineral':(.77,0),
        'Coast_Painted':(.28,0), 'Coast_Foliage':(.38,0),
        'Coast_Water':(.20,0), 'Coast_Metal':(.26,.65),
        'Review_Backdrop_Water':(.20,0),
    }
    for name,(rough,metal) in settings.items():
        m=bpy.data.materials.get(name)
        if m:
            bs=m.node_tree.nodes.get('Principled BSDF')
            bs.inputs['Roughness'].default_value=rough
            bs.inputs['Metallic'].default_value=metal

def tune_review(scene):
    tune_materials()
    bg=scene.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value=(.45,.60,.80,1)
    bg.inputs[1].default_value=.30
    sun=bpy.data.lights.get('Coastal_sun')
    sun.energy=3.2; sun.color=(1,.965,.90); sun.angle=.018
    fill=bpy.data.lights.get('Sky_softbox')
    fill.energy=450; fill.color=(.80,.89,1)
    scene.view_settings.view_transform='Khronos PBR Neutral'
    scene.view_settings.look='None'
    scene.view_settings.exposure=.60
    scene.view_settings.gamma=1


