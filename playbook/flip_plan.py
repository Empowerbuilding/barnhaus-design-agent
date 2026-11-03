#!/usr/bin/env python3
"""
flip_plan.py — Playbook: mirror-flip an entire Revit house plan about its
centerline, then fix the annotation. Generalized from the proven
Kever / Spring Mountain flip (2026-11-02, Blueprint session 283e9257).

Works on any plan:
  - doc-title safety gate (--doc), plane auto-derived from walls bbox
  - census-driven category handling; unknown categories flagged loudly
  - E-W flip (N<->S swap, mirror across horizontal line) or N-S flip (E<->W)

Phases (state-gated, resumable — one phase per invocation, like the originals):
  preflight   census + plane + sample capture + views + rollback save
  mirror      M2 stairs canary -> M1 building core -> M3 site (copy-semantics,
              NO deletes, NO saves)
  delete      W0 groups -> W1 hosts -> W2 survivors -> W3 stairs (if canary
              verified) -> W4 site, then final census vs baseline + SAVE
  annotate    plan-view text notes + all section markers (mechanical, auto);
              elevation/section view notes -> review table (opt-in --apply)
  verify      census vs baseline, originals-gone check, sample mirror-check,
              warnings delta, optional before/after image export
  all         preflight -> mirror -> delete -> annotate -> verify
  status      print current state file

Usage (from barnhaus-design-agent repo root):
  REVIT_BRIDGE_URL=https://<tunnel> python3 playbook/flip_plan.py preflight \
      --doc "Spring Mountain" --axis ew
  python3 playbook/flip_plan.py mirror
  python3 playbook/flip_plan.py delete
  python3 playbook/flip_plan.py annotate
  python3 playbook/flip_plan.py verify --export

See playbook/README.md for decision rules and what is auto vs review.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # barnhaus-design-agent repo root
sys.path.insert(0, ROOT)
try:
    from core import revit_client as rc
except ImportError:
    print("!! core/revit_client.py not found — run from the barnhaus-design-agent repo root")
    sys.exit(2)

# ---------------------------------------------------------------------------
# Category plan — proven on the Kever flip. Unknown categories fall into M1
# (mirrored+deleted like everything else) but are PRINTED LOUDLY for review.
# ---------------------------------------------------------------------------
M2_CATS = ["Stairs", "Railings"]                     # canary batch (smallest risk first)
M3_CATS = ["Planting", "Topography", "Site", "Parking", "Entourage", "Mass"]
M1_CATS = [
    "Walls", "Doors", "Windows", "Floors", "Roofs", "Ceilings", "Roof Soffits",
    "Fascias", "Structural Columns", "Structural Framing", "Structural Foundations",
    "Furniture", "Casework", "Plumbing Fixtures", "Plumbing Equipment",
    "Lighting Fixtures", "Electrical Fixtures", "Electrical Equipment",
    "Mechanical Equipment", "Generic Models", "Specialty Equipment", "Data Devices",
    "Rooms", "Curtain Systems", "Curtain Wall Mullions", "Columns",
]
EXCLUDED_CATS = [
    "Lines", "<Sketch>", "Unknown", "<Area Boundary>", "Legend Components",
    "Model Groups", "Detail Groups", "Detail Items", "Cameras", "Reference Planes",
    "Survey Point", "Project Base Point", "Internal Origin", "Work Plane Grid",
    "Supports", "Runs", "Landings", "Balusters", "Top Rails",
    "Railing Rail Path Extension Lines", "Grids", "Levels", "Scope Boxes",
    "Text Notes", "Dimensions", "Section Marks", "Elevation Marks",
]
HOST_CATS = [
    "Walls", "Floors", "Roofs", "Ceilings", "Roof Soffits", "Fascias",
    "Structural Columns", "Structural Framing", "Structural Foundations",
]

CENSUS_BOX = {"min_point": {"x": -5000, "y": -5000, "z": -1000},
              "max_point": {"x": 5000, "y": 5000, "z": 5000}}
SAMPLE_PER_CAT = 20          # bbox sample size for the verify mirror-check
DEFAULT_SKIP_VIEWS = ["survey", "site"]   # substring match, case-insensitive


# ---------------------------------------------------------------------------
# bridge plumbing
# ---------------------------------------------------------------------------
def resolve_bridge_url(cli_url, channel):
    if cli_url:
        os.environ["REVIT_BRIDGE_URL"] = cli_url
        return cli_url
    if os.environ.get("REVIT_BRIDGE_URL"):
        return os.environ["REVIT_BRIDGE_URL"]
    for cand in (os.path.join(os.path.dirname(ROOT), "bridge_sessions.json"),
                 "/home/node/.openclaw/workspace/bridge_sessions.json"):
        try:
            sess = json.load(open(cand))
            url = sess["channels"][channel]
            os.environ["REVIT_BRIDGE_URL"] = url
            return url
        except Exception:
            continue
    print("!! no bridge URL: pass --bridge, set REVIT_BRIDGE_URL, or have "
          "bridge_sessions.json present")
    sys.exit(2)


class Bridge:
    def __init__(self, doc_substring, timeout):
        self.doc_substring = doc_substring
        rc.REQUEST_TIMEOUT = timeout

    def call(self, tool, params):
        try:
            return rc.call(tool, params)
        except Exception as e:
            return {"success": False, "error": "EXC:" + str(e)}

    def res(self, r):
        return (r or {}).get("result") or {}

    def doc_ok(self, verbose=False):
        d = self.res(self.call("revit.get_document_info", {}))
        title = str(d.get("title", ""))
        if verbose:
            print("DOC:", title, "| modified:", d.get("is_modified"))
        if self.doc_substring and self.doc_substring.lower() not in title.lower():
            print("!! ACTIVE DOC CHANGED:", repr(title), "— expected", repr(self.doc_substring), "— ABORT")
            return False
        return True

    def census(self):
        r = self.call("revit.filter_elements_by_bounding_box", CENSUS_BOX)
        els = self.res(r).get("elements", [])
        cats = {}
        for e in els:
            cats.setdefault(e["category"], []).append(e["id"])
        return cats

    def views(self):
        r = self.call("revit.list_views", {})
        vres = self.res(r)
        return vres.get("views", vres.get("elements", []))


def cross(axis):
    """('ew' -> 'y', 'ns' -> 'x') — the coordinate the flip transforms."""
    return "y" if axis == "ew" else "x"


def plane_normal(axis):
    return (0.0, 1.0, 0.0) if axis == "ew" else (1.0, 0.0, 0.0)


def load_state(out):
    p = os.path.join(out, "flip_state.json")
    if not os.path.exists(p):
        print("!! no flip_state.json in", out, "— run preflight first")
        sys.exit(2)
    return json.load(open(p))


def save_state(out, state):
    json.dump(state, open(os.path.join(out, "flip_state.json"), "w"), indent=1)


def require_phase(state, phase):
    if state.get("phase") != phase:
        print("!! state phase is", repr(state.get("phase")), "— expected", repr(phase), "— ABORT")
        sys.exit(2)


def classify(cats):
    """split census categories into m1/m2/m3/excluded; unknowns -> m1 + warning"""
    m1, m2, m3, excluded, unknown = [], [], [], [], []
    for c in cats:
        if c.endswith(" Tags"):
            excluded.append(c)          # view-specific annotation — annotate phase reports
        elif c in M2_CATS:
            m2.append(c)
        elif c in M3_CATS:
            m3.append(c)
        elif c in M1_CATS:
            m1.append(c)
        elif c in EXCLUDED_CATS:
            excluded.append(c)
        else:
            m1.append(c)
            unknown.append(c)
    if unknown:
        print("\n!! UNKNOWN CATEGORIES auto-assigned to the mirrored set (review):")
        for c in unknown:
            print(f"   {c}: {len(cats[c])} elements")
        print("   (override with --exclude-cat on preflight if any should NOT flip)\n")
    return m1, m2, m3, excluded


# ---------------------------------------------------------------------------
# phases
# ---------------------------------------------------------------------------
def cmd_preflight(b, out, args):
    os.makedirs(out, exist_ok=True)
    if not b.doc_ok(verbose=True):
        sys.exit(2)
    state = {"ts": datetime.datetime.utcnow().isoformat(), "steps": [],
             "axis": args.axis, "doc": args.doc, "plane": None,
             "exclude_cats": args.exclude_cat or []}

    # census
    cats = b.census()
    json.dump({"cats": cats, "total": sum(len(v) for v in cats.values())},
              open(os.path.join(out, "census_now.json"), "w"))
    print(f"\nCENSUS: {sum(len(v) for v in cats.values())} elements, {len(cats)} categories")
    m1, m2, m3, excluded = classify(cats)
    for c in args.exclude_cat or []:
        if c in m1:
            m1.remove(c)
            excluded.append(c)
            print(f"excluded by flag: {c}")
    state["cats_split"] = {"m1": m1, "m2": m2, "m3": m3, "excluded": excluded}
    state["census"] = {k: len(v) for k, v in cats.items()}

    # plane from walls bbox (cross-axis extent)
    ax = cross(args.axis)
    vals = []
    for wid in cats.get("Walls", []):
        bb = b.res(b.call("revit.get_element_bounding_box", {"element_id": wid}))
        if bb.get("has_bbox"):
            vals.append((bb["min"][ax], bb["max"][ax]))
    if not vals:
        print("!! no wall bboxes — cannot auto-derive the mirror plane. "
              "Pass --plane explicitly.")
        sys.exit(2)
    lo = min(a for a, _ in vals)
    hi = max(c for _, c in vals)
    plane = args.plane if args.plane is not None else round((lo + hi) / 2.0, 4)
    print(f"\nWALLS {ax.upper()}-EXTENT: [{lo:.2f} .. {hi:.2f}]  ->  plane = {plane}")
    state["plane"] = plane
    state["walls_extent"] = {"min": lo, "max": hi}

    # bbox sample for the verify-phase mirror-check (originals; transform known)
    sample = {}
    for c in m1 + m2 + m3:
        centers = []
        for eid in cats.get(c, [])[:SAMPLE_PER_CAT]:
            bb = b.res(b.call("revit.get_element_bounding_box", {"element_id": eid}))
            if bb.get("has_bbox"):
                centers.append(round((bb["min"][ax] + bb["max"][ax]) / 2.0, 4))
        if centers:
            sample[c] = sorted(centers)
    state["sample_centers_pre"] = sample

    # views + export picks
    views = b.views()
    plans = [v for v in views if v.get("type") in ("FloorPlan", "CeilingPlan", "AreaPlan")]
    skips = args.skip_view or DEFAULT_SKIP_VIEWS
    skipped = [v["name"] for v in plans if any(s.lower() in str(v["name"]).lower() for s in skips)]
    print(f"\nFLOOR PLANS ({len(plans)}); skip-views matched: {skipped or 'none'}")
    pick = {}
    for v in plans:
        nm = str(v.get("name", ""))
        if any(s.lower() in nm.lower() for s in skips):
            continue
        lvl = nm.split(".")[0].strip().lower()
        if lvl not in pick:
            pick[lvl] = {"id": v["id"], "name": nm}
        if "simple" in nm.lower() and lvl in pick and "simple" not in pick[lvl]["name"].lower():
            pick[lvl] = {"id": v["id"], "name": nm}
    state["export_views"] = list(pick.values())
    state["skip_views"] = skipped
    print("export picks:", [v["name"] for v in state["export_views"]])

    # warnings baseline
    w = b.res(b.call("revit.get_warnings", {}))
    try:
        nwarn = len(w.get("warnings", w if isinstance(w, list) else []))
    except Exception:
        nwarn = None
    state["warnings_pre"] = nwarn
    print("warnings baseline:", nwarn)

    # rollback save (only when dry_run is off)
    d = b.res(b.call("revit.get_document_info", {}))
    if args.dry_run:
        print("\nDRY RUN — no save, state NOT written as runnable")
        state["phase"] = "preflight_dryrun"
    elif d.get("is_modified"):
        r = b.call("revit.save_document", {})
        print("\nSAVE rollback point:", r.get("success"))
        state["saved_preflight"] = True
        state["phase"] = "preflight_done"
    else:
        print("\nDoc not modified — on-disk state is the rollback point.")
        state["saved_preflight"] = False
        state["phase"] = "preflight_done"

    save_state(out, state)
    print("STATE -> flip_state.json  phase =", state["phase"])


def _mirror_batch(b, ids, plane, axis, label):
    nx, ny, nz = plane_normal(axis)
    if axis == "ew":
        origin = {"x": 0.0, "y": plane, "z": 0.0}
    else:
        origin = {"x": plane, "y": 0.0, "z": 0.0}
    print(f"\n=== {label}: mirroring {len(ids)} elements about {axis.upper()} plane = {plane} ===")
    if not b.doc_ok():
        sys.exit(3)
    r = b.call("revit.batch_mirror_elements",
               {"element_ids": ids, "plane_origin": origin,
                "plane_normal": {"x": nx, "y": ny, "z": nz}})
    print("response:", json.dumps(r)[:300])
    return r


def _verify_doubled(b, cats_before, batch_cats):
    after = b.census()
    report, ok = {}, True
    for c in batch_cats:
        before_ids = set(cats_before.get(c, []))
        if not before_ids:
            continue
        after_ids = set(after.get(c, []))
        new_ids = sorted(after_ids - before_ids)
        doubled = len(after_ids) == 2 * len(before_ids)
        if not doubled:
            ok = False
        report[c] = {"before": len(before_ids), "after": len(after_ids),
                     "new": len(new_ids), "doubled": doubled}
        flag = "" if doubled else "  <-- NOT DOUBLED"
        print(f"  {c}: {len(before_ids)} -> {len(after_ids)} (new {len(new_ids)}){flag}")
    return report, ok


def cmd_mirror(b, out, args):
    state = load_state(out)
    require_phase(state, "preflight_done")
    b.doc_substring = state.get("doc") or b.doc_substring
    cats = json.load(open(os.path.join(out, "census_now.json")))["cats"]
    split = state["cats_split"]
    plane, axis = state["plane"], state["axis"]

    # M2 canary — smallest risk first (stairs are the known poison)
    m2_ids = [i for c in split["m2"] for i in cats.get(c, [])]
    if m2_ids:
        _mirror_batch(b, m2_ids, plane, axis, "M2 canary (stairs/railings)")
        rep, ok = _verify_doubled(b, cats, split["m2"])
        state["m2"] = {"verified": ok, "report": rep}
        state["steps"].append("m2_" + ("verified" if ok else "FAILED-silent-rollback-suspected"))
        if not ok:
            print("\nM2 DID NOT PERSIST (known stairs poison). Stairs stay original; "
                  "they will NOT be deleted — flagged for GUI mirror.")
    else:
        state["m2"] = {"verified": None, "note": "no stairs/railings in census"}
        print("M2 canary: no stairs/railings present — skipping")

    # M1 building core
    m1_ids = [i for c in split["m1"] for i in cats.get(c, [])]
    print(f"\nM1 set: {len(m1_ids)} elements")
    if m1_ids:
        _mirror_batch(b, m1_ids, plane, axis, "M1 building core")
        rep, ok = _verify_doubled(b, cats, split["m1"])
        state["m1"] = {"count": len(m1_ids), "verified": ok, "report": rep}
        state["steps"].append("m1_" + ("verified" if ok else "INCOMPLETE"))
    else:
        state["m1"] = {"count": 0, "verified": True}

    # M3 site
    m3_ids = [i for c in split["m3"] for i in cats.get(c, [])]
    if m3_ids:
        _mirror_batch(b, m3_ids, plane, axis, "M3 site")
        rep, ok = _verify_doubled(b, cats, split["m3"])
        state["m3"] = {"count": len(m3_ids), "verified": ok, "report": rep}
        state["steps"].append("m3_" + ("verified" if ok else "FAILED"))
    else:
        state["m3"] = {"count": 0, "verified": True}

    state["phase"] = "mirrors_done"
    state["ts"] = datetime.datetime.utcnow().isoformat()
    save_state(out, state)
    print(f"\nPHASE: mirrors_done  (M1 {'OK' if state['m1']['verified'] else 'INCOMPLETE'} / "
          f"M2 {state['m2']['verified']} / M3 {'OK' if state['m3']['verified'] else 'FAILED'})")
    print("Nothing deleted, nothing saved. Run the delete phase next.")


def cmd_delete(b, out, args):
    state = load_state(out)
    require_phase(state, "mirrors_done")
    b.doc_substring = state.get("doc") or b.doc_substring
    cats = json.load(open(os.path.join(out, "census_now.json")))["cats"]
    split = state["cats_split"]
    baseline = {k: len(v) for k, v in cats.items()}

    # sanity: mirrors still intact (each mirrored cat should be doubled)
    cur = b.census()
    anchor = next((c for c in split["m1"] if baseline.get(c)), None)
    if anchor and len(cur.get(anchor, [])) != 2 * baseline[anchor]:
        print(f"!! {anchor} = {len(cur.get(anchor, []))}, expected {2 * baseline[anchor]} — "
              "mirror copies missing (doc reset?). ABORT — nothing deleted.")
        sys.exit(3)

    def delete_wave(label, target_ids):
        if not b.doc_ok():
            sys.exit(3)
        cur = b.census()
        existing = set()
        for v in cur.values():
            existing.update(v)
        live = [i for i in target_ids if i in existing]
        gone = len(target_ids) - len(live)
        if gone:
            print(f"  ({gone} already gone via cascade)")
        if not live:
            print(f"=== {label}: nothing left to delete")
            return 0
        print(f"=== {label}: deleting {len(live)} originals ===")
        r = b.call("revit.batch_delete_elements", {"element_ids": live})
        rr = b.res(r)
        print("  response:", json.dumps(
            {k: rr.get(k) for k in ("success", "requestedCount", "deletedCount", "error")})[:220])
        if not rr.get("success"):
            print("  !! DELETE FAILED — stopping this wave")
            return -1
        return rr.get("deletedCount", 0)

    delete_wave("W0 model groups", cats.get("Model Groups", []))
    host_ids = [i for c in HOST_CATS if c in split["m1"] for i in cats.get(c, [])]
    delete_wave("W1 hosts", host_ids)
    m1_ids = [i for c in split["m1"] for i in cats.get(c, [])]
    delete_wave("W2 M1 survivors", m1_ids)

    # verify M1 back to baseline with all-new ids
    cur = b.census()
    print("\n--- M1 verify (want: count == baseline, all ids NEW) ---")
    m1_ok = True
    for c in split["m1"]:
        bcount, acount = baseline.get(c, 0), len(cur.get(c, []))
        remaining = len(set(cats.get(c, [])) & set(cur.get(c, [])))
        if not (bcount == acount and remaining == 0):
            m1_ok = False
            print(f"  {c}: {bcount} -> {acount}, remaining originals: {remaining}  <-- CHECK")
    print("M1:", "OK — flipped set in place, originals gone" if m1_ok else "ANOMALY — see above")

    if state.get("m2", {}).get("verified"):
        delete_wave("W3 stairs/railings", [i for c in split["m2"] for i in cats.get(c, [])])
    else:
        print("\nW3 SKIPPED — canary did not verify; original stairs stay in place "
              "(mirror them manually in the GUI)")

    delete_wave("W4 site", [i for c in split["m3"] for i in cats.get(c, [])])

    # final census vs baseline
    cur = b.census()
    json.dump({"cats": cur, "total": sum(len(v) for v in cur.values())},
              open(os.path.join(out, "census_final.json"), "w"))
    print("\n--- FINAL vs BASELINE (all categories) ---")
    for c in sorted(set(baseline) | set(cur)):
        bcount, acount = baseline.get(c, 0), len(cur.get(c, []))
        mark = "" if bcount == acount else "   <-- CHANGED"
        print(f"  {c}: {bcount} -> {acount}{mark}")

    w = b.res(b.call("revit.get_warnings", {}))
    try:
        nwarn = len(w.get("warnings", w if isinstance(w, list) else []))
    except Exception:
        nwarn = None
    print(f"\nWarnings now: {nwarn} (baseline was {state.get('warnings_pre')})")

    r = b.call("revit.save_document", {})
    print("\nSAVE:", b.res(r).get("success") if r.get("success") else r.get("error"))

    state.update({"phase": "flip_complete", "m1_final_ok": m1_ok,
                  "final_census": {k: len(v) for k, v in cur.items()},
                  "warnings_after": nwarn,
                  "ts": datetime.datetime.utcnow().isoformat()})
    state["steps"].append("flip_complete_saved")
    save_state(out, state)
    print("\nPHASE: flip_complete — mirrored set in place, originals deleted, document saved.")


def _plan_views(b, skip_views):
    views = b.views()
    plans = [v for v in views if v.get("type") in ("FloorPlan", "CeilingPlan", "AreaPlan")]
    keep = [v for v in plans
            if not any(s.lower() in str(v.get("name", "")).lower() for s in skip_views)]
    return views, plans, keep


def _elements_by_view(b, view_id, cache):
    if view_id not in cache:
        cache[view_id] = b.res(
            b.call("revit.filter_elements_by_view", {"view_id": view_id})).get("elements", [])
    return cache[view_id]


def cmd_annotate(b, out, args):
    state = load_state(out)
    require_phase(state, "flip_complete")
    b.doc_substring = state.get("doc") or b.doc_substring
    plane, axis = state["plane"], state["axis"]
    ax = cross(axis)
    skips = args.skip_view or DEFAULT_SKIP_VIEWS
    if not b.doc_ok(verbose=True):
        sys.exit(2)

    views, plans, keep = _plan_views(b, skips)
    print(f"plan views: {len(keep)} kept / {len(plans) - len(keep)} skipped {state.get('skip_views') or ''}")
    cache = {}
    moved, failed = 0, []

    # ---- 1. text notes in kept plan views: mirror cross-axis coord ----
    print("\n=== TEXT NOTES in plan views ===")
    groups = {}
    for v in keep:
        for e in _elements_by_view(b, v["id"], cache):
            if e.get("category") != "Text Notes":
                continue
            c = b.res(b.call("revit.reflect_get",
                             {"target_id": str(e["id"]), "property_name": "Coord"}))
            if isinstance(c, dict) and ax in c:
                groups.setdefault(round(c[ax], 4), []).append(e["id"])
    print(f"notes grouped into {len(groups)} coord rows")
    for coord, ids in sorted(groups.items()):
        delta = 2 * (plane - coord)
        translation = ({"x": 0.0, "y": delta, "z": 0.0} if axis == "ew"
                       else {"x": delta, "y": 0.0, "z": 0.0})
        r = b.call("revit.batch_move_elements",
                   {"element_ids": ids, "translation": translation})
        if b.res(r).get("success") or r.get("success"):
            moved += len(ids)
        else:
            failed.extend(ids)
            print(f"  !! move failed at {ax}={coord}: {json.dumps(r)[:160]}")
    print(f"moved: {moved}, failed: {len(failed)}")

    # report other annotation categories found in plan views (NOT auto-moved)
    other = {}
    for v in keep:
        for e in _elements_by_view(b, v["id"], cache):
            cat = e.get("category", "")
            if cat not in ("Text Notes",) and (cat.endswith(" Tags") or cat in
                                               ("Dimensions", "Section Marks", "Elevation Marks")):
                other.setdefault(cat, 0)
                other[cat] += 1
    if other:
        print("\nOTHER ANNOTATION in plan views (reported, NOT auto-moved — "
              "tags may auto-follow their hosts; verify visually):", other)

    # ---- 2. section markers in plan views: mirror cross-axis coord ----
    print("\n=== SECTION MARKERS ===")
    sections = [v for v in views if v.get("type") == "Section"]
    marker_moves = 0
    for s in sections:
        found = None
        for pv in keep:
            for e in _elements_by_view(b, pv["id"], cache):
                if str(e.get("name", "")).strip() == str(s.get("name", "")).strip():
                    found = (e, pv)
                    break
            if found:
                break
        if not found:
            continue
        e, pv = found
        c = b.res(b.call("revit.reflect_get",
                         {"target_id": str(e["id"]), "property_name": "Coord"}))
        if not (isinstance(c, dict) and ax in c):
            print(f"  !! marker '{s['name']}' coord unreadable")
            continue
        delta = 2 * (plane - c[ax])
        translation = ({"x": 0.0, "y": delta, "z": 0.0} if axis == "ew"
                       else {"x": delta, "y": 0.0, "z": 0.0})
        r = b.call("revit.batch_move_elements",
                   {"element_ids": [e["id"]], "translation": translation})
        ok = b.res(r).get("success") or r.get("success")
        marker_moves += 1 if ok else 0
        print(f"  marker '{s['name']}' ({pv['name']}): {ax} {c[ax]:.2f} -> "
              f"{2 * plane - c[ax]:.2f} {'OK' if ok else 'FAIL'}")
    print(f"section markers moved: {marker_moves}/{len(sections)}")

    # ---- 3. elevation/section view notes: review table + optional apply ----
    print("\n=== ELEVATION/SECTION VIEW NOTES (review table) ===")
    print("Rule of thumb: a view's notes move when the view's HORIZONTAL axis is the "
          "flipped axis (facing perpendicular to the flip normal).")
    suggestions = []
    for v in views:
        if v.get("type") not in ("Elevation", "Section"):
            continue
        vd = b.res(b.call("revit.reflect_get",
                          {"target_id": str(v["id"]), "property_name": "ViewDirection"}))
        if not (isinstance(vd, dict) and "x" in vd):
            continue
        facing_x = abs(vd.get("x", 0)) > 0.5
        # horizontal axis of the view = the OTHER horizontal axis
        horiz_is_flipped = (facing_x and axis == "ew") or (not facing_x and axis == "ns")
        els = b.res(b.call("revit.filter_elements_by_view", {"view_id": v["id"]})) \
                .get("elements", [])
        texts = [e for e in els if e.get("category") == "Text Notes"]
        if not texts:
            continue
        action = "MIRROR" if horiz_is_flipped else "leave (review)"
        print(f"  [{v['type']}] '{v['name']}': {len(texts)} notes -> {action}")
        if horiz_is_flipped:
            suggestions.append({"view": v["name"], "type": v["type"], "ids": [t["id"] for t in texts]})

    if args.apply_view_notes and suggestions:
        print("\n--apply-view-notes: moving suggested view notes")
        for s in suggestions:
            for eid in s["ids"]:
                c = b.res(b.call("revit.reflect_get",
                                 {"target_id": str(eid), "property_name": "Coord"}))
                if not (isinstance(c, dict) and ax in c):
                    continue
                delta = 2 * (plane - c[ax])
                translation = ({"x": 0.0, "y": delta, "z": 0.0} if axis == "ew"
                               else {"x": delta, "y": 0.0, "z": 0.0})
                r = b.call("revit.batch_move_elements",
                           {"element_ids": [eid], "translation": translation})
                ok = b.res(r).get("success") or r.get("success")
                print(f"  [{s['view']}] {eid}: {'OK' if ok else 'FAIL'}")
    elif suggestions:
        print("\n(suggested moves NOT applied — re-run with --apply-view-notes after review)")

    r = b.call("revit.save_document", {})
    print("\nSAVE:", "ok" if (r.get("success") or b.res(r).get("saved")) else json.dumps(r)[:150])

    state["annotate"] = {"notes_moved": moved, "notes_failed": len(failed),
                         "view_note_suggestions": [s["view"] for s in suggestions],
                         "applied_view_notes": bool(args.apply_view_notes)}
    state["phase"] = "annotate_done"
    state["ts"] = datetime.datetime.utcnow().isoformat()
    save_state(out, state)
    print("PHASE: annotate_done")


def cmd_verify(b, out, args):
    state = load_state(out)
    if state.get("phase") not in ("flip_complete", "annotate_done"):
        print("!! verify expects flip_complete or annotate_done, got", state.get("phase"))
        sys.exit(2)
    plane, axis = state["plane"], state["axis"]
    ax = cross(axis)
    b.doc_substring = state.get("doc") or b.doc_substring
    baseline = json.load(open(os.path.join(out, "census_now.json")))["cats"]
    if not b.doc_ok(verbose=True):
        sys.exit(2)

    ok_all = True

    # 1. census vs baseline + originals gone
    cur = b.census()
    print("\n--- CENSUS vs BASELINE ---")
    for c in sorted(set(baseline) | set(cur)):
        bcount, acount = len(baseline.get(c, [])), len(cur.get(c, []))
        remaining = len(set(baseline.get(c, [])) & set(cur.get(c, [])))
        if bcount != acount or remaining:
            ok_all = False
            print(f"  {c}: {bcount} -> {acount}, originals remaining: {remaining}  <-- CHECK")
    print("census:", "OK" if ok_all else "ANOMALY — see above")

    # 2. sample mirror-check: multiset compare of cross-axis centers
    print("\n--- SAMPLE MIRROR-CHECK (originals vs current, transformed) ---")
    sample_pre = state.get("sample_centers_pre", {})
    checked = 0
    for c, olds in sample_pre.items():
        cur_ids = cur.get(c, [])[:SAMPLE_PER_CAT]
        centers = []
        for eid in cur_ids:
            bb = b.res(b.call("revit.get_element_bounding_box", {"element_id": eid}))
            if bb.get("has_bbox"):
                centers.append(round((bb["min"][ax] + bb["max"][ax]) / 2.0, 4))
        want = sorted(round(2 * plane - o, 4) for o in olds[:len(centers)])
        got = sorted(centers)
        if len(want) == len(got) and all(abs(a - b_) < 0.02 for a, b_ in zip(want, got)):
            checked += 1
        else:
            ok_all = False
            print(f"  {c}: mismatch — want {want[:5]}... got {got[:5]}...  <-- CHECK")
    print(f"sample mirror-check: {checked}/{len(sample_pre)} categories OK")

    # 3. warnings delta
    w = b.res(b.call("revit.get_warnings", {}))
    try:
        nwarn = len(w.get("warnings", w if isinstance(w, list) else []))
    except Exception:
        nwarn = None
    print(f"\nwarnings: {state.get('warnings_pre')} -> {nwarn}")

    # 4. optional image export (agent views these for the visual verdict)
    if args.export:
        views = state.get("export_views", [])
        os.makedirs(os.path.join(out, "verify"), exist_ok=True)
        for v in views:
            dest = os.path.join(out, "verify", f"after_{str(v['name']).replace(' ', '_')}.png")
            try:
                subprocess.run(["python3", "run.py", "export-image", str(v["id"]), dest],
                               cwd=ROOT, check=True, capture_output=True, timeout=120)
                print("exported:", dest)
            except Exception as e:
                print(f"!! export failed for {v['name']}: {e}")

    state["verify"] = {"ok": ok_all, "warnings": nwarn,
                       "ts": datetime.datetime.utcnow().isoformat()}
    save_state(out, state)
    print("\nVERIFY:", "PASS" if ok_all else "ISSUES FOUND — review above before delivering")


def cmd_status(out):
    state = load_state(out)
    print(json.dumps(state, indent=1)[:4000])


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, need_out=True):
        p.add_argument("--bridge", help="bridge URL (else REVIT_BRIDGE_URL env / bridge_sessions.json)")
        p.add_argument("--channel", default="blueprint-mitch",
                       help="bridge_sessions.json channel (default blueprint-mitch)")
        p.add_argument("--out", default=os.path.join(ROOT, "exports", "flip_plan"),
                       help="state/output dir (one flip at a time per dir)")
        p.add_argument("--timeout", type=int, default=150)
        if need_out:
            pass

    p = sub.add_parser("preflight"); common(p)
    p.add_argument("--doc", required=True, help="active-document title substring (safety gate)")
    p.add_argument("--axis", choices=["ew", "ns"], default="ew",
                   help="ew = N<->S swap (E-W flip line); ns = E<->W swap")
    p.add_argument("--plane", type=float, default=None, help="mirror plane coord (default: walls bbox center)")
    p.add_argument("--skip-view", action="append", help="plan views to skip in annotate (substring; default survey/site)")
    p.add_argument("--exclude-cat", action="append", help="category to exclude from the flip")
    p.add_argument("--dry-run", action="store_true", help="census+plane preview, no save, no runnable state")

    for name in ("mirror", "delete", "verify"):
        p = sub.add_parser(name); common(p)
        if name == "verify":
            p.add_argument("--export", action="store_true", help="export after-images for visual verdict")

    p = sub.add_parser("annotate"); common(p)
    p.add_argument("--skip-view", action="append")
    p.add_argument("--apply-view-notes", action="store_true",
                   help="apply the suggested elevation/section view-note moves after review")

    p = sub.add_parser("all"); common(p)
    p.add_argument("--doc", required=True)
    p.add_argument("--axis", choices=["ew", "ns"], default="ew")
    p.add_argument("--plane", type=float, default=None)
    p.add_argument("--skip-view", action="append")
    p.add_argument("--exclude-cat", action="append")
    p.add_argument("--skip-annotate", action="store_true")
    p.add_argument("--apply-view-notes", action="store_true")
    p.add_argument("--export", action="store_true")

    p = sub.add_parser("status"); common(p)

    args = ap.parse_args()
    if args.cmd == "status":
        cmd_status(args.out)
        return
    url = resolve_bridge_url(args.bridge, args.channel)
    print("bridge:", url)
    b = Bridge(doc_substring=args.doc if hasattr(args, "doc") else None, timeout=args.timeout)

    if args.cmd == "preflight":
        cmd_preflight(b, args.out, args)
    elif args.cmd == "mirror":
        cmd_mirror(b, args.out, args)
    elif args.cmd == "delete":
        cmd_delete(b, args.out, args)
    elif args.cmd == "annotate":
        cmd_annotate(b, args.out, args)
    elif args.cmd == "verify":
        cmd_verify(b, args.out, args)
    elif args.cmd == "all":
        args.dry_run = False
        cmd_preflight(b, args.out, args)
        cmd_mirror(b, args.out, args)
        cmd_delete(b, args.out, args)
        if not args.skip_annotate:
            cmd_annotate(b, args.out, args)
        cmd_verify(b, args.out, args)


if __name__ == "__main__":
    main()
