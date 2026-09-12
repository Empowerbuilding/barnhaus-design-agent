"""
roof_builder.py — One-command roof creation with visual QA.

Usage (via run.py):
    python3 run.py roof 5:12 gable
    python3 run.py roof 5:12 gable --porch south,east --porch-depth 10
    python3 run.py roof 4:12 hip --overhang 2 --type '13" Roof No Gyp'

What it does:
  1. Reads exterior walls (type name contains "EXT"), computes the footprint rectangle
  2. Finds top-of-wall height and the right base level + offset
  3. Resolves the roof type (--type, or revit.list_types, or document default via reflection)
  4. Creates the main roof (gable/hip/flat) with overhang
  5. Optional wraparound porch roof: single side strip or L-shape over two adjacent
     sides, eave at porch level, outer edges slope-defining (clean hip miter)
  6. Exports a 3D check image ("BP Roof Check" view) for visual QA

Limits (v1): rectangular footprints; porch on 1 side or 2 adjacent sides.
"""

import sys
import os
from core.revit_client import call

CHECK_VIEW_NAME = "BP Roof Check"
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")


def _fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def _pts(pairs):
    return [{"x": x, "y": y, "z": 0} for x, y in pairs]


def parse_pitch(s):
    """'5:12' or '5/12' or '0.4167' -> rise/run float."""
    s = s.strip()
    for sep in (":", "/"):
        if sep in s:
            a, b = s.split(sep, 1)
            return float(a) / float(b)
    return float(s)


def get_exterior_walls():
    r = call("revit.list_elements_by_category", {"category": "Walls"})
    if not r["success"]:
        _fail(f"Can't list walls: {r['error']}")
    res = r["result"]
    els = res.get("elements") if isinstance(res, dict) else res
    ext = [w for w in els if "EXT" in (w.get("type") or "").upper()]
    if not ext:
        _fail("No exterior walls found (looking for wall type containing 'EXT').")
    return ext


def footprint_rect(ext_walls, min_len=20.0):
    """Main rectangle from the long exterior walls' centerline extents."""
    main = [w for w in ext_walls if (w.get("length_ft") or 0) >= min_len] or ext_walls
    xs, ys = [], []
    for w in main:
        xs += [w["start_x"], w["end_x"]]
        ys += [w["start_y"], w["end_y"]]
    return min(xs), max(xs), min(ys), max(ys), main


def wall_top(main_walls):
    top = 0.0
    for w in main_walls:
        i = call("revit.inspect_element", {"element_id": w["id"]})
        bb = (i.get("result") or {}).get("bounding_box") or {}
        top = max(top, bb.get("max_z") or 0)
    if top <= 0:
        _fail("Couldn't determine top of exterior walls.")
    return top


def get_levels():
    r = call("revit.list_levels", {})
    if not r["success"]:
        _fail(f"Can't list levels: {r['error']}")
    lv = r["result"]["levels"]
    return sorted(lv, key=lambda l: l["elevation_ft"])


def base_level_for(elev, levels):
    """Highest level at or below elev; returns (name, offset)."""
    best = levels[0]
    for l in levels:
        if l["elevation_ft"] <= elev + 0.001:
            best = l
    return best["name"], elev - best["elevation_ft"]


def resolve_roof_type(explicit=None):
    if explicit:
        return explicit, "explicit"
    r = call("revit.list_types", {"category": "Roofs"})
    if r["success"]:
        types = r["result"]["types"]
        if not types:
            _fail("No roof types in this project.")
        return types[0]["name"], f"list_types ({len(types)} available: {', '.join(t['name'] for t in types[:8])})"
    # old DLL fallback: document default roof type via reflection
    ext = get_exterior_walls()
    d = call("revit.reflect_get", {"target_id": str(ext[0]["id"]), "property_name": "Document"})
    if not d["success"]:
        _fail("Can't resolve roof type (no list_types, reflection failed). Pass --type.")
    tid = call("revit.invoke_method", {
        "class_name": "Document", "method_name": "GetDefaultElementTypeId",
        "target_id": d["result"]["id"], "arguments": ["RoofType"]})
    if not tid["success"]:
        _fail("Can't resolve default roof type. Pass --type.")
    i = call("revit.inspect_element", {"element_id": tid["result"]})
    name = (i.get("result") or {}).get("name")
    if not name:
        _fail("Can't read default roof type name. Pass --type.")
    return name, "document default (update bridge for list_types)"


def supports_slope_edges():
    """Probe: list_types exists in the same build that added slope_edges."""
    return call("revit.list_types", {"category": "Roofs"})["success"]


