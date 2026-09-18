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

    meta = {
        "project": geo.get("project", ""),
        "model": geo.get("model", ""),
        "date": geo.get("date", datetime.date.today().isoformat()),
    }
    result = bom.build_bom(wall_lf, truss_lf, plates,
                           wall_flags + truss_flags, meta)

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
