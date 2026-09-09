import { Scene } from '@babylonjs/core/scene';
import type { Engine } from '@babylonjs/core/Engines/engine';
import { Constants } from '@babylonjs/core/Engines/constants';
import { ArcRotateCamera } from '@babylonjs/core/Cameras/arcRotateCamera';
import { DirectionalLight } from '@babylonjs/core/Lights/directionalLight';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { Vector3, Quaternion } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { CreateGround } from '@babylonjs/core/Meshes/Builders/groundBuilder';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import { PBRMaterial } from '@babylonjs/core/Materials/PBR/pbrMaterial';
import { RawCubeTexture } from '@babylonjs/core/Materials/Textures/rawCubeTexture';
import { CubeMapToSphericalPolynomialTools } from '@babylonjs/core/Misc/HighDynamicRange/cubemapToSphericalPolynomial';
import { LoadAssetContainerAsync } from '@babylonjs/core/Loading/sceneLoader';
import type { TransformNode } from '@babylonjs/core/Meshes/transformNode';
import '@babylonjs/loaders/glTF';
import contract from '../../../config/car-v006.json';

export const viewNames = ['game', 'rear', 'front', 'side'] as const;
export type CarView = typeof viewNames[number];

// A small, locally generated neutral environment. No remote HDRI or studio render is used.
function localEnvironment(scene: Scene) {
  const size = 32;
  const faces = Array.from({ length: 6 }, (_, side) => {
    const pixels = new Uint8Array(size * size * 4);
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const sky = side === 2 ? 0.65 : side === 3 ? 0.12 : 0.18 + 0.42 * (1 - y / (size - 1));
      const panel = side !== 2 && side !== 3 && x > 9 && x < 17 && y > 4 && y < 15 ? 0.3 : 0;
      const offset = (y * size + x) * 4;
      pixels[offset] = Math.round(255 * Math.min(1, sky + panel));
      pixels[offset + 1] = Math.round(255 * Math.min(1, sky * 1.02 + panel));
      pixels[offset + 2] = Math.round(255 * Math.min(1, sky * 1.08 + panel));
      pixels[offset + 3] = 255;
    }
    return pixels;
  });
  const environment = new RawCubeTexture(scene, faces, size, Constants.TEXTUREFORMAT_RGBA, Constants.TEXTURETYPE_UNSIGNED_BYTE, true);
  environment.name = 'local-neutral-environment-32';
  environment.gammaSpace = false;
  environment.sphericalPolynomial = CubeMapToSphericalPolynomialTools.ConvertCubeMapToSphericalPolynomial({
    size, right: faces[0]!, left: faces[1]!, up: faces[2]!, down: faces[3]!, front: faces[4]!, back: faces[5]!,
    format: Constants.TEXTUREFORMAT_RGBA, type: Constants.TEXTURETYPE_UNSIGNED_BYTE, gammaSpace: false,
  });
  scene.environmentTexture = environment;
  scene.environmentIntensity = 0.8;
}

async function loadVerified(scene: Scene, file: typeof contract.model, signal: AbortSignal) {
  const response = await fetch(new URL(import.meta.env.BASE_URL + file.path, document.baseURI), { signal });
  if (!response.ok) throw new Error('GLB не загрузился (HTTP ' + response.status + ').');
  const bytes = await response.arrayBuffer();
  const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), value => value.toString(16).padStart(2, '0')).join('');
  if (bytes.byteLength !== file.bytes || digest !== file.sha256) throw new Error('GLB отличается от принятой v006. Проверьте версию файла.');
  return LoadAssetContainerAsync(new Uint8Array(bytes), scene, { pluginExtension: '.glb', name: file.path.split('/').at(-1) });
}

