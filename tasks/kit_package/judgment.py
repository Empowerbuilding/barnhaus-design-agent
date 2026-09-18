"""
judgment.py — Code-sourced confidence assessment for kit BOM outputs.

Every threshold cites a published source. This is what lets the pipeline
(and Blueprint) say not just "here's a number" but "here's how much to
trust it and why" — the same call a human estimator makes.

Sources (verified 2026-09-17):
- IRC Section R804 (Cold-Formed Steel Roof Framing): prescriptive CFS roof
  framing applies to buildings ≤60 ft perpendicular to truss span and
  ≤40 ft in width parallel to the truss span. => 40 ft = prescriptive
  truss span ceiling.
- IBC 2206.1.3.2 (and up.codes mirror): CFS truss clear spans ≥60 ft
  require a special inspector to verify temporary + permanent bracing
  during erection. => 60 ft = code-mandated special-inspection threshold.
- Alpine TrusSteel engineering manual (industry): engineered CFS trusses
  span 80+ ft — long spans are feasible, but always engineered, often with
  interior bearing considered.
- AISI S230 (Prescriptive Method, 1-2 family dwellings): wall stud tables
  top out at 10 ft stud height => taller walls leave prescriptive method.
- Calibration basis: ASF Allen production BOM (46.3 ft span) — empirical
  truss intensity 4.41 LF/sqft plan validated to +0.06% at that span.
"""

# Confidence levels
HIGH = "HIGH"       # inside calibrated + prescriptive envelope
MEDIUM = "MEDIUM"   # engineered territory, but routine for fabricators
LOW = "LOW"         # outside calibration and/or special-inspection regime

CALIBRATED_SPAN_FT = 46.3     # ASF Allen ground truth
PRESCRIPTIVE_SPAN_FT = 40.0   # IRC R804
SPECIAL_INSPECTION_SPAN_FT = 60.0  # IBC 2206.1.3.2
PRESCRIPTIVE_WALL_FT = 10.0   # AISI S230


def assess(geo: dict, flags: list) -> dict:
    """Returns per-component confidence with cited reasons."""
    roof = geo.get("roof", {})
    span = float(roof.get("span_ft", 0.0))
    walls = geo.get("walls", [])
    tall = [w for w in walls if float(w.get("height_ft", 0)) > PRESCRIPTIVE_WALL_FT]
    big_open = [o for w in walls for o in (w.get("openings") or [])
                if float(o.get("width_ft", 0)) > 8.0]

    out = {}

    # --- Trusses ---
    if span <= PRESCRIPTIVE_SPAN_FT:
        out["trusses"] = {
            "confidence": HIGH,
            "reason": (f"span {span:.0f} ft within IRC R804 prescriptive limit "
                       f"(40 ft) and near calibration point ({CALIBRATED_SPAN_FT} ft)"),
        }
    elif span <= SPECIAL_INSPECTION_SPAN_FT:
        out["trusses"] = {
            "confidence": MEDIUM if span <= CALIBRATED_SPAN_FT + 10 else MEDIUM,
            "reason": (f"span {span:.0f} ft exceeds IRC R804 prescriptive 40 ft — "
                       "engineered truss design required (routine for FRAMECAD "
                       "fabricators); weight estimate reasonable, verify with PE"),
        }
    else:
        out["trusses"] = {
            "confidence": LOW,
            "reason": (f"span {span:.0f} ft ≥ 60 ft IBC 2206.1.3.2 special-"
                       "inspection threshold and far from the 46 ft calibration "
                       "point. Likely needs interior bearing or primary steel — "
                       "treat truss weight as placeholder until PE/fabricator "
                       "design. NOTE: span is bounding-box derived; L-shaped or "
                       "multi-mass roofs may overstate true clear span — check "
                       "the model for interior bearing lines."),
        }

    # --- Wall panels ---
    if not tall:
        out["walls"] = {
            "confidence": HIGH,
            "reason": "all walls within AISI S230 10 ft prescriptive stud tables",
        }
    else:
        frac = len(tall) / max(len(walls), 1)
        out["walls"] = {
            "confidence": MEDIUM if frac < 0.25 else LOW,
            "reason": (f"{len(tall)} of {len(walls)} walls exceed the AISI S230 "
                       "10 ft stud-table ceiling — gauge/spacing upsize likely on "
                       "those (weight may run light there); PE to size"),
        }

    # --- Headers/openings ---
    if big_open:
        out["headers"] = {
            "confidence": MEDIUM,
            "reason": (f"{len(big_open)} opening(s) over 8 ft — hot-rolled "
                       "headers estimated by allowance, PE to size actual members"),
        }

    # --- Overall ---
    ranks = {HIGH: 0, MEDIUM: 1, LOW: 2}
    worst = max(out.values(), key=lambda v: ranks[v["confidence"]])
    out["overall"] = {
        "confidence": worst["confidence"],
        "reason": ("governed by weakest component; pricing ballpark quality "
                   "tracks the overall confidence tier"),
    }
    return out


def render(assessment: dict) -> str:
    lines = ["\nCONFIDENCE ASSESSMENT (code-sourced — see docs/kit-engineering-judgment.md):"]
    order = ["overall", "trusses", "walls", "headers"]
    for k in order:
        if k in assessment:
            a = assessment[k]
            lines.append(f"  [{a['confidence']:<6}] {k}: {a['reason']}")
    return "\n".join(lines) + "\n"
