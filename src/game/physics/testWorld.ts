import { Scene } from '@babylonjs/core/scene';
import type { AbstractEngine } from '@babylonjs/core/Engines/abstractEngine';
import { FreeCamera } from '@babylonjs/core/Cameras/freeCamera';
import { HemisphericLight } from '@babylonjs/core/Lights/hemisphericLight';
import { Vector3, Quaternion } from '@babylonjs/core/Maths/math.vector';
import { Color3, Color4 } from '@babylonjs/core/Maths/math.color';
import { CreateBox } from '@babylonjs/core/Meshes/Builders/boxBuilder';
import { StandardMaterial } from '@babylonjs/core/Materials/standardMaterial';
import type { Mesh } from '@babylonjs/core/Meshes/mesh';
import { HavokPlugin } from '@babylonjs/core/Physics/v2/Plugins/havokPlugin';
import { PhysicsAggregate } from '@babylonjs/core/Physics/v2/physicsAggregate';
import { PhysicsShapeType } from '@babylonjs/core/Physics/v2/IPhysicsEnginePlugin';
import { PhysicsEngine } from '@babylonjs/core/Physics/v2/physicsEngine';
import '@babylonjs/core/Physics/joinedPhysicsEngineComponent';
import '@babylonjs/core/Rendering/edgesRenderer';
import type { HavokRuntime } from './havok';

interface TestBody {
  collider: Mesh;
  visual: Mesh;
  aggregate: PhysicsAggregate;
  previousPosition: Vector3;
  previousRotation: Quaternion;
}

export function createTestWorld(engine: AbstractEngine, runtime: HavokRuntime) {
  const scene = new Scene(engine);
  scene.clearColor = new Color4(0.36, 0.75, 0.81, 1);
  const camera = new FreeCamera('stand-camera', new Vector3(10, 26, -30), scene);
  camera.setTarget(new Vector3(0, 0, -10));
  camera.fov = 0.85;
  camera.minZ = 0.1;
  camera.maxZ = 150;
  const light = new HemisphericLight('sunlight', new Vector3(-0.5, 1, -0.3), scene);
  light.intensity = 1.2;
  light.groundColor = Color3.FromHexString('#536175');
  const plugin = new HavokPlugin(true, runtime);
  scene.enablePhysics(new Vector3(0, -9.81, 0), plugin);
  const physics = scene.getPhysicsEngine();
  if (!(physics instanceof PhysicsEngine)) throw new Error('Ожидалась физика Babylon V2.');
  physics.setTimeStep(1 / 60);
  // Step explicitly through the public Havok API so the application owns its clock.
  scene.physicsEnabled = false;

  const material = (name: string, hex: string) => {
    const result = new StandardMaterial(name, scene);
    result.diffuseColor = Color3.FromHexString(hex);
    result.specularColor = new Color3(0.12, 0.12, 0.12);
    return result;
  };
  const roadMaterial = material('asphalt', '#354653');
  const edgeMaterial = material('concrete', '#e1e6d8');
  const lineMaterial = material('markings', '#ecedcb');
  const sandMaterial = material('sand', '#e8ca91');
  const aggregates: PhysicsAggregate[] = [];
  const box = (name: string, width: number, height: number, depth: number, position: Vector3, mat: StandardMaterial, solid = false) => {
    const mesh = CreateBox(name, { width, height, depth }, scene);
    mesh.position.copyFrom(position);
    mesh.material = mat;
    if (solid) aggregates.push(new PhysicsAggregate(mesh, PhysicsShapeType.BOX, { mass: 0, friction: 0.65, restitution: 0.05 }, scene));
    return mesh;
  };
  box('shore', 6, 0.5, 70, new Vector3(10, -0.7, 4), sandMaterial);
  box('road', 14, 0.6, 54, new Vector3(0, -0.3, 4), roadMaterial, true);
  for (const side of [-1, 1]) {
    box(`barrier-${side}`, 0.5, 0.8, 54, new Vector3(side * 7, 0.4, 4), edgeMaterial, true);
    box(`edge-line-${side}`, 0.12, 0.015, 52, new Vector3(side * 6.3, 0.012, 4), lineMaterial);
  }
  for (let z = -20; z < 30; z += 5) box(`dash-${z}`, 0.12, 0.015, 2.2, new Vector3(0, 0.012, z), lineMaterial);
  box('end-barrier', 14, 0.8, 0.6, new Vector3(0, 0.4, 31), edgeMaterial, true);
  box('start-barrier', 14, 0.8, 0.6, new Vector3(0, 0.4, -23), edgeMaterial, true);

  const colors = ['#fc7051', '#f4ce58', '#52d8c9', '#728cff', '#e18dde', '#edf3eb'];
  const cars: TestBody[] = colors.map((color, i) => {
    const collider = CreateBox(`body-${i}`, { width: 1.8, height: 0.8, depth: 3.5 }, scene);
    collider.position.set(i % 2 === 0 ? -1.15 : 1.15, 1.5 + i * 0.1, -7 + Math.floor(i / 2) * 5);
    collider.rotationQuaternion = Quaternion.Identity();
    collider.isVisible = false;
    const aggregate = new PhysicsAggregate(collider, PhysicsShapeType.BOX, { mass: 1000, friction: 0.55, restitution: 0.12 }, scene);
    aggregate.body.setLinearDamping(0.2);
    aggregate.body.setAngularDamping(0.8);
    aggregates.push(aggregate);
    const visual = CreateBox(`chassis-${i}`, { width: 1.8, height: 0.8, depth: 3.5 }, scene);
    visual.material = material(`body-color-${i}`, color);
    visual.rotationQuaternion = Quaternion.Identity();
    visual.position.copyFrom(collider.position);
    visual.enableEdgesRendering();
    visual.edgesWidth = 1.5;
    visual.edgesColor = new Color4(0.05, 0.13, 0.17, 0.5);
    return { collider, visual, aggregate, previousPosition: collider.position.clone(), previousRotation: Quaternion.Identity() };
  });

  return {
    scene,
    cars,
    step(seconds: number) {
      for (const car of cars) {
        car.previousPosition.copyFrom(car.collider.position);
        car.previousRotation.copyFrom(car.collider.rotationQuaternion!);
      }
      plugin.executeStep(seconds, physics.getBodies());
    },
    interpolate(alpha: number) {
      for (const car of cars) {
        Vector3.LerpToRef(car.previousPosition, car.collider.position, alpha, car.visual.position);
        Quaternion.SlerpToRef(car.previousRotation, car.collider.rotationQuaternion!, alpha, car.visual.rotationQuaternion!);
      }
    },
    impulse() {
      const car = cars[0]!;
      car.aggregate.body.applyImpulse(new Vector3(1700, 500, 8000), car.collider.position);
    },
    resources() {
      return { meshes: scene.meshes.length, materials: scene.materials.length, textures: scene.textures.length, bodies: physics.getBodies().length, dynamicBodies: cars.length, observers: scene.onBeforeRenderObservable.observers.length + scene.onAfterRenderObservable.observers.length };
    },
    dispose() {
      for (const aggregate of aggregates) aggregate.dispose();
      scene.dispose();
    },
  };
}
