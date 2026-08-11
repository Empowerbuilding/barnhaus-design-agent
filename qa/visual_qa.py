"""
visual_qa.py — High-res sheet export + tiling for vision QA.

Problem: a 24x36 sheet exported at 1500px is ~42 DPI — dimension text and
4x4 HSS column symbols become 2-4 pixel blobs. Vision models also downscale
large images internally, so one giant export doesn't help either.

Solution: export ONCE at high resolution, then slice into overlapping tiles
sized for what vision models can actually resolve (~1500px each). The agent
inspects the overview + each tile.

Usage:
    python3 run.py export-tiles <view_id> [out_dir]
      → exports at 6000px, writes overview.png + tile_r{row}c{col}.png
"""

import os
from core import revit_client as rc

EXPORT_RES   = 6000   # px, larger dimension — ~167 DPI on a 36" sheet
TILE_TARGET  = 1500   # px per tile edge (sweet spot for vision models)
OVERLAP      = 200    # px overlap so nothing is lost on tile seams
OVERVIEW_RES = 2000   # downscaled full-sheet overview

TILE_QA_PROMPT = """You are inspecting ONE TILE of a residential construction sheet
(steel-frame custom home). This tile is a crop — elements cut off at tile edges are
NORMAL, do not report them. Report ONLY clear quality problems visible within the tile:

1. text_overlap — text/dimensions/tags overlapping each other or drawn through geometry
   so they are hard to read
2. illegible — text that is garbled, colliding, or unreadable (NOT text cut by tile edge)
3. bad_annotation — grid lines running through grid-bubble letters, leaders pointing at
   nothing, tags detached from their element, empty tags (?? or blank)
4. drafting_glitch — floating/orphaned elements, broken linework, hatch spilling outside
   boundaries, duplicated overlapping text
5. layout — views/schedules colliding with the title block or bleeding off the sheet

Respond with ONLY a JSON array (no prose). Each finding:
{"type": "<category>", "severity": "error|warning", "description": "<specific, mention
the text/values involved>", "location": "<where in this tile, e.g. top-left>"}
If the tile is clean, respond with []"""

OVERVIEW_QA_PROMPT = """This is a full sheet overview from a residential construction set
(downscaled — small text is expected to be unreadable, do NOT report illegible text).
Assess ONLY sheet-level layout: views placed crooked or colliding, huge empty regions on
a sheet that should be full, schedule/view overlapping the title block, missing title
block fields (blank sheet name/number), duplicated views.
Respond with ONLY a JSON array like:
[{"type": "layout", "severity": "error|warning", "description": "...", "location": "..."}]
If clean, respond with []"""


