# BRIDGE_API.md — How to Call the Bridge (payloads, gotchas, zero source-grepping)

_This doc + `docs/bridge_schemas.json` + `bridge.py` exist so nobody ever greps
the DLL source for an arg name again. On 2026-11-04 a single countertop task
burned ~15 execs re-deriving command schemas from `BridgeCommandFactory.cs`.
That failure mode is dead: schema lookup is now one command, offline._

**Lookup order for "how do I call X":**
1. `bridge.py doc <command>` — arg names, required flags, parked status
2. `docs/bridge_schemas.json` — all 294 commands (261 compiled + 33 parked), machine-readable
3. `bridge.py tools` — LIVE catalog on the connected DLL (what's actually installed)
4. Only if a schema disagrees with live behavior: the C# source (and that's a bug to report)

Never answer "does X exist" from this file — `GET /tools` on the live bridge is
the only truth for existence (see `docs/REVIT_CAPABILITIES.md` Rule 0).

---

## The CLI (`bridge.py`, repo root)

```
bridge.py health                                 # status, build sha, active document
bridge.py tools                                  # live command catalog
bridge.py doc place_family_instance              # payload schema (offline)
bridge.py find 'countertop|material'             # name search (offline)
bridge.py call revit.get_document_info           # one call, no payload
bridge.py call revit.list_elements_by_category '{"category":"Casework"}'
bridge.py call place_family_instance --arg family_name='Counter Top' --arg type_name='24" Depth' --arg location='{"x":10,"y":5,"z":0}' --arg level='Level 1'
bridge.py script batch_task.py                   # many calls in ONE exec (see batching)
```

- Tool names auto-prefix `revit.` — bare names work.
- Output: `{"success": bool, "result": ..., "error": ...}` on one line. Exit 1 on failure. `--full` adds the raw response.
- URL resolution: `--url` > `$REVIT_BRIDGE_URL` > `bridge_sessions.json [--channel blueprint-mitch]` > `http://localhost:3000`.
- `bridge.py script FILE` runs a python file with `rc` (revit_client) and `call` preloaded — this is the batching path.

## Universal rules

- **All coordinates/lengths are decimal feet** (not inches, not mm). Z is up.
- **Category names** are Revit display names: `Walls`, `Casework`, `Furniture`, `Generic Models`, `Specialty Equipment`, `Rooms`, `Dimensions`… `bridge.py call get_categories` lists what the open model has.
- **Batch, don't loop calls**: one `bridge.py script` with N calls beats N execs — every round trip costs seconds and tokens.
- **Verify writes**: read back what you wrote (bounding box / parameter readback). The 2026-10-31 bridge makes refusals loud (`status:error`, "Revit REFUSED…") — a `success:true` means it actually happened. If you see REFUSED: stop retrying; the element is pinned/constrained/hosted. Diagnose with `try_delete` / `get_dependencies` / `inspect_element`.

## Core commands (source-verified payloads)

`*` = required. `xyz` = `{"x":..,"y":..,"z":..}` in feet.

### State & discovery
| Command | Args | Notes |
|---|---|---|
| `get_document_info` | — | title, path, modified, project meta. First call of every session |
| `get_active_view` | — | |
| `get_categories` | — | valid category names for this model |
| `list_families` | `category` | families loaded in the project |
| `list_local_families` | — | local (unshared) families |
| `list_views` / `list_sheets` | — | |
| `get_warnings` | — | model warnings |

### Read / inspect
| Command | Args | Notes |
|---|---|---|
| `list_elements_by_category` | `*category`, `view_id` | view_id scopes to a view. Elements carry id/name/type/level/length_ft/area_sf |
| `get_element_parameters` | `*element_id` | all instance params |
| `get_type_parameters` | `*element_id` | all TYPE params (type_name, type_family, parameters[]) |
| `get_parameter_value` | `*element_id`, `*parameter_name` | single value |
| `get_element_bounding_box` | `*element_id` | min/max xyz — placement verification |
| `get_element_type` | `*category_name`, `family_name` | |
| `inspect_element` | `*element_id` | deep dive: class, type, level, bbox, host, params, dependents |
| `get_dependencies` | `*element_id` (client convention) | hosted families, sketch lines, constraints |
| `try_delete` | `*element_id` (client convention) | **always rolls back** — pure diagnostic of delete blockers |
| `diagnose_element` | `*element_id` | |

### Place / create
| Command | Args | Notes |
|---|---|---|
| `place_family_instance` | `*location` xyz, `*family_name`, `*type_name`, `*level`, `rotation` | **check `placement_ok` + `actual_location` vs `requested_location`** — families can override placement internally |
| `download_family` | `*url` | pulls an .rfa from the web into the project |
| `create_solid_extrusion` | `*name`, `*profile_points`, `*height` | freeform DirectShape solid |
| `create_walls` | `walls[]` `{start,end,wall_type_name,level_name,height_ft,base_offset_ft,structural}`, `allow_fallback` | batch; strict name resolution; per-item errors + available_* lists. Docs: revit-bridge/docs/create-walls.md |
| `create_roof_fascia` | `*roof_id`, `fascia_type_name` (default: first loaded), `edge_filter` (`all` default \| `horizontal` = eaves only \| `sloped` = rakes) | NATIVE parametric fascia (HostedSweep) — follows the roof when it edits. Edges auto-picked from the roof's bottom faces (eaves+rakes, ridge excluded). Needs a fascia family loaded; errors list available types, `revit.load_family` fixes it. Per-edge results. **Requires DLL build 234a085+ (2026-11-05)** |
| `create_material` | `*name`, `color` `{"r":..,"g":..,"b":..}`, `transparency`, `shininess`, `smoothness` | |
| `create_level` / `create_floor` / `place_room` | see `bridge.py doc` | |

### Modify
| Command | Args | Notes |
|---|---|---|
| `move_element` | `*element_id`, `*vector` xyz | refuses loudly on pinned/hosted |
| `batch_move_elements` | `*element_ids[]`, `*translation` xyz | |
| `set_parameter_value` | `*element_id`, `*parameter_name`, `*value` | instance param |
| `set_type_parameter` | **`*type_id`** (NOT element id), `*parameter_name`, `*value` | classic mistake: passing element id |
| `batch_set_parameters` | `*element_ids[]`, `*parameter_name`, `*value` | per-item status — count only non-error items as done |
| `set_element_material` | `*element_id`, `*material_name`, `face_index` | |
| `copy_element` | `*element_id`, `*vector` xyz | |
| `delete_element` | `*element_id` | |
| `edit_family` | `family_name` / `family_symbol_id` / `family_instance_id` (one of) | opens family for editing — pair with the family-doc flow |

### Universal escape hatch (when no command fits)
| Command | Args | Notes |
|---|---|---|
| `invoke_method` | `*class_name`, `*method_name`, `*arguments[]`, `target_id`, `use_transaction` | raw Revit API reflection. There is **no `get_property` command** — reflection reads go through `invoke_method` too |

### Views & export
| Command | Args | Notes |
|---|---|---|
| `create_section_view` | `*start_point` xyz, `*end_point` xyz, `name` | |
| `create_3d_view` / `create_floor_plan_view` | see `bridge.py doc` | floor plan takes `level` as a NAME string |
| `export_view_image_base64` | `*view_id`, `resolution` (default 1500), `format` | image bytes back through the tunnel in one call |
| `export_image` | view_id, output_path… | writes to the BRIDGE HOST disk — prefer base64 variant |
| `get_file_base64` | `*path`, `max_bytes` | bridge-host file fetch (RevitMCP/temp dirs only) |
| `capture_screen` | `scope`, `max_width`, `format` | |

## Gotchas (paid for in real minutes)

- **Families place at 8–12 ft default z** depending on internal origin — verify actual z immediately, correct in the same script (recipes/2026-10-31).
- **`place_door` client helper is stale**: `core/revit_client.place_door()` sends `position_along_wall`, but the DLL wants `*wall_id` + `*location` xyz. Call the bridge directly for doors/windows.
- **`calculate_material_quantities`**: Walls/Roofs/Floors/Ceilings ONLY. Structural foundations/framing/columns → workaround via `get_parameter_value` (Area) or bounding boxes.
- **`create_dimension`** works floor-plan wall-to-wall, **broken in elevations**. `create_height_dimension` broken. `set_category_visibility` silently no-ops.
- **`create_sheet`** takes `titleblock_name` (not title_block_family). Query titleblocks first.
- **Parked commands** (33: MEP, structural, stairs-by-sketch, spaces, phasing, design options…) are in the source tree but **not in any DLL** — live calls return Unknown tool. `bridge.py doc <name>` marks them `[parked]`. Full list: `docs/bridge_schemas.json`.
- The installed DLL can be older than this repo (check `bridge.py health` → `build` sha vs revit-bridge HEAD). A health response without `build` = pre-2026-09-14 DLL → tell the user to run UpdateBridge.bat.

## Keeping this current

`docs/bridge_schemas.json` is generated from the revit-bridge source:

```
python3 scripts/gen_bridge_schemas.py            # sibling checkout ../../revit-bridge
python3 scripts/gen_bridge_schemas.py --src /path/to/revit-bridge
```

Rerun after revit-bridge changes land (CI also regenerates `BRIDGE_COMMANDS.md` +
`tools.json` on the revit-bridge side — those carry names only, this carries
schemas). If `bridge.py doc` and live behavior disagree, trust live, then fix
the generator.
