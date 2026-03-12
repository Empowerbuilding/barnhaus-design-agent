"""
STAGE 4 (v4) — Fixtures + Cabinets — with door clearance checks
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_against_wall, place_fixture

LEVEL = "Level 1.0"
Z = 0; EXT = 0.625; INT = 0.375

# Door positions per wall: (wall_coord, position_along, door_width_ft, swing_clearance_ft)
DOORS_Y60 = [(60, 35, 8, 2.0), (60, 55, 8, 2.0)]          # porch sliders
DOORS_X22 = [(22, 31, 3, 2.5), (22, 52, 3, 2.5)]           # pantry + master entry
DOORS_Y40 = [(40, 11, 3, 2.5)]                              # service→master
DOORS_Y50 = [(50, 5, 3, 2.5), (50, 18, 2.5, 2.0)]          # mbath + wic
DOORS_X72 = [(72, 30, 3, 2.5), (72, 42, 2.67, 2.5), (72, 53, 3, 2.5)]
DOORS_X12 = [(12, 31, 2.5, 2.5)]

def kn(family, typ, pos, depth=0, label=""):   # kitchen north wall helper
    place_against_wall(family, typ, 60, 'S', pos, Z, LEVEL,
                       fixture_depth=depth, wall_thickness=INT,
                       door_positions=DOORS_Y60, label=label)

def kw(family, typ, pos, depth=0, label=""):   # kitchen west wall helper
    place_against_wall(family, typ, 22, 'E', pos, Z, LEVEL,
                       fixture_depth=depth, wall_thickness=INT,
                       door_positions=DOORS_X22, label=label)

print("=" * 60)
print("STAGE 4 (v4) — d160ad8a — Fixtures + Cabinets")
print("=" * 60)

# ── KITCHEN ───────────────────────────────────────────────────
print("\n── Kitchen (north wall) ──")
kn("Refrigerator",                       '24" LH',        24,  0,     "fridge")
kn("Base Cabinet-Double Door & 1 Drawer",'36"',           28,  0,     "base N1")
kn("Base Cabinet-Double Door Sink Unit", '36"',           32,  0,     "sink base")
kn("Sink Kitchen-Single",                '30" x 21"',     32,  0.875, "kitchen sink")
kn("Dishwasher",                         '24"',           35.5,0,     "dishwasher")
kn("Range-Gas",                          '36"',           39,  0,     "range")
kn("Hood-Wall",                          '36"',           39,  0,     "hood")
kn("Base Cabinet-Double Door & 1 Drawer",'36"',           43,  0,     "base N2")

print("\n── Kitchen (upper cabs north wall) ──")
for pos, lbl in [(28,'upper N1'),(36,'upper N2'),(40,'upper N3')]:
    kn("Upper Cabinet-Double Door-Wall", '36"', pos, 0, lbl)

print("\n── Kitchen (west wall) ──")
kw("Tall Cabinet-Double Door",            '48"', 57, 0, "pantry")
kw("Base Cabinet-Double Door & 1 Drawer", '36"', 52, 0, "base W1")
kw("Upper Cabinet-Double Door-Wall",      '36"', 52, 0, "upper W1")

# ── MASTER BATH ───────────────────────────────────────────────
print("\n── Master Bath ──")
# South wall y=40 INT, room north → 'N'
place_against_wall("Vanity Cabinet-Double Door Sink Unit", '36"',
    40, 'N', 4, Z, LEVEL, 0, INT, DOORS_Y40, "MB vanity sink")
place_against_wall("Vanity Cabinet-3 Drawers", '18"',
    40, 'N', 8.5, Z, LEVEL, 0, INT, DOORS_Y40, "MB vanity draw")
place_against_wall("Upper Cabinet-Double Door-Short-Wall", '36"',
    40, 'N', 4, Z, LEVEL, 0, INT, DOORS_Y40, "MB mirror")

# Shower: west wall x=0 EXT, room east → 'E', rotation=90
place_fixture("Shower_columns_15486", "Shower_columns_15486",
    EXT/2, 48, Z, LEVEL, rotation=90, label="MB shower")

# Toilet: east wall x=14 INT, room west → 'W'
place_against_wall("Toilet-Domestic-3D", "Toilet-Domestic-3D",
    14, 'W', 43, Z, LEVEL, 1.25, INT, None, "MB toilet")

# ── J&J BATH ──────────────────────────────────────────────────
print("\n── J&J Bath ──")
# West wall x=72 INT, room east → 'E'
place_against_wall("Vanity Cabinet-Double Door Sink Unit", '36"',
    72, 'E', 42, Z, LEVEL, 0, INT, DOORS_X72, "JJ vanity")
place_against_wall("Upper Cabinet-Double Door-Short-Wall", '36"',
    72, 'E', 42, Z, LEVEL, 0, INT, DOORS_X72, "JJ mirror")

# Shower: east wall x=84 EXT, room west → 'W', rotation=270
place_fixture("Shower_columns_15486", "Shower_columns_15486",
    84-EXT/2, 40, Z, LEVEL, rotation=270, label="JJ shower")

# Toilet: north wall y=46 INT, room south → 'S'
place_against_wall("Toilet-Domestic-3D", "Toilet-Domestic-3D",
    46, 'S', 81, Z, LEVEL, 1.25, INT, None, "JJ toilet")

# ── LAUNDRY ───────────────────────────────────────────────────
print("\n── Laundry ──")
place_against_wall("Washer-Dryer-Stack", '27" x 30"',
    12, 'W', 36, Z, LEVEL, 1.25, INT, DOORS_X12, "washer dryer")

print("\n" + "=" * 60)
print("STAGE 4 COMPLETE")
print("=" * 60)
