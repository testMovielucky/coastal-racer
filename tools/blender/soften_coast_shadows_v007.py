"""Lighting-only review revision; reuses immutable coast GLBs v006.
Blender --background --factory-startup --python-exit-code 1 --python <script>
Append -- --preview for a small detail render before final rendering.
"""
import bpy, math, json, hashlib, sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
VERSION='v007'
SRC=ROOT/'assets-source/blender/coast_sample'/VERSION
PRE=ROOT/'assets-source/previews/coast_sample'/VERSION
META=ROOT/'assets-source/metadata/coast_sample'/VERSION
BASE=ROOT/'assets-source/blender/coast_sample/v006/coast_sample_v006.blend'
BLEND=SRC/'coast_sample_v007.blend'
preview='--preview' in sys.argv
if BLEND.exists(): raise RuntimeError('Preserve existing v007; use a new revision.')
for directory in (SRC,PRE,META): directory.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'assets-source/metadata/coast_sample/v006/manifest.json').read_text(encoding='utf-8-sig'))
def check_baseline():
    for entry in manifest['files']:
        assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256'],entry['path']
    car=ROOT/'public/assets/cars/cr_sport_01/v006/cr_sport_01_v006.glb'
    assert hashlib.sha256(car.read_bytes()).hexdigest()==manifest['accepted_car_sha256']
check_baseline()
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene=bpy.context.scene
sun=bpy.data.lights['Coastal_sun']
old_angle=sun.angle
sun.angle=math.radians(4)
# Sampling improves the penumbra quality; there is no image blur/compositing.
scene.cycles.samples=32 if preview else 64
camera=scene.camera
views={
    'overview':{'pos':(-31,37,30),'target':(5,0,.3),'ortho':57,'size':(1600,1100)},
    'gameplay':{'pos':(.8,20.5,9.8),'target':(-.9,7.4,.3),'lens':42,'size':(1080,1440)},
    'coast_detail':{'pos':(21,15,10),'target':(7.4,3,.9),'lens':45,'size':(1500,1050)},
    'tower_detail':{'pos':(16,-16,6.5),'target':(10.6,-7.5,1.75),'lens':48,'size':(1400,1100)},
    'gameplay_composed':{'pos':(-10,24,14),'target':(2,7,.5),'lens':42,'size':(1600,1000)},
}
def view(params):
    camera.location=params['pos']
    camera.rotation_euler=(Vector(params['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO' if 'ortho' in params else 'PERSP'
    if 'ortho' in params: camera.data.ortho_scale=params['ortho']
    else: camera.data.lens=params['lens']
    scene.render.resolution_x,scene.render.resolution_y=params['size']
    scene.render.resolution_percentage=50 if preview else 100

if preview:
    view(views['coast_detail'])
    scene.render.filepath=str(PRE/'shadow_preview_4deg.png')
    bpy.ops.render.render(write_still=True)
else:
    view(views['overview'])
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    for name,params in views.items():
        view(params)
        scene.render.filepath=str(PRE/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    check_baseline()
    report={
        'revision':VERSION,'baseline':'v006','type':'Blender review lighting only',
        'seed':909061,'scenario':'coast-art-sample-40m','blender':bpy.app.version_string,
        'sun_angle_before_radians':old_angle,'sun_angle_after_radians':sun.angle,
        'sun_angle_after_degrees':4,'cycles_samples':scene.cycles.samples,
        'sun_energy':sun.energy,'exposure':scene.view_settings.exposure,
        'view_transform':scene.view_settings.view_transform,
        'previous_manifest_files_unchanged':len(manifest['files']),
        'car_bytes_unchanged':True,'materials_geometry_placements':'loaded unchanged from v006',
        'exports_reused':'public/assets/themes/coast/sample-v006/sample_layout.json',
        'new_glb_exports':0,'render_names':list(views),
        'not_verified':['human artistic approval','Babylon shadows','device performance'],
    }
    (META/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('SHADOW_REVIEW_COMPLETE', 'preview' if preview else str(BLEND),flush=True)

