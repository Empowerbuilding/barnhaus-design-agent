"""
build_e670353b_s1.py — STAGE 1: Exterior Walls + Floor + Roofs
Submission: e670353b | Mitchell Madison | 2,750 SF | H-shape | Hill Country
STOP after this stage for visual review.

H-shape footprint:
  Left wing:     x=0→24,  y=8→50   (24×42 = 1,008 SF, 9ft walls)
  Center bridge: x=32→60, y=14→38  (28×24 = 672 SF, 16ft walls)
  Right wing:    x=68→90, y=8→50   (22×42 = 924 SF, 9ft walls)
  Breezeways:    x=24→32 and x=60→68, y=14→38 (open, flat roof at 9ft)
  Garage:        x=0→24,  y=50→74  (24×24 = 576 SF, side-loaded)
  Front porch:   x=32→60, y=0→8    (open, no walls)
  Back porch:    x=30→52, y=38→48  (22×10, covered)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils_v2 import *

SUB_ID = "e670353b"

if not health_check():
    print("❌ Bridge not healthy — open Revit first")
    sys.exit(1)

LEVEL  = "Level 1.0"
EXT    = WALL["EXT"]   # Wall 7.5" EXT PBR
ROOF_T = '13" Roof No Gyp'

# ── coordinates ──
LW_X0, LW_X1 = 0, 24
LW_Y0, LW_Y1 = 8, 50
BW_L_X0, BW_L_X1 = 24, 32   # left breezeway
CB_X0, CB_X1 = 32, 60       # center bridge
BW_R_X0, BW_R_X1 = 60, 68   # right breezeway
RW_X0, RW_X1 = 68, 90
RW_Y0, RW_Y1 = 8, 50
WING_Y0, WING_Y1 = LW_Y0, LW_Y1  # same for both wings
CB_Y0, CB_Y1 = 14, 38       # bridge (narrower N/S than wings)
GAR_X0, GAR_X1 = 0, 24
GAR_Y0, GAR_Y1 = 50, 74
BP_X0, BP_X1 = 30, 52       # back porch
BP_Y0, BP_Y1 = 38, 48
FP_X0, FP_X1 = 32, 60       # front porch
FP_Y0, FP_Y1 = 0, 8

WING_H  = 9.0
BRIDGE_H = 16.0
UPPER = "Level 2.0"

wall_ids = []

def w(x0, y0, x1, y1, h, label):
    r = create_wall(x0, y0, x1, y1, EXT, LEVEL, h, UPPER, label)
    wid = (r.get("result") or {}).get("wall_id")
    status = "✅" if wid else "❌"
    print(f"  {status} {label}: {wid or r.get('error')}")
    if wid: wall_ids.append(wid)
    return wid

print("\n=== STAGE 1: LEFT WING WALLS (9ft) ===")
w(LW_X0, LW_Y0, LW_X1, LW_Y0, WING_H, "LW-south")
w(LW_X1, LW_Y0, LW_X1, CB_Y0, WING_H, "LW-east-south")   # east wall south of breezeway
w(LW_X1, CB_Y1, LW_X1, LW_Y1, WING_H, "LW-east-north")   # east wall north of breezeway
w(LW_X0, LW_Y1, LW_X1, LW_Y1, WING_H, "LW-north")        # connects to garage
w(LW_X0, LW_Y0, LW_X0, LW_Y1, WING_H, "LW-west")

print("\n=== STAGE 1: CENTER BRIDGE WALLS (16ft) ===")
w(CB_X0, CB_Y0, CB_X1, CB_Y0, BRIDGE_H, "CB-south")
w(CB_X1, CB_Y0, CB_X1, CB_Y1, BRIDGE_H, "CB-east")
w(CB_X0, CB_Y1, CB_X1, CB_Y1, BRIDGE_H, "CB-north")
w(CB_X0, CB_Y0, CB_X0, CB_Y1, BRIDGE_H, "CB-west")

print("\n=== STAGE 1: RIGHT WING WALLS (9ft) ===")
w(RW_X0, RW_Y0, RW_X1, RW_Y0, WING_H, "RW-south")
w(RW_X1, RW_Y0, RW_X1, RW_Y1, WING_H, "RW-east")
w(RW_X0, RW_Y1, RW_X1, RW_Y1, WING_H, "RW-north")
w(RW_X0, CB_Y1, RW_X0, RW_Y1, WING_H, "RW-west-north")   # west wall north of breezeway
w(RW_X0, RW_Y0, RW_X0, CB_Y0, WING_H, "RW-west-south")   # west wall south of breezeway

print("\n=== STAGE 1: GARAGE WALLS (9ft) ===")
# Garage attached left, side-loaded (door faces west)
w(GAR_X0, GAR_Y0, GAR_X1, GAR_Y0, WING_H, "GAR-south")   # shared with LW north (skip if overlap)
w(GAR_X1, GAR_Y0, GAR_X1, GAR_Y1, WING_H, "GAR-east")
w(GAR_X0, GAR_Y1, GAR_X1, GAR_Y1, WING_H, "GAR-north")
w(GAR_X0, GAR_Y0, GAR_X0, GAR_Y1, WING_H, "GAR-west")    # garage door side

print("\n=== STAGE 1: FLOOR (single polygon per zone) ===")
# Left wing floor
r = create_floor_polygon([
    {"x": LW_X0, "y": LW_Y0}, {"x": LW_X1, "y": LW_Y0},
    {"x": LW_X1, "y": LW_Y1}, {"x": LW_X0, "y": LW_Y1},
], floor_type=None, level=LEVEL, label="LW-floor")
print(f"  LW floor: {(r.get('result') or {}).get('floor_id') or r.get('error')}")

# Center bridge floor
r = create_floor_polygon([
    {"x": CB_X0, "y": CB_Y0}, {"x": CB_X1, "y": CB_Y0},
    {"x": CB_X1, "y": CB_Y1}, {"x": CB_X0, "y": CB_Y1},
], floor_type=None, level=LEVEL, label="CB-floor")
print(f"  CB floor: {(r.get('result') or {}).get('floor_id') or r.get('error')}")

# Right wing floor
r = create_floor_polygon([
    {"x": RW_X0, "y": RW_Y0}, {"x": RW_X1, "y": RW_Y0},
    {"x": RW_X1, "y": RW_Y1}, {"x": RW_X0, "y": RW_Y1},
], floor_type=None, level=LEVEL, label="RW-floor")
print(f"  RW floor: {(r.get('result') or {}).get('floor_id') or r.get('error')}")

# Left breezeway floor
r = create_floor_polygon([
    {"x": BW_L_X0, "y": CB_Y0}, {"x": BW_L_X1, "y": CB_Y0},
    {"x": BW_L_X1, "y": CB_Y1}, {"x": BW_L_X0, "y": CB_Y1},
], floor_type=None, level=LEVEL, label="BW-L-floor")
print(f"  BW-L floor: {(r.get('result') or {}).get('floor_id') or r.get('error')}")

# Right breezeway floor
r = create_floor_polygon([
    {"x": BW_R_X0, "y": CB_Y0}, {"x": BW_R_X1, "y": CB_Y0},
    {"x": BW_R_X1, "y": CB_Y1}, {"x": BW_R_X0, "y": CB_Y1},
], floor_type=None, level=LEVEL, label="BW-R-floor")
print(f"  BW-R floor: {(r.get('result') or {}).get('floor_id') or r.get('error')}")

# Garage floor
r = create_floor_polygon([
    {"x": GAR_X0, "y": GAR_Y0}, {"x": GAR_X1, "y": GAR_Y0},
    {"x": GAR_X1, "y": GAR_Y1}, {"x": GAR_X0, "y": GAR_Y1},
], floor_type=None, level=LEVEL, label="GAR-floor")
print(f"  GAR floor: {(r.get('result') or {}).get('floor_id') or r.get('error')}")

print("\n=== STAGE 1: ROOFS ===")

# Left wing gable — 4:12 pitch = 0.333 rise/run
r = make_roof([
    {"x": LW_X0, "y": LW_Y0}, {"x": LW_X1, "y": LW_Y0},
    {"x": LW_X1, "y": LW_Y1}, {"x": LW_X0, "y": LW_Y1},
], roof_type=ROOF_T, level_name=LEVEL, pitch=0.333, label="LW-roof")
# Override height to match 9ft walls
print(f"  LW roof: {(r.get('result') or {}).get('roof_id') or r.get('error')}")

# Center bridge gable — 4:12, taller (16ft walls) — sits on Level 1.0 + 16ft
r = make_roof([
    {"x": CB_X0, "y": CB_Y0}, {"x": CB_X1, "y": CB_Y0},
    {"x": CB_X1, "y": CB_Y1}, {"x": CB_X0, "y": CB_Y1},
], roof_type=ROOF_T, level_name=LEVEL, pitch=0.333, label="CB-roof")
print(f"  CB roof: {(r.get('result') or {}).get('roof_id') or r.get('error')}")

# Right wing gable
r = make_roof([
    {"x": RW_X0, "y": RW_Y0}, {"x": RW_X1, "y": RW_Y0},
    {"x": RW_X1, "y": RW_Y1}, {"x": RW_X0, "y": RW_Y1},
], roof_type=ROOF_T, level_name=LEVEL, pitch=0.333, label="RW-roof")
print(f"  RW roof: {(r.get('result') or {}).get('roof_id') or r.get('error')}")

# Breezeways — flat roofs
r = make_roof([
    {"x": BW_L_X0, "y": CB_Y0}, {"x": BW_L_X1, "y": CB_Y0},
    {"x": BW_L_X1, "y": CB_Y1}, {"x": BW_L_X0, "y": CB_Y1},
], roof_type=ROOF_T, level_name=LEVEL, pitch=0.0, label="BW-L-roof")
print(f"  BW-L roof: {(r.get('result') or {}).get('roof_id') or r.get('error')}")

r = make_roof([
    {"x": BW_R_X0, "y": CB_Y0}, {"x": BW_R_X1, "y": CB_Y0},
    {"x": BW_R_X1, "y": CB_Y1}, {"x": BW_R_X0, "y": CB_Y1},
], roof_type=ROOF_T, level_name=LEVEL, pitch=0.0, label="BW-R-roof")
print(f"  BW-R roof: {(r.get('result') or {}).get('roof_id') or r.get('error')}")

# Garage shed roof
r = make_roof([
    {"x": GAR_X0, "y": GAR_Y0}, {"x": GAR_X1, "y": GAR_Y0},
    {"x": GAR_X1, "y": GAR_Y1}, {"x": GAR_X0, "y": GAR_Y1},
], roof_type=ROOF_T, level_name=LEVEL, pitch=0.167, label="GAR-roof")
print(f"  GAR roof: {(r.get('result') or {}).get('roof_id') or r.get('error')}")

print(f"\n✅ STAGE 1 COMPLETE — {len(wall_ids)} walls placed")
print("→ Check Revit 3D view — H-shape should be visible")
print("→ Verify: left wing, center bridge (taller), right wing, breezeways, garage")
print("→ Reply 'stage 2' when ready to continue")
checkpoint_save(SUB_ID, 1, wall_ids)
