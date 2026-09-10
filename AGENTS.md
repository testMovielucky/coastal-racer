# Coastal Racer

Read docs/GAME_IMPLEMENTATION_PLAN.md before implementation. Work one requested stage at a time. Current scope: stage 0 plus the explicitly requested visual Babylon previews of accepted car v006 and the explicitly requested static 40m coast sample-v006 with v007 lighting reference. No race-controller implementation.

- TypeScript strict + Vite + ordinary Babylon.js, WebGL2, Babylon Physics V2 + Havok. Keep exact versions and package-lock.json.
- No stack/control/MVP changes without a recorded decision. No custom collision solver.
- No ads, payments, paid generation APIs, accounts, backend, analytics, runtime CDN or network dependency during simulation.
- Generated original assets via local Blender scripts in later stages; no downloaded game models and no images presented as GLB. Preserve accepted sources/versions.
- Blender 5.2.1 LTS was verified in the modeling task at C:/Program Files/Blender Foundation/Blender 5.2/blender.exe. Do not install or update it silently. Accepted v006 is immutable; the user approved a 25k triangle budget in the modeling task.
- Technical boxes in stage 0 are placeholders. Visual acceptance and device performance remain separate gates.
- Keep frame/physics clocks separate. Test pause/resume, visibility, orientation, resize and disposal when changing lifecycle.
- Preserve seed/scenario/version in diagnostics; do not claim cross-browser physics determinism.
- Do not load new assets or compile new materials during an active race. Stage 0 warms the scene before activation.
- Never disable tests to get green output. Build success and emulated mobile tests are not evidence of 60 FPS on iPhone/iPad.
- Keep docs/DECISIONS.md and docs/PROGRESS.md factual. Report changes, commands actually run, checks passed, outstanding device/visual acceptance and budget changes.
- Do not implement the shop, full bot behavior, race controls or track generator during stage 0.

Commands (Node >=22.12): npm ci; npm run typecheck; npm test; npm run build; npm run test:e2e; npm run dev.
On this Windows host npm is local: .\\tools\\npm.ps1 <arguments>. Run .\\tools\\bootstrap-npm.ps1 once if needed; it only downloads into .tools. Local Playwright uses installed Chrome; CI installs Chromium. Tests exercise the production build at /coastal-racer/.
