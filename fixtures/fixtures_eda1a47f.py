"""
fixtures_eda1a47f.py — Mitchell Madison H-Shape Fixtures + Room Labels
place_against_wall(family, type_name, wall_coord, wall_face, position_along, z, level, ...)
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_against_wall, label_rooms

LEVEL = "Level 1.0"

print("=== eda1a47f Fixtures ===")

# ── KITCHEN (x=8→22, y=32→44) ─────────────────────────────────────────────────
# North wall y=32 (wall_face='S' = room to south, fixtures face south)
place_against_wall("Range-Gas",  '30"',          32, 'S', 12, 0, LEVEL, label="Range")
place_against_wall("Hood-Wall",  '30"',          32, 'S', 12, 5.5, LEVEL, label="Hood")
place_against_wall("Base Cabinet-Double Door & 1 Drawer", '36"', 32, 'S', 9,  0, LEVEL, label="Kit-Base1")
place_against_wall("Base Cabinet-Double Door & 1 Drawer", '24"', 32, 'S', 15, 0, LEVEL, label="Kit-Base2")
place_against_wall("Upper Cabinet-Double Door-Wall", '36"', 32, 'S', 9,  5.5, LEVEL, label="Kit-Upper1")
place_against_wall("Upper Cabinet-Double Door-Wall", '24"', 32, 'S', 15, 5.5, LEVEL, label="Kit-Upper2")

# East wall x=22 (wall_face='W' = room to west, fixtures face west)
place_against_wall("Sink Kitchen-Single", '30" x 21"', 22, 'W', 38, 0, LEVEL, fixture_depth=0.875, label="KitSink")
place_against_wall("Dishwasher", '24"',              22, 'W', 35, 0, LEVEL, label="DW")
place_against_wall("Fridge-Dbl Door", '59" x 30" x 74"', 22, 'W', 43, 0, LEVEL, label="Fridge")

# West wall x=8 (wall_face='E' = room to east, fixtures face east) — pantry
place_against_wall("Tall Cabinet-Double Door", '48"', 8, 'E', 34, 0, LEVEL, label="Pantry1")
place_against_wall("Tall Cabinet-Double Door", '36"', 8, 'E', 39, 0, LEVEL, label="Pantry2")

print("✅ Kitchen fixtures placed")

# ── MASTER BATH (x=0→14, y=22→32) ────────────────────────────────────────────
# East wall x=14 (wall_face='W')
place_against_wall("Vanity Cabinet-Double Door Sink Unit", '36"', 14, 'W', 25, 0, LEVEL, label="MBath-Van")
place_against_wall("Vanity Cabinet-3 Drawers", '18"',          14, 'W', 29, 0, LEVEL, label="MBath-Draw")

# South wall y=32 (wall_face='N')
place_against_wall("Toilet-Domestic-3D", "Toilet-Domestic-3D", 32, 'N', 5, 0, LEVEL, fixture_depth=1.25, label="MBath-Toilet")

# Freestanding tub near north wall y=22
place_against_wall("Tub-Free Standing-3D", '30" x 60"', 22, 'S', 7, 0, LEVEL, label="MBath-Tub")

print("✅ Master bath fixtures placed")

# ── BATH 2 (x=84→98, y=22→32) ────────────────────────────────────────────────
place_against_wall("Vanity Cabinet-Double Door Sink Unit", '30"', 98, 'W', 26, 0, LEVEL, label="Bath2-Van")
place_against_wall("Toilet-Domestic-3D", "Toilet-Domestic-3D",   22, 'S', 88, 0, LEVEL, fixture_depth=1.25, label="Bath2-Toilet")
place_against_wall("Shower_columns_15486", "Shower_columns_15486", 84, 'E', 28, 0, LEVEL, fixture_depth=0.5, label="Bath2-Shower")
print("✅ Bath 2 fixtures placed")

# ── BATH 3 (x=84→98, y=44→54) ────────────────────────────────────────────────
place_against_wall("Vanity Cabinet-Double Door Sink Unit", '30"', 98, 'W', 49, 0, LEVEL, label="Bath3-Van")
place_against_wall("Toilet-Domestic-3D", "Toilet-Domestic-3D",   54, 'N', 88, 0, LEVEL, fixture_depth=1.25, label="Bath3-Toilet")
place_against_wall("Shower_columns_15486", "Shower_columns_15486", 84, 'E', 47, 0, LEVEL, fixture_depth=0.5, label="Bath3-Shower")
print("✅ Bath 3 fixtures placed")

# ── LAUNDRY (x=0→11, y=44→54) ────────────────────────────────────────────────
place_against_wall("Washer-Dryer-Stack", '27" x 30"', 0, 'E', 49, 0, LEVEL, label="WasherDryer")
print("✅ Laundry fixtures placed")

# ── ROOM LABELS ───────────────────────────────────────────────────────────────
label_rooms([
    {"name": "Master Bedroom",  "x": 11,  "y": 15},
    {"name": "Master Bath",     "x":  7,  "y": 27},
    {"name": "Walk-In Closet",  "x":  5,  "y": 36},
    {"name": "Kitchen",         "x": 15,  "y": 38},
    {"name": "Butler Pantry",   "x":  4,  "y": 36},
    {"name": "Dining",          "x": 11,  "y": 49},
    {"name": "Mudroom",         "x": 17,  "y": 49},
    {"name": "Laundry",         "x":  5,  "y": 49},
    {"name": "Great Room",      "x": 53,  "y": 40},
    {"name": "Bedroom 2",       "x": 95,  "y": 15},
    {"name": "Bath 2",          "x": 91,  "y": 27},
    {"name": "Bedroom 3",       "x": 95,  "y": 49},
    {"name": "Bath 3",          "x": 91,  "y": 49},
    {"name": "Hallway",         "x": 95,  "y": 24},
    {"name": "Garage",          "x": 18,  "y": 66},
])
print("✅ Room labels placed")

print("\n=== BUILD COMPLETE ===")
