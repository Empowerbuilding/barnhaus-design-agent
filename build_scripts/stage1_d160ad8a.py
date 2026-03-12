"""
STAGE 1 — Exterior Walls + Floor + Garage
Submission: d160ad8a | Mitchell Madison | H-Shape | 3,250 SF | Single Story | Hill Country
3 bed / 3 bath | 3-car garage attached SW | mudroom + butler pantry + covered back porch

FOOTPRINT:
  West wing  (master + service): x=0-22,  y=22-60  (836 SF)
  Main body  (living core):      x=22-68, y=22-60  (1,748 SF)
  East wing  (bed wing):         x=68-84, y=22-60  (608 SF)
  Back porch (covered, N):       x=22-68, y=60-72  (552 SF)
  Garage     (3-car, attached):  x=0-36,  y=0-22   (792 SF)

  Total living: ~3,192 SF

ORIENTATION:
  South (y=22) = front/entry side
  North (y=60-72) = rear/view/back porch
  West  (x=0)  = master side
  East  (x=84) = bed wing side
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    call, create_wall, create_garage,
    smart_floor, make_roof,
    label_rooms
)

LEVEL = "Level 1.0"
EXT  = 'Wall 7.5" EXT PBR'
H    = 11   # standard wall height
GH   = 12   # garage wall height

print("=" * 60)
print("STAGE 1 — d160ad8a — Exterior Shell")
print("=" * 60)

# ── GARAGE (3-car, attached SW) ───────────────────────────────
print("\n[1/5] Garage...")
g = create_garage(0, 0, 36, 22, 0, LEVEL, EXT,
                  height=GH, garage_cars=3,
                  door_face="south",
                  label="Garage")
print(f"  Garage walls: {g}")

# ── EXTERIOR WALLS — H-SHAPE HOUSE ───────────────────────────
print("\n[2/5] H-shape exterior walls...")

walls = []

# WEST WING — west & north faces
w = create_wall(0,22,0, 0,60,0, LEVEL, EXT, height=H, label="WW-west")
walls.append(w); print(f"  WW west:  {w}")

w = create_wall(0,60,0, 22,60,0, LEVEL, EXT, height=H, label="WW-north")
walls.append(w); print(f"  WW north: {w}")

# BACK PORCH — open, posts only (no enclosing walls)
# 4 HSS6x6 steel posts on outer north face (y=72) at x=22,37,52,68
# (placed after roofs below)

# EAST WING — north, east, south faces
w = create_wall(68,60,0, 84,60,0, LEVEL, EXT, height=H, label="EW-north")
walls.append(w); print(f"  EW north: {w}")

w = create_wall(84,60,0, 84,22,0, LEVEL, EXT, height=H, label="EW-east")
walls.append(w); print(f"  EW east:  {w}")

w = create_wall(84,22,0, 68,22,0, LEVEL, EXT, height=H, label="EW-south")
walls.append(w); print(f"  EW south: {w}")

# MAIN BODY — south face (exposed between garage and east wing)
w = create_wall(68,22,0, 36,22,0, LEVEL, EXT, height=H, label="MB-south")
walls.append(w); print(f"  MB south: {w}")

print(f"\n  Total house walls placed: {len(walls)}")

# ── FLOORS ────────────────────────────────────────────────────
print("\n[3/5] Floors...")

# Single polygon floor — entire footprint, no overlaps
# Vertices trace the full perimeter (CCW from SW corner of garage):
# Garage SW → Garage SE → House SE → House NE → Porch NE → Porch NW → House NW → Garage NW
from barnhaus_revit_utils import call as _call
boundary = [
    {"x":  0, "y":  0},   # Garage SW
    {"x": 36, "y":  0},   # Garage SE
    {"x": 36, "y": 22},   # Garage NE / House join
    {"x": 84, "y": 22},   # House SE
    {"x": 84, "y": 60},   # House NE
    {"x": 68, "y": 60},   # Porch SE
    {"x": 68, "y": 72},   # Porch NE
    {"x": 22, "y": 72},   # Porch NW
    {"x": 22, "y": 60},   # Porch SW
    {"x":  0, "y": 60},   # House NW
    {"x":  0, "y":  0},   # back to start
]
r = _call("revit.create_floor", {"level": LEVEL, "boundary_points": boundary})
fid = r.get("Result", {}).get("floor_id", "ERR")
print(f"  Single polygon floor: {fid}")

# ── ROOF (gable, hill country) ────────────────────────────────
print("\n[4/5] Roof...")

# Main house roof (covers west wing + main body + east wing)
r1 = make_roof("MainRoof", 0, 22, 84, 60,
               level_name="Level 2.0",
               pitch=0.5, slope_style="gable",
               overhang=1.5)
print(f"  Main roof: {r1}")

# Back porch roof (shed, slopes north)
r2 = make_roof("PorchRoof", 22, 60, 68, 72,
               level_name="Level 2.0",
               pitch=0.083, slope_style="shed",
               overhang=0.5)
print(f"  Porch roof: {r2}")

# Garage roof (shed, slopes south away from house)
r3 = make_roof("GarageRoof", 0, 0, 36, 22,
               level_name="Level 2.0",
               pitch=0.083, slope_style="shed",
               overhang=0.5)
print(f"  Garage roof: {r3}")

# ── PORCH POSTS ───────────────────────────────────────────────
print("\n[5a/5] Back porch posts...")
from barnhaus_revit_utils import place_fixture
for px in [22, 37, 52, 68]:
    r = place_fixture('HSS-Hollow Structural Section-Column', 'HSS6X6X3/16',
                      px, 72, 0, LEVEL, label=f'Porch Post {px}')
    print(f"  Post ({px},72): {r}")

# ── ROOM LABEL (placeholder for Stage 1 verification) ─────────
print("\n[5/5] Stage 1 room label...")
label_rooms([
    ("H-Shape Shell", 42, 40),
], LEVEL, upper_limit_level="Level 2.0")

print("\n" + "=" * 60)
print("STAGE 1 COMPLETE")
print(f"Footprint: 84 x 72 ft")
print(f"Living area: ~3,192 SF")
print(f"Garage: 36 x 22 = 792 SF (3-car)")
print(f"Back porch: 46 x 12 = 552 SF covered")
print("=" * 60)
print("\nReview in Revit. Approve to proceed to Stage 2 (interior walls).")