def create_main_roof(rect, top, levels, rt, pitch, style, overhang):
    x0, x1, y0, y1 = rect
    o = overhang
    level, offset = base_level_for(top, levels)
    r = call("revit.create_roof", {
        "boundary_points": _pts([(x0-o, y0-o), (x1+o, y0-o), (x1+o, y1+o), (x0-o, y1+o)]),
        "level": level, "roof_type": rt, "pitch": pitch, "slope_style": style,
    })
    if not r["success"]:
        _fail(f"Main roof failed: {r['error']}")
    rid = r["result"]["roof_id"]
    if abs(offset) > 0.001:
        s = call("revit.set_parameter_value", {
            "element_id": rid, "parameter_name": "Base Offset From Level", "value": offset})
        if not s["success"]:
            print(f"⚠️  Roof {rid} created but base offset failed: {s['error']}")
    return rid, level, offset


PORCH_GEOM = {
    # side(s) -> (polygon builder, outer slope edge indices)
    ("south",): lambda x0, x1, y0, y1, D: ([(x0, y0), (x1, y0), (x1, y0-D), (x0, y0-D)], [2]),
    ("north",): lambda x0, x1, y0, y1, D: ([(x1, y1), (x0, y1), (x0, y1+D), (x1, y1+D)], [2]),
    ("east",):  lambda x0, x1, y0, y1, D: ([(x1, y0), (x1, y1), (x1+D, y1), (x1+D, y0)], [2]),
    ("west",):  lambda x0, x1, y0, y1, D: ([(x0, y1), (x0, y0), (x0-D, y0), (x0-D, y1)], [2]),
    ("east", "south"): lambda x0, x1, y0, y1, D: (
        [(x0, y0), (x1, y0), (x1, y1), (x1+D, y1), (x1+D, y0-D), (x0, y0-D)], [3, 4]),
    ("east", "north"): lambda x0, x1, y0, y1, D: (
        [(x1, y0), (x1+D, y0), (x1+D, y1+D), (x0, y1+D), (x0, y1), (x1, y1)], [1, 2]),
    ("north", "west"): lambda x0, x1, y0, y1, D: (
        [(x1, y1), (x1, y1+D), (x0-D, y1+D), (x0-D, y0), (x0, y0), (x0, y1)], [2, 3]),
    ("south", "west"): lambda x0, x1, y0, y1, D: (
        [(x1, y0), (x1, y0-D), (x0-D, y0-D), (x0-D, y1), (x0, y1), (x0, y0)], [2, 3]),
}


def create_porch_roof(rect, sides, depth, level, rt, pitch, use_slope_edges):
    x0, x1, y0, y1 = rect
    key = tuple(sorted(sides))
    if key not in PORCH_GEOM:
        _fail(f"Porch sides {sides} not supported (1 side or 2 adjacent sides).")
    poly, slope_edges = PORCH_GEOM[key](x0, x1, y0, y1, depth)

    payload = {
        "boundary_points": _pts(poly), "level": level,
        "roof_type": rt, "pitch": pitch,
    }
    if use_slope_edges:
        payload["slope_style"] = "custom"
        payload["slope_edges"] = slope_edges
    else:
        payload["slope_style"] = "shed"
        payload["shed_low_edge"] = slope_edges[0]

    r = call("revit.create_roof", payload)
    if not r["success"]:
        _fail(f"Porch roof failed: {r['error']}")
    rid = r["result"]["roof_id"]

    # old-DLL workaround: mark remaining outer edges slope-defining via sketch params
    if not use_slope_edges and len(slope_edges) > 1:
        _fix_extra_slope_edges(rid, poly, slope_edges[1:], pitch)
    return rid


def _fix_extra_slope_edges(roof_id, poly, edge_idxs, pitch):
    i = call("revit.inspect_element", {"element_id": roof_id})
    deps = (i.get("result") or {}).get("dependents") or []
    lines = [d for d in deps if (d.get("class_name") or "").endswith("Line")]
    n = len(poly)
    for idx in edge_idxs:
        sx, sy = poly[idx]
        ex, ey = poly[(idx + 1) % n]
        for c in lines:
            ci = call("revit.inspect_element", {"element_id": c["id"]})
            loc = (ci.get("result") or {}).get("location") or {}
            pts_match = lambda ax, ay, bx, by: abs(ax-bx) < 0.01 and abs(ay-by) < 0.01
            s_ok = pts_match(loc.get("start_x", 9e9), loc.get("start_y", 9e9), sx, sy) or \
                   pts_match(loc.get("start_x", 9e9), loc.get("start_y", 9e9), ex, ey)
            e_ok = pts_match(loc.get("end_x", 9e9), loc.get("end_y", 9e9), sx, sy) or \
                   pts_match(loc.get("end_x", 9e9), loc.get("end_y", 9e9), ex, ey)
            if s_ok and e_ok:
                call("revit.set_parameter_value", {
                    "element_id": c["id"], "parameter_name": "Defines Roof Slope", "value": 1})
                call("revit.set_parameter_value", {
                    "element_id": c["id"], "parameter_name": "Slope", "value": pitch})
                break
        else:
            print(f"⚠️  Couldn't find sketch line for slope edge {idx} — check corner miter manually.")


