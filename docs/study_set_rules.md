# Study Set Production Rules
## Lessons learned from Allen project (2026-06-16)

---

## Bridge API Rules

### Title Block
- **Correct parameter name**: `titleblock_name` (NOT `title_block_family`)
- **Correct family name**: query with `revit.list_titleblocks` or `revit.list_families` first — do NOT hardcode `"Barnhaus Title Block"`
- If `titleblock_name` is missing/wrong, Revit creates a **placeholder sheet** — shows in `list_sheets` API but NOT in Project Browser
- Always verify sheet appears in Project Browser after creation

```python
# Always do this first:
r = rc.call('revit.list_families', {})
title_blocks = [f for f in r['result']['families'] if f.get('category') == 'Title Blocks']
# Use title_blocks[0]['name'] as titleblock_name
```

### Sheet Numbers
- Avoid numbers that conflict with existing sheets (e.g. if `A100.2` exists, don't create `A100.2.1`)
- Use `A100.3`, `A100.4` etc. for 3D view sheets in this model

### set_category_visibility
- **DOES NOT EXIST in the bridge** — calls return success silently but do NOTHING
- To clean up elevation views: **DELETE the annotation elements directly**
- Categories to delete for study set elevations: `Door Tags`, `Window Tags`, `Dimensions`
- Since study set is a separate copy (Save As), deletion is safe and non-destructive to original

### Dimension Elements in Elevation Views
- `revit.create_dimension` with Level references creates elements with correct values but **they don't appear in elevation views**
- Root cause: the dimension line XY must match the elevation view's cut plane position exactly
- **TODO**: add `revit.get_view_origin` tool to query each elevation view's marker position and orientation
- Until then: use `revit.create_text_note` for height callouts on elevation views
- Floor plan dimensions between walls work fine

### Text Notes
- `revit.create_text_note` works after the June 2026 bridge fix
- The bridge must use `FilteredElementCollector` to find a valid `TextNoteType` — the old hardcoded `BuiltInParameter.TEXT_SIZE` was broken

### Room Dimensions
- Set room `Name` parameter via `revit.set_parameter_value` with dimensions: `"15' x 16'"`
- Room tags may not be loaded — don't rely on them
- Text notes placed at room centroid are a reliable fallback

---

## Model Scan Rules

### Story Detection
- Do NOT rely on level count to detect `is_two_story`
- A project can have 4 levels (roof levels) but be single-story living
- Check if rooms exist on Level 2 with area > 0 to confirm two-story

### Elevation View IDs
- `list_sheets` returns sheet elements — the A105/A106 IDs are SHEETS, not the views inside them
- To find the actual elevation views (Left, Right, Front, Back):
  - Query viewports on sheets using `revit.get_parameter_value` with `View Name` and `Sheet Number`
  - Or search `list_views` for views named `Left`, `Right`, `Front`, `Back`

### Study Set Sheet Inventory (per project)
Always check what sheets exist before creating:
- `A100` — Cover Sheet (renderings) — usually exists
- `A100.1` — Interior renders — **may not exist** (skip if not present)
- `A100.3` / `A100.4` — 3D Views / Cuts — usually need to be created
- `A101.1` — Floor Plan F1 — usually exists
- `A101.2` — Floor Plan F2 — **only add if two-story**
- `A105` — Elevations Sides — usually exists
- `A106` — Elevations Front/Back — usually exists
- `A111` — Upsell page — always generate with Python

---

## Build & Deploy Rules

### Revit 2025 Target
Always pass `-p:RevitVersion=2025` to dotnet build:
```
dotnet build packages/revit-bridge-addin/RevitBridge.csproj -c Release -p:RevitVersion=2025
```
Without it, builds to `bin/Release/2024/net48/` — WRONG target.

### DLL Deploy
- File at `C:\ProgramData\RevitMCP\bin\RevitBridge.dll` is read-only
- Must run as admin CMD to copy
- Close Revit BEFORE copying (sharing violation otherwise)
- Use: `xcopy /Y <source> C:\ProgramData\RevitMCP\bin\`
- Verify with md5sum before and after — if same hash, build didn't produce new output

### Incremental Build Cache
If md5sum doesn't change after build, delete the cache and force full recompile:
```bash
rm -rf packages/revit-bridge-addin/bin packages/revit-bridge-addin/obj
dotnet build packages/revit-bridge-addin/RevitBridge.csproj -c Release -p:RevitVersion=2025
```

---

## Study Set Workflow Checklist

For each new project:

1. **Save As** from full construction set → create study set copy
2. **Scan**: `python3 run.py scan`
3. **Check title block name**: query `revit.list_families` for Title Blocks category
4. **Check existing sheets**: note what already exists vs what needs creating
5. **Delete full-set annotations from elevation views**: Door Tags, Window Tags, Dimensions
6. **Create 3D view sheets** (A100.3, A100.4) with correct titleblock_name
7. **Create 3D views** and place on sheets — user positions camera
8. **Add room dimension labels**: scan rooms > 100 SF, set Name parameter to "W' x D'"
9. **Add elevation height callouts**: text notes for overall height
10. **Generate A111**: `generate_a111(project_name, full_sheet_count, output_path)`
11. **Export PDF**: `python3 run.py study-set-export`

---

## Changing Fonts / Text Type Parameters

`set_type_parameter` requires `type_id` NOT `element_id`. Get the type ID from `get_type_parameters` result field `type_id`.

```python
# CORRECT way to change font on all text types:
notes = rc.call('revit.list_elements_by_category', {'category': 'Text Notes'})
seen_type_ids = {}
for n in notes['result']['elements']:
    type_name = n.get('type', '')
    if type_name not in seen_type_ids:
        r2 = rc.call('revit.get_type_parameters', {'element_id': n['id']})
        type_id = r2.get('result', {}).get('type_id')
        if type_id:
            seen_type_ids[type_name] = type_id

for tname, type_id in seen_type_ids.items():
    rc.call('revit.set_type_parameter', {
        'type_id': type_id,          # <-- type_id, not element_id
        'parameter_name': 'Text Font',
        'value': 'Arial Narrow',
    })
```

Same pattern works for any type parameter: Bold, Italic, Text Size, etc.

---

## Known Bridge Gaps (TODO)

| Feature | Status | Notes |
|---|---|---|
| `revit.get_view_origin` | ❌ Missing | Need for elevation dimension placement |
| `revit.set_category_visibility` | ❌ Missing | Currently a no-op, need real implementation |
| `revit.create_height_dimension` | ⚠️ Broken | `HostObjectUtils` doesn't work for walls; needs rethink |
| Camera orientation for 3D views | ❌ Missing | `revit.set_3d_view_orientation` not implemented |
| Duplicate view | ❌ Missing | `revit.duplicate_view` not in bridge |

---

## ⚠️ CRITICAL: Never Delete Annotations Project-Wide

When cleaning up elevation views, NEVER delete by category project-wide.
Dimensions and text notes exist in FLOOR PLANS too.

**WRONG:**
```python
# This deletes from ALL views including floor plans
r = rc.call('revit.list_elements_by_category', {'category': 'Dimensions'})
for e in elems: rc.call('revit.delete_element', ...)
```

**RIGHT (future fix):** Filter by view before deleting — need `revit.get_view_origin` 
and view-specific element queries. Until then, have user manually delete elevation 
annotations via Revit UI (VG → Annotations → uncheck), or accept that deletion 
will be project-wide and recreate floor plan text notes afterward.

Floor plan text notes to recreate if deleted:
- Room dimension labels: query rooms from project_state.json, recreate via create_text_note
- Other annotations: must be re-added manually from full set reference

---

## Bridge Health Endpoint Shows Stale Document
`health_check()` and `/health` endpoint can show old document name when switching files.
Always verify with `revit.get_document_info` — that's the reliable check:
```python
r = rc.call('revit.get_document_info', {})
print(r['result']['title'])  # actual active doc
```

---

## Floor Plan View for Text Notes
The view placed on A101.1 is NOT always "Level 1.0 Simple".
Always find the correct floor plan view dynamically:
```python
# Find the simple/clean floor plan view on A101.1
result = rc.call('revit.list_sheets', {})
# Get viewport's view by querying viewport elements with Sheet Number = A101.1
# Then get that view's ID and use it for text note placement
```
Hardcoding view ID 1306933 will break on next project.

---

## Study Set Workflow Summary (what actually worked on Allen)
1. scan → get room sizes + bounding boxes
2. list_sheets → find existing sheets, note which are missing
3. list_families → get titleblock_name (don't hardcode)
4. create_sheet with titleblock_name → creates real sheets
3D views: create_3d_view → place on sheets → user positions camera
5. delete Door Tags, Window Tags, Dimensions (project-wide — be aware floor plan loses dims too)
6. set room Name params to "W' x D'" via set_parameter_value
7. create_text_note on the correct floor plan view for room labels
8. generate_a111 → A111 upsell page PDF
9. Manual: user adds elevation dimensions + exports PDF
