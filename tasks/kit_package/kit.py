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


def run_from_geometry(geo, out_dir: str | None = None) -> dict:
    if isinstance(geo, str):
        with open(geo) as f:
            geo = json.load(f)

    wall_lf, wall_flags = framing.frame_walls(geo["walls"])
    truss_lf, plates, truss_flags = trusses.truss_package(geo["roof"])

    # Hot-rolled allowance when long-span flag trips (ASF Allen precedent:
    # ~122 LF S7x15.3 on a 46 ft span / 97 ft ridge building ≈ 1.25 x ridge)
    hot_lf = 0.0
    roof = geo.get("roof", {})
    all_flags = wall_flags + truss_flags
    if any("hot-rolled" in f for f in all_flags):
        hot_lf = 1.25 * float(roof.get("ridge_length_ft", 0.0))
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

    stem = (meta["project"] or "project").replace(" ", "_").lower()
    out_dir = out_dir or os.path.join("kit_output", stem)
    paths = bom.save_all(result, out_dir)
    print(bom.render_text(result))
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
