import { Scene } from '@babylonjs/core/scene';
import type { Engine } from '@babylonjs/core/Engines/engine';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { ShadowGenerator } from '@babylonjs/core/Lights/Shadows/shadowGenerator';
import { Vector3, Quaternion, Matrix } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import { CreateGround } from '@babylonjs/core/Meshes/Builders/groundBuilder';
import { PBRMaterial } from '@babylonjs/core/Materials/PBR/pbrMaterial';
import { RawCubeTexture } from '@babylonjs/core/Materials/Textures/rawCubeTexture';
import { Constants } from '@babylonjs/core/Engines/constants';
import { ImageProcessingConfiguration } from '@babylonjs/core/Materials/imageProcessingConfiguration';
import { CubeMapToSphericalPolynomialTools } from '@babylonjs/core/Misc/HighDynamicRange/cubemapToSphericalPolynomial';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import type { AssetContainer } from '@babylonjs/core/assetContainer';
import '@babylonjs/loaders/glTF';
import contract from '../../../config/coast-v006.json';
import car from '../../../config/car-v006.json';

type Placement = { asset: string; position_blender_m: number[]; rotation_z_radians: number; uniform_scale: number };
type Layout = { schema_version: number; asset_version: string; seed: number; scenario: string; road: { sample_length_m: number }; placements: Placement[]; review_car: { position_blender_m: number[]; sha256: string } };
export const coastViews = ['game', 'reference', 'overview', 'detail'] as const;
export type CoastView = typeof coastViews[number];
const toWorld = (p: number[]) => new Vector3(p[0]!, p[2]!, -p[1]!);
async function verifiedBytes(file: { path: string; sha256: string; bytes: number }, signal: AbortSignal) {
  const response = await fetch(new URL(import.meta.env.BASE_URL + file.path, document.baseURI), { signal });
  if (!response.ok) throw new Error('Не загрузился ' + file.path + ' (HTTP ' + response.status + ').');
  const bytes = await response.arrayBuffer();
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
  if (hash !== file.sha256 || bytes.byteLength !== file.bytes) throw new Error('Файл отличается от сохранённого оригинала: ' + file.path);
  return bytes;
}
// Local sky radiance only: no remote HDRI and no claim of scene-reflected buildings.
function environment(scene: Scene) {
  const size = 32;
  const faces = Array.from({ length: 6 }, (_, side) => {
    const data = new Float32Array(size * size * 4);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const elevation = side === 2 ? 1 : side === 3 ? 0 : 1 - y / (size - 1);
      const t = .12 + elevation * .33;
      const panel = side === 2 && Math.abs(x - 11) < 5 && Math.abs(y - 20) < 5 ? .7 : 0;
      const i = (y * size + x) * 4;
      data[i] = t * .80 + panel; data[i + 1] = t * .90 + panel; data[i + 2] = t + panel; data[i + 3] = 1;
    }
    return data;
  });
  // Byte cube avoids relying on float texture filtering on mobile WebGL2.
  const bytes = faces.map(face => Uint8Array.from(face, v => Math.round(Math.min(1, v) * 255)));
  const texture = new RawCubeTexture(scene, bytes, size, Constants.TEXTUREFORMAT_RGBA, Constants.TEXTURETYPE_UNSIGNED_BYTE, true);
  texture.name = 'coast-local-sky-32'; texture.gammaSpace = false;
  texture.sphericalPolynomial = CubeMapToSphericalPolynomialTools.ConvertCubeMapToSphericalPolynomial({
    size, right: bytes[0]!, left: bytes[1]!, up: bytes[2]!, down: bytes[3]!, front: bytes[4]!, back: bytes[5]!,
    format: Constants.TEXTUREFORMAT_RGBA, type: Constants.TEXTURETYPE_UNSIGNED_BYTE, gammaSpace: false,
  });
  scene.environmentTexture = texture; scene.environmentIntensity = .65;
}
export async function createCoastPreviewScene(engine: Engine, canvas: HTMLCanvasElement, signal: AbortSignal) {
  const scene = new Scene(engine);
  const containers: AssetContainer[] = [];
  try {
    scene.useRightHandedSystem = true;
    scene.clearColor = new Color4(.12, .62, .82, 1);
    const processing = scene.imageProcessingConfiguration;
    processing.toneMappingEnabled = true;
    processing.toneMappingType = ImageProcessingConfiguration.TONEMAPPING_KHR_PBR_NEUTRAL;
    processing.exposure = Math.pow(2, .6);
    environment(scene);
    const sun = new DirectionalLight('coast-sun', new Vector3(12, -20, -8).normalize(), scene);
    sun.position = new Vector3(-12, 20, 8); sun.intensity = 3.2;
    sun.diffuse = new Color3(1, .965, .90);
    sun.autoUpdateExtends = false;
    sun.orthoLeft = -35; sun.orthoRight = 35; sun.orthoBottom = -35; sun.orthoTop = 35;
    sun.shadowMinZ = .1; sun.shadowMaxZ = 100;
    const fill = new HemisphericLight('coast-sky-fill', Vector3.Up(), scene);
    fill.diffuse = new Color3(.80, .89, 1); fill.groundColor = new Color3(.20, .23, .18); fill.intensity = .24;
    const shadows = new ShadowGenerator(2048, sun);
    shadows.useContactHardeningShadow = true;
    shadows.contactHardeningLightSizeUVRatio = .035;
    shadows.filteringQuality = ShadowGenerator.QUALITY_MEDIUM;
    shadows.bias = .0006; shadows.normalBias = .035;
    const layout = JSON.parse(new TextDecoder().decode(await verifiedBytes(contract.layout, signal))) as Layout;
    if (layout.schema_version !== 1 || layout.seed !== 909061 || layout.road.sample_length_m !== 40 || layout.placements.length !== 76 || layout.review_car.sha256 !== car.model.sha256) throw new Error('Неожиданная версия раскладки побережья.');
    const prototypes = new Map<string, AssetContainer>();
    // Bounded sequential loads keep peak decode/shader pressure predictable.
    for (const entry of contract.assets) {
      const bytes = await verifiedBytes(entry, signal);
      const container = await LoadAssetContainerAsync(new Uint8Array(bytes), scene, { pluginExtension: '.glb', name: entry.path.split('/').at(-1) });
      containers.push(container); prototypes.set(entry.id, container);
    }
    const placed = layout.placements.map((entry, index) => {
      const container = prototypes.get(entry.asset);
      if (!container) throw new Error('Неизвестный модуль ' + entry.asset);
      const instance = container.instantiateModelsToScene(name => index + ':' + name, false);
      const pivot = new TransformNode('placement-' + index + '-' + entry.asset, scene);
      pivot.position.copyFrom(toWorld(entry.position_blender_m));
      pivot.rotationQuaternion = Quaternion.RotationAxis(Vector3.Up(), entry.rotation_z_radians);
      pivot.scaling.setAll(entry.uniform_scale);
      for (const root of instance.rootNodes) root.parent = pivot;
      for (const mesh of pivot.getChildMeshes()) {
        if (!mesh.getTotalVertices()) continue;
        mesh.receiveShadows = true;
        if (!['water_8m', 'road_straight_8m', 'beach_8m', 'inland_strip_8m', 'promenade_8m'].includes(entry.asset)) shadows.addShadowCaster(mesh, false);
      }
      return pivot;
    });
    const model = await LoadAssetContainerAsync(new Uint8Array(await verifiedBytes(car.model, signal)), scene, { pluginExtension: '.glb', name: 'cr_sport_01_v006.glb' });
    containers.push(model); model.addAllToScene();
    const carRoot = scene.getTransformNodeByName('CR_Sport_01');
    if (!carRoot) throw new Error('Не найден корень принятой машины.');
    carRoot.position.copyFrom(toWorld(layout.review_car.position_blender_m));
    for (const mesh of model.meshes) if (mesh.getTotalVertices()) { mesh.receiveShadows = true; shadows.addShadowCaster(mesh, false); }
    // The Blender reference has a 2 km review ocean outside the bounded asset sample.
    const ocean = CreateGround('review-ocean-backdrop', { width: 2000, height: 2000 }, scene);
    ocean.position.y = -.38;
    const water = new PBRMaterial('review-ocean-backdrop-material', scene);
    water.albedoColor = new Color3(.002, .23, .43); water.roughness = .20; water.metallic = 0;
    ocean.material = water;
    const camera = new ArcRotateCamera('coast-review-camera', 0, 1, 20, Vector3.Zero(), scene);
    camera.minZ = .1; camera.maxZ = 2500;
    camera.lowerRadiusLimit = 5; camera.upperRadiusLimit = 110;
    camera.lowerBetaLimit = .15; camera.upperBetaLimit = 1.52;
    camera.panningSensibility = 0; camera.wheelDeltaPercentage = .015;
    camera.attachControl(canvas, true);
    let currentView: CoastView = 'game';
    function setView(view: CoastView) {
      currentView = view;
      const settings = {
        game: { pos: [-1.85, 21.5, 6.2], target: [-1.85, 6, .4], fov: .72 },
        reference: { pos: [.8, 20.5, 9.8], target: [-.9, 7.4, .3], fov: 2 * Math.atan(36 / (2 * 42)) },
        overview: { pos: [-31, 37, 30], target: [5, 0, .3], fov: 1.1 },
        detail: { pos: [21, 15, 10], target: [7.4, 3, .9], fov: .80 },
      }[view];
      camera.inertialAlphaOffset = camera.inertialBetaOffset = camera.inertialRadiusOffset = 0;
      camera.fov = settings.fov;
      camera.setTarget(toWorld(settings.target)); camera.setPosition(toWorld(settings.pos));
    }
    setView('game');
    await Promise.all(scene.meshes.filter(mesh => mesh.material && mesh.getTotalVertices()).map(mesh => mesh.material!.forceCompilationAsync(mesh)));
    await shadows.forceCompilationAsync();
    await scene.whenReadyAsync();
    scene.render();
    // Static visual sample: shadow map stays valid during camera orbit, no moving objects.
    shadows.getShadowMap()!.refreshRate = 0;
    for (const mesh of scene.meshes) mesh.computeWorldMatrix(true);
    const carBounds = carRoot.getHierarchyBoundingVectors(true);
    return {
      scene, camera, setView,
      report() {
        const viewport = camera.viewport.toGlobal(engine.getRenderWidth(), engine.getRenderHeight());
        const projected: number[][] = [];
        for (const x of [carBounds.min.x, carBounds.max.x]) for (const y of [carBounds.min.y, carBounds.max.y]) for (const z of [carBounds.min.z, carBounds.max.z]) {
          const point = Vector3.Project(new Vector3(x, y, z), Matrix.IdentityReadOnly, scene.getTransformMatrix(), viewport);
          projected.push([point.x / viewport.width, point.y / viewport.height, point.z]);
        }
        return {
          seed: layout.seed, scenario: layout.scenario, assetRevision: layout.asset_version, lightingReference: 'v007',
          layoutSha256: contract.layout.sha256, placementCount: placed.length, moduleCount: prototypes.size, lengthMetres: layout.road.sample_length_m,
          carSha256: car.model.sha256, carPosition: carRoot.position.asArray(), carProjectedBounds: projected,
          environmentTriangles: layout.placements.reduce((n, entry) => n + contract.assets.find(a => a.id === entry.asset)!.triangles, 0),
          carTriangles: model.meshes.reduce((n, mesh) => n + mesh.getTotalIndices() / 3, 0),
          placements: placed.map((pivot, i) => ({ asset: layout.placements[i]!.asset, position: pivot.position.asArray(), rotation: pivot.rotationQuaternion!.asArray(), scale: pivot.scaling.x })),
          view: currentView, camera: { position: camera.position.asArray(), target: camera.getTarget().asArray(), fov: camera.fov },
          lighting: { sunIntensity: sun.intensity, exposure: processing.exposure, toneMapping: 'KHR PBR Neutral', environmentIntensity: scene.environmentIntensity, shadowMapSize: 2048, shadowFilter: 'PCSS medium', lightSizeUVRatio: shadows.contactHardeningLightSizeUVRatio, staticShadowMap: true },
          resources: { meshes: scene.meshes.length, materials: scene.materials.length, textures: scene.textures.length, shadowCasters: shadows.getShadowMap()!.renderList!.length },
          physicsEnabled: Boolean(scene.isPhysicsEnabled()),
        };
      },
      dispose() { shadows.dispose(); for (const container of containers) container.dispose(); scene.dispose(); },
    };
  } catch (error) { for (const container of containers) container.dispose(); scene.dispose(); throw error; }
}
