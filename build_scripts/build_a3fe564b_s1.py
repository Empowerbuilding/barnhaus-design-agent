"""
build_a3fe564b_s1.py — STAGE 1
Submission: a3fe564b | Test User | 3000 SF | 4bd | Rectangle | Hill Country
Stage 1: Exterior walls + floor + roof + porch posts
STOP after this stage for visual review.

Footprint:
  Main house:  x=0→80,  y=0→40  (80×40 = 3,200 SF)
  Garage:      x=58→80, y=40→64 (22×24 = 528 SF, 2-car attached right-rear)
  L-shape total footprint

Roof: 1:12 shed (high front, low rear) — standing seam metal
Wall height: 11ft, upper_limit_level="Level 2.0"
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils_v2 import *

SUB_ID = "a3fe564b"

# ── Confirm bridge healthy ──
if not health_check():
    print("❌ Bridge not healthy — open Revit first")
    sys.exit(1)

# ── Dimensions ──
# Main house
HX0, HY0, HX1, HY1 = 0, 0, 80, 40
# Garage (attached right rear)
GX0, GY0, GX1, GY1 = 58, 40, 80, 64

WALL_H = 11.0
LEVEL  = "Level 1.0"
UPPER  = "Level 2.0"

print("\n=== STAGE 1: EXTERIOR WALLS ===")

# ── Main house exterior walls (L-shape) ──
# South wall: full width
r = create_wall(HX0, HY0, HX1, HY0, WALL["EXT"], LEVEL, WALL_H, UPPER, "S-main")
print(f"S wall: {r.get('result', r.get('error'))}")

# East wall: full depth of main house
r = create_wall(HX1, HY0, HX1, HY1, WALL["EXT"], LEVEL, WALL_H, UPPER, "E-main")
print(f"E wall: {r.get('result', r.get('error'))}")

# NOTE: HX1==GX1==80, so N-main-right has zero length — omitted

# Garage east wall (continuous with main north)
r = create_wall(GX1, HY1, GX1, GY1, WALL["EXT"], LEVEL, WALL_H, UPPER, "E-garage")
print(f"E-garage wall: {r.get('result', r.get('error'))}")

# Garage south wall (rear)
r = create_wall(GX1, GY1, GX0, GY1, WALL["EXT"], LEVEL, WALL_H, UPPER, "S-garage-rear")
print(f"S-garage rear: {r.get('result', r.get('error'))}")

# Garage west wall (from rear to main house north)
r = create_wall(GX0, GY1, GX0, HY1, WALL["EXT"], LEVEL, WALL_H, UPPER, "W-garage")
print(f"W-garage wall: {r.get('result', r.get('error'))}")

# North wall of main house: from west to garage west face
r = create_wall(GX0, HY1, HX0, HY1, WALL["EXT"], LEVEL, WALL_H, UPPER, "N-main-left")
print(f"N wall left: {r.get('result', r.get('error'))}")

# West wall: full depth of main house
r = create_wall(HX0, HY1, HX0, HY0, WALL["EXT"], LEVEL, WALL_H, UPPER, "W-main")
print(f"W wall: {r.get('result', r.get('error'))}")

print("\n=== STAGE 1: FLOOR ===")
# Single L-shape polygon — never two overlapping floors
# HX1==GX1 so skip duplicate point — L-shape is really a rectangle with garage on right rear
boundary = [
    {"x": HX0, "y": HY0},
    {"x": HX1, "y": HY0},
    {"x": HX1, "y": GY1},   # east wall goes full depth incl garage
    {"x": GX0, "y": GY1},   # garage rear
    {"x": GX0, "y": HY1},   # step in at garage west
    {"x": HX0, "y": HY1},   # west
]
r = create_floor_polygon(boundary, floor_type=None, level=LEVEL, label="main+garage slab")
print(f"Floor: {r.get('result', r.get('error'))}")

print("\n=== STAGE 1: ROOF ===")
# Main house roof — 1:12 shed on Level 2.0 (top of 11ft walls)
roof_boundary = [
    {"x": HX0, "y": HY0},
    {"x": HX1, "y": HY0},
    {"x": HX1, "y": HY1},
    {"x": HX0, "y": HY1},
]
r = make_roof(roof_boundary,
              roof_type='13" Roof No Gyp',
              level_name="Level 2.0",
              pitch=1.0,
              label="main-shed-roof")
print(f"Main roof: {r.get('result', r.get('error'))}")

# Garage roof — same 1:12 shed
garage_roof_boundary = [
    {"x": GX0, "y": HY1},
    {"x": GX1, "y": HY1},
    {"x": GX1, "y": GY1},
    {"x": GX0, "y": GY1},
]
r = make_roof(garage_roof_boundary,
              roof_type='13" Roof No Gyp',
              level_name="Level 2.0",
              pitch=1.0,
              label="garage-shed-roof")
print(f"Garage roof: {r.get('result', r.get('error'))}")

print("\n✅ STAGE 1 COMPLETE")
print("→ Check Revit: walls, floor slab, and roof should be visible")
print("→ Confirm footprint looks correct before running Stage 2")
checkpoint_save(SUB_ID, 1, [])
