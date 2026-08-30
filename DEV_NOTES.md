# DEV_NOTES — dev/verify branch

**Status: UNTESTED AGAINST LIVE BRIDGE.** Everything on this branch compiles
and follows existing repo call patterns, but none of it has run against an
open Revit model or the live portal tables. Do NOT merge to master until the
first desk session validates the assumptions below (master = live, Blueprint
hard-resets to it).

## What's on this branch

| File | What |
|---|---|
| `intent_queries.py` | Query primitives (`room_exists_in_region`, `elements_exist`, `get_room_area`, `count_elements`) + `run_verify()` |
| `core/portal.py` | Portal Supabase REST helpers (intent items fetch/patch, portal_messages post) |
| `weight_report.py` | `run.py weight` — model weight hit list |
| `standards.yaml` | Rules skeleton — **Michael must author the real content** |
| `standards_runner.py` | Executes standards.yaml → PASS/FAIL per rule |
| `tasks/gate.py` | `run.py gate` — standards + verify + qa → GATE: PASS/FAIL, `--post` to juanito-production |
| `run.py` | New dispatcher entries only: `verify`, `weight`, `standards`, `gate` |

## Setup required before first run

1. **Portal key** — `core/portal.py` follows the `frank_sync.py` convention
   (never hardcode keys in the repo). Provision ONE of:
   - env var `PORTAL_SUPABASE_KEY` (portal service-role key — Tony has it), or
   - `/home/node/.openclaw/workspace/.portal_keys.json` with
     `{"portal_supabase_key": "..."}`
2. **`design_intent_items` table** must exist in the portal project with
   columns: id uuid, project_name text, item text, category text,
   check_type text, check_params jsonb, status text, source text,
   details jsonb, created_at, updated_at. (Tony builds the Juanito side.)
3. PyYAML is optional — `standards_runner.py` falls back to a mini-parser
   that handles the skeleton's structure. `pip install pyyaml` in Blueprint's
   container is still the better path once standards.yaml grows.

## Assumptions to validate in the first desk session

**Bridge response shapes (biggest risk):**
- [ ] `list_elements_by_category("Rooms")` returns elements under key
  `elements` (revit_client.get_all_rooms reads `rooms` — the two existing
  code paths disagree; intent_queries uses the generic `elements` path).
- [ ] Element dicts carry `family` / `type` / `name` fields as used by
  `_matching_elements()` and `weight_report._family_type_key()` — confirm
  actual key names for doors/windows/casework.
- [ ] `get_element_bounding_box` result has `has_bbox`, `min`, `max` keys
  (copied from project_state usage — should be right).
- [ ] `list_views()` entries carry `name`; `list_sheets()` entries carry `id`
  (numbers/names read per-sheet via `get_parameter_value`, per the known
  bridge gotcha).
- [ ] "Title Blocks" works as a `list_elements_by_category` category string
  for PLACED titleblocks (only verified for `list_families` so far).
- [ ] Imported CAD category mapping — `weight_report.py` tries
  "Imports" / "Import Instances" / "ImportInstance" / "DWG"; likely none map.
  If so, a dedicated `revit.list_imports` DLL command is needed.

**Semantics:**
- [ ] Region check = room bbox CENTER vs midpoint of the union of all placed
  room bboxes. A room straddling the midline lands in neither half of that
  axis — confirm this matches how Michael/Juanito phrase intent ("master on
  the south side"). May need a tolerance band or area-majority test.
- [ ] `fetch_intent_items` matches `project_name` with ilike `*name*` —
  confirm Juanito writes project_name values that substring-match document
  titles (gate falls back to the open document title).
- [ ] Gate verdict: standards fails + verify fails + QA "fix" issues fail the
  gate; NEEDS-HUMAN and skipped sections don't. Confirm with Michael.
- [ ] `status` values written back: `verified` / `failed`. Manual items are
  left untouched (reported NEEDS-HUMAN only). Confirm Juanito's side expects
  these exact strings.

**Weight report:**
- Per-family byte sizes, geometry complexity, purge-unused, and link sizes
  all need DLL support that doesn't exist yet — the report says so explicitly
  and ranks by instance-count × category-heaviness heuristic in the meantime.

## First desk session script (suggested)

```bash
python3 run.py standards          # exercises sheets/views/titleblock reads
python3 run.py weight             # exercises category scans + families
python3 run.py verify McGee       # needs portal key + seeded intent rows
python3 run.py gate McGee --post  # full loop incl. portal post
```

Fix key-name mismatches as they surface (they'll be quick), then merge.
