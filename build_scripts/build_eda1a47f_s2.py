"""
build_eda1a47f_s2.py — Mitchell Madison H-Shape Stage 2
Interior walls
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_wall

LEVEL = "Level 1.0"
INT   = 'Wall 4.5 Interior"'

print("=== eda1a47f Stage 2: Interior Walls ===")

# ── LEFT WING ─────────────────────────────────────────────────────────────────
create_wall(0,  22, 0, 22, 22, 0, LEVEL, INT, height=10, label="MBed-S")       # Master bed south
create_wall(14, 22, 0, 14, 32, 0, LEVEL, INT, height=10, label="MBath-E")      # Master bath east
create_wall(0,  32, 0, 14, 32, 0, LEVEL, INT, height=10, label="MBath-S")      # Master bath south
create_wall(10, 32, 0, 10, 40, 0, LEVEL, INT, height=10, label="WIC-E")        # WIC east
create_wall(0,  40, 0, 10, 40, 0, LEVEL, INT, height=10, label="WIC-S")        # WIC south
create_wall(16, 22, 0, 16, 44, 0, LEVEL, INT, height=10, label="MHall-W")      # Master hall west wall
create_wall(8,  32, 0,  8, 44, 0, LEVEL, INT, height=10, label="Kit-Pan-div")  # Kitchen/pantry divider
create_wall(0,  44, 0, 22, 44, 0, LEVEL, INT, height=10, label="Dining-N")     # Dining north / kitchen south
create_wall(11, 44, 0, 11, 54, 0, LEVEL, INT, height=10, label="Mud-Laun-div") # Mudroom/laundry divider
print("✅ Left wing interior walls placed")

# ── RIGHT WING ────────────────────────────────────────────────────────────────
create_wall(84, 22, 0, 106, 22, 0, LEVEL, INT, height=10, label="BHall-S")     # Bed hallway south
create_wall(84, 32, 0, 106, 32, 0, LEVEL, INT, height=10, label="Bed2-S")      # Bed 2 south / bath 2 south
create_wall(98, 22, 0,  98, 32, 0, LEVEL, INT, height=10, label="Bath2-W")     # Bath 2 west
create_wall(84, 32, 0, 106, 32, 0, LEVEL, INT, height=10, label="Bed3-N")      # Bed 3 north (same as Bed2-S)
create_wall(98, 44, 0,  98, 54, 0, LEVEL, INT, height=10, label="Bath3-W")     # Bath 3 west
create_wall(84, 44, 0, 106, 44, 0, LEVEL, INT, height=10, label="Bath3-N")     # Bath 3 north / bed 3 south split
print("✅ Right wing interior walls placed")

print("\n=== STAGE 2 COMPLETE ===")
print("Check Revit — interior room divisions visible.")
print("Reply 'run stage 3' when ready.")
