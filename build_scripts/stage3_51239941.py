"""
STAGE 3 — Doors & Windows
Submission: 51239941 | Mitchell Madison | H-shape | Contemporary
Window style: floor-to-ceiling → use 48" x 96" (drama) at sill z=1.0

WALL IDs from Stage 1 & 2:
  LW exterior: 5959672(S), 5959673(N), 5959674(W), 5959675(E)
  CB exterior: 5959676(N/y=14), 5959677(S/y=38), clerestory W:5959678, E:5959679
  RW exterior: 5959680(S/y=8), 5959681(N/y=44), 5959682(W/x=66), 5959683(E/x=88)
  Interior:
    LW: 5960208(MBed-S y=26), 5960209(Bath/WIC x=14), 5960210(Bath-S y=36), 5960211(Lndry/Util x=11)
    CB: 5960212(Kit/GR x=44), 5960213(Kit/Dining y=26), 5960214(PowderW x=52), 5960215(PowderN y=32)
    RW: 5960216(Hallway x=70), 5960217(Bed3/Bath y=24), 5960218(Bath/Bed2 y=32),
        5960219(Bed3ClosetW x=80), 5960220(Bed3ClosetS y=16),
        5960221(Bed2ClosetW x=80), 5960222(Bed2ClosetN y=32)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_door, place_window, WIN

LEVEL = 'Level 1.0'
SILL  = 1.0   # floor-to-ceiling sill height (low = dramatic)
SILL_BATH = 5.0  # privacy sill for bathrooms

INT_SINGLE  = 'Door-Interior-Single-1_Panel-Wood'
INT_CLOSET  = 'Door-Interior-Single-1_Panel-Wood'
EXT_SINGLE  = 'Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad'
EXT_DOUBLE  = 'Door-Exterior-Double-Full Glass-Wood_Clad'
EXT_SLIDER  = 'Exterior_Sliding_Door_3843'
THREE_PANEL = 'Three_Panel_Sliding_Door_17534'
WIN_FTC     = 'Instance-Window-Fixed'   # floor-to-ceiling
WIN_AWNING  = 'Window-Awning-Single'

print("=" * 60)
print("STAGE 3 — Doors & Windows — 51239941")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# DOORS
# ══════════════════════════════════════════════════════════════
print("\n── DOORS ──")

# ── LEFT WING ─────────────────────────────────────────────────
print("\n[LEFT WING DOORS]")
# Entry from east breezeway — exterior single, mid-wing at y=30 (into bath/WIC zone)
d_lw_entry = place_door(5959675, 22, 30, 0, EXT_SINGLE, '36" x 96"',
                         label="LW-Entry", level=LEVEL)
# Master bed patio slider — north wall y=8, centered at x=11
d_lw_patio = place_door(5959673, 11, 8, 0, EXT_SLIDER, "6'-0\"W. x 8'-0\"H.",
                         label="LW-MasterPatio", level=LEVEL)
# Master bed → bath (south wall y=26, west side x=5)
d_lw_mbath = place_door(5960208, 5, 26, 0, INT_SINGLE, '36" x 96"',
                         label="LW-MBed-to-Bath", level=LEVEL)
# Master bed → WIC (south wall y=26, east side x=18)
d_lw_wic   = place_door(5960208, 18, 26, 0, INT_CLOSET, '30" x 96"',
                         label="LW-MBed-to-WIC", level=LEVEL)
# Master bath → WIC divider (x=14 wall, y=31)
d_lw_bwic  = place_door(5960209, 14, 31, 0, INT_CLOSET, '30" x 96"',
                         label="LW-Bath-to-WIC", level=LEVEL)
# Laundry door (y=36 wall, x=5)
d_lw_lndry = place_door(5960210, 5, 36, 0, INT_SINGLE, '36" x 96"',
                         label="LW-Laundry", level=LEVEL)
# Utility door (y=36 wall, x=17)
d_lw_util  = place_door(5960210, 17, 36, 0, INT_SINGLE, '36" x 96"',
                         label="LW-Utility", level=LEVEL)

# ── CENTER BRIDGE ─────────────────────────────────────────────
print("\n[CENTER BRIDGE DOORS]")
# Back porch — three panel hero slider on north wall (y=14), centered at x=44
d_cb_back  = place_door(5959676, 44, 14, 0, THREE_PANEL, '144" x 96"',
                         label="CB-BackPorch-Slider", level=LEVEL)
# Front entry — double glass door on south wall (y=38), centered at x=44
d_cb_front = place_door(5959677, 44, 38, 0, EXT_DOUBLE, '72" x 96"',
                         label="CB-FrontEntry", level=LEVEL)
# Powder room door (west wall x=52, y=35)
d_cb_pwd   = place_door(5960214, 52, 35, 0, INT_SINGLE, '30" x 96"',
                         label="CB-PowderRm", level=LEVEL)

# ── RIGHT WING ────────────────────────────────────────────────
print("\n[RIGHT WING DOORS]")
# Entry from west breezeway — exterior single on west wall (x=66), at y=26 (hallway)
d_rw_entry = place_door(5959682, 66, 26, 0, EXT_SINGLE, '36" x 96"',
                         label="RW-Entry", level=LEVEL)
# Bed 3 door — hallway wall (x=70), y=16
d_rw_bed3  = place_door(5960216, 70, 16, 0, INT_SINGLE, '36" x 96"',
                         label="RW-Bed3", level=LEVEL)
# J&J Bath — from hallway (x=70, y=28)
d_rw_bath_hall = place_door(5960216, 70, 28, 0, INT_SINGLE, '36" x 96"',
                             label="RW-Bath-Hall", level=LEVEL)
# J&J Bath — from Bed 3 (y=24 wall, x=80)
d_rw_bath_b3   = place_door(5960217, 80, 24, 0, INT_SINGLE, '30" x 96"',
                             label="RW-Bath-Bed3", level=LEVEL)
# J&J Bath — from Bed 2 (y=32 wall, x=80)
d_rw_bath_b2   = place_door(5960218, 80, 32, 0, INT_SINGLE, '30" x 96"',
                             label="RW-Bath-Bed2", level=LEVEL)
# Bed 2 door — hallway wall (x=70), y=38
d_rw_bed2  = place_door(5960216, 70, 38, 0, INT_SINGLE, '36" x 96"',
                         label="RW-Bed2", level=LEVEL)
# Bed 3 closet door (y=16 wall, x=84)
d_rw_cl3   = place_door(5960220, 84, 16, 0, INT_CLOSET, '30" x 96"',
                         label="RW-Bed3Closet", level=LEVEL)
# Bed 2 closet door (x=80 wall, y=40)
d_rw_cl2   = place_door(5960221, 80, 40, 0, INT_CLOSET, '30" x 96"',
                         label="RW-Bed2Closet", level=LEVEL)

# ══════════════════════════════════════════════════════════════
# WINDOWS
# ══════════════════════════════════════════════════════════════
print("\n── WINDOWS ──")

# ── LEFT WING ─────────────────────────────────────────────────
print("\n[LEFT WING WINDOWS]")
# Master bed north wall (y=8) — 2× floor-to-ceiling flanking patio door
place_window(5959673,  4,  8, SILL, WIN_FTC, '48" x 96"', label="LW-MBed-N1")
place_window(5959673, 18,  8, SILL, WIN_FTC, '48" x 96"', label="LW-MBed-N2")
# Master bed west wall (x=0) — 1× floor-to-ceiling center
place_window(5959674, 0, 17, SILL, WIN_FTC, '48" x 96"', label="LW-MBed-W")
# Master bath — awning privacy window on west wall
place_window(5959674, 0, 31, SILL_BATH, WIN_AWNING, '24" x 72"', label="LW-Bath-W")
# WIC — small accent on west wall (above cabinet height)
place_window(5959674, 0, 29, 6.0, WIN_FTC, '18" X 18"', label="LW-WIC-W")

# ── CENTER BRIDGE ─────────────────────────────────────────────
print("\n[CENTER BRIDGE WINDOWS]")
# Great room east clerestory wall (x=58, z=11-16, height=5ft) — floor-to-ceiling strip
# sill at z=11.5 (just above clerestory base), window 48" x 48" (fits in 5ft space)
place_window(5959679, 58, 20, 11.5, WIN_FTC, '48" x 48"', label="CB-GR-Clerestory-E1")
place_window(5959679, 58, 30, 11.5, WIN_FTC, '48" x 48"', label="CB-GR-Clerestory-E2")
# Great room west clerestory wall (x=30, z=11-16)
place_window(5959678, 30, 20, 11.5, WIN_FTC, '48" x 48"', label="CB-Kit-Clerestory-W1")
place_window(5959678, 30, 30, 11.5, WIN_FTC, '48" x 48"', label="CB-Kit-Clerestory-W2")
# South wall (y=38) — flanking front entry, floor-to-ceiling
place_window(5959677, 36, 38, SILL, WIN_FTC, '48" x 96"', label="CB-Front-W1")
place_window(5959677, 52, 38, SILL, WIN_FTC, '48" x 96"', label="CB-Front-W2")
# Powder room — small accent on south wall
place_window(5959677, 55, 38, SILL_BATH, WIN_AWNING, '24" x 72"', label="CB-PowderRm-S")

# ── RIGHT WING ────────────────────────────────────────────────
print("\n[RIGHT WING WINDOWS]")
# Bed 3 north wall (y=8) — 2× floor-to-ceiling
place_window(5959680, 76,  8, SILL, WIN_FTC, '48" x 96"', label="RW-Bed3-N1")
place_window(5959680, 84,  8, SILL, WIN_FTC, '48" x 96"', label="RW-Bed3-N2")
# Bed 3 east wall (x=88) — 1× floor-to-ceiling
place_window(5959683, 88, 16, SILL, WIN_FTC, '48" x 96"', label="RW-Bed3-E")
# Bath 2 east wall — awning privacy
place_window(5959683, 88, 28, SILL_BATH, WIN_AWNING, '24" x 72"', label="RW-Bath-E")
# Bed 2 south wall (y=44) — 2× floor-to-ceiling
place_window(5959681, 76, 44, SILL, WIN_FTC, '48" x 96"', label="RW-Bed2-S1")
place_window(5959681, 84, 44, SILL, WIN_FTC, '48" x 96"', label="RW-Bed2-S2")
# Bed 2 east wall (x=88)
place_window(5959683, 88, 38, SILL, WIN_FTC, '48" x 96"', label="RW-Bed2-E")

print("\n" + "=" * 60)
print("STAGE 3 COMPLETE — Review doors & windows in Revit")
print("=" * 60)
