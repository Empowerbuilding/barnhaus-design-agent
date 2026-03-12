"""
STAGE 2 (revised) — Interior Walls + Hallways
Submission: d160ad8a | H-Shape | 3,250 SF

WEST WING (x=0-22, y=22-60):
  Service zone (y=22-40):
    Mudroom:       x=0-12,  y=22-32  (12x10 = 120 SF)
    Laundry:       x=0-12,  y=32-40  (12x8  =  96 SF)
    Butler Pantry: x=12-22, y=22-40  (10x18 = 180 SF)
  Master zone (y=40-60):
    Master Bath:   x=0-14,  y=40-50  (14x10 = 140 SF)
    W.I.C.:        x=14-22, y=40-50  ( 8x10 =  80 SF)
    Master Bed:    x=0-22,  y=50-60  (22x10 = 220 SF)

MAIN BODY (x=22-68, y=22-60) — open plan:
    Great Room:    x=22-68, y=22-44  (46x22 open)
    Kitchen:       x=22-46, y=44-60  (24x16)
    Dining:        x=46-68, y=44-60  (22x16)

EAST WING (x=68-84, y=22-60):
    Hallway:       x=68-72, y=22-60  ( 4x38 = 152 SF) ← single-loaded corridor
    Bed 3:         x=72-84, y=22-38  (12x16 = 192 SF)
    J&J Bath:      x=72-84, y=38-46  (12x8  =  96 SF)
    Bed 2:         x=72-84, y=46-60  (12x14 = 168 SF)

BACK PORCH (x=22-68, y=60-72) — open covered
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_wall, label_rooms

LEVEL = "Level 1.0"
INT   = 'Wall 4.5 Interior"'
H     = 11

print("=" * 60)
print("STAGE 2 (revised) — Interior Walls + Hallways")
print("=" * 60)

walls = []

# ── ZONE CONNECTION WALLS ─────────────────────────────────────
print("\n[1/5] Zone connection walls...")

w = create_wall(22,22,0, 22,60,0, LEVEL, INT, height=H, label="WW|MB-divide")
walls.append(w); print(f"  WW|MB  x=22: {w}")

w = create_wall(22,22,0, 36,22,0, LEVEL, INT, height=H, label="gap-fill-south")
walls.append(w); print(f"  Gap fill y=22 x=22-36: {w}")

w = create_wall(68,22,0, 68,60,0, LEVEL, INT, height=H, label="MB|EW-divide")
walls.append(w); print(f"  MB|EW  x=68: {w}")

w = create_wall(22,60,0, 68,60,0, LEVEL, INT, height=H, label="MB|Porch-divide")
walls.append(w); print(f"  MB|Porch y=60: {w}")

# ── WEST WING INTERIOR WALLS ──────────────────────────────────
print("\n[2/5] West wing interior walls...")

# Service / master divider
w = create_wall(0,40,0, 22,40,0, LEVEL, INT, height=H, label="Service|Master")
walls.append(w); print(f"  Service|Master y=40: {w}")

# Master bath+WIC / master bed divider
w = create_wall(0,50,0, 22,50,0, LEVEL, INT, height=H, label="MBath|MBed")
walls.append(w); print(f"  MBath|MBed y=50: {w}")

# Master bath / WIC divider
w = create_wall(14,40,0, 14,50,0, LEVEL, INT, height=H, label="MBath|WIC")
walls.append(w); print(f"  MBath|WIC x=14: {w}")

# Mudroom / butler pantry divider
w = create_wall(12,22,0, 12,40,0, LEVEL, INT, height=H, label="Mud|Pantry")
walls.append(w); print(f"  Mudroom|Pantry x=12: {w}")

# Mudroom / laundry divider
w = create_wall(0,32,0, 12,32,0, LEVEL, INT, height=H, label="Mud|Laundry")
walls.append(w); print(f"  Mudroom|Laundry y=32: {w}")

# ── EAST WING INTERIOR WALLS ──────────────────────────────────
print("\n[3/5] East wing interior walls...")

# Hallway / rooms divider (the key hallway wall)
w = create_wall(72,22,0, 72,60,0, LEVEL, INT, height=H, label="Hallway|Rooms")
walls.append(w); print(f"  Hallway|Rooms x=72: {w}")

# Bed 3 / J&J bath divider
w = create_wall(72,38,0, 84,38,0, LEVEL, INT, height=H, label="Bed3|Bath")
walls.append(w); print(f"  Bed3|Bath y=38: {w}")

# J&J bath / Bed 2 divider
w = create_wall(72,46,0, 84,46,0, LEVEL, INT, height=H, label="Bath|Bed2")
walls.append(w); print(f"  Bath|Bed2 y=46: {w}")

print(f"\n  Total interior walls: {len(walls)}")

# ── ROOM LABELS ───────────────────────────────────────────────
print("\n[4/5] Room labels...")

rooms = [
    # West wing — service
    {"name": "Mudroom",        "x":  6,  "y": 27},
    {"name": "Laundry",        "x":  6,  "y": 36},
    {"name": "Butler Pantry",  "x": 17,  "y": 31},
    # West wing — master
    {"name": "Master Bath",    "x":  7,  "y": 45},
    {"name": "W.I.C.",         "x": 18,  "y": 45},
    {"name": "Master Bed",     "x": 11,  "y": 55},
    # Main body
    {"name": "Great Room",     "x": 45,  "y": 33},
    {"name": "Kitchen",        "x": 34,  "y": 52},
    {"name": "Dining",         "x": 57,  "y": 52},
    # East wing
    {"name": "Hallway",        "x": 70,  "y": 41},
    {"name": "Bed 3",          "x": 78,  "y": 30},
    {"name": "Bath",           "x": 78,  "y": 42},
    {"name": "Bed 2",          "x": 78,  "y": 53},
    # Back porch
    {"name": "Back Porch",     "x": 45,  "y": 66},
]

label_rooms(rooms, LEVEL, upper_limit_level="Level 2.0")

print("\n" + "=" * 60)
print("STAGE 2 COMPLETE — review floor plan in Revit")
print("Approve to proceed to Stage 3 (doors + windows)")
print("=" * 60)