def export_tiles(view_id: int, out_dir: str = "exports") -> dict:
    """Export a view/sheet at high res and slice into vision-ready tiles."""
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)

    print(f"🖼️  Exporting view {view_id} at {EXPORT_RES}px...")
    full_path = os.path.join(out_dir, f"full_{view_id}.png")
    saved = rc.save_view_image(view_id, full_path, resolution=EXPORT_RES)
    if not saved:
        return {"error": "export failed"}

    im = Image.open(full_path)
    w, h = im.size
    print(f"   Full export: {w}x{h}")

    # Overview (whole sheet, readable layout)
    overview_path = os.path.join(out_dir, f"overview_{view_id}.png")
    scale = OVERVIEW_RES / max(w, h)
    im.resize((int(w * scale), int(h * scale)), Image.LANCZOS).save(overview_path)

    # Tile grid
    step = TILE_TARGET - OVERLAP
    cols = max(1, (w - OVERLAP + step - 1) // step)
    rows = max(1, (h - OVERLAP + step - 1) // step)

    tiles = []
    for r in range(rows):
        for c in range(cols):
            x0 = min(c * step, max(0, w - TILE_TARGET))
            y0 = min(r * step, max(0, h - TILE_TARGET))
            x1 = min(x0 + TILE_TARGET, w)
            y1 = min(y0 + TILE_TARGET, h)
            tile_path = os.path.join(out_dir, f"tile_{view_id}_r{r}c{c}.png")
            im.crop((x0, y0, x1, y1)).save(tile_path)
            tiles.append({"path": tile_path, "row": r, "col": c,
                          "region": [x0, y0, x1, y1]})

    # Remove the giant original — tiles + overview carry everything
    os.remove(full_path)

    print(f"   ✅ {len(tiles)} tiles ({rows}x{cols}) + overview → {out_dir}/")
    print(f"   Inspect: overview first (layout), then each tile for text/symbols.")
    return {"view_id": view_id, "overview": overview_path,
            "grid": f"{rows}x{cols}", "tiles": tiles}


# ────────────────────────────────────────────────────────────
# BATCH VISUAL QA — Phase 3
# ────────────────────────────────────────────────────────────

def run_visual_qa(sheet_filter: str = None, max_sheets: int = None) -> dict:
    """
    Export every populated sheet → tiles → Gemini vision pass per tile →
    aggregated report. The agent only reads the final report, not 300 tiles.

    sheet_filter: substring match on sheet number or name (e.g. "A104", "dimension")
    """
    import shutil
    from qa.gemini_vision import ask_image_json

    sheets = rc.list_sheets()
    populated = [s for s in sheets if s.get("viewport_count", 0) > 0]
    if sheet_filter:
        f = sheet_filter.lower()
        populated = [s for s in populated
                     if f in s.get("sheet_number", "").lower()
                     or f in s.get("sheet_name", "").lower()]
    if max_sheets:
        populated = populated[:max_sheets]

    if not populated:
        print("   No matching populated sheets.")
        return {"sheets": []}

    print(f"\n🔎 Visual QA — {len(populated)} sheet(s): "
          f"{', '.join(s['sheet_number'] for s in populated)}")

    report = {"sheets": [], "total_findings": 0}

    for s in populated:
        num, name, sid = s["sheet_number"], s["sheet_name"], s["id"]
        print(f"\n── {num} — {name} ──")
        work_dir = f"exports/vqa_{num.replace('.', '_')}"
        tiled = export_tiles(sid, work_dir)
        if tiled.get("error"):
            report["sheets"].append({"sheet": num, "error": tiled["error"]})
            continue

        findings = []

        # Overview pass — sheet-level layout
        try:
            ov = ask_image_json(tiled["overview"], OVERVIEW_QA_PROMPT)
            if isinstance(ov, list):
                for fnd in ov:
                    fnd["tile"] = "overview"
                    findings.append(fnd)
        except Exception as e:
            print(f"   ⚠️  overview pass failed: {e}")

        # Tile passes — detail
        for t in tiled["tiles"]:
            try:
                res = ask_image_json(t["path"], TILE_QA_PROMPT)
            except Exception as e:
                print(f"   ⚠️  tile r{t['row']}c{t['col']} failed: {e}")
                continue
            if isinstance(res, list):
                for fnd in res:
                    if not isinstance(fnd, dict):
                        continue
                    fnd["tile"] = f"r{t['row']}c{t['col']}"
                    fnd["region_px"] = t["region"]
                    findings.append(fnd)
            elif isinstance(res, dict) and res.get("parse_error"):
                print(f"   ⚠️  tile r{t['row']}c{t['col']}: unparseable response")

        # Dedupe near-identical findings from overlapping tiles
        deduped, seen = [], set()
        for fnd in findings:
            key = (fnd.get("type"), (fnd.get("description") or "")[:60].lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(fnd)

        errors = [f for f in deduped if f.get("severity") == "error"]
        print(f"   {len(deduped)} findings ({len(errors)} errors)")
        for fnd in deduped[:12]:
            icon = "❌" if fnd.get("severity") == "error" else "⚠️ "
            print(f"   {icon} [{fnd.get('type')}] {fnd.get('description','')[:110]}")

        report["sheets"].append({"sheet": num, "name": name,
                                 "finding_count": len(deduped), "findings": deduped})
        report["total_findings"] += len(deduped)

        # Clean tiles after analysis — keep only the overview per sheet
        for t in tiled["tiles"]:
            try: os.remove(t["path"])
            except OSError: pass

    with open("visual_qa_report.json", "w") as f:
        import json
        json.dump(report, f, indent=2)

    print(f"\n══ Visual QA complete — {report['total_findings']} findings "
          f"across {len(report['sheets'])} sheets ══")
    print("💾 visual_qa_report.json saved")
    return report
