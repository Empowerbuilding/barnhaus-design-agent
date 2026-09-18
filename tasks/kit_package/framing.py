"""
framing.py — Wall framing rules engine: geometry -> member lineal feet.

Input geometry schema (per wall):
    {
      "id": 123, "length_ft": 24.0, "height_ft": 10.0,
      "function": "exterior" | "interior",
      "openings": [{"width_ft": 3.0, "height_ft": 6.8, "kind": "door"|"window"}]
    }

Rules (v1, Allen-precedent + AISI S230 prescriptive conventions):
  - Studs at 24" o.c. exterior / 24" o.c. interior (configurable)
  - count = floor(length/spacing) + 1, +2 per corner allowance folded into
    a wall-end factor, +2 king +2 jack per opening
  - Top + bottom track = 2 x wall length (aggregated under stud profile
    family to match fabricator BOM convention)
  - Lintel per opening, profile by width band
  - Blocking/bridging allowance: +5% of stud LF (calibration knob)

Output: dict profile -> lineal feet, plus flags[].
"""

import math
from . import profiles as P

SPACING_FT = {"exterior": 2.0, "interior": 2.0}  # 24" o.c.
BLOCKING_ALLOWANCE = 0.05
WALL_END_EXTRA_STUDS = 2  # boxed ends / corner allowance per wall


def frame_wall(wall: dict, cfg: dict | None = None) -> tuple[dict, list]:
    cfg = cfg or {}
    fn = wall.get("function", "exterior")
    length = float(wall["length_ft"])
    height = float(wall["height_ft"])
    openings = wall.get("openings", []) or []
    spacing = cfg.get("spacing_ft", SPACING_FT).get(fn, 2.0)

    stud_profile = P.DEFAULTS[f"{fn}_stud"]
    lf: dict[str, float] = {}
    flags: list[str] = []

    if height > P.PRESCRIPTIVE_LIMITS["max_wall_height_ft"]:
        flags.append(
            f"wall {wall.get('id','?')}: height {height:.1f} ft exceeds prescriptive "
            f"{P.PRESCRIPTIVE_LIMITS['max_wall_height_ft']} ft — engineer to verify gauge/spacing"
        )

    # Field studs
    stud_count = math.floor(length / spacing) + 1 + WALL_END_EXTRA_STUDS
    # King + jack studs per opening
    stud_count += 4 * len(openings)
    # Cripples above/below openings (approx: one per 2 ft of opening width)
    cripple_count = sum(math.ceil(o["width_ft"] / 2.0) for o in openings)

    stud_lf = stud_count * height + cripple_count * (height * 0.35)

    # Track: top + bottom, minus nothing (openings still get track/head+sill)
    track_lf = 2.0 * length

    # Blocking / bridging allowance
    stud_lf *= (1.0 + BLOCKING_ALLOWANCE)

    if P.AGGREGATE_TRACK_AS_STUD:
        lf[stud_profile] = lf.get(stud_profile, 0.0) + stud_lf + track_lf
    else:
        track_profile = P.DEFAULTS[f"{fn}_track"]
        lf[stud_profile] = lf.get(stud_profile, 0.0) + stud_lf
        lf[track_profile] = lf.get(track_profile, 0.0) + track_lf

    # Lintels
    for o in openings:
        w = float(o["width_ft"])
        if w > P.PRESCRIPTIVE_LIMITS["max_opening_width_ft"]:
            flags.append(
                f"wall {wall.get('id','?')}: opening {w:.1f} ft exceeds "
                f"{P.PRESCRIPTIVE_LIMITS['max_opening_width_ft']} ft — hot-rolled header likely (S/W section)"
            )
            continue
        if w < 4.0:
            lp = P.DEFAULTS["lintel_small"]
        elif w <= 6.0:
            lp = P.DEFAULTS["lintel_medium"]
        else:
            lp = P.DEFAULTS["lintel_large"]
        lf[lp] = lf.get(lp, 0.0) + w + 1.0  # +1 ft bearing

    return lf, flags


def frame_walls(walls: list[dict], cfg: dict | None = None) -> tuple[dict, list]:
    """Aggregate all walls -> {profile: lf}, flags[]."""
    total: dict[str, float] = {}
    all_flags: list[str] = []
    for w in walls:
        lf, flags = frame_wall(w, cfg)
        for k, v in lf.items():
            total[k] = total.get(k, 0.0) + v
        all_flags.extend(flags)
    return total, all_flags
