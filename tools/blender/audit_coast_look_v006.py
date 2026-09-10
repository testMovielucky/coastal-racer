"""Verify this revision changes shading only, against preserved v005 bytes."""
import json, struct, hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
META=ROOT/'assets-source/metadata/coast_sample/v006'
old=ROOT/'public/assets/themes/coast/sample-v005'
new=ROOT/'public/assets/themes/coast/sample-v006'

def read_glb(path):
    raw=path.read_bytes(); size=struct.unpack_from('<I',raw,12)[0]
    return json.loads(raw[20:20+size]),raw[28+size:]

def accessor(g,b,idx):
    a=g['accessors'][idx]; v=g['bufferViews'][a['bufferView']]
    fmt,n={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    start=v.get('byteOffset',0)+a.get('byteOffset',0)
    stride=v.get('byteStride',n*width)
    return [struct.unpack_from('<'+fmt*width,b,start+i*stride) for i in range(a['count'])]

def geometry(g,b):
    triangles=Counter()
    for mesh in g['meshes']:
        for p in mesh['primitives']:
            attrs=p['attributes']
            pos=accessor(g,b,attrs['POSITION'])
            normals=accessor(g,b,attrs['NORMAL'])
            uv=accessor(g,b,attrs['TEXCOORD_0']) if 'TEXCOORD_0' in attrs else [()]*len(pos)
            ids=[v[0] for v in accessor(g,b,p['indices'])]
            for i in range(0,len(ids),3):
                corners=tuple((pos[j],normals[j],uv[j]) for j in ids[i:i+3])
                # Preserve winding; tolerate a cyclic change of starting vertex.
                triangles[min(corners,corners[1:]+corners[:1],corners[2:]+corners[:2])]+=1
    return triangles

def structure(g):
    return [{k:n[k] for k in ('name','children','mesh','translation','rotation','scale','matrix') if k in n} for n in g['nodes']]

previous=json.loads((old/'sample_layout.json').read_text())
current=json.loads((new/'sample_layout.json').read_text())
assert previous['placements']==current['placements']
assert previous['road']==current['road'] and previous['axes']==current['axes']
assert previous['review_car']==current['review_car']
assert set(previous['assets'])==set(current['assets'])
asset_checks={}
for name,spec in current['assets'].items():
    prev=previous['assets'][name]
    for key in ('bounds_blender_m','connections_blender_m','colliders_blender','triangles'):
        assert spec[key]==prev[key],(name,key)
    ga,ba=read_glb(old/spec['file']); gb,bb=read_glb(new/spec['file'])
    assert geometry(ga,ba)==geometry(gb,bb),(name,'geometry changed')
    assert structure(ga)==structure(gb),(name,'hierarchy changed')
    # Exporter must carry the intended material settings, not only render them.
    expected={'Coast_Asphalt':(.82,0),'Coast_Mineral':(.77,0),'Coast_Painted':(.28,0),
              'Coast_Foliage':(.38,0),'Coast_Water':(.20,0),'Coast_Metal':(.26,.65)}
    for mat in gb['materials']:
        rough,metal=expected[mat['name']]
        pbr=mat['pbrMetallicRoughness']
        assert abs(pbr.get('roughnessFactor',1)-rough)<1e-6
        assert abs(pbr.get('metallicFactor',1)-metal)<1e-6
    asset_checks[name]={'positions_normals_uv_winding_unchanged':True,'hierarchy_unchanged':True,'pbr_export_matches':True}

manifest=json.loads((ROOT/'assets-source/metadata/coast_sample/v005/manifest.json').read_text(encoding='utf-8-sig'))
for item in manifest['files']:
    assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
car=ROOT/current['review_car']['path']
assert hashlib.sha256(car.read_bytes()).hexdigest()==current['review_car']['sha256']
report={'revision':'v006','baseline':'v005','status':'passed',
        'previous_manifest_files_unchanged':len(manifest['files']),
        'placements_road_axes_colliders_unchanged':True,'car_bytes_unchanged':True,
        'assets':asset_checks}
(META/'shading_revision_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
