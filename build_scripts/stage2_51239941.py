"""
STAGE 2 — Interior Walls
Submission: 51239941 | Mitchell Madison | H-shape with 8ft breezeways

LEFT WING (x=0-22, y=8-44):
  Master bed  : x=0-22,  y=8-26  (22×18 = 396 SF)
  Master bath : x=0-14,  y=26-36 (14×10 = 140 SF)
  WIC         : x=14-22, y=26-36 (8×10  =  80 SF)
  Laundry     : x=0-11,  y=36-44 (11×8  =  88 SF)
  Utility     : x=11-22, y=36-44 (11×8  =  88 SF)

CENTER BRIDGE (x=30-58, y=14-38) — mostly open plan:
  Kitchen     : x=30-44, y=14-26 (open to dining/GR)
  Dining      : x=30-44, y=26-38 (open to kitchen/GR)
  Great room  : x=44-58, y=14-38 (open)
  Powder room : x=52-58, y=32-38 (6×6 = 36 SF — carved from GR corner)

RIGHT WING (x=66-88, y=8-44):
  Hallway     : x=66-70, y=8-44  (4ft corridor)
  Bed 3       : x=70-88, y=8-24  (18×16 = 288 SF)
  J&J Bath    : x=70-88, y=24-32 (18×8  = 144 SF)
  Bed 2       : x=70-88, y=32-44 (18×12 = 216 SF)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_wall

LEVEL = 'Level 1.0'
INT   = 'Wall 4.5 Interior"'

# Exterior bounds per wing (guards against placing interior walls on exterior face)
LW_BOUNDS = {"x_min": 0,  "x_max": 22, "y_min": 8,  "y_max": 44}
CB_BOUNDS = {"x_min": 30, "x_max": 58, "y_min": 14, "y_max": 38}
RW_BOUNDS = {"x_min": 66, "x_max": 88, "y_min": 8,  "y_max": 44}

H = 11   # standard interior wall height
HC = 16  # center bridge height (powder room walls go full height)

print("=" * 60)
print("STAGE 2 — Interior Walls — 51239941")
print("=" * 60)

# ── LEFT WING ─────────────────────────────────────────────────
print("\n[LEFT WING]")

# Master bed south wall (separates master from bath+WIC)
lw1 = create_wall( 0, 26, 0, 22, 26, 0, LEVEL, INT, height=H,
                   label="LW MasterBed-S", _ext_bounds=LW_BOUNDS)

# Master bath / WIC divider (vertical at x=14, y=26-36)
lw2 = create_wall(14, 26, 0, 14, 36, 0, LEVEL, INT, height=H,
                   label="LW Bath/WIC-div", _ext_bounds=LW_BOUNDS)

# Bath+WIC south wall (separates from laundry/utility zone)
lw3 = create_wall( 0, 36, 0, 22, 36, 0, LEVEL, INT, height=H,
                   label="LW Bath-S/Laundry-N", _ext_bounds=LW_BOUNDS)

# Laundry / Utility split (vertical at x=11, y=36-44)
lw4 = create_wall(11, 36, 0, 11, 44, 0, LEVEL, INT, height=H,
                   label="LW Laundry/Utility-div", _ext_bounds=LW_BOUNDS)

# ── CENTER BRIDGE ─────────────────────────────────────────────
print("\n[CENTER BRIDGE]")

# Kitchen/Dining east wall — separates kitchen+dining from great room
cb1 = create_wall(44, 14, 0, 44, 38, 0, LEVEL, INT, height=HC,
                   label="CB Kitchen/GR-div", _ext_bounds=CB_BOUNDS)

# Kitchen/Dining divider (horizontal at y=26)
cb2 = create_wall(30, 26, 0, 44, 26, 0, LEVEL, INT, height=HC,
                   label="CB Kitchen/Dining-div", _ext_bounds=CB_BOUNDS)

# Powder room west wall (x=52, y=32-38)
cb3 = create_wall(52, 32, 0, 52, 38, 0, LEVEL, INT, height=HC,
                   label="CB PowderRm-W", _ext_bounds=CB_BOUNDS)

# Powder room north wall (y=32, x=52-58)
cb4 = create_wall(52, 32, 0, 58, 32, 0, LEVEL, INT, height=HC,
                   label="CB PowderRm-N", _ext_bounds=CB_BOUNDS)

# ── RIGHT WING ────────────────────────────────────────────────
print("\n[RIGHT WING]")

# Hallway east wall (x=70, full wing depth y=8-44)
rw1 = create_wall(70,  8, 0, 70, 44, 0, LEVEL, INT, height=H,
                   label="RW Hallway-E", _ext_bounds=RW_BOUNDS)

# Bed3 / Bath divider (y=24, x=70-88)
rw2 = create_wall(70, 24, 0, 88, 24, 0, LEVEL, INT, height=H,
                   label="RW Bed3/Bath-div", _ext_bounds=RW_BOUNDS)

# Bath / Bed2 divider (y=32, x=70-88)
rw3 = create_wall(70, 32, 0, 88, 32, 0, LEVEL, INT, height=H,
                   label="RW Bath/Bed2-div", _ext_bounds=RW_BOUNDS)

# Bed3 closet — NE corner (x=80, y=8-16) + south wall (y=16, x=80-88)
rw4 = create_wall(80,  8, 0, 80, 16, 0, LEVEL, INT, height=H,
                   label="RW Bed3Closet-W", _ext_bounds=RW_BOUNDS)
rw5 = create_wall(80, 16, 0, 88, 16, 0, LEVEL, INT, height=H,
                   label="RW Bed3Closet-S", _ext_bounds=RW_BOUNDS)

# Bed2 closet — SE corner (x=80, y=36-44) + north wall (y=36, x=80-88)
rw6 = create_wall(80, 36, 0, 80, 44, 0, LEVEL, INT, height=H,
                   label="RW Bed2Closet-W", _ext_bounds=RW_BOUNDS)
rw7 = create_wall(80, 32, 0, 88, 32, 0, LEVEL, INT, height=H,
                   label="RW Bed2Closet-N (shared w/ Bath)", _ext_bounds=RW_BOUNDS)

print("\n" + "=" * 60)
print("STAGE 2 COMPLETE — Review interior walls in Revit")
print("=" * 60)
