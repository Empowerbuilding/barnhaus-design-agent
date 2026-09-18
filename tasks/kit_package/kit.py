"""
kit.py — kit_package orchestrator.

Two entry points:
  run_from_geometry(geo_dict_or_path)  — offline: geometry JSON -> BOM outputs
  run_live(project_name)               — extract from open Revit model, then run

Outputs land in ./kit_output/<project>/: kit_bom.txt / .csv / .json
"""

import datetime
import json
import os

from . import framing, trusses, bom


def _normalize_roof(roof: dict) -> dict:
    """Effective-span correction: a bbox lies on L/cross-gable masses.
    If a mass fills <80% of its bbox, its true average span ≈ plan/ridge
    (Titan: 71x71 bbox mass → 2485 sqft → effective span 35 ft, not 71).
    Governing roof span = max effective span across masses."""
    masses = roof.get("masses") or []
    if not masses:
        return roof
    eff_max = 0.0
    for m in masses:
        bspan, ridge = float(m["span_ft"]), float(m["ridge_ft"])
        area = float(m.get("plan_area_sqft") or 0.0)
        fill = area / (bspan * ridge) if bspan * ridge > 0 else 1.0
        eff = area / ridge if (area > 0 and ridge > 0 and fill < 0.8) else bspan
        m["effective_span_ft"] = round(eff, 1)
        eff_max = max(eff_max, eff)
    roof = dict(roof)
    roof["bbox_span_ft"] = roof.get("span_ft")
    roof["span_ft"] = round(eff_max, 1)
    return roof


def run_from_geometry(geo, out_dir: str | None = None) -> dict:
    if isinstance(geo, str):
        with open(geo) as f:
            geo = json.load(f)

    geo = dict(geo)
    geo["roof"] = _normalize_roof(geo.get("roof", {}))

    wall_lf, wall_flags = framing.frame_walls(geo["walls"])
    truss_lf, plates, truss_flags = trusses.truss_package(geo["roof"])

    # Hot-rolled allowance when long-span flag trips (ASF Allen precedent:
    # ~122 LF S7x15.3 on a 46 ft span / 97 ft ridge building ≈ 1.25 x ridge)
    hot_lf = 0.0
    roof = geo.get("roof", {})
    all_flags = wall_flags + truss_flags
    if any("hot-rolled" in f for f in all_flags):
        # Scale allowance to the FLAGGED masses only (not total ridge —
        # Titan run 2 over-allowed 502 LF by using the 402 ft ridge sum)
        masses = roof.get("masses") or []
        if masses:
            flagged_ridge = sum(float(m["ridge_ft"]) for m in masses
                                if float(m.get("effective_span_ft", m["span_ft"])) > 40.0)
            basis = flagged_ridge if flagged_ridge > 0 else max(
                (float(m["ridge_ft"]) for m in masses), default=0.0)
        else:
            basis = float(roof.get("ridge_length_ft", 0.0))
        hot_lf = 1.25 * basis
        if hot_lf > 0:
            all_flags.append(
                f"hot-rolled allowance added: {hot_lf:.0f} LF {bom.HOT_ROLLED_PROFILE} "
                "(estimate — PE to size actual beams/headers)")

    meta = {
        "project": geo.get("project", ""),
        "model": geo.get("model", ""),
        "date": geo.get("date", datetime.date.today().isoformat()),
    }
    result = bom.build_bom(wall_lf, truss_lf, plates,
                           all_flags, meta, hot_rolled_lf=hot_lf)

    from . import judgment
    result["confidence"] = judgment.assess(geo, all_flags)

    stem = (meta["project"] or "project").replace(" ", "_").lower()
    out_dir = out_dir or os.path.join("kit_output", stem)
    paths = bom.save_all(result, out_dir)
    print(bom.render_text(result))  # includes confidence section
    print("Saved:", *paths, sep="\n  ")
    return result


def run_live(project_name: str = "", out_dir: str | None = None) -> dict:
    from . import extract
    geo = extract.extract(project_name)
    stem = (project_name or "project").replace(" ", "_").lower()
    gdir = out_dir or os.path.join("kit_output", stem)
    os.makedirs(gdir, exist_ok=True)
    gpath = os.path.join(gdir, "geometry.json")
    with open(gpath, "w") as f:
        json.dump(geo, f, indent=2)
    print(f"geometry snapshot: {gpath}")
    return run_from_geometry(geo, out_dir=gdir)
