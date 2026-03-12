"""
build_bac79cf7.py — 693 Rancho Real (bac79cf7) v5
4 bed / 3 full + 1 half bath | 2-story | Hill Country / Single Slope | ~2,450 SF living

CHANGES v4:
  - Exterior walls draw in reversed direction — correct facing, NO flips needed
  - Back to centerline walls + T expansion on floors (clean alignment)
  - Interior walls at pure centerline coords (no poke-through when no flipping)
  - L1 foyer corridor added along north side of master (y=24-28, x=0-22)
  - Garage door on east face (away from house)
  - Roof junction fixed: service oh_e=False, garage oh_w=False

LAYOUT:
  L1:
    x=0-22   Master suite
      y=24-28  Foyer/entry corridor (connects front door to master)
      y=10-24  Master bed
      x=11-22, y=0-10  Master bath
      x=0-11,  y=0-10  His/hers closet
    x=22-48  Living core (great room + kitchen, open plan)
    x=48-56  Service (mudroom y=18-28, pantry y=9-18, half bath y=0-9)
    x=56-80  Garage (2-car, door on east face)

  L2 (x=22-56, corridor 4ft wide at center y=14 → walls y=12, y=16):
    North (y=16-28): Bed2(22-36) Bath2(36-44) Bed3(44-56)
    South (y=0-12):  Bed4(22-36) Bath3(36-44) Bonus(44-56)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
import time
from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, create_garage,
    place_door, place_window,
    smart_floor, make_roof,
    create_double_loaded_corridor, create_stairs,
    call, T, WIN
)

EXT = 'Wall 7.5" EXT PBR'
INT = 'Wall 4.5 Interior"'
L1  = "Level 1.0"
L2  = "Level 2.0"
H   = 10    # L1 ceiling/plate height (Level 1 → L1 Roof at z=10)
L2_Z = 11   # Level 2.0 actual elevation (confirmed from manifest)
H12 = 12    # Garage wall height
W1  = 2.5   # L1 window sill height
W2  = L2_Z + 2.5  # L2 window sill height (above L2 floor)

MX0, MY0, MX1, MY1 = 0, 0, 56, 28
GX0, GY0, GX1, GY1 = 56, 0, 80, 24

MASTER_X  = 22
FOYER_Y   = 24   # foyer corridor starts here (y=24-28, 4ft wide)
MBED_Y    = 10
MBATH_X   = 11

SVC_X     = 48
MUD_Y     = 18
PANTRY_Y  = 9

L2X0, L2Y0, L2X1, L2Y1 = 22, 0, 56, 28
L2_COR_CENTER = 14
L2_COR_S  = 12
L2_COR_N  = 16
L2_N_B2E  = 36
L2_N_B3W  = 44
L2_S_B4E  = 36
L2_S_BONW = 44


def make_level(name, elev):
    r = call("revit.create_level", {"name": name, "elevation": elev})
    print(f"  level [{name}]: {'ok' if r['Status']=='ok' else 'exists/ok'}")
    return name

print("=" * 60)
print("BUILD v5: 693 Rancho Real | bac79cf7")
print("2-story | ~2,450 SF | 4 bed / 3.5 bath")
print("=" * 60)

# ── PHASE 0: LEVELS ─────────────────────────────────────────────
print("\n=== PHASE 0: LEVELS ===")
L_L1R  = make_level("L1 Roof",     H)
L_GARR = make_level("Garage Roof", H12)
L_L2R  = make_level("L2 Roof",     20)

# ── PHASE 1: EXTERIOR WALLS ─────────────────────────────────────
print("\n=== PHASE 1: EXTERIOR WALLS ===")
# Main house — skip east wall (shared with garage)
L1w = create_rect_exterior(MX0, MY0, MX1, MY1, 0, L1, EXT, H, "L1", skip_faces=["east"])
w_l1_s = L1w["south"]; w_l1_n = L1w["north"]
w_l1_w = L1w["west"]

# Single shared wall at x=56 — spans full house height (not garage height)
w_shared = create_wall(MX1, MY1, 0, MX1, MY0, 0, L1, EXT, H, "house/garage shared")

# Garage — skip west wall (shared wall above handles it)
Gw = create_garage(GX0, GY0, GX1, GY1, 0, L1, EXT, H12,
                   garage_cars=2, door_face="east", skip_faces=["west"], label="Garage")
w_gar_s = Gw["south"]; w_gar_n = Gw["north"]
w_gar_e = Gw["east"]

time.sleep(2)  # extra buffer after garage door — Revit join engine can be slow here

L2w = create_rect_exterior(L2X0, L2Y0, L2X1, L2Y1, L2_Z, L2, EXT, H, "L2")
w_l2_s = L2w["south"]; w_l2_n = L2w["north"]
w_l2_w = L2w["west"];  w_l2_e = L2w["east"]

# ── PHASE 2: INTERIOR WALLS ─────────────────────────────────────
print("\n=== PHASE 2: INTERIOR WALLS ===")

# Master east wall (full depth) — entry door provides L1 circulation from living core
w_master_e = create_wall(MASTER_X, MY0, 0, MASTER_X, MY1, 0, L1, INT, H, "master east")

# No foyer pocket wall — living core is open plan circulation

# Master bed / bath+closet divider (y=10)
w_mbed_s   = create_wall(MX0, MBED_Y, 0, MASTER_X, MBED_Y, 0, L1, INT, H, "master bed south")

# Bath / closet divider (x=11)
w_mbath_e  = create_wall(MBATH_X, MY0, 0, MBATH_X, MBED_Y, 0, L1, INT, H, "mbath east/closet west")

# Service zone
w_svc_w    = create_wall(SVC_X, MY0, 0, SVC_X, MY1, 0, L1, INT, H, "service west")
w_mud_s    = create_wall(SVC_X, MUD_Y, 0, MX1, MUD_Y, 0, L1, INT, H, "mudroom south")
w_pant_s   = create_wall(SVC_X, PANTRY_Y, 0, MX1, PANTRY_Y, 0, L1, INT, H, "pantry south")

# L2 corridor (4ft zone)
corridor   = create_double_loaded_corridor(L2X0, L2X1, L2_COR_CENTER, L2_Z, L2, INT, H,
                                           corridor_width=4.0, label="L2 corridor")
w_cor_s    = corridor["south_wall"]
w_cor_n    = corridor["north_wall"]

# L2 north room dividers
w_l2_n1 = create_wall(L2_N_B2E, L2_COR_N, L2_Z, L2_N_B2E, L2Y1, L2_Z, L2, INT, H, "L2 bed2E/bath2W")
w_l2_n2 = create_wall(L2_N_B3W, L2_COR_N, L2_Z, L2_N_B3W, L2Y1, L2_Z, L2, INT, H, "L2 bath2E/bed3W")

# L2 south room dividers
w_l2_s1 = create_wall(L2_S_B4E,  L2Y0, L2_Z, L2_S_B4E,  L2_COR_S, L2_Z, L2, INT, H, "L2 bed4E/bath3W")
w_l2_s2 = create_wall(L2_S_BONW, L2Y0, L2_Z, L2_S_BONW, L2_COR_S, L2_Z, L2, INT, H, "L2 bath3E/bonusW")

# ── PHASE 3: FLOORS ─────────────────────────────────────────────
print("\n=== PHASE 3: FLOORS ===")
# Both slabs expand to cover the shared wall at x=56 (centerline wall, ext face at x=56±T)
smart_floor(L1, 0, MX0, MY0, MX1, MY1)                # house: full expansion all sides
smart_floor(L1, 0, GX0, GY0, GX1, GY1)                # garage: full expansion all sides
smart_floor(L2, L2_Z, L2X0, L2Y0, L2X1, L2Y1)

# ── PHASE 4: L1 DOORS ────────────────────────────────────────────
print("\n=== PHASE 4: L1 DOORS ===")

# Front entry — north wall, living core
place_door(w_l1_n, None, MY1, 0,
    "Door-Exterior-Double-Full Glass-Wood_Clad", '60" x 96"',
    label="front entry", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

# Rear slider — south wall, living core
place_door(w_l1_s, None, MY0, 0,
    "Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00",
    label="rear slider", wall_axis='x', wall_start=MASTER_X, wall_end=SVC_X)

# Master suite entry — from living core, upper portion of master east wall
place_door(w_master_e, MASTER_X, 20, 0,
    "Door-Interior-Single-1_Panel-Wood", '36" x 96"',
    label="master entry")

# Master bath — mbed_s wall (x=11-22)
place_door(w_mbed_s, None, MBED_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '32" x 96"',
    label="master bath", wall_axis='x', wall_start=MBATH_X, wall_end=MASTER_X)

# Closet — mbed_s wall (x=0-11)
place_door(w_mbed_s, 5, MBED_Y, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="closet", tight=True)

# Mudroom
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="mudroom", wall_axis='y', wall_start=MUD_Y, wall_end=MY1)

# Butler pantry
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '30" x 96"',
    label="butler pantry", wall_axis='y', wall_start=PANTRY_Y, wall_end=MUD_Y)

# Half bath
place_door(w_svc_w, SVC_X, None, 0,
    "Door-Interior-Single-1_Panel-Wood", '28"',
    label="half bath", wall_axis='y', wall_start=MY0, wall_end=PANTRY_Y, tight=True)

# Mud to garage
place_door(w_gar_n, None, GY1, 0,
    "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
    label="mud to garage", wall_axis='x', wall_start=GX0, wall_end=GX1)

# ── PHASE 5: L1 WINDOWS ──────────────────────────────────────────
print("\n=== PHASE 5: L1 WINDOWS ===")
# Living core south — windows flanking the 4-panel slider (slider is centered at x=35)
# Keep windows well outside slider zone (x=22-48)
# Place on master zone south wall and service zone south wall instead
place_window(w_l1_s,  8, MY0, W1, label="master S1",   **WIN["master"])   # master bedroom south
place_window(w_l1_s, 52, MY0, W1, label="service S1",  **WIN["accent"])   # service zone south
# Living core north — feature windows flanking entry door (entry centered at x=35)
# Push windows to either side, clear of door opening (~5ft wide = x=32.5-37.5)
place_window(w_l1_n, 26, MY1, W1, label="living N1", **WIN["living"])   # left of entry
place_window(w_l1_n, 45, MY1, W1, label="living N2", **WIN["living"])   # right of entry
# Master zone north — smaller bedroom windows
place_window(w_l1_n,  8, MY1, W1, label="master N",  **WIN["master"])
# Master west wall — two master bedroom windows
place_window(w_l1_w, MX0, 14, W1, label="master W1", **WIN["master"])
place_window(w_l1_w, MX0, 20, W1, label="master W2", **WIN["master"])
# Master bath — privacy window (high sill set by caller)
place_window(w_l1_w, MX0,  5, W1 + 2.0, label="mbath W", **WIN["bath"])

# ── PHASE 6: L2 DOORS ────────────────────────────────────────────
print("\n=== PHASE 6: L2 DOORS ===")
place_door(w_cor_s, 29, L2_COR_S, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bed2",  level=L2)
place_door(w_cor_s, 40, L2_COR_S, L2_Z, "Door-Interior-Single-1_Panel-Wood", '28"',        label="L2 bath2", tight=True, level=L2)
place_door(w_cor_s, 50, L2_COR_S, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bed3",  level=L2)
place_door(w_cor_n, 28, L2_COR_N, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bed4",  level=L2)
place_door(w_cor_n, 39, L2_COR_N, L2_Z, "Door-Interior-Single-1_Panel-Wood", '28"',        label="L2 bath3", tight=True, level=L2)
place_door(w_cor_n, 49, L2_COR_N, L2_Z, "Door-Interior-Single-1_Panel-Wood", '30" x 96"', label="L2 bonus", level=L2)

# ── PHASE 7: L2 WINDOWS ──────────────────────────────────────────
print("\n=== PHASE 7: L2 WINDOWS ===")
# Bedrooms — standard bedroom windows
place_window(w_l2_n, 29,   L2Y1, W2, label="L2 bed2 N",  **WIN["bedroom"])
place_window(w_l2_n, 50,   L2Y1, W2, label="L2 bed3 N",  **WIN["bedroom"])
place_window(w_l2_s, 29,   L2Y0, W2, label="L2 bed4 S",  **WIN["bedroom"])
place_window(w_l2_s, 50,   L2Y0, W2, label="L2 bonus S", **WIN["bedroom"])
# Bathrooms — small/privacy
place_window(w_l2_n, 40,   L2Y1, W2 + 1.5, label="L2 bath2 N", **WIN["bath"])
place_window(w_l2_s, 40,   L2Y0, W2 + 1.5, label="L2 bath3 S", **WIN["bath"])
# End walls — accent windows
place_window(w_l2_w, L2X0, 21,   W2, label="L2 west",  **WIN["accent"])
place_window(w_l2_e, L2X1, 7,    W2, label="L2 east",  **WIN["accent"])

# ── PHASE 8: STAIRS ──────────────────────────────────────────────
print("\n=== PHASE 8: STAIRS ===")
create_stairs(SVC_X, MY0, L1, L2, width=4.0, run_length=12.0, label="Main stairs")

# ── PHASE 9: ROOFS ───────────────────────────────────────────────
print("\n=== PHASE 9: ROOFS ===")
make_roof("L2 upper",   L2X0, L2Y0, L2X1, L2Y1, L_L2R)
# L1 master: ONLY single-story zone (x=0-22). No overhang on east (L2 west wall is there).
make_roof("L1 master",  MX0,  MY0,  MASTER_X, MY1, L_L1R, oh_e=False)
# NOTE: NO roof for service zone (x=48-56) — it sits directly below L2 floor.
#       The L2 floor slab is the ceiling for that zone. Never place a roof below another floor level.
# Garage: no overhang toward house on west side (shared wall)
make_roof("Garage",     GX0,  GY0,  GX1, GY1,      L_GARR, oh_w=False)

print("\n✅ Build v4 complete — 693 Rancho Real (bac79cf7)")
print("   Manual: set single-slope pitch on roofs, add stairs family")
