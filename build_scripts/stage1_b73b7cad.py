"""
STAGE 1 — Exterior Shell
Submission: b73b7cad | Mitchell Madison | L-shape | 2,750 SF | Single Story | Contemporary
3 bed / 3 bath | 2-car garage attached right/south | covered back porch + front porch

FOOTPRINT:
  Main bar:    x=0-70,  y=22-54  (70×32 = 2,240 SF)
  Garage arm:  x=48-70, y=0-22   (22×22 =   484 SF, door south)
  Back porch:  x=25-45, y=54-66  (20×12 posts only)
  Front porch: x=24-44, y=10-22  (20×12 posts only)

ORIENTATION:
  South (y=22) = front/entry (street)
  North (y=54) = rear/back porch/view
  West  (x=0)  = bed wing side
  East  (x=70) = master/garage side

L-SHAPE PERIMETER (clockwise from SW):
  (0,22)→(0,54)→(70,54)→(70,0)→(48,0)→(48,22)→(0,22)

ZONE LAYOUT:
  x=0-20:  Bed wing  (beds 2&3, J&J bath, hallway)
  x=20-50: Living core (great room, kitchen, dining)
  x=50-70: Master zone (master bed, bath, WIC, laundry, mudroom)
  x=48-70, y=0-22: Garage (2-car, door south)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, create_garage, smart_floor, make_roof,
    attach_walls_to_roof, place_fixture, place_porch_posts, call as _call
)

LEVEL = "Level 1.0"
EXT   = 'Wall 7.5" EXT PBR'
H     = 11   # standard wall height
GH    = 12   # garage height

print("=" * 60)
print("STAGE 1 — b73b7cad — Exterior Shell")
print("=" * 60)

# ── GARAGE (2-car, attached SE) ───────────────────────────────
print("\n[1/6] Garage...")
g = create_garage(48, 0, 70, 22, 0, LEVEL, EXT,
                  height=GH, garage_cars=2,
                  door_face="south", label="Garage")
print(f"  Garage: {g}")

# ── L-SHAPE EXTERIOR WALLS ────────────────────────────────────
print("\n[2/6] L-shape exterior walls...")
walls = []

# West face (x=0, y=22-54)
w = create_wall(0,22,0, 0,54,0, LEVEL, EXT, height=H, label="West")
walls.append(w); print(f"  West: {w}")

# North face (y=54, x=0-70)
w = create_wall(0,54,0, 70,54,0, LEVEL, EXT, height=H, label="North")
walls.append(w); print(f"  North: {w}")

# East face (x=70, y=0-54) — continuous, covers main bar + garage
w = create_wall(70,54,0, 70,0,0, LEVEL, EXT, height=H, label="East-main")
walls.append(w); print(f"  East: {w}")

# Garage south (y=0, x=48-70) — already created by create_garage
# Garage west/inner corner (x=48, y=0-22)
w = create_wall(48,0,0, 48,22,0, LEVEL, EXT, height=H, label="Inner-corner")
walls.append(w); print(f"  Inner corner: {w}")

# South face of main bar (y=22, x=0-48)
w = create_wall(48,22,0, 0,22,0, LEVEL, EXT, height=H, label="South")
walls.append(w); print(f"  South: {w}")

print(f"\n  Total exterior walls: {len(walls)}")

# ── SINGLE POLYGON FLOOR ──────────────────────────────────────
print("\n[3/6] Floors...")

# Main house — L-shape polygon (no overlaps)
boundary = [
    {"x":  0, "y": 22},   # SW corner of main bar
    {"x":  0, "y": 54},   # NW corner
    {"x": 70, "y": 54},   # NE corner
    {"x": 70, "y":  0},   # SE corner (garage)
    {"x": 48, "y":  0},   # garage SW
    {"x": 48, "y": 22},   # inner L corner
    {"x":  0, "y": 22},   # back to start
]
r = _call("revit.create_floor", {"level": LEVEL, "boundary_points": boundary})
fid = r.get("Result", {}).get("floor_id", "ERR")
print(f"  L-shape floor: {fid}")

# Back porch floor
f2 = smart_floor(LEVEL, 0, 25, 54, 45, 66)
print(f"  Back porch floor: {f2}")

# Front porch floor
f3 = smart_floor(LEVEL, 0, 24, 10, 44, 22)
print(f"  Front porch floor: {f3}")

# ── ROOFS ─────────────────────────────────────────────────────
print("\n[4/6] Roofs...")

# Main house gable (contemporary = shallower 4:12 pitch)
r1 = make_roof("MainRoof", 0, 22, 70, 54,
               level_name="Level 2.0",
               pitch=0.333, slope_style="gable",
               overhang=1.5)
print(f"  Main roof: {r1}")

# Garage roof (shed)
r2 = make_roof("GarageRoof", 48, 0, 70, 22,
               level_name="Level 2.0",
               pitch=0.083, slope_style="shed",
               overhang=0.5)
print(f"  Garage roof: {r2}")

# Back porch roof (shed)
r3 = make_roof("BackPorchRoof", 25, 54, 45, 66,
               level_name="Level 2.0",
               pitch=0.083, slope_style="shed",
               overhang=0.5)
print(f"  Back porch roof: {r3}")

# Front porch roof (shed)
r4 = make_roof("FrontPorchRoof", 24, 10, 44, 22,
               level_name="Level 2.0",
               pitch=0.083, slope_style="shed",
               overhang=0.5)
print(f"  Front porch roof: {r4}")

# ── ATTACH WALLS TO ROOFS ─────────────────────────────────────
print("\n[5/6] Attach walls to roofs...")
attach_walls_to_roof(walls, r1)
garage_walls = [g['south'], g['north'], g['west'], g['east']]
attach_walls_to_roof(garage_walls, r2)

# ── PORCH POSTS ───────────────────────────────────────────────
print("\n[6/6] Porch posts...")
COL = 'HSS-Hollow Structural Section-Column'
TYP = 'HSS6X6X3/16'

# Back porch — posts at y=66 (large y = low end of shed, no offset needed)
place_porch_posts([25, 32, 38, 45], 66, LEVEL,
                  roof_pitch=0.083, porch_depth=12,
                  shed_slopes_toward_larger_y=True)

# Front porch — posts at y=10 (small y = HIGH end of shed, needs Top Offset)
place_porch_posts([24, 34, 44], 10, LEVEL,
                  roof_pitch=0.083, porch_depth=12,
                  shed_slopes_toward_larger_y=False)

print("\n" + "=" * 60)
print("STAGE 1 COMPLETE — b73b7cad")
print("Footprint: 70×32 main bar + 22×22 garage arm")
print("Living: ~2,240 SF | Garage: 484 SF")
print("=" * 60)
print("\nReview in Revit → approve to proceed to Stage 2.")
