import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { beforeAll, expect, it } from 'vitest';
import HavokPhysics from '@babylonjs/havok';
import { NullEngine } from '@babylonjs/core/Engines/nullEngine';
import { PhysicsEngine } from '@babylonjs/core/Physics/v2/physicsEngine';
import { createTestWorld } from '../../src/game/physics/testWorld';
import type { HavokRuntime } from '../../src/game/physics/havok';

let runtime: HavokRuntime;
beforeAll(async () => {
  const path = createRequire(import.meta.url).resolve('@babylonjs/havok/lib/esm/HavokPhysics.wasm');
  runtime = await HavokPhysics({ wasmBinary: Uint8Array.from(await readFile(path)).buffer });
});

it('six real Havok bodies settle on the road and transfer an impulse through contact', () => {
  const engine = new NullEngine();
  const world = createTestWorld(engine, runtime);
  try {
    for (let i = 0; i < 180; i++) world.step(1 / 60);
    for (const car of world.cars) expect(car.collider.position.y).toBeCloseTo(0.4, 1);
    const before = world.cars.map(car => car.collider.position.z);
    world.impulse();
    for (let i = 0; i < 120; i++) world.step(1 / 60);
    expect(world.cars[0]!.collider.position.z).toBeGreaterThan(before[0]! + 1);
    expect(world.cars[2]!.collider.position.z).toBeGreaterThan(before[2]! + 0.1);
    for (const car of world.cars) expect(car.collider.position.asArray().every(Number.isFinite)).toBe(true);
  } finally { world.dispose(); engine.dispose(); }
});

it('disposes bodies and scenes across twenty independent worlds', () => {
  const engine = new NullEngine();
  try {
    let baseline: ReturnType<ReturnType<typeof createTestWorld>['resources']> | undefined;
    for (let i = 0; i < 20; i++) {
      const world = createTestWorld(engine, runtime);
      world.step(1 / 60);
      baseline ??= world.resources();
      expect(world.resources()).toEqual(baseline);
      const physics = world.scene.getPhysicsEngine() as PhysicsEngine;
      world.dispose();
      expect(physics.getBodies()).toHaveLength(0);
      expect(engine.scenes).toHaveLength(0);
    }
  } finally { engine.dispose(); }
});
