"""
fixtures_3fd426b2.py — Fixtures & cabinets for 3fd426b2
OFFSET RULES (from barnhaus_revit_utils pattern):
  Back/base cabs:  wall_face - 1.5  (center of 2ft deep cabinet)
  Upper cabs:      wall_face - 0.5  (cabinet back flush to wall)
  Appliances:      wall_face - 1.25 (center of appliance)

  North wall y=42 (EXT, 7.5"): interior face ≈ 41.7
    base center  = 42 - 1.5 = 40.5
    upper center = 42 - 0.5 = 41.5
    appliance    = 42 - 1.25 = 40.75

  West wall x=18 (INT, 4.5"): interior face ≈ 18.2
    base center  = 18 + 1.5 = 19.5
    upper center = 18 + 0.5 = 18.5
    appliance    = 18 + 1.25 = 19.25

  East wall x=48 (EXT, 7.5"): interior face ≈ 47.7
    base center  = 48 - 1.5 = 46.5
    upper center = 48 - 0.5 = 47.5
    appliance    = 48 - 1.25 = 46.75
"""

from barnhaus_revit_utils import place_fixture

L1 = "Level 1.0"

# Confirmed casework families
BASE_1D   = "Base Cabinet-Double Door & 1 Drawer"
BASE_2D   = "Base Cabinet-Double Door & 2 Drawer"
BASE_SINK = "Base Cabinet-Double Door Sink Unit"
UPPER     = "Upper Cabinet-Double Door-Wall"
UPPER_SH  = "Upper Cabinet-Double Door-Short-Wall"
TALL      = "Tall Cabinet-Double Door"
VAN_SINK  = "Vanity Cabinet-Double Door Sink Unit"
VAN_DRAW  = "Vanity Cabinet-3 Drawers"
VAN_4D    = "Vanity Cabinet-Double Door & 4 Drawer"

# Wall offsets
N_BASE  = 40.5   # north wall y=42, base center
N_UPPER = 41.5   # north wall, upper center
N_APPL  = 40.75  # north wall, appliance center
W_BASE  = 19.5   # west wall x=18, base center
W_UPPER = 18.5   # west wall, upper center
W_APPL  = 19.25  # west wall, appliance center
E_BASE  = 46.5   # east wall x=48, base center
E_UPPER = 47.5   # east wall, upper center

print("=" * 55)
print("FIXTURES: Mitchell Davis Madison | 3fd426b2")
print("=" * 55)

# ─────────────────────────────────────────────────────
# MASTER BATH  (12-22, 0-20) — 10×20 ft
# East wall x=22 (EXT): interior face ≈ 21.7
#   base offset from east wall: 22 - 1.5 = 20.5
#   upper offset:               22 - 0.5 = 21.5
# ─────────────────────────────────────────────────────
print("\n── Master Bath ──")

BATH_E_BASE  = 20.5  # east wall x=22, base center
BATH_E_UPPER = 21.5  # east wall, upper center
BATH_E_APPL  = 20.75 # east wall, appliance center

# Toilet: south wall (y=0), against west section
place_fixture("Toilet-Domestic-3D", "Toilet-Domestic-3D", 13.5, 1.5, 0, L1, 0, "toilet")

# Shower column: NE corner of bath
place_fixture("Shower_columns_15486", "Shower_columns_15486", BATH_E_APPL, 4, 0, L1, 90, "shower")

# Dual vanity sinks along east wall — two 36" units
place_fixture(VAN_SINK, "36\"", BATH_E_BASE, 10, 0, L1, 90, "vanity sink L")
place_fixture(VAN_SINK, "36\"", BATH_E_BASE, 14, 0, L1, 90, "vanity sink R")
place_fixture(VAN_DRAW, "18\"", BATH_E_BASE, 9,  0, L1, 90, "drawer L")
place_fixture(VAN_DRAW, "18\"", BATH_E_BASE, 16, 0, L1, 90, "drawer R")

# Makeup vanity station (brief: makeupVanitySpace=true)
place_fixture(VAN_4D, "48\"", BATH_E_BASE, 18, 0, L1, 90, "makeup vanity")

# Upper cabs / mirrors over vanity
place_fixture(UPPER_SH, "42\"", BATH_E_UPPER, 11, 0, L1, 90, "mirror L")
place_fixture(UPPER_SH, "42\"", BATH_E_UPPER, 14, 0, L1, 90, "mirror R")

