import HavokPhysics from '@babylonjs/havok';
import wasmUrl from '@babylonjs/havok/lib/esm/HavokPhysics.wasm?url';

export type HavokRuntime = Awaited<ReturnType<typeof HavokPhysics>>;

export async function loadHavok(): Promise<HavokRuntime> {
  // Explicit fetch gives a useful HTTP error and guarantees the bundled local URL.
  const response = await fetch(wasmUrl, { signal: AbortSignal.timeout(30_000) });
  if (!response.ok) throw new Error(`Физика не загрузилась (HTTP ${response.status}).`);
  return HavokPhysics({ wasmBinary: await response.arrayBuffer() });
}
