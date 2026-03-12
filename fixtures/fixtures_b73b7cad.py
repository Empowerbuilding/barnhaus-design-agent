"""
STAGE 4 — Fixtures, Cabinets & Room Labels
Submission: b73b7cad | L-shape | Contemporary

ROOMS:
  Bed 3        : x=0-16,  y=22-34
  J&J Bath     : x=0-16,  y=34-42
  Bed 2        : x=0-16,  y=42-54
  Hallway      : x=16-20, y=22-54
  Dining       : x=20-34, y=22-38  (open plan)
  Kitchen      : x=34-50, y=22-38  (open plan, SE of living core)
  Great Room   : x=20-50, y=38-54
  Laundry      : x=50-60, y=22-30
  Mudroom      : x=60-70, y=22-30
  Master Bath  : x=50-64, y=30-42
  WIC          : x=64-70, y=30-42
  Master Bed   : x=50-70, y=42-54
  Garage       : x=48-70, y=0-22

WALL FACE ROTATION CONVENTION (empirically confirmed):
  'S' (north wall face) = rotation 0   → front faces south
  'N' (south wall face) = rotation 180 → front faces north
  'E' (west wall face)  = rotation 90  → front faces east
  'W' (east wall face)  = rotation 270 → front faces west
"""

import sys, time
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_against_wall, place_fixture, create_room

LEVEL = 'Level 1.0'
UL    = 'Level 2.0'   # upper limit for L1 rooms

# Families
BASE  = 'Base Cabinet-Double Door & 1 Drawer'
BSNK  = 'Base Cabinet-Double Door Sink Unit'
UPPER = 'Upper Cabinet-Double Door-Wall'
TALL  = 'Tall Cabinet-Double Door'
VSINK = 'Vanity Cabinet-Double Door Sink Unit'
VDRAW = 'Vanity Cabinet-3 Drawers'
TOILET= 'Toilet-Domestic-3D'
SHOWER= 'Shower_columns_15486'
RANGE = 'Range-Gas'
HOOD  = 'Hood-Wall'
DW    = 'Dishwasher'
KSINK = 'Sink Kitchen-Single'
FRIDGE= 'Refrigerator'

print("=" * 60)
print("STAGE 4 — b73b7cad — Fixtures & Room Labels")
print("=" * 60)

# ── DOOR POSITIONS (wall_coord, pos_along, width_ft, clearance_ft) ──────────
# Used to prevent fixtures from blocking doorways

DOORS_Y22  = [(22, 35, 3, 2)]                    # front entry x=35 on south wall
DOORS_X50  = [(50, 26, 2.5, 2), (50, 36, 3, 2)] # laundry door y=26, master entry y=36
DOORS_X16  = [(16, 28, 2.5, 2), (16, 38, 2.5, 2), (16, 48, 2.5, 2)]  # bed wing doors
DOORS_X20  = [(20, 38, 3, 2)]                    # hallway/living door
DOORS_Y30  = [(30, None, 0, 0)]                  # no doors on service/bath divide
DOORS_X60  = [(60, 26, 2.5, 2)]                  # mudroom/laundry door
DOORS_Y42  = [(42, 57, 2.5, 2)]                  # master bath/bed door
DOORS_X64  = [(64, 36, 2.5, 2)]                  # WIC door

# ── KITCHEN (SE quadrant of living core, x=34-50, y=22-38) ───
print("\n— Kitchen —")
# South wall (y=22): front entry at x=35 — keep cabs away from it
place_against_wall(BASE,  '36"',       22, 'N', 40,   0, LEVEL, door_positions=DOORS_Y22, label='Kcab S1')
place_against_wall(RANGE, '36"',       22, 'N', 43,   0, LEVEL, door_positions=DOORS_Y22, label='Range')
place_against_wall(HOOD,  '36"',       22, 'N', 43, 6.5, LEVEL, door_positions=DOORS_Y22, label='Hood')
place_against_wall(BASE,  '36"',       22, 'N', 46,   0, LEVEL, door_positions=DOORS_Y22, label='Kcab S2')
place_against_wall(BSNK,  '36"',       22, 'N', 49,   0, LEVEL, door_positions=DOORS_Y22, label='KSink Base')
place_against_wall(KSINK, '30" x 21"', 22, 'N', 49, 0.9, LEVEL, door_positions=DOORS_Y22, fixture_depth=0.875, label='KSink')
place_against_wall(UPPER, '36"', 22, 'N', 40, 5.5, LEVEL, door_positions=DOORS_Y22, label='Upper S1')
place_against_wall(UPPER, '36"', 22, 'N', 46, 5.5, LEVEL, door_positions=DOORS_Y22, label='Upper S2')

