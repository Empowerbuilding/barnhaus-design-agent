"""
STAGE 4 — Fixtures & Cabinets
Submission: 51239941 | Mitchell Madison | H-shape | Contemporary

Cabinet offset rule:
  Base cabs   : wall_coord ± 1.5  (2ft deep, center = back+1ft)
  Upper cabs  : wall_coord ± 0.5
  Appliances  : wall_coord ± 1.25
  Vanity      : wall_coord ± 1.5
  Toilet      : wall_coord ± 1.25 (center of tank)
  Shower      : wall_coord ± 2.0

Rotation:
  0   = faces SOUTH (back to north wall)
  180 = faces NORTH (back to south wall)
  90  = faces WEST  (back to east wall)
  270 = faces EAST  (back to west wall)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_fixture, place_against_wall

LEVEL = 'Level 1.0'

print("=" * 60)
print("STAGE 4 — Fixtures — 51239941")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# LEFT WING — MASTER BATH (x=0-14, y=26-36)
# South wall y=36 (interior, faces north): dual vanity
# East wall x=14 (interior): toilet
# North wall y=26 (interior, master bed side): shower
# ══════════════════════════════════════════════════════════════
print("\n[MASTER BATH]")

# Dual vanity — back to south wall y=36, facing north
place_fixture('Vanity Cabinet-Double Door Sink Unit', '36"',
              7, 34.5, 0, LEVEL, rotation=180, label='MBath-VanitySink')
place_fixture('Vanity Cabinet-3 Drawers', '18"',
              2.5, 34.5, 0, LEVEL, rotation=180, label='MBath-VanityDrawer-L')
place_fixture('Vanity Cabinet-3 Drawers', '18"',
              11.5, 34.5, 0, LEVEL, rotation=180, label='MBath-VanityDrawer-R')

# Mirror cabinet above vanity
place_fixture('Upper Cabinet-Double Door-Short-Wall', '36"',
              7, 34.5, 0, LEVEL, rotation=180, label='MBath-Mirror')

# Toilet — against east wall x=14, facing west (rotation=90)
place_fixture('Toilet-Domestic-3D', 'Toilet-Domestic-3D',
              12.75, 29, 0, LEVEL, rotation=90, label='MBath-Toilet')

# Walk-in shower — NW corner, against north wall y=26, facing south
place_fixture('Shower_columns_15486', 'Shower_columns_15486',
              4, 28, 0, LEVEL, rotation=0, label='MBath-Shower')

# Makeup vanity — against east wall x=14, south end
place_fixture('Vanity Cabinet-Double Door & 4 Drawer', '48"',
              12.5, 33, 0, LEVEL, rotation=90, label='MBath-MakeupVanity')

# ══════════════════════════════════════════════════════════════
# LEFT WING — WIC (x=14-22, y=26-36)
# ══════════════════════════════════════════════════════════════
print("\n[WIC]")
# Tall wardrobe cabs along east wall x=22 (interior face)
place_fixture('Tall Cabinet-Double Door', '30"',
              20.5, 29, 0, LEVEL, rotation=90, label='WIC-Wardrobe1')
place_fixture('Tall Cabinet-Double Door', '30"',
              20.5, 33, 0, LEVEL, rotation=90, label='WIC-Wardrobe2')

# ══════════════════════════════════════════════════════════════
# LEFT WING — LAUNDRY (x=0-11, y=36-44)
# ══════════════════════════════════════════════════════════════
print("\n[LAUNDRY]")
# W/D stack against north wall y=36, facing south
place_fixture('Washer-Dryer-Stack', '27" x 30"',
              5, 37.25, 0, LEVEL, rotation=0, label='Laundry-WD')
# Utility sink against south wall y=44, facing north
place_fixture('Sink Kitchen-Single', '30" x 21"',
              5, 42.5, 0, LEVEL, rotation=180, label='Laundry-Sink')

# ══════════════════════════════════════════════════════════════
# CENTER BRIDGE — KITCHEN (x=30-44, y=14-26)
# North wall y=14: base cabs + range + hood
# East wall x=44: base cabs + sink + upper cabs
# Island: center of kitchen
# ══════════════════════════════════════════════════════════════
print("\n[KITCHEN]")

# North wall (y=14) base cabs — back to y=14, facing south (rotation=0)
place_fixture('Base Cabinet-Double Door & 1 Drawer', '36"',
              32, 15.5, 0, LEVEL, rotation=0, label='Kit-Base-N1')
place_fixture('Base Cabinet-Double Door & 1 Drawer', '36"',
              35.5, 15.5, 0, LEVEL, rotation=0, label='Kit-Base-N2')
place_fixture('Base Cabinet-Double Door & 1 Drawer', '36"',
              42, 15.5, 0, LEVEL, rotation=0, label='Kit-Base-N3')

# Range + Hood on north wall, centered
place_fixture('Range-Gas', '36"',
              38.5, 15.25, 0, LEVEL, rotation=0, label='Kit-Range')
place_fixture('Hood-Wall', '36"',
              38.5, 14.5, 0, LEVEL, rotation=0, label='Kit-Hood')

# Upper cabs north wall
place_fixture('Upper Cabinet-Double Door-Wall', '36"',
              32, 14.5, 0, LEVEL, rotation=0, label='Kit-Upper-N1')
place_fixture('Upper Cabinet-Double Door-Wall', '36"',
              35.5, 14.5, 0, LEVEL, rotation=0, label='Kit-Upper-N2')
place_fixture('Upper Cabinet-Double Door-Wall', '36"',
              42, 14.5, 0, LEVEL, rotation=0, label='Kit-Upper-N3')

# East wall (x=44) base cabs — back to x=44, facing west (rotation=90)
place_fixture('Base Cabinet-Double Door Sink Unit', '36"',
              42.5, 21, 0, LEVEL, rotation=90, label='Kit-SinkBase')
place_fixture('Base Cabinet-Double Door & 1 Drawer', '36"',
              42.5, 17.5, 0, LEVEL, rotation=90, label='Kit-Base-E1')
place_fixture('Base Cabinet-Double Door & 1 Drawer', '24"',
              42.5, 24.5, 0, LEVEL, rotation=90, label='Kit-Base-E2')

# Sink
place_fixture('Sink Kitchen-Single', '30" x 21"',
              42.5, 21, 0, LEVEL, rotation=90, label='Kit-Sink')

# Fridge — north end of east run
place_fixture('Refrigerator', '24" LH',
              42.5, 15.5, 0, LEVEL, rotation=90, label='Kit-Fridge')

# Upper cabs east wall
place_fixture('Upper Cabinet-Double Door-Wall', '36"',
              43.5, 18, 0, LEVEL, rotation=90, label='Kit-Upper-E1')
place_fixture('Upper Cabinet-Double Door-Wall', '36"',
              43.5, 22, 0, LEVEL, rotation=90, label='Kit-Upper-E2')

# Pantry/tall cab — SE corner of kitchen against south wall y=26
place_fixture('Tall Cabinet-Double Door', '30"',
              33, 24.5, 0, LEVEL, rotation=180, label='Kit-Pantry')

# Island — center of kitchen (x=34-40, y=18-23)
place_fixture('Base Cabinet-Double Door & 1 Drawer', '36"',
              35.5, 20.5, 0, LEVEL, rotation=0, label='Kit-Island-1')
place_fixture('Base Cabinet-Double Door & 1 Drawer', '36"',
              39, 20.5, 0, LEVEL, rotation=0, label='Kit-Island-2')
place_fixture('Sink Kitchen-Island', '18" x 18"',
              37, 20.5, 0, LEVEL, rotation=0, label='Kit-Island-Sink')

# ══════════════════════════════════════════════════════════════
# CENTER BRIDGE — POWDER ROOM (x=52-58, y=32-38)
# ══════════════════════════════════════════════════════════════
print("\n[POWDER ROOM]")
# Toilet against north wall y=32, facing south
place_fixture('Toilet-Domestic-3D', 'Toilet-Domestic-3D',
              55, 33.25, 0, LEVEL, rotation=0, label='PowderRm-Toilet')
# Small vanity against east wall x=58, facing west
place_fixture('Vanity Cabinet-Double Door Sink Unit', '30"',
              56.5, 36, 0, LEVEL, rotation=90, label='PowderRm-Vanity')

# ══════════════════════════════════════════════════════════════
# RIGHT WING — BATH 2 / J&J (x=70-88, y=24-32)
# East wall x=88: dual vanity
# North wall y=24: shower
# South wall y=32: toilet
# ══════════════════════════════════════════════════════════════
print("\n[BATH 2 — J&J]")

# Dual vanity — back to east wall x=88, facing west
place_fixture('Vanity Cabinet-Double Door Sink Unit', '36"',
              86.5, 27, 0, LEVEL, rotation=90, label='Bath2-VanitySink')
place_fixture('Vanity Cabinet-3 Drawers', '18"',
              86.5, 24.5, 0, LEVEL, rotation=90, label='Bath2-Drawer-N')
place_fixture('Vanity Cabinet-3 Drawers', '18"',
              86.5, 30, 0, LEVEL, rotation=90, label='Bath2-Drawer-S')

# Shower — NW corner against north wall y=24, facing south
place_fixture('Shower_columns_15486', 'Shower_columns_15486',
              74, 26, 0, LEVEL, rotation=0, label='Bath2-Shower')

# Toilet — against south wall y=32, facing north
place_fixture('Toilet-Domestic-3D', 'Toilet-Domestic-3D',
              74, 30.75, 0, LEVEL, rotation=180, label='Bath2-Toilet')

# ══════════════════════════════════════════════════════════════
# ROOM LABELS
# ══════════════════════════════════════════════════════════════
print("\n[ROOM LABELS]")
from barnhaus_revit_utils import label_rooms

label_rooms([
    # Left wing
    {'name': 'Master Bedroom',  'x': 11, 'y': 17, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Master Bath',     'x':  7, 'y': 31, 'upper_limit_level': 'Level 2.0'},
    {'name': 'W.I.C.',          'x': 18, 'y': 31, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Laundry',         'x':  5, 'y': 40, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Utility',         'x': 17, 'y': 40, 'upper_limit_level': 'Level 2.0'},
    # Center bridge
    {'name': 'Kitchen',         'x': 37, 'y': 20, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Dining',          'x': 37, 'y': 32, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Great Room',      'x': 51, 'y': 26, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Powder Room',     'x': 55, 'y': 35, 'upper_limit_level': 'Level 2.0'},
    # Right wing
    {'name': 'Bedroom 3',       'x': 79, 'y': 16, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Bath 2',          'x': 79, 'y': 28, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Bedroom 2',       'x': 79, 'y': 38, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Hallway',         'x': 68, 'y': 26, 'upper_limit_level': 'Level 2.0'},
    # Porches
    {'name': 'Covered Back Porch',  'x': 44, 'y':  7, 'upper_limit_level': 'Level 2.0'},
    {'name': 'Covered Front Porch', 'x': 44, 'y': 45, 'upper_limit_level': 'Level 2.0'},
], level=LEVEL)

print("\n" + "=" * 60)
print("STAGE 4 COMPLETE — 51239941")
print("=" * 60)