def qa_image(rect, top, tag="roof"):
    """Ensure the check view exists, section-box it around the building, export."""
    x0, x1, y0, y1 = rect
    r = call("revit.list_views", {})
    view_id = None
    if r["success"]:
        for v in (r["result"].get("views") or []):
            if v.get("name") == CHECK_VIEW_NAME:
                view_id = v.get("id") or v.get("view_id")
                break
    if not view_id:
        c = call("revit.create_3d_view", {"name": CHECK_VIEW_NAME})
        if not c["success"]:
            print(f"⚠️  No QA image (couldn't make 3D view: {c['error']})")
            return None
        view_id = c["result"]["view_id"]

    # section box via universal bridge
    b = call("revit.invoke_method", {"class_name": "BoundingBoxXYZ", "method_name": "new", "arguments": []})
    if b["success"]:
        bref = b["result"]["id"]
        call("revit.reflect_set", {"target_id": bref, "property_name": "Min",
                                   "value": {"x": x0-20, "y": y0-20, "z": -3}})
        call("revit.reflect_set", {"target_id": bref, "property_name": "Max",
                                   "value": {"x": x1+20, "y": y1+20, "z": top+15}})
        call("revit.invoke_method", {"class_name": "View3D", "method_name": "SetSectionBox",
                                     "target_id": str(view_id),
                                     "arguments": [{"type": "reference", "id": bref}],
                                     "use_transaction": True})

    os.makedirs(EXPORT_DIR, exist_ok=True)
    out = os.path.join(EXPORT_DIR, f"{tag}_check.png")
    from core.revit_client import save_view_image
    try:
        save_view_image(int(view_id), out, resolution=3000)
        return out
    except Exception as e:
        print(f"⚠️  Image export failed: {e}")
        return None


def run_roof(args):
    if len(args) < 2:
        print("Usage: run.py roof <pitch e.g. 5:12> <gable|hip|flat> "
              "[--porch south,east] [--porch-depth 10] [--porch-level <name>] "
              "[--overhang 1.5] [--type <roof type name>] [--no-image]")
        sys.exit(1)

    pitch = parse_pitch(args[0])
    style = args[1].lower()
    if style not in ("gable", "hip", "flat"):
        _fail(f"Style '{style}' not supported (gable | hip | flat).")

    opts = {"porch": None, "porch-depth": 10.0, "porch-level": None,
            "overhang": 1.5, "type": None, "no-image": False}
    i = 2
    while i < len(args):
        a = args[i].lstrip("-")
        if a == "no-image":
            opts["no-image"] = True
            i += 1
        elif a in ("porch", "porch-depth", "porch-level", "overhang", "type"):
            opts[a] = args[i+1]
            i += 2
        else:
            _fail(f"Unknown option: {args[i]}")

    ext = get_exterior_walls()
    x0, x1, y0, y1, main_walls = footprint_rect(ext)
    rect = (x0, x1, y0, y1)
    top = wall_top(main_walls)
    levels = get_levels()
    rt, rt_src = resolve_roof_type(opts["type"])

    print(f"📐 Footprint: {x1-x0:.1f} x {y1-y0:.1f} ft · wall top {top:.1f} ft · roof type: {rt} ({rt_src})")

    main_id, level, offset = create_main_roof(
        rect, top, levels, rt, pitch, style, float(opts["overhang"]))
    print(f"✅ Main {style} roof {main_id} @ {level} +{offset:.2f} ft, pitch {pitch:.4f}, overhang {opts['overhang']} ft")

    if opts["porch"]:
        sides = [s.strip().lower() for s in str(opts["porch"]).split(",")]
        if opts["porch-level"]:
            plevel = opts["porch-level"]
        else:
            mids = [l for l in levels if 0.5 < l["elevation_ft"] < top - 0.5]
            if not mids:
                _fail("No level between ground and wall top for the porch eave — pass --porch-level.")
            plevel = mids[0]["name"]
            print(f"ℹ️  Porch eave level defaulted to {plevel} — pass --porch-level to override.")
        pid = create_porch_roof(rect, sides, float(opts["porch-depth"]), plevel,
                                rt, pitch, supports_slope_edges())
        print(f"✅ Porch roof {pid} ({'+'.join(sides)}, {opts['porch-depth']} ft deep, eave @ {plevel})")

    if not opts["no-image"]:
        img = qa_image(rect, top)
        if img:
            print(f"🖼️  QA image: {img} — VISUALLY VERIFY before calling it done.")

    print("⚠️  Gable-end walls are NOT auto-attached (no API). Manual: select wall → Attach Top/Base → pick roof.")
