"""
trusses.py — Roof truss weight approximation from roof geometry.

v1 model: standard fink-style CFS truss @ 24" o.c.
  member LF per truss = top chords + bottom chord + web factor
    top chords  = span / cos(theta)
    bottom      = span
    webs        = WEB_FACTOR * span   (heuristic — CALIBRATE against Allen)
  gable ends   = studs at 24" o.c. under each gable, avg height = rise/2

CALIBRATION TARGET (Allen, ASF BOM): Truss.1 tab = 19,855 LF of
362S162-33-50 = 18,411.9 lbs. Once the Allen model's roof span/length/pitch
are extracted live, solve WEB_FACTOR so predicted truss LF matches 19,855.
Until then WEB_FACTOR=1.4 (typical fink web-to-span ratio for 30-40 ft spans).

Connection plates (Allen ratios): apex/heel plates = 2 per truss,
fix plates = 4 per truss (92 / 184 on Allen => 46 trusses).
"""

import math
from . import profiles as P

TRUSS_SPACING_FT = 2.0
WEB_FACTOR = 1.4          # calibration knob — solve against Allen live
APEX_HEEL_PER_TRUSS = 2
FIX_PLATES_PER_TRUSS = 4


def truss_package(roof: dict) -> tuple[dict, dict, list]:
    """
    roof schema:
      { "span_ft": 40.0, "ridge_length_ft": 60.0, "pitch_rise_per_12": 4.0,
        "gable_ends": 2 }
    Returns ({profile: lf}, {plate_name: qty}, flags[])
    """
    flags: list[str] = []
    span = float(roof["span_ft"])
    ridge = float(roof["ridge_length_ft"])
    rise12 = float(roof.get("pitch_rise_per_12", 4.0))
    gables = int(roof.get("gable_ends", 2))

    if span > P.PRESCRIPTIVE_LIMITS["max_truss_clear_span_ft"]:
        flags.append(
            f"roof span {span:.0f} ft exceeds {P.PRESCRIPTIVE_LIMITS['max_truss_clear_span_ft']} ft "
            "— expect engineered truss or hot-rolled ridge/beam (Allen used S7x15.3)"
        )

    theta = math.atan(rise12 / 12.0)
    n_trusses = math.floor(ridge / TRUSS_SPACING_FT) + 1

    top_chords = span / math.cos(theta)
    bottom = span
    webs = WEB_FACTOR * span
    lf_per_truss = top_chords + bottom + webs
    truss_lf = n_trusses * lf_per_truss

    # Gable end framing (studs under gable at 24" o.c., avg height = rise/2)
    rise = (span / 2.0) * (rise12 / 12.0)
    gable_studs = math.floor(span / 2.0) + 1
    gable_lf = gables * gable_studs * (rise / 2.0)

    profile = P.DEFAULTS["truss_member"]
    lf = {profile: truss_lf + gable_lf}
    plates = {
        "FRAMECAD 1.15mm Apex/Heel Plate (AHCP-A2)": n_trusses * APEX_HEEL_PER_TRUSS,
        "FRAMECAD 1.15mm Fix Plate (FP-A2)": n_trusses * FIX_PLATES_PER_TRUSS,
    }
    return lf, plates, flags
