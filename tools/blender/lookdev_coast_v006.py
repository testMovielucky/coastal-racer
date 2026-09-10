"""Small actual Cycles preview before final asset export; no source overwrite."""
import bpy, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/'assets-source/previews/coast_sample/v006/lookdev'
SRC=ROOT/'assets-source/blender/coast_sample/v006/lookdev'
PRE.mkdir(parents=True,exist_ok=True)
SRC.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets-source/blender/coast_sample/v005/coast_sample_v005.blend'))
exec(compile((ROOT/'tools/blender/coast_look_v006.py').read_text(encoding='utf-8-sig'),'coast_look_v006.py','exec'))
exec(compile((ROOT/'tools/blender/coast_details_v006.py').read_text(encoding='utf-8-sig'),'coast_details_v006.py','exec'))
for obj in bpy.data.collections['ASSET_PROTOTYPES'].objects:
    if obj.type=='MESH': recolor_asset(obj,obj.name)
water=bpy.data.materials['Coast_Water']
make_water_texture()
scene=bpy.context.scene
tune_review(scene)
obj=bpy.data.objects['Review_ocean_backdrop']
for c in obj.data.color_attributes['Color'].data: c.color=(.002,.23,.43,1)
scene.cycles.samples=24
scene.render.resolution_x=1000; scene.render.resolution_y=688
scene.render.filepath=str(PRE/'overview_candidate_b.png')
bpy.ops.render.render(write_still=True)
print('LOOKDEV_COMPLETE',scene.view_settings.view_transform,flush=True)


