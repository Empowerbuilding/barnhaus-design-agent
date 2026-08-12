"""
visual_qa.py — High-res sheet export + tiling for vision QA.

Problem: a 24x36 sheet exported at 1500px is ~42 DPI — dimension text and
4x4 HSS column symbols become 2-4 pixel blobs. Vision models also downscale
large images internally, so one giant export doesn't help either.

Solution: export ONCE at high resolution, then slice into overlapping tiles
sized for what vision models can actually resolve (~1500px each). The agent
inspects the overview + each tile.

Phase 1 speed upgrades (2026-08):
  - Tile vision calls run in PARALLEL (default 5 workers)
  - Blank tiles (>98.5% white) are skipped — no vision call
  - Unchanged sheets (pixel hash vs last report) reuse previous findings
  - --include / --exclude scoping so scrap sheets never enter the queue
  - --tile-size to experiment with larger tiles (fewer calls)

Usage:
    python3 run.py export-tiles <view_id> [out_dir]
      → exports at 6000px, writes overview.png + tile_r{row}c{col}.png
    python3 run.py qa-visual [filter] [--max N] [--fresh]
        [--include A1] [--exclude scrap,temp] [--tile-size 2000] [--workers 5]
"""

import hashlib
import os
from core import revit_client as rc

EXPORT_RES   = 6000   # px, larger dimension — ~167 DPI on a 36" sheet
TILE_TARGET  = 1500   # px per tile edge (sweet spot for vision models)
OVERLAP      = 200    # px overlap so nothing is lost on tile seams
OVERVIEW_RES = 2000   # downscaled full-sheet overview
MAX_WORKERS  = 5      # concurrent Gemini calls
BLANK_THRESH = 0.985  # fraction of near-white pixels → tile skipped

TILE_QA_PROMPT = """You are inspecting ONE TILE of a residential construction sheet
(steel-frame custom home). This tile is a crop — elements cut off at tile edges are
NORMAL, do not report them. Report ONLY clear quality problems visible within the tile:

1. text_overlap — text/dimensions/tags ACTUALLY OBSCURED or genuinely hard to read.
   Text that is merely near, touching, or crossing light linework but remains fully
   legible is NOT a finding — construction drawings routinely have text over geometry
2. illegible — text that is garbled, colliding, or unreadable (NOT text cut by tile edge)
3. bad_annotation — grid lines running through grid-bubble letters, leaders pointing at
   nothing, tags detached from their element, empty tags (?? or blank)
4. drafting_glitch — floating/orphaned elements, broken linework, hatch spilling outside
   boundaries, duplicated overlapping text
5. layout — views/schedules colliding with the title block or bleeding off the sheet

Respond with ONLY a JSON array (no prose). Each finding:
{"type": "<category>", "severity": "error|warning", "description": "<specific, mention
the text/values involved>", "location": "<where in this tile, e.g. top-left>"}
Be conservative: report only what a reviewing architect would mark up. If unsure
whether something is a real problem, do NOT report it.
If the tile is clean, respond with []"""

OVERVIEW_QA_PROMPT = """This is a full sheet overview from a residential construction set
(downscaled — small text is expected to be unreadable, do NOT report illegible text).
Assess ONLY sheet-level layout: views placed crooked or colliding, huge empty regions on
a sheet that should be full, schedule/view overlapping the title block, missing title
block fields (blank sheet name/number), duplicated views.
Respond with ONLY a JSON array like:
[{"type": "layout", "severity": "error|warning", "description": "...", "location": "..."}]
If clean, respond with []"""


def _pixel_hash(im) -> str:
    """Content hash of an image, robust to PNG encoder differences.
    Any real pixel change (moved wall, edited text) flips the hash."""
    small = im.convert("L").resize((512, 512))
    return hashlib.sha256(small.tobytes()).hexdigest()


def _is_blank(tile_im) -> bool:
    """True if the tile is essentially empty white space (margins, dead areas)."""
    g = tile_im.convert("L")
    hist = g.histogram()
    total = g.size[0] * g.size[1]
    if not total:
        return True
    near_white = sum(hist[245:])
    return (near_white / total) > BLANK_THRESH


