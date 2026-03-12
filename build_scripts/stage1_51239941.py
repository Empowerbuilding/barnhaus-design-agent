"""
STAGE 1 — Exterior Shell
Submission: 51239941 | Mitchell Madison | H-shape | 2,250 SF | Contemporary
3 bed / 2.5 bath | No garage | Floor-to-ceiling windows | Brick exterior
Wall heights: left_wing=11ft, center_bridge=16ft, right_wing=11ft

H-SHAPE FOOTPRINT:
  Left wing   : x=0-22,  y=8-44  (22×36 = 792 SF)
  Center bridge: x=22-50, y=14-38 (28×24 = 672 SF)
  Right wing  : x=50-72, y=8-44  (22×36 = 792 SF)
  Total living : 2,256 SF ✅

  Back porch  : x=22-50, y=0-8   (28×8, posts at y=0)
  Front porch : x=22-50, y=44-54 (28×10, posts at y=54)

ORIENTATION:
  South (large y=54) = street/entry
  North (small y=0)  = rear/view/back porch

H-SHAPE PERIMETER (two separate rectangular wings + bridge):
  Left wing exterior:  (0,8)→(0,44)→(22,44)→(22,8)→(0,8)  [skip east face shared w/ bridge]
  Bridge exterior:     north y=14, south y=38, spans x=22-50 [skip east/west shared w/ wings]
  Right wing exterior: (72,8)→(72,44)→(50,44)→(50,8)→(72,8) [skip west face shared w/ bridge]

  Outer perimeter walls:
    Left wing:  West (x=0), North (y=8), South (y=44), partial E (x=22 above/below bridge)
    Bridge:     North (y=14), South (y=38)
    Right wing: East (x=72), North (y=8), South (y=44), partial W (x=50 above/below bridge)

ZONE HEIGHTS:
  Left wing    = 11ft (wall_height: tall)
  Center bridge = 16ft (wall_height: center_bridge override — DRAMATIC)
  Right wing   = 11ft
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, smart_floor, make_roof,
    attach_walls_to_roof, place_porch_posts, call as _call
)

LEVEL = 'Level 1.0'
EXT   = 'Wall 7.5" EXT PBR'
HL    = 11   # left/right wing height
HC    = 16   # center bridge height — dramatic 16ft
EXT_BOUNDS_L = {"x_min": 0,  "x_max": 22, "y_min": 8,  "y_max": 44}
EXT_BOUNDS_C = {"x_min": 22, "x_max": 50, "y_min": 14, "y_max": 38}
EXT_BOUNDS_R = {"x_min": 50, "x_max": 72, "y_min": 8,  "y_max": 44}

print("=" * 60)
print("STAGE 1 — 51239941 — Exterior Shell (H-shape)")
print("=" * 60)

walls = {'left': [], 'center': [], 'right': []}

# ── LEFT WING (11ft, master suite) ───────────────────────────
print("\n[LEFT WING — 11ft]")
lw = [
    create_wall( 0,  8, 0,  0, 44, 0, LEVEL, EXT, height=HL, label="LW-West"),
    create_wall( 0, 44, 0, 22, 44, 0, LEVEL, EXT, height=HL, label="LW-South"),
    create_wall( 0,  8, 0, 22,  8, 0, LEVEL, EXT, height=HL, label="LW-North"),
    # East face: x=22, y=8-14 (below bridge) and y=38-44 (above bridge)
    create_wall(22,  8, 0, 22, 14, 0, LEVEL, EXT, height=HL, label="LW-East-N"),
    create_wall(22, 38, 0, 22, 44, 0, LEVEL, EXT, height=HL, label="LW-East-S"),
]
walls['left'] = lw
print(f"  Left wing: {lw}")

# ── CENTER BRIDGE (16ft, great room hero) ─────────────────────
print("\n[CENTER BRIDGE — 16ft]")
cw = [
    create_wall(22, 14, 0, 50, 14, 0, LEVEL, EXT, height=HC, label="CB-North"),
    create_wall(50, 14, 0, 50, 38, 0, LEVEL, EXT, height=HC, label="CB-East"),
    create_wall(50, 38, 0, 22, 38, 0, LEVEL, EXT, height=HC, label="CB-South"),
    create_wall(22, 38, 0, 22, 14, 0, LEVEL, EXT, height=HC, label="CB-West"),
]
walls['center'] = cw
print(f"  Center bridge: {cw}")

# ── RIGHT WING (11ft, bed wing) ───────────────────────────────
print("\n[RIGHT WING — 11ft]")
rw = [
    create_wall(72, 44, 0, 72,  8, 0, LEVEL, EXT, height=HL, label="RW-East"),
    create_wall(72,  8, 0, 50,  8, 0, LEVEL, EXT, height=HL, label="RW-North"),
    create_wall(50, 44, 0, 72, 44, 0, LEVEL, EXT, height=HL, label="RW-South"),
    # West face: x=50, y=8-14 and y=38-44
    create_wall(50,  8, 0, 50, 14, 0, LEVEL, EXT, height=HL, label="RW-West-N"),
    create_wall(50, 38, 0, 50, 44, 0, LEVEL, EXT, height=HL, label="RW-West-S"),
]
walls['right'] = rw
print(f"  Right wing: {rw}")

# ── FLOORS ────────────────────────────────────────────────────
print("\n[FLOORS]")
f1 = smart_floor(LEVEL, 0,  0,  8, 22, 44)
f2 = smart_floor(LEVEL, 0, 22, 14, 50, 38)
f3 = smart_floor(LEVEL, 0, 50,  8, 72, 44)
f4 = smart_floor(LEVEL, 0, 22,  0, 50,  8)   # back porch
f5 = smart_floor(LEVEL, 0, 22, 44, 50, 54)   # front porch
print(f"  LW floor: {f1} | Bridge floor: {f2} | RW floor: {f3}")
print(f"  Back porch floor: {f4} | Front porch floor: {f5}")

# ── ROOFS ─────────────────────────────────────────────────────
print("\n[ROOFS]")
# Left wing — gable at 11ft walls → Level 2.0 = z=11
r_lw = make_roof("LW-Roof", 0, 8, 22, 44,
                 level_name="Level 2.0", pitch=0.25, slope_style="gable", overhang=1.5)
# Center bridge — gable at 16ft walls → need a level at z=16
# Use Level 2.0 + top_offset trick: create roof at Level 2.0 with base_offset=5
# Actually: bridge walls are 16ft. Level 2.0 = z=11. We need roof base at z=16.
# Workaround: use make_roof with level_name="Level 2.0" but add top_offset via set_parameter_value after
r_cb = make_roof("CB-Roof", 22, 14, 50, 38,
                 level_name="Level 2.0", pitch=0.333, slope_style="gable", overhang=1.5)
# Right wing — gable at 11ft walls
r_rw = make_roof("RW-Roof", 50, 8, 72, 44,
                 level_name="Level 2.0", pitch=0.25, slope_style="gable", overhang=1.5)
# Back porch — shed
r_bp = make_roof("BackPorch-Roof", 22, 0, 50, 8,
                 level_name="Level 2.0", pitch=0.083, slope_style="shed", overhang=0.5)
# Front porch — shed (posts at y=54, large y = low end, no offset needed)
r_fp = make_roof("FrontPorch-Roof", 22, 44, 50, 54,
                 level_name="Level 2.0", pitch=0.083, slope_style="shed", overhang=0.5)
print(f"  LW: {r_lw} | Bridge: {r_cb} | RW: {r_rw}")
print(f"  Back porch: {r_bp} | Front porch: {r_fp}")

# Lift center bridge roof to match 16ft wall height
# Roof base is at Level 2.0 (z=11) — need to add 5ft offset so ridge starts at z=16
print("\n[LIFT CENTER BRIDGE ROOF to 16ft]")
for param in ['Base Offset', 'Base Level Offset']:
    r = _call('revit.set_parameter_value', {
        'element_id': r_cb,
        'parameter_name': param,
        'value': 5.0
    })
    status = r.get('Result', {}).get('status', 'err') if r else 'err'
    print(f"  {param}: {status}")

# ── ATTACH WALLS TO ROOFS ─────────────────────────────────────
print("\n[ATTACH WALLS]")
attach_walls_to_roof(walls['left'],   r_lw)
attach_walls_to_roof(walls['center'], r_cb)
attach_walls_to_roof(walls['right'],  r_rw)

# ── PORCH POSTS ───────────────────────────────────────────────
print("\n[PORCH POSTS]")
# Back porch: posts at y=0 (small y = HIGH end of shed) → needs Top Offset
place_porch_posts([22, 32, 42, 50], 0, LEVEL,
                  roof_pitch=0.083, porch_depth=8,
                  shed_slopes_toward_larger_y=False)
# Front porch: posts at y=54 (large y = LOW end of shed) → no offset
place_porch_posts([22, 32, 42, 50], 54, LEVEL,
                  roof_pitch=0.083, porch_depth=10,
                  shed_slopes_toward_larger_y=True)

print("\n" + "=" * 60)
print("STAGE 1 COMPLETE — 51239941")
print("H-shape: left 11ft | center 16ft bridge | right 11ft")
print("Living: ~2,256 SF | No garage")
print("Review in Revit → approve for Stage 2")
print("=" * 60)
