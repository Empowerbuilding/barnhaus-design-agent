# Revit Capabilities — Blueprint (TRUTH-BASED)

_This file replaces the old workspace `REVIT_CAPABILITIES.md` ("Status: COMPLETE ✅"),
which claimed parked modules were live and directly caused the 2026-09-14 over-promise
to Michael. Rules first, tiers second, **no counts, no "COMPLETE" claims — ever.**_

## Rule 0 — The only source of truth is the live bridge

```
GET <bridge_url>/tools          → the installed DLL's real command catalog
core.revit_client.list_tools()  → same thing from python
```

- Run it **at session start** and **after every UpdateBridge.bat run**.
- Never answer "can you do X in Revit?" from memory or from this file — check `/tools`.
- Never quote command counts. Counts drift; the catalog is generated per-build.
- `GET /health` on new builds includes `build` (git sha) + `command_count` — use it to
  tell whether the user's installed DLL is current or stale. A health response
  **without** a `build` field = pre-2026-09-14 DLL → tell the user to run UpdateBridge.bat.
- `BRIDGE_COMMANDS.md` + `tools.json` in the revit-bridge repo are CI-generated from
  source on every push — they describe the **latest build**, not what a user has installed.

## Rule 1 — All dispatch names use the `revit.` prefix

The bridge keys on `revit.*`. `core/revit_client.py::call()` auto-prefixes since
2026-09-14, and new DLLs normalize server-side too — but write the prefix explicitly
anyway. Older installed DLLs return "Unknown tool" for bare names.

## Rule 2 — Compiled ≠ proven

CI compiles against NuGet API stubs. **Compile-pass ≠ runtime-pass.** Any command that
has never run against a live model gets smoke-tested on a scratch element/model before
it touches real work. Track first-live-use in memory files.

## Rule 3 — Never promise parked commands

Modules excluded from compilation (see the csproj `<Compile Remove>` block and the
PARKED section of `BRIDGE_COMMANDS.md`) do **not exist in any DLL**, no matter what any
doc says. As of 2026-09-14 that includes: **railings, sketch-based stairs
(create_stairs_by_sketch / modify_stairs_run / set_stairs_path), spaces, MEP
(ducts/pipes/cable tray/routing/sizing/systems), structural (columns/framing/truss/
rebar/loads), phasing, design options, units commands.** If asked for these: say
they're parked, offer the Universal Bridge reflection layer as an experimental
workaround, or manual placement.

## Rule 4 — Update flow

1. Push bridge change → CI must go **green** (verify the run, not the push).
2. CI publishes the DLL zip + regenerates the catalog.
3. User runs UpdateBridge.bat (close Revit → update → reopen).
4. **Verify**: `/health` build sha matches the new commit → only then claim the
   capability exists on their machine.

## Capability tiers (orientation only — `/tools` overrides this file)

**Tier A — compiled + proven live:** walls (create_wall/create_walls, batch,
strict type/level resolution), roofs (create_roof + per-edge slope_edges, fascia/
gutter/soffit sweeps, attach_walls_to_roof), levels/grids, element query + inspection,
parameters (get/set/batch), views/sheets/viewports/tags, export-image + vision QA,
schedules read, delete + try_delete (dry-run), Universal Bridge reflection
(invoke_method / reflect_get / reflect_set), diagnostics, capture_screen.

**Tier B — compiled, not yet proven live (smoke-test first):** place_door,
place_window, place_family_instance hosting paths, create_floor (boundary+level+type),
basic create_stairs, list_types, and anything newly unlocked by the 2026-09-14
registry wiring. Promote to Tier A in this file only after a successful live run.

**Tier C — PARKED (not in any DLL):** see Rule 3 list.

**UI-only (genuine API gaps):** interactive sketch-mode editing, certain modal
dialogs, third-party plugins without APIs (Enscape).

## Operating rules (unchanged, still binding)

- Health-check before any command; never run against a stale tunnel.
- Deletes and model-wide changes: explicit user confirmation, always — re-confirm the
  active document name at delete time.
- Transactions + rollback on every mutation.
- Only tell Michael/Mitch to update after the CI run is verified green.
