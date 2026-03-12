"""
build_c1e4332c_s2.py — Mitchell Madison H-Shape Stage 2
Interior walls — all room divisions
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_wall

LEVEL = "Level 1.0"
EXT   = 'Wall 7.5" EXT PBR'
INT   = 'Wall 4.5 Interior"'
EH    = 0.3125

print("=== Stage 2: Interior Walls ===")

# ── LEFT WING interior walls ──────────────────────────────────────────────────
# Master Bed south wall (y=38, x=0→16)
create_wall(0, 38, 0, 16, 38, 0, LEVEL, INT, height=9, label="MBed-S")
# Master Bed east wall (x=16, y=38→54)
create_wall(16, 38, 0, 16, 54, 0, LEVEL, INT, height=9, label="MBed-E")
# Master Bath south wall (y=26, x=0→12)
create_wall(0, 26, 0, 12, 26, 0, LEVEL, INT, height=9, label="MBath-S")
# Master Bath east wall (x=12, y=26→38)
create_wall(12, 26, 0, 12, 38, 0, LEVEL, INT, height=9, label="MBath-E")
# WIC south wall (y=18, x=0→8)
create_wall(0, 18, 0, 8, 18, 0, LEVEL, INT, height=9, label="WIC-S")
# WIC east wall (x=8, y=18→26)
create_wall(8, 18, 0, 8, 26, 0, LEVEL, INT, height=9, label="WIC-E")
# Master Hall west wall (x=24, y=14→48) — separates master zone from kitchen/dining
create_wall(24, 14, 0, 24, 48, 0, LEVEL, INT, height=9, label="MHall-W")
# Kitchen south wall (y=26, x=12→24)
create_wall(12, 26, 0, 24, 26, 0, LEVEL, INT, height=9, label="Kit-S")
# Dining north wall = Kitchen south (already placed above)
# Pantry north wall (y=18, x=0→12)
create_wall(0, 18, 0, 12, 18, 0, LEVEL, INT, height=9, label="Pan-N")
# Pantry east wall (x=12, y=14→18)
create_wall(12, 14, 0, 12, 18, 0, LEVEL, INT, height=9, label="Pan-E")
# Mudroom north wall (y=14, x=0→8) — separates mudroom from pantry/WIC
create_wall(0, 14, 0, 8, 14, 0, LEVEL, INT, height=9, label="Mud-N")
# Mudroom east wall (x=8, y=8→14)
create_wall(8, 8, 0, 8, 14, 0, LEVEL, INT, height=9, label="Mud-E")
# Laundry/Util north wall (y=14, x=8→24)
create_wall(8, 14, 0, 24, 14, 0, LEVEL, INT, height=9, label="Laun-N")

print("✅ Left wing interior walls placed")

# ── RIGHT WING interior walls ─────────────────────────────────────────────────
# Storage north wall (y=18, x=68→96)
create_wall(68, 18, 0, 96, 18, 0, LEVEL, INT, height=9, label="Stor-N")
# Bed hallway north wall (y=22, x=68→96)
create_wall(68, 22, 0, 96, 22, 0, LEVEL, INT, height=9, label="BHall-N")
# Bed 3 / Bath 3 divider (x=84, y=22→34)
create_wall(84, 22, 0, 84, 34, 0, LEVEL, INT, height=9, label="B3-Bath3-div")
# Bed 3 north wall = Bed 2 south wall (y=34, x=68→96)
create_wall(68, 34, 0, 96, 34, 0, LEVEL, INT, height=9, label="Bed3N-Bed2S")
# Bed 2 / Bath 2 divider (x=84, y=34→50)
create_wall(84, 34, 0, 84, 50, 0, LEVEL, INT, height=9, label="B2-Bath2-div")

print("✅ Right wing interior walls placed")

print("\n=== STAGE 2 COMPLETE ===")
print("Check Revit — all interior room divisions should be visible.")
print("Reply 'stage 3' when ready for doors and windows.")
