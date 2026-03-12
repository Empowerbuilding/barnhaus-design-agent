"""
STAGE 3 — Doors + Windows
Submission: d160ad8a | H-Shape | Single Story

WALL IDs FROM STAGE 1 (last clean run):
  Garage south (y=0):    5958174
  Garage north (y=22):   5958175
  Garage west  (x=0):    5958176
  Garage east  (x=36):   5958177
  WW-west      (x=0):    5958179   y=22-60
  WW-north     (y=60):   5958180   x=0-22
  Porch-west   (x=22):   5958181   y=60-72
  Porch-north  (y=72):   5958182   x=22-68
  Porch-east   (x=68):   5958183   y=60-72
  EW-north     (y=60):   5958184   x=68-84
  EW-east      (x=84):   5958185   y=22-60
  EW-south     (y=22):   5958186   x=68-84
  MB-south     (y=22):   5958187   x=36-68

WALL IDs FROM STAGE 2:
  WW|MB-divide  (x=22):  5958265   y=22-60
  gap-fill-south(y=22):  5958266   x=22-36
  MB|EW-divide  (x=68):  5958268   y=22-60
  MB|Porch-div  (y=60):  5958269   x=22-68
  Service|Master(y=40):  5958270   x=0-22
  MBath|MBed    (y=50):  5958271   x=0-22
  MBath|WIC     (x=14):  5958272   y=40-50
  Mud|Pantry    (x=12):  5958273   y=22-40
  Mud|Laundry   (y=32):  5958274   x=0-12
  Hallway|Rooms (x=72):  5958275   y=22-60
  Bed3|Bath     (y=38):  5958276   x=72-84
  Bath|Bed2     (y=46):  5958277   x=72-84
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_door, place_window

LEVEL  = "Level 1.0"
INT    = 'Door-Interior-Single-1_Panel-Wood'
EXT_S  = 'Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad'
SLIDER = 'Exterior_Sliding_Door_3843'
WIN    = 'Instance-Window-Fixed'
AWN    = 'Window-Awning-Single'
SILL   = 2.5   # standard L1 sill height
BSILL  = 5.0   # bath privacy sill

print("=" * 60)
print("STAGE 3 — d160ad8a — Doors + Windows")
print("=" * 60)

# ════════════════════════════════════════════════════════════
# DOORS
# ════════════════════════════════════════════════════════════
print("\n── DOORS ──")

# ── EXTERIOR ENTRY ────────────────────────────────────────────
# Front door — main body south wall, centered between x=36-68 → x=52
d = place_door(5958187, 52, 22, 0, EXT_S, '36" x 96"', label="Front Entry", level=LEVEL)
print(f"  Front entry (MB south): {d}")

# Garage-to-mudroom — garage north wall, centered in mudroom zone x=0-12 → x=6
d = place_door(5958175, 6, 22, 0, INT, '36" x 96"', label="Garage→Mudroom", level=LEVEL)
print(f"  Garage→Mudroom: {d}")

# ── WEST WING — SERVICE ZONE ──────────────────────────────────
# Mudroom → Butler Pantry (x=12 wall, y=22-40, center y=31)
d = place_door(5958273, 12, 31, 0, INT, '30" x 96"', label="Mud→Pantry", level=LEVEL)
print(f"  Mud→Pantry: {d}")

# Butler Pantry → Main Body kitchen (x=22 wall, center of pantry y=22-40 → y=31)
d = place_door(5958265, 22, 31, 0, INT, '36" x 96"', label="Pantry→Kitchen", level=LEVEL)
print(f"  Pantry→Kitchen: {d}")

# ── WEST WING — MASTER ZONE ───────────────────────────────────
# Main Body → Master zone (x=22 wall, center of master zone y=40-60 → y=52)
d = place_door(5958265, 22, 52, 0, INT, '36" x 96"', label="MB→Master corridor", level=LEVEL)
print(f"  MB→Master: {d}")

# Service → Master transition (y=40 wall, centered x=0-22 → x=11)
d = place_door(5958270, 11, 40, 0, INT, '36" x 96"', label="Service→Master", level=LEVEL)
print(f"  Service→Master: {d}")

# Master Bath door (y=50 wall, west side → x=5)
d = place_door(5958271, 5, 50, 0, INT, '36" x 96"', label="MBath door", level=LEVEL)
print(f"  Master Bath door: {d}")

# WIC door (y=50 wall, east side → x=18)
d = place_door(5958271, 18, 50, 0, INT, '30" x 96"', label="WIC door", level=LEVEL)
print(f"  WIC door: {d}")

# ── EAST WING — HALLWAY ───────────────────────────────────────
# Main Body → Hallway (x=68 wall, center of hallway y=22-60 → y=41)
d = place_door(5958268, 68, 41, 0, INT, '36" x 96"', label="MB→Hallway", level=LEVEL)
print(f"  MB→Hallway: {d}")

# Hallway → Bed 3 (x=72 wall, center y=22-38 → y=30)
d = place_door(5958275, 72, 30, 0, INT, '36" x 96"', label="Hall→Bed3", level=LEVEL)
print(f"  Hall→Bed3: {d}")

# Hallway → Bath (x=72 wall, center y=38-46 → y=42)
d = place_door(5958275, 72, 42, 0, INT, '32" x 96"', label="Hall→Bath", level=LEVEL)
print(f"  Hall→Bath: {d}")

# Hallway → Bed 2 (x=72 wall, center y=46-60 → y=53)
d = place_door(5958275, 72, 53, 0, INT, '36" x 96"', label="Hall→Bed2", level=LEVEL)
print(f"  Hall→Bed2: {d}")

# ── BACK PORCH ────────────────────────────────────────────────
# Main Body → Back Porch — two large sliders in y=60 wall
d = place_door(5958269, 35, 60, 0, SLIDER, "8'-0\"W. x 8'-0\"H. 2", label="Porch slider W", level=LEVEL)
print(f"  Porch slider W: {d}")

d = place_door(5958269, 55, 60, 0, SLIDER, "8'-0\"W. x 8'-0\"H. 2", label="Porch slider E", level=LEVEL)
print(f"  Porch slider E: {d}")

# ════════════════════════════════════════════════════════════
# WINDOWS
# ════════════════════════════════════════════════════════════
print("\n── WINDOWS ──")

# ── MASTER BED (west wing north + west faces) ─────────────────
# North face (y=60 wall, x=0-22)
w = place_window(5958180, 6,  60, SILL, WIN, '72" x 36"', label="MBed N1", level=LEVEL)
print(f"  MBed north 1: {w}")
w = place_window(5958180, 16, 60, SILL, WIN, '72" x 36"', label="MBed N2", level=LEVEL)
print(f"  MBed north 2: {w}")

# West face (x=0 wall, y=50-60 = master bed zone)
w = place_window(5958179, 0, 55, SILL, WIN, '72" x 36"', label="MBed W", level=LEVEL)
print(f"  MBed west: {w}")

# ── MASTER BATH + WIC ─────────────────────────────────────────
# West face (x=0 wall, y=40-50)
w = place_window(5958179, 0, 44, BSILL, AWN, '24" x 72"', label="MBath W", level=LEVEL)
print(f"  MBath west: {w}")

# ── MAIN BODY — GREAT ROOM ────────────────────────────────────
# South face (y=22 wall, x=36-68) — restrained street side
w = place_window(5958187, 45, 22, SILL, WIN, '60" x 30"', label="GR south", level=LEVEL)
print(f"  Great Rm south: {w}")

# North face — back porch divide (y=60) has sliders, no windows needed

# ── EAST WING — BED ROOMS ─────────────────────────────────────
# East face (x=84 wall)
# Bed 3 east (y=22-38, center y=30)
w = place_window(5958185, 84, 30, SILL, WIN, '48" x 48"', label="Bed3 E", level=LEVEL)
print(f"  Bed3 east: {w}")

# Bath east (y=38-46, center y=42) — privacy
w = place_window(5958185, 84, 42, BSILL, AWN, '24" x 72"', label="Bath E", level=LEVEL)
print(f"  Bath east: {w}")

# Bed 2 east (y=46-60, center y=53)
w = place_window(5958185, 84, 53, SILL, WIN, '48" x 48"', label="Bed2 E", level=LEVEL)
print(f"  Bed2 east: {w}")

# Bed 2 north (y=60 wall, x=68-84)
w = place_window(5958184, 76, 60, SILL, WIN, '48" x 48"', label="Bed2 N", level=LEVEL)
print(f"  Bed2 north: {w}")

# Bed 3 south (y=22 wall, x=68-84)
w = place_window(5958186, 76, 22, SILL, WIN, '48" x 48"', label="Bed3 S", level=LEVEL)
print(f"  Bed3 south: {w}")

# ── KITCHEN ───────────────────────────────────────────────────
# Main body south (y=22, kitchen zone x=22-46)
w = place_window(5958187, 38, 22, SILL, WIN, '60" x 30"', label="Kitchen S", level=LEVEL)
print(f"  Kitchen south: {w}")

print("\n" + "=" * 60)
print("STAGE 3 COMPLETE — review in Revit")
print("Approve to proceed to Stage 4 (fixtures + cabinets)")
print("=" * 60)