# Linen tall cabinet near bath entry (x=12 wall)
place_fixture(TALL, "30\"", 12.7, 18.5, 0, L1, 0, "linen")

# ─────────────────────────────────────────────────────
# KITCHEN — U-shape with island
# Zone: x=18-48, y=20-42
# North wall y=42: main appliance + sink run
# West wall  x=18: fridge end + left leg
# East wall  x=48: storage right leg
# Island: x≈30-36, y≈30 (4ft clearance from all legs)
# ─────────────────────────────────────────────────────
print("\n── Kitchen — Back wall (north, y=42) ──")

# Range + hood centered at x=28
place_fixture("Range-Gas", "36\"",   28, N_APPL, 0, L1, 180, "range")
place_fixture("Hood-Wall",  "36\"",   28, N_UPPER, 0, L1, 180, "hood")

# Dishwasher + sink run (right of range)
place_fixture("Dishwasher", "24\"",         32, N_APPL, 0, L1, 180, "dishwasher")
place_fixture("Sink Kitchen-Single", "30\" x 21\"", 35.5, N_APPL, 0, L1, 180, "kitchen sink")
place_fixture(BASE_SINK, "36\"",             35.5, N_BASE, 0, L1, 180, "sink base")

# Base cabinets — back wall (skip range x=26-30, DW x=31-33, sink x=34-37)
for cx, w in [(21,"36\""),(24,"36\""),(38,"36\""),(41,"36\""),(44,"36\""),(46,"24\"")]:
    place_fixture(BASE_1D, w, cx, N_BASE, 0, L1, 180, f"base-back-{cx}")

# Upper cabinets — back wall
for cx, w in [(21,"36\""),(24,"36\""),(38,"36\""),(41,"36\""),(44,"36\"")]:
    place_fixture(UPPER, w, cx, N_UPPER, 0, L1, 180, f"upper-back-{cx}")

print("\n── Kitchen — Left leg (west wall, x=18) ──")

# Fridge at far end of left leg (near north wall)
place_fixture("Refrigerator", "24\" LH", W_APPL, 39, 0, L1, 270, "fridge")

# Base + upper cabinets running south along west wall
for cy, w in [(23,"36\""),(26,"36\""),(29,"36\""),(32,"36\""),(35,"36\"")]:
    place_fixture(BASE_1D, w, W_BASE, cy, 0, L1, 270, f"base-left-{cy}")

for cy, w in [(23,"36\""),(27,"36\""),(31,"36\""),(35,"36\"")]:
    place_fixture(UPPER, w, W_UPPER, cy, 0, L1, 270, f"upper-left-{cy}")

print("\n── Kitchen — Right leg (east wall, x=48) ──")

# Base + upper cabinets along east wall
for cy, w in [(23,"36\""),(26,"36\""),(29,"36\""),(32,"36\""),(35,"36\"")]:
    place_fixture(BASE_1D, w, E_BASE, cy, 0, L1, 90, f"base-right-{cy}")

for cy, w in [(23,"36\""),(27,"36\""),(31,"36\""),(35,"36\"")]:
    place_fixture(UPPER, w, E_UPPER, cy, 0, L1, 90, f"upper-right-{cy}")

# Tall pantry at far south end of right leg
place_fixture(TALL, "48\"", E_BASE, 38, 0, L1, 90, "pantry tall")

print("\n── Kitchen — Island (clearance: 4ft min all sides) ──")
# Island centered at x=33, y=30 — 4ft from west leg (x=19+2=21 front, island at x=26+)
# and 4ft from east leg (x=46-2=44 front, island ends at x=39-)
# and 4ft from back wall (y=40.5-2=38.5 front of base, island at y≤34-)
place_fixture(BASE_2D, "48\"", 30, 30, 0, L1, 0, "island base L")
place_fixture(BASE_2D, "48\"", 34, 30, 0, L1, 0, "island base R")
place_fixture("Sink Kitchen-Island", "18\" x 18\"", 32, 30, 0, L1, 0, "island sink")

print("\n✅ Fixtures complete — 3fd426b2")
print("   Cabinets placed flush to interior wall faces")
print("   Check: back wall bases at y=40.5, uppers at y=41.5")
print("   Check: west leg bases at x=19.5, east leg at x=46.5")
