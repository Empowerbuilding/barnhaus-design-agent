"""
profiles.py — CFS member profile catalog with weights per lineal foot.

Calibration source: Accurate Steel Fab "Allen" Manufacturing Summary
(FRAMECAD Structure v11.1.12.0, Nov 2025). Empirical plf derived from
their aggregate LF + weight columns — these are ground truth because
they came off the fabricator's own production software:

    362S162-33-50: 19855.04 ft -> 18411.9 lbs = 0.9273 plf
    362S162-43-50:  5325.96 ft ->  6370.4 lbs = 1.1961 plf
    600S162-43-50:  5623.92 ft ->  8805.3 lbs = 1.5657 plf
    S7x15.3:         121.69 ft ->  1861.8 lbs = 15.30  plf  (validates method)

Computed fallback (for profiles not in the empirical set) uses developed
cross-section: plf = (web + 2*flange + 2*lip) * design_thickness * 3.4028
(steel @ 490 lb/ft^3). Verified within ~1% of ASF empirical values.
"""

# SSMA design thickness (inches) by mil designation
MIL_THICKNESS = {
    18: 0.0188, 27: 0.0283, 30: 0.0312, 33: 0.0346, 43: 0.0451,
    54: 0.0566, 68: 0.0713, 97: 0.1017,
}

# Stiffening lip length by flange designation (inches) — SSMA Product
# Technical Guide: S125=0.188, S137=0.375, S162=0.500, S200/S250=0.625, S350=1.0
LIP_BY_FLANGE = {125: 0.188, 137: 0.375, 162: 0.500, 200: 0.625,
                 250: 0.625, 300: 0.625, 350: 1.000}

# Exact member dimensions (inches) — SSMA designations are nominal
# hundredths; true dims are fractional (362 = 3-5/8", 162 = 1-5/8")
EXACT_HUNDREDTHS = {125: 1.25, 137: 1.375, 150: 1.5, 162: 1.625, 200: 2.0,
                    250: 2.5, 300: 3.0, 350: 3.5, 362: 3.625, 400: 4.0,
                    550: 5.5, 600: 6.0, 800: 8.0, 1000: 10.0, 1200: 12.0}


def _dim(code: int) -> float:
    return EXACT_HUNDREDTHS.get(code, code / 100.0)

# Empirical plf from ASF Allen BOM — always preferred when present
EMPIRICAL_PLF = {
    "362S162-33-50": 0.9273,
    "362S162-43-50": 1.1961,
    "600S162-43-50": 1.5657,
    # FRAMECAD metric lintel profiles (web mm x flange mm x mil)
    "600x125x33 Lintel": 0.975,
    "600x125x43 Lintel": 1.170,
    "850x125x54 Lintel": 1.856,
    # Hot-rolled sections pass through at nominal weight
    "S7x15.3": 15.30,
    "S8x18.4": 18.40,
    "W8x10": 10.0,
    "W10x12": 12.0,
}

STEEL_PLF_PER_SQIN = 3.4028  # 490 lb/ft3 * 1 ft length / 144 in2


def parse_ssma(designation: str):
    """Parse '600S162-43-50' -> (web_in, flange_in, mil, ksi). None if not SSMA."""
    try:
        body, mil, ksi = designation.split("-")
        if "S" in body:
            web_raw, flange_raw = body.split("S")
            member = "S"
        elif "T" in body:
            web_raw, flange_raw = body.split("T")
            member = "T"
        else:
            return None
        web = _dim(int(web_raw))         # 362 -> 3.625 (3-5/8")
        flange_code = int(flange_raw)
        flange = _dim(flange_code)       # 162 -> 1.625 (1-5/8")
        return (web, flange, int(mil), int(ksi), member, flange_code)
    except (ValueError, AttributeError):
        return None


def plf(designation: str) -> float:
    """Weight per lineal foot for a profile designation."""
    if designation in EMPIRICAL_PLF:
        return EMPIRICAL_PLF[designation]
    parsed = parse_ssma(designation)
    if parsed is None:
        raise ValueError(f"Unknown profile: {designation!r} — add to EMPIRICAL_PLF")
    web, flange, mil, _ksi, member, flange_code = parsed
    t = MIL_THICKNESS[mil]
    lip = LIP_BY_FLANGE.get(flange_code, 0.5) if member == "S" else 0.0  # track (T) has no lips
    developed = web + 2 * flange + 2 * lip
    return round(developed * t * STEEL_PLF_PER_SQIN, 4)


# --- Barnhaus default profile selection (Allen-precedent conventions) ------
# ASF framed Allen with 600-series 43mil exterior, 362-series 43mil interior,
# 362-series 33mil trusses. These are the v1 defaults; AISI S230 checks can
# upgrade gauge when spans/heights/loads demand it.

DEFAULTS = {
    "exterior_stud": "600S162-43-50",
    "exterior_track": "600T150-43-50",
    "interior_stud": "362S162-43-50",
    "interior_track": "362T150-43-50",
    "truss_member": "362S162-33-50",
    "lintel_small": "600x125x33 Lintel",   # openings < 4 ft
    "lintel_medium": "600x125x43 Lintel",  # openings 4-6 ft
    "lintel_large": "850x125x54 Lintel",   # openings > 6 ft
}

# v1 simplification used by ASF's own summary: track aggregates under the
# stud profile family (their BOM shows no separate track lines — track LF
# is rolled into the S-profile totals). Mirror that so our totals compare
# apples-to-apples with fabricator BOMs.
AGGREGATE_TRACK_AS_STUD = True

# AISI S230 prescriptive envelope sanity limits (flag, don't fail)
PRESCRIPTIVE_LIMITS = {
    "max_wall_height_ft": 10.0,
    "max_truss_clear_span_ft": 40.0,   # beyond this expect engineered/hot-rolled
    "max_opening_width_ft": 8.0,       # beyond this expect hot-rolled header
}