export async function createCarPreviewScene(engine: Engine, canvas: HTMLCanvasElement, signal: AbortSignal) {
  const scene = new Scene(engine);
  scene.useRightHandedSystem = true; // Keep authored glTF +Z forward and wheel local X unchanged.
  scene.clearColor = new Color4(0.12, 0.23, 0.28, 1);
  try {
    localEnvironment(scene);
    const sun = new DirectionalLight('preview-sun', new Vector3(-0.5, -1, 0.4), scene);
    sun.intensity = 2.4;
    const fill = new HemisphericLight('preview-fill', Vector3.Up(), scene);
    fill.intensity = 0.35;
    fill.groundColor = Color3.FromHexString('#52606c');
    const ground = CreateGround('preview-ground', { width: 200, height: 200 }, scene);
    ground.position.y = -0.015;
    const groundMaterial = new StandardMaterial('preview-ground-material', scene);
    groundMaterial.diffuseColor = Color3.FromHexString('#556973');
    groundMaterial.specularColor = Color3.Black();
    groundMaterial.disableLighting = true;
    groundMaterial.emissiveColor = Color3.FromHexString('#263f4a');
    ground.material = groundMaterial;
    const camera = new ArcRotateCamera('car-preview-camera', -Math.PI / 2, 1.15, 7.5, new Vector3(0, 0.5, 0), scene);
    camera.minZ = 0.05;
    camera.maxZ = 250;
    camera.fov = 0.65;
    camera.lowerRadiusLimit = 4.5;
    camera.upperRadiusLimit = 12;
    camera.lowerBetaLimit = 0.2;
    camera.upperBetaLimit = 1.52;
    camera.panningSensibility = 0;
    camera.wheelDeltaPercentage = 0.02;
    camera.attachControl(canvas, true);

    const model = await loadVerified(scene, contract.model, signal);
    model.addAllToScene();
    const root = scene.getTransformNodeByName('CR_Sport_01');
    if (!root) throw new Error('В GLB отсутствует CR_Sport_01.');
    const wheels = ['Wheel_FL', 'Wheel_FR', 'Wheel_RL', 'Wheel_RR'].map(name => {
      const node = scene.getTransformNodeByName(name);
      if (!node) throw new Error('В GLB отсутствует ' + name);
      return node;
    });
    const initialWheelRotations = wheels.map(wheel => (wheel.rotationQuaternion ?? Quaternion.Identity()).clone());
    const paint = scene.getMaterialByName('Body_Paint');
    if (!(paint instanceof PBRMaterial)) throw new Error('Не найден PBR-материал Body_Paint.');
    const originalPaint = paint.albedoColor.clone();
    const meshes = model.meshes.filter(mesh => mesh.getTotalVertices() > 0);
    const triangles = meshes.reduce((sum, mesh) => sum + mesh.getTotalIndices() / 3, 0);
    if (triangles !== contract.triangles) throw new Error('Изменилось число треугольников принятой модели.');
    if (model.materials.length !== 4) throw new Error('Ожидались четыре материала модели.');
    for (const mesh of model.meshes) mesh.computeWorldMatrix(true);
    const bounds = root.getHierarchyBoundingVectors(true);

    const collider = await loadVerified(scene, contract.collider, signal);
    collider.addAllToScene();
    const colliderRoot = collider.rootNodes[0] as TransformNode;
    const colliderMaterial = new StandardMaterial('collider-wire', scene);
    colliderMaterial.emissiveColor = Color3.FromHexString('#abff80');
    colliderMaterial.disableLighting = true;
    colliderMaterial.wireframe = true;
    for (const mesh of collider.meshes) if (mesh.getTotalVertices()) mesh.material = colliderMaterial;
    // Prepare the actual material variants before controls become active.
    await Promise.all(scene.meshes.filter(mesh => mesh.material).map(mesh => mesh.material!.forceCompilationAsync(mesh)));
    await scene.whenReadyAsync();
    colliderRoot.setEnabled(false);

    let currentView: CarView = 'game';
    let wheelAngle = 0;
    function fitCamera() {
      const target = camera.getTarget();
      const forward = target.subtract(camera.position).normalize();
      const right = Vector3.Cross(forward, Vector3.Up()).normalize();
      const up = Vector3.Cross(right, forward).normalize();
      const tanV = Math.tan(camera.fov / 2);
      const tanH = tanV * engine.getAspectRatio(camera);
      let distance = camera.radius;
      for (const x of [bounds.min.x, bounds.max.x]) for (const y of [bounds.min.y, bounds.max.y]) for (const z of [bounds.min.z, bounds.max.z]) {
        const relative = new Vector3(x, y, z).subtract(target);
        const depth = Vector3.Dot(relative, forward);
        distance = Math.max(distance, Math.abs(Vector3.Dot(relative, right)) * 1.15 / tanH - depth, Math.abs(Vector3.Dot(relative, up)) * 1.15 / tanV - depth);
      }
      camera.upperRadiusLimit = Math.max(12, distance * 1.5);
      camera.radius = distance;
    }

    function setView(view: CarView) {
      currentView = view;
      const target = view === 'game' ? new Vector3(0, 0.55, 0.6) : new Vector3(0, 0.6, 0);
      const positions: Record<CarView, Vector3> = {
        game: new Vector3(0, 2.7, -7.4),
        rear: new Vector3(0, 1.7, -7),
        front: new Vector3(0, 1.7, 7),
        side: new Vector3(7.5, 1.8, 0),
      };
      camera.inertialAlphaOffset = camera.inertialBetaOffset = camera.inertialRadiusOffset = 0;
      camera.setTarget(target);
      camera.setPosition(positions[view]);
      fitCamera();
    }
    setView('game');
    return {
      scene, camera, wheels, root, paint,
      setView, fitCamera,
      setPaint(hex: string) { paint.albedoColor = hex === 'original' ? originalPaint.clone() : Color3.FromHexString(hex).toLinearSpace(); },
      setCollider(visible: boolean) { colliderRoot.setEnabled(visible); },
      stepWheels(seconds: number) {
        wheelAngle = (wheelAngle + seconds * 2.5) % (2 * Math.PI);
        wheels.forEach((wheel, i) => {
          wheel.rotationQuaternion = initialWheelRotations[i]!.multiply(Quaternion.RotationAxis(Vector3.Right(), wheelAngle));
        });
      },
      report() {
        return {
          asset: contract.id, revision: contract.revision, sha256: contract.model.sha256,
          bytes: contract.model.bytes, triangles, triangleBudget: contract.triangleBudget,
          materialCount: model.materials.length, materials: model.materials.map(material => material.name),
          pbr: model.materials.filter((material): material is PBRMaterial => material instanceof PBRMaterial).map(material => ({ name: material.name, metallic: material.metallic, roughness: material.roughness, doubleSided: !material.backFaceCulling, clearCoat: material.clearCoat.isEnabled ? material.clearCoat.intensity : 0 })),
          renderMeshes: meshes.length, vertices: meshes.reduce((sum, mesh) => sum + mesh.getTotalVertices(), 0),
          dimensions: bounds.max.subtract(bounds.min).asArray(), modelBounds: { min: bounds.min.asArray(), max: bounds.max.asArray() },
          coordinateSystem: 'right-handed; +Z forward, +Y up; wheel spin local X',
          colorLinear: paint.albedoColor.asArray(), colliderVisible: colliderRoot.isEnabled(), view: currentView,
          wheels: wheels.map(wheel => ({ name: wheel.name, pivot: wheel.getAbsolutePosition().asArray(), rotation: wheel.rotationQuaternion?.asArray() })),
          vertexColorMeshes: meshes.filter(mesh => mesh.isVerticesDataPresent('color')).length,
          resources: { meshes: scene.meshes.length, materials: scene.materials.length, textures: scene.textures.length },
        };
      },
      dispose() { model.dispose(); collider.dispose(); scene.dispose(); },
    };
  } catch (error) { scene.dispose(); throw error; }
}