def export_tiles(view_id: int, out_dir: str = "exports",
                 tile_target: int = None) -> dict:
    """Export a view/sheet at high res and slice into vision-ready tiles.
    Blank tiles are still listed but flagged blank=True (no file written)."""
    from PIL import Image

    tile_target = tile_target or TILE_TARGET
    os.makedirs(out_dir, exist_ok=True)

    print(f"🖼️  Exporting view {view_id} at {EXPORT_RES}px...")
    full_path = os.path.join(out_dir, f"full_{view_id}.png")
    saved = rc.save_view_image(view_id, full_path, resolution=EXPORT_RES)
    if not saved:
        return {"error": "export failed"}

    im = Image.open(full_path)
    w, h = im.size
    print(f"   Full export: {w}x{h}")

    pixel_hash = _pixel_hash(im)

    # Overview (whole sheet, readable layout)
    overview_path = os.path.join(out_dir, f"overview_{view_id}.png")
    scale = OVERVIEW_RES / max(w, h)
    im.resize((int(w * scale), int(h * scale)), Image.LANCZOS).save(overview_path)

    # Tile grid
    step = tile_target - OVERLAP
    cols = max(1, (w - OVERLAP + step - 1) // step)
    rows = max(1, (h - OVERLAP + step - 1) // step)

    tiles, blanks = [], 0
    for r in range(rows):
        for c in range(cols):
            x0 = min(c * step, max(0, w - tile_target))
            y0 = min(r * step, max(0, h - tile_target))
            x1 = min(x0 + tile_target, w)
            y1 = min(y0 + tile_target, h)
            crop = im.crop((x0, y0, x1, y1))
            entry = {"row": r, "col": c, "region": [x0, y0, x1, y1]}
            if _is_blank(crop):
                blanks += 1
                entry["blank"] = True
                entry["path"] = None
            else:
                tile_path = os.path.join(out_dir, f"tile_{view_id}_r{r}c{c}.png")
                crop.save(tile_path)
                entry["path"] = tile_path
            tiles.append(entry)

    # Remove the giant original — tiles + overview carry everything
    os.remove(full_path)

    live = len(tiles) - blanks
    print(f"   ✅ {rows}x{cols} grid — {live} tiles to inspect, {blanks} blank skipped → {out_dir}/")
    return {"view_id": view_id, "overview": overview_path,
            "grid": f"{rows}x{cols}", "tiles": tiles,
            "blank_count": blanks, "pixel_hash": pixel_hash}


# ────────────────────────────────────────────────────────────
# BATCH VISUAL QA — Phase 3 (parallel since Phase 1 upgrades)
# ────────────────────────────────────────────────────────────

REPORT_PATH = "visual_qa_report.json"


def _save_report(report: dict):
    import json
    tmp = REPORT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(report, f, indent=2)
    os.replace(tmp, REPORT_PATH)


def _analyze_sheet(tiled: dict, workers: int) -> list:
    """Run overview + tile vision passes concurrently. Returns findings list."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from qa.gemini_vision import ask_image_json

    jobs = [("overview", tiled["overview"], OVERVIEW_QA_PROMPT, None)]
    for t in tiled["tiles"]:
        if t.get("blank") or not t.get("path"):
            continue
        jobs.append((f"r{t['row']}c{t['col']}", t["path"], TILE_QA_PROMPT, t["region"]))

    findings = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(ask_image_json, path, prompt): (label, region)
                for label, path, prompt, region in jobs}
        for fut in as_completed(futs):
            label, region = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                print(f"   ⚠️  {label} failed: {e}")
                continue
            if isinstance(res, list):
                for fnd in res:
                    if not isinstance(fnd, dict):
                        continue
                    fnd["tile"] = label
                    if region:
                        fnd["region_px"] = region
                    findings.append(fnd)
            elif isinstance(res, dict) and res.get("parse_error"):
                print(f"   ⚠️  {label}: unparseable response")
    return findings


def run_visual_qa(sheet_filter: str = None, max_sheets: int = None,
                  fresh: bool = False, include: str = None,
                  exclude: list = None, tile_size: int = None,
                  workers: int = None) -> dict:
    """
    Export every populated sheet → tiles → PARALLEL Gemini vision pass →
    aggregated report. The agent only reads the final report, not 300 tiles.

    Speed features:
      - Sheets whose pixels haven't changed since the last report reuse
        previous findings (no vision calls). Use fresh=True to force re-analysis.
      - Blank tiles are never sent to the vision model.
      - include/exclude scope the sheet set (substring match on number/name).

    sheet_filter: substring match on sheet number or name (e.g. "A104")
    """
    import json

    workers = workers or MAX_WORKERS

    sheets = rc.list_sheets()
    populated = [s for s in sheets if s.get("viewport_count", 0) > 0]

    def _match(s, needle):
        n = needle.lower()
        return (n in s.get("sheet_number", "").lower()
                or n in s.get("sheet_name", "").lower())

    if sheet_filter:
        populated = [s for s in populated if _match(s, sheet_filter)]
    if include:
        populated = [s for s in populated if _match(s, include)]
    if exclude:
        for ex_kw in exclude:
            populated = [s for s in populated if not _match(s, ex_kw)]
    if max_sheets:
        populated = populated[:max_sheets]

    if not populated:
        print("   No matching populated sheets.")
        return {"sheets": []}

    # Previous report — for hash-based skip (and crash resume)
    prev_by_sheet = {}
    if not fresh and os.path.exists(REPORT_PATH):
        try:
            prev = json.load(open(REPORT_PATH))
            prev_by_sheet = {s.get("sheet"): s for s in prev.get("sheets", [])
                             if not s.get("error")}
        except (json.JSONDecodeError, OSError):
            pass

    report = {"sheets": [], "total_findings": 0}

    print(f"\n🔎 Visual QA — {len(populated)} sheet(s): "
          f"{', '.join(s['sheet_number'] for s in populated)}"
          f"  [{workers} workers]")

    for s in populated:
        num, name, sid = s["sheet_number"], s["sheet_name"], s["id"]
        print(f"\n── {num} — {name} ──")
        work_dir = f"exports/vqa_{num.replace('.', '_')}"
        tiled = export_tiles(sid, work_dir, tile_target=tile_size)
        if tiled.get("error"):
            report["sheets"].append({"sheet": num, "error": tiled["error"]})
            _save_report(report)
            continue

        # Hash skip — sheet pixels unchanged since last report → reuse findings
        prev_entry = prev_by_sheet.get(num)
        if (prev_entry and prev_entry.get("export_hash")
                and prev_entry["export_hash"] == tiled["pixel_hash"]):
            print(f"   ⏭️  unchanged since last report — reusing "
                  f"{prev_entry.get('finding_count', 0)} finding(s), no vision calls")
            report["sheets"].append(prev_entry)
            report["total_findings"] += prev_entry.get("finding_count", 0)
            _save_report(report)
            for t in tiled["tiles"]:
                if t.get("path"):
                    try: os.remove(t["path"])
                    except OSError: pass
            continue

        findings = _analyze_sheet(tiled, workers)

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

        # Annotated crops for the punch list — must happen BEFORE tile cleanup
        if deduped:
            try:
                from qa.annotate import annotate_sheet_findings
                n_crops = annotate_sheet_findings(tiled, deduped, num)
                if n_crops:
                    print(f"   🖼️  {n_crops} annotated crop(s) → exports/findings/")
            except Exception as e:
                print(f"   ⚠️  annotation skipped: {e}")

        report["sheets"].append({"sheet": num, "name": name,
                                 "export_hash": tiled["pixel_hash"],
                                 "finding_count": len(deduped),
                                 "findings": deduped})
        report["total_findings"] += len(deduped)

        # Persist after EVERY sheet — a killed run loses nothing
        _save_report(report)

        # Clean tiles after analysis — keep only the overview per sheet
        for t in tiled["tiles"]:
            if t.get("path"):
                try: os.remove(t["path"])
                except OSError: pass

    _save_report(report)

    print(f"\n══ Visual QA complete — {report['total_findings']} findings "
          f"across {len(report['sheets'])} sheets ══")
    print("💾 visual_qa_report.json saved")
    return report
