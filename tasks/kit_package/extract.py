"""
extract.py — Pull kit geometry from the open Revit model via the bridge.

Produces geometry JSON consumed by kit.py:
{
  "project": "...", "model": "...",
  "walls": [{id, length_ft, height_ft, function, openings:[{width_ft, height_ft, kind}]}],
  "roof":  {span_ft, ridge_length_ft, pitch_rise_per_12, gable_ends}
}

Uses ONLY existing bridge commands (no DLL changes needed):
  - list_elements_by_category Walls / Doors / Windows / Roofs
  - get_parameter_value (Length, Unconnected Height, Width, etc.)
  - get_element_bounding_box (roof span/ridge estimation fallback)

Wall classification: exterior if wall type/function says so, else interior.
Opening->wall assignment: v1 assigns by host id when the bridge exposes it,
else falls back to nearest-wall-by-bounding-box.
"""

import datetime
import json
from core import revit_client as rc


def _param(eid, name):
    try:
        return rc.get_parameter_value(eid, name)
    except Exception:
        return None


def _is_exterior(wall: dict) -> bool:
    blob = " ".join(str(wall.get(k, "")) for k in ("type", "type_name", "family_name", "name")).lower()
    if "ext" in blob:
        return True
    if "int" in blob:
        return False
    fn = _param(wall.get("id"), "Function")
    if fn is not None:
        # Revit WallFunction enum: Interior=0, Exterior=1 (Foundation=2, ...)
        return str(fn).lower().startswith("ext") or str(fn) == "1"
    return True  # conservative default: heavier framing


def extract(project_name: str = "", pitch_default: float = 4.0) -> dict:
    walls_raw = rc.get_all_walls()
    doors_raw = rc.get_all_doors()
    windows_raw = rc.get_all_windows()

    walls = []
    wall_index = {}
    for w in walls_raw:
        wid = w.get("id")
        length = w.get("length_ft") or _param(wid, "Length")
        height = w.get("height_ft") or _param(wid, "Unconnected Height")
        if not length or not height:
            continue
        entry = {
            "id": wid,
            "length_ft": float(length),
            "height_ft": float(height),
            "function": "exterior" if _is_exterior(w) else "interior",
            "openings": [],
        }
        walls.append(entry)
        wall_index[wid] = entry

    # Bounding-box cache: at most ONE bridge call per element, ever.
    # (v1 bug: nearest-wall fallback re-fetched every wall bbox per opening
    # -> O(openings x walls) tunnel calls -> 10-min agent timeout. Fixed.)
    _bb_cache: dict = {}

    def _center(eid):
        if eid in _bb_cache:
            return _bb_cache[eid]
        try:
            bb = rc.get_element_bounding_box(eid)
            c = ((bb["min"]["x"] + bb["max"]["x"]) / 2,
                 (bb["min"]["y"] + bb["max"]["y"]) / 2)
        except Exception:
            c = None
        _bb_cache[eid] = c
        return c

    def _type_param(eid, names):
        """Width/Height usually live on the TYPE for door/window families."""
        try:
            tp = rc.get_type_param_map(eid)
        except Exception:
            return None
        if not tp:
            return None
        for n in names:
            v = tp.get(n)
            if v not in (None, "", 0):
                return v
        return None

    skipped = []

    def _attach(elements, kind):
        total = len(elements)
        for i, e in enumerate(elements):
            eid = e.get("id")
            width = (e.get("width_ft") or _param(eid, "Width") or _param(eid, "Rough Width")
                     or _type_param(eid, ["Width", "Rough Width"]))
            height = (e.get("height_ft") or _param(eid, "Height") or _param(eid, "Rough Height")
                      or _type_param(eid, ["Height", "Rough Height"]))
            host = e.get("host_id") or e.get("host")
            target = wall_index.get(host)
            if target is None and walls:
                c = _center(eid)
                if c is not None:
                    best, best_d = None, 1e18
                    for wl in walls:
                        wc = _center(wl["id"])
                        if wc is None:
                            continue
                        d = (c[0] - wc[0]) ** 2 + (c[1] - wc[1]) ** 2
                        if d < best_d:
                            best, best_d = wl, d
                    target = best
                else:
                    target = walls[0]
            if target is not None and width:
                target["openings"].append({
                    "width_ft": float(width),
                    "height_ft": float(height or 6.8),
                    "kind": kind,
                })
            else:
                skipped.append((kind, eid))
            if (i + 1) % 10 == 0 or i + 1 == total:
                print(f"  {kind}s: {i+1}/{total}", flush=True)

    print(f"extracting: {len(walls)} walls, {len(doors_raw)} doors, {len(windows_raw)} windows", flush=True)
    _attach(doors_raw, "door")
    _attach(windows_raw, "window")
    attached = sum(len(w["openings"]) for w in walls)
    print(f"openings attached: {attached}  skipped (no width resolved): {len(skipped)}", flush=True)
    if skipped:
        print(f"  skipped ids: {[s[1] for s in skipped][:20]}", flush=True)

    # Roofs: measure each roof mass separately (a global bbox lies badly on
    # L/T/cross-gable plans — Titan read 71x71 square). Prefer Revit's Area
    # parameter (true surface area) converted to plan area via slope.
    import math as _math
    roofs = rc.list_elements_by_category("Roofs")
    span, ridge = 0.0, 0.0
    plan_area = 0.0
    roof_masses = []
    for r in roofs:
        rid = r["id"]
        try:
            bb = rc.get_element_bounding_box(rid)
            dx = bb["max"]["x"] - bb["min"]["x"]
            dy = bb["max"]["y"] - bb["min"]["y"]
        except Exception:
            continue
        r_slope = _param(rid, "Slope")
        r_area = _param(rid, "Area")  # surface area, sqft
        mass_span, mass_ridge = min(dx, dy), max(dx, dy)
        if r_area:
            theta = _math.atan(float(r_slope)) if r_slope else 0.0
            mass_plan = float(r_area) * _math.cos(theta)
        else:
            mass_plan = dx * dy
        # skip trivial roof scraps (porch stubs under 100 sqft still count,
        # but sub-10 sqft crickets/eyebrows just add noise)
        if mass_plan < 10:
            continue
        plan_area += mass_plan
        span = max(span, mass_span)
        ridge += mass_ridge          # total truss-run length across masses
        roof_masses.append({"id": rid, "span_ft": round(mass_span, 1),
                            "ridge_ft": round(mass_ridge, 1),
                            "plan_area_sqft": round(mass_plan, 0),
                            "slope": r_slope})
    slope = roof_masses[0]["slope"] if roof_masses else None
    print(f"roof masses: {len(roof_masses)}, plan area {plan_area:.0f} sqft, "
          f"max span {span:.1f} ft", flush=True)

    geometry = {
        "project": project_name,
        "model": project_name,
        "date": datetime.date.today().isoformat(),
        "walls": walls,
        "roof": {
            "span_ft": round(span, 1),
            "ridge_length_ft": round(ridge, 1),
            "plan_area_sqft": round(plan_area, 0),
            "pitch_rise_per_12": float(slope) * 12 if slope else pitch_default,
            "gable_ends": 2,
            "masses": roof_masses,
        },
    }
    return geometry


def extract_to_file(path: str, project_name: str = "") -> str:
    geo = extract(project_name)
    with open(path, "w") as f:
        json.dump(geo, f, indent=2)
    print(f"geometry written: {path}  "
          f"({len(geo['walls'])} walls, roof span {geo['roof']['span_ft']} ft)")
    return path