# East wall of kitchen (x=50): laundry door swings INTO laundry (east) — no conflict
# on kitchen side. Master entry at y=36 swings into master zone (east) — also fine.
# So DOORS_X50 is empty for kitchen-side placement.
DOORS_X50_KITCHEN = []
place_against_wall(FRIDGE, '24" LH',  50, 'W', 24,   0, LEVEL, door_positions=DOORS_X50_KITCHEN, label='Fridge')
place_against_wall(DW,     '24"',     50, 'W', 29,   0, LEVEL, door_positions=DOORS_X50_KITCHEN, label='DW')
place_against_wall(BASE,   '36"',     50, 'W', 33,   0, LEVEL, door_positions=DOORS_X50_KITCHEN, label='Kcab E1')
place_against_wall(UPPER,  '36"',     50, 'W', 33, 5.5, LEVEL, door_positions=DOORS_X50_KITCHEN, label='Upper E1')
place_against_wall(TALL,   '48"',     50, 'W', 37,   0, LEVEL, door_positions=DOORS_X50_KITCHEN, label='Pantry')

# ── J&J BATH (x=0-16, y=34-42) ───────────────────────────────
print("\n— J&J Bath —")
# x=16 wall has doors at y=38 (bath door) — vanity on south wall y=34, toilet + shower away from door
DOORS_Y34  = []  # no doors on bed3/bath divide (y=34)
DOORS_Y42B = []  # no doors on bath/bed2 divide (y=42)
place_against_wall(VSINK,  '36"',               34, 'N',  8,   0, LEVEL, door_positions=DOORS_Y34,  label='JJ Vanity')
place_against_wall(TOILET, 'Toilet-Domestic-3D', 42, 'S',  5,   0, LEVEL, door_positions=DOORS_Y42B, fixture_depth=1.25, label='JJ Toilet')
place_against_wall(SHOWER, 'Shower_columns_15486', 0, 'E', 40,   0, LEVEL, door_positions=DOORS_X16,  fixture_depth=0.5,  label='JJ Shower')

# ── MASTER BATH (x=50-64, y=30-42) ───────────────────────────
print("\n— Master Bath —")
# y=30 wall: no doors. x=64 wall: WIC door at y=36. y=42 wall: master bath/bed door at y=57
place_against_wall(VSINK,  '36"',               30, 'N', 54,   0, LEVEL, label='MB Vanity L')
place_against_wall(VSINK,  '36"',               30, 'N', 60,   0, LEVEL, label='MB Vanity R')
# Toilet on east wall (x=64): WIC door at y=36, push toilet south to y=32
place_against_wall(TOILET, 'Toilet-Domestic-3D', 64, 'W', 32, 0, LEVEL, door_positions=DOORS_X64, fixture_depth=1.25, label='MB Toilet')
# Shower: master bath/bed door at y=42 x=57 — push shower west to x=52
place_against_wall(SHOWER, 'Shower_columns_15486', 42, 'S', 52, 0, LEVEL, door_positions=DOORS_Y42, fixture_depth=0.5, label='MB Shower')

# ── LAUNDRY (x=50-60, y=22-30) ───────────────────────────────
print("\n— Laundry —")
# y=30 wall (north of laundry): no doors. x=60 wall: mudroom/laundry door at y=26
place_against_wall('Washer-Dryer-Stack', '27" x 30"', 30, 'S', 55, 0, LEVEL,
                   door_positions=DOORS_X60, label='W/D Stack')

# ── GREAT ROOM (x=20-50, y=38-54) ────────────────────────────
print("\n— Great Room —")
# x=20 wall (west): hallway/living door at y=38
place_against_wall('Fireplace-Gas-Heat&Glo-Fortress', 'FORTRESS-36',
                   20, 'E', 46, 0, LEVEL, door_positions=DOORS_X20, label='Fireplace')

# ── ROOM LABELS ───────────────────────────────────────────────
print("\n— Room Labels —")
rooms = [
    ("Bed 3",        8,  28),
    ("J&J Bath",     8,  38),
    ("Bed 2",        8,  48),
    ("Hallway",     18,  38),
    ("Dining",      27,  30),
    ("Kitchen",     42,  30),
    ("Great Room",  35,  46),
    ("Laundry",     55,  26),
    ("Mudroom",     65,  26),
    ("Master Bath", 57,  36),
    ("WIC",         67,  36),
    ("Master Bed",  60,  48),
    ("Garage",      59,  11),
    ("Back Porch",  35,  60),
    ("Front Porch", 34,  28),
]
for name, rx, ry in rooms:
    create_room(rx, ry, 0, LEVEL, name, upper_limit_level=UL)

print("\n" + "=" * 60)
print("STAGE 4 COMPLETE — b73b7cad")
print("Full build done. Review in Revit.")
print("=" * 60)
