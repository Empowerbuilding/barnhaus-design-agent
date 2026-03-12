"""
STAGE 3 — Doors & Windows
Submission: b73b7cad | L-shape | Contemporary

EXTERIOR WALL IDs (from Stage 1):
  West  x=0,  y=22-54 : 5959355
  North y=54, x=0-70  : 5959356
  East  x=70, y=22-54 : 5959362   (main bar only — y=22-54)
  South y=22, x=0-48  : 5959361
  Garage south y=0    : 5959350
  Garage north y=22   : 5959351  (x=48-70, party wall)
  Garage west x=48    : 5959352
  Garage east x=70    : 5959353  (y=0-22)

INTERIOR WALL IDs (from Stage 2):
  BedWing/Living x=20   : 5959580
  Living/Master  x=50   : 5959581
  Hallway east   x=16   : 5959584
  Bed3/Bath      y=34   : 5959585
  Bath/Bed2      y=42   : 5959586
  Service/Bath   y=30   : 5959587
  Laundry/Mudroom x=60  : 5959588
  Bath/MasterBed y=42   : 5959589
  MasterBath/WIC x=64   : 5959590
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_door, place_window

LEVEL = 'Level 1.0'
# Door families
EXT_ENTRY  = 'Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad'
EXT_SLIDER = 'Exterior_Sliding_Door_3843'
HERO_SLIDE = 'Three_Panel_Sliding_Door_17534'
INT_DOOR   = 'Door-Interior-Single-1_Panel-Wood'
GAR_DOOR   = 'Door-Garage-Flush_Panel'
# Window family
WIN        = 'Instance-Window-Fixed'

print("=" * 60)
print("STAGE 3 — b73b7cad — Doors & Windows")
print("=" * 60)

# ── EXTERIOR DOORS ────────────────────────────────────────────
print("\n— Exterior Doors —")

# Front entry — south wall y=22, centered on living core x=20-50 → x=35
d1 = place_door(5959361, 35, 22, 0, EXT_ENTRY, '36" x 96"',
                label="Front Entry", level=LEVEL)
print(f"  Front entry: {d1}")

# Great room back porch hero slider — north wall y=54, x=20-50 → center x=35
d2 = place_door(5959356, 35, 54, 0, HERO_SLIDE, '144" x 96"',
                label="GR Back Slider", level=LEVEL)
print(f"  GR back porch slider: {d2}")

# Master bed patio slider — north wall y=54, x=50-70 → center x=60
d3 = place_door(5959356, 60, 54, 0, EXT_SLIDER, '6\'-0"W. x 8\'-0"H.',
                label="Master Patio Slider", level=LEVEL)
print(f"  Master patio slider: {d3}")

# Mudroom → garage — garage north wall y=22, x=48-70 → x=65
d4 = place_door(5959351, 65, 22, 0, INT_DOOR, '36" x 96"',
                label="Mudroom/Garage", level=LEVEL)
print(f"  Mudroom/Garage door: {d4}")

# ── INTERIOR DOORS ────────────────────────────────────────────
print("\n— Interior Doors —")

# Bed 3 → hallway — x=16 wall, y=22-34 → center y=28
d5 = place_door(5959584, 16, 28, 0, INT_DOOR, '30" x 96"',
                label="Bed3/Hallway", level=LEVEL)
print(f"  Bed 3: {d5}")

# J&J Bath → hallway — x=16 wall, y=34-42 → center y=38
d6 = place_door(5959584, 16, 38, 0, INT_DOOR, '30" x 96"',
                label="Bath/Hallway", level=LEVEL)
print(f"  J&J Bath: {d6}")

# Bed 2 → hallway — x=16 wall, y=42-54 → center y=48
d7 = place_door(5959584, 16, 48, 0, INT_DOOR, '30" x 96"',
                label="Bed2/Hallway", level=LEVEL)
print(f"  Bed 2: {d7}")

# Hallway → living core — x=20 wall, center y=38 (middle of hallway)
d8 = place_door(5959580, 20, 38, 0, INT_DOOR, '36" x 96"',
                label="Hallway/Living", level=LEVEL)
print(f"  Hallway/Living: {d8}")

# Laundry → kitchen/living — x=50 wall, y=22-30 → center y=26
d9 = place_door(5959581, 50, 26, 0, INT_DOOR, '30" x 96"',
                label="Laundry/Living", level=LEVEL)
print(f"  Laundry: {d9}")

# Mudroom → kitchen — x=50 wall, y=22-30 already has laundry door — use y=25 offset
# Actually mudroom is x=60-70, y=22-30 — opens to living core via x=50 wall at y=25
# But laundry is x=50-60 so mudroom door needs to be on x=50 east section... 
# Mudroom is fully east of x=60. It only touches x=50 wall at x=50 (but that's laundry).
# Mudroom opens to: garage (south, already done), and kitchen via the service/bath wall y=30? No.
# Better: open mudroom to laundry through x=60 wall (laundry/mudroom divide)
d10 = place_door(5959588, 60, 26, 0, INT_DOOR, '30" x 96"',
                 label="Mudroom/Laundry", level=LEVEL)
print(f"  Mudroom/Laundry: {d10}")

# Master bath → master bed — y=42 wall, x=50-70 → center x=57
d11 = place_door(5959589, 57, 42, 0, INT_DOOR, '30" x 96"',
                 label="MasterBath/Bed", level=LEVEL)
print(f"  Master bath/bed: {d11}")

# WIC → master bath — x=64 wall, y=30-42 → center y=36
d12 = place_door(5959590, 64, 36, 0, INT_DOOR, '30" x 96"',
                 label="WIC/MasterBath", level=LEVEL)
print(f"  WIC: {d12}")

# Master zone entry — x=50 wall, y=30-42 → center y=36 (from living → master bath)
d13 = place_door(5959581, 50, 36, 0, INT_DOOR, '36" x 96"',
                 label="Living/MasterZone", level=LEVEL)
print(f"  Living/Master zone: {d13}")

# ── WINDOWS ───────────────────────────────────────────────────
print("\n— Windows —")
Z = 2.5   # standard L1 sill height

# North wall (y=54) — great room: 2 large windows flanking the hero slider
w1 = place_window(5959356, 26, 54, Z, WIN, '72" x 36"', label="GR North W1")
w2 = place_window(5959356, 44, 54, Z, WIN, '72" x 36"', label="GR North W2")
print(f"  GR north windows: {w1}, {w2}")

# West wall (x=0) — bed 2 + bed 3
w3 = place_window(5959355, 0, 48, Z, WIN, '48" x 48"', label="Bed2 West")
w4 = place_window(5959355, 0, 28, Z, WIN, '48" x 48"', label="Bed3 West")
print(f"  Bed 2 west: {w3} | Bed 3 west: {w4}")

# South wall (y=22) — dining + kitchen
w5 = place_window(5959361, 27, 22, Z, WIN, '60" x 30"', label="Dining South")
w6 = place_window(5959361, 43, 22, Z, WIN, '60" x 30"', label="Kitchen South")
print(f"  Dining south: {w5} | Kitchen south: {w6}")

# East wall (x=70) — master bath accent
w7 = place_window(5959362, 70, 36, 5.0, WIN, '18" X 18"', label="MasterBath East")
print(f"  Master bath east: {w7}")

# J&J bath — west wall privacy
w8 = place_window(5959355, 0, 38, 5.0, WIN, '18" X 18"', label="JJBath West")
print(f"  J&J bath privacy: {w8}")

print("\n" + "=" * 60)
print("STAGE 3 COMPLETE")
print("Review in Revit → approve to proceed to Stage 4 (fixtures + room labels)")
print("=" * 60)
