"""
STAGE 2 — Interior Walls
Submission: b73b7cad | L-shape | 2,750 SF | Contemporary

ZONE LAYOUT:
  West wing  (x=0-20,  y=22-54): Bed 3 (S), J&J Bath (mid), Bed 2 (N), Hallway strip (x=16-20)
  Living core(x=20-50, y=22-54): Dining (SW), Kitchen (SE), Great Room (N) — open plan
  Master zone(x=50-70, y=22-54): Laundry (x=50-60,y=22-30), Mudroom (x=60-70,y=22-30),
                                   Master Bath (x=50-64,y=30-42), WIC (x=64-70,y=30-42),
                                   Master Bed (x=50-70,y=42-54)
  Garage     (x=48-70, y=0-22):  already enclosed from Stage 1

INTERIOR WALLS:
  Zone dividers:
    1. x=20, y=22-54  — bed wing / living core
    2. x=50, y=22-54  — living core / master zone

  West wing:
    3. x=16, y=22-54  — hallway strip east wall
    4. y=34, x=0-16   — bed 3 / J&J bath
    5. y=42, x=0-16   — J&J bath / bed 2

  Master zone:
    6. y=30, x=50-70  — service (laundry/mudroom) / bath zone
    7. x=60, y=22-30  — laundry / mudroom
    8. y=42, x=50-70  — bath+WIC / master bed
    9. x=64, y=30-42  — master bath / WIC
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_wall

LEVEL = 'Level 1.0'
INT   = 'Wall 4.5 Interior"'

# Exterior perimeter bounds — used to guard against interior walls on exterior faces
EXT_BOUNDS = {"x_min": 0, "x_max": 70, "y_min": 22, "y_max": 54}

print("=" * 60)
print("STAGE 2 — b73b7cad — Interior Walls")
print("=" * 60)

walls = []

def w(x0, y0, x1, y1, label):
    wid = create_wall(x0, y0, 0, x1, y1, 0, LEVEL, INT, height=11, label=label,
                      _ext_bounds=EXT_BOUNDS)
    walls.append(wid)
    return wid

print("\n— Zone Dividers —")
w(20, 22,  20, 54,  "BedWing/LivingCore divide")
w(50, 22,  50, 54,  "LivingCore/MasterZone divide")

print("\n— West Wing (Bed 3 / J&J Bath / Bed 2) —")
w(16, 22,  16, 54,  "Hallway east wall")
w( 0, 34,  16, 34,  "Bed3/JJBath divide")
w( 0, 42,  16, 42,  "JJBath/Bed2 divide")

print("\n— Master Zone —")
w(50, 30,  70, 30,  "Service/BathZone divide")
w(60, 22,  60, 30,  "Laundry/Mudroom divide")
w(50, 42,  70, 42,  "BathZone/MasterBed divide")
w(64, 30,  64, 42,  "MasterBath/WIC divide")

print(f"\nTotal interior walls: {len(walls)}")
print("=" * 60)
print("STAGE 2 COMPLETE")
print("Review in Revit → approve to proceed to Stage 3 (doors + windows)")
print("=" * 60)
