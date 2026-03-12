"""
build_237e8fc6.py — v3 CORRECT
Mitchell Madison | 3,000 SF | 2-Story | Contemporary | L-Shape
4 bed | 2 full + 1 half bath | 2-car garage attached left

CONCEPT:
- L1 = full L footprint (main wing + service zone + garage)
- L2 = true second floor OVER SERVICE ZONE ONLY (x=0–30, y=0–52)
- Main wing stays single story (contemporary flat look, CB Roof z=16)
- Garage single story (Garage Roof z=12)
- Service zone walls go full 2-story height (L1 H=11 + L2 H=9 = 20ft total)
- L2 floor at z=11 (Level 2.0)

FOOTPRINT:
N (back porch / views)
y=0  ┌──────────────────────────────────────────────┐
     │ SVC/L2│     MAIN WING (single story)         │
     │ x=0–30│     x=30–96                          │
     │       │  Kitchen │ Great Room │ Master        │
     │       │  x=30–74 │ x=52–74   │ x=74–96       │
y=26 │       ├──────────┼────────────┤               │
     │ GARAGE│  MUD/PANT│ open       │               │
     │ x=0–26│  x=26–52 │ great rm   │               │
y=52 └───────┴──────────┴────────────┴───────────────┘
S (street / front entry)
     x=0   x=26  x=30  x=52        x=74         x=96

L1 ZONES:
- Great room:   x=52–96, y=0–26   (44×26 = 1,144 SF) vaulted, OPEN
- Kitchen/Dining: x=30–52, y=0–26 (22×26 = 572 SF) open to great room
- Master bed:   x=74–96, y=26–48  (22×22 = 484 SF)
- Master bath:  x=74–96, y=48–52  (22×4) + part of zone
- Service zone: x=0–30, y=0–52   (30×52 = 1,560 SF) mud+pantry+stair+half bath+laundry
- Garage:       x=0–26, y=26–52  (26×26 = 676 SF)

Wait — let me resize to give master more depth and kitchen more room:
- Main wing:    x=30–96, y=0–52  (66×52 = 3,432 SF single story)
- Master:       x=74–96, y=0–36  (22×36 = 792 SF zone — bed+bath+closet)
- Great room:   x=30–74, y=0–28  (44×28 = 1,232 SF) vaulted HERO
- Kitchen/Dining: x=30–74, y=28–52 (44×24 = 1,056 SF) open to great rm
- Service:      x=0–30, y=0–52   (30×52 = 1,560 SF) L2 over this zone
- Garage:       x=0–26, y=26–52  (26×26 = 676 SF)

L2 (over service zone x=0–30, y=0–52):
- Landing:      x=0–30, y=22–32  (30×10 = 300 SF)
- Bed 3:        x=0–15, y=0–22   (15×22 = 330 SF)
- Bed 4:        x=15–30, y=0–22  (15×22 = 330 SF)
- Bath 2:       x=0–15, y=32–44  (15×12 = 180 SF)
- Bath 3:       x=15–30, y=32–44 (15×12 = 180 SF)
- Laundry L2:   x=0–30, y=44–52  (30×8 = 240 SF)

Back porch: x=30–74, y=-12–0 (44ft wide, 12ft deep, N face main wing)
Front porch: x=57–67, y=52–60 (10ft wide, 8ft deep, S face centered)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    create_wall, create_rect_exterior,
    place_door, place_window,
    smart_floor, make_roof,
    create_room, label_rooms,
    attach_walls_to_roof,
    call, T, WIN
)

# ── LEVELS ────────────────────────────────────────────────
L1   = "Level 1.0"
L2   = "Level 2.0"
L1R  = "L1 Roof"     # z=10  — back/front porch roof
GARR = "Garage Roof" # z=12  — garage roof
CBR  = "CB Roof"     # z=16  — main wing roof (contemporary)
L2R  = "L2 Roof"     # z=20  — L2 roof

# ── WALL TYPES ────────────────────────────────────────────
EXT  = 'Wall 7.5" EXT PBR'
INT  = 'Wall 4.5 Interior"'

# ── HEIGHTS ───────────────────────────────────────────────
H1   = 11   # L1 wall plate height (→ Level 2.0 z=11)
H2   = 9    # L2 wall plate height (z=11 → L2 Roof z=20)
HGAR = 12   # garage height (→ Garage Roof z=12)

# ── FAMILIES ──────────────────────────────────────────────
IDOOR  = "Door-Interior-Single-1_Panel-Wood"
ISLIDE = "Exterior_Sliding_Door_3843"
GOHD   = "Door-Garage-Flush_Panel"
WFAM   = "Instance-Window-Fixed"

print("=" * 60)
print("BUILD: Mitchell Madison | 237e8fc6 v3")
print("3,000 SF | 2-Story | Contemporary | L-Shape")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# STAGE 1 — L1 EXTERIOR WALLS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 1: L1 EXTERIOR WALLS ===")

# ── MAIN WING (x=30–96, y=0–52) H=11 ───────────────────
w_s  = create_wall(30, 52, 0, 96, 52, 0, L1, EXT, H1, "Main-S")
w_e  = create_wall(96, 52, 0, 96,  0, 0, L1, EXT, H1, "Main-E")
w_n  = create_wall(96,  0, 0, 30,  0, 0, L1, EXT, H1, "Main-N")
# West wall of main wing = x=30, y=0–52
# But y=0–52 — service zone is at x=0–30 so x=30 is the dividing line
# This wall is INTERIOR between service and main wing
w_mw_w = create_wall(30, 52, 0, 30,  0, 0, L1, INT, H1, "Main-W (SVC divider)")

# ── SERVICE ZONE OUTER WALLS (x=0–30, y=0–52) H=11 ─────
# These go full L1 height — L2 walls sit on top at z=11
w_sv_s = create_wall( 0, 52, 0, 26, 52, 0, L1, EXT, H1, "SVC-S (shared w gar)")
w_sv_w = create_wall( 0, 52, 0,  0,  0, 0, L1, EXT, H1, "SVC-W")
w_sv_n = create_wall( 0,  0, 0, 30,  0, 0, L1, EXT, H1, "SVC-N")
# SVC east = w_mw_w (already created as interior)

# ── GARAGE (x=0–26, y=26–52) H=12 ──────────────────────
# Garage south shares w_sv_s — skip
# Garage west shares w_sv_w — skip
w_gar_n = create_wall( 0, 26, 0, 26, 26, 0, L1, EXT, HGAR, "GAR-N")
w_gar_e = create_wall(26, 26, 0, 26, 52, 0, L1, EXT, HGAR, "GAR-E")

# ── L2 EXTERIOR WALLS (z=11, over service zone) ─────────
w_l2_n = create_wall(30,  0, 11,  0,  0, 11, L2, EXT, H2, "L2-N")
w_l2_w = create_wall( 0,  0, 11,  0, 52, 11, L2, EXT, H2, "L2-W")
w_l2_s = create_wall( 0, 52, 11, 30, 52, 11, L2, EXT, H2, "L2-S")
w_l2_e = create_wall(30, 52, 11, 30,  0, 11, L2, EXT, H2, "L2-E")

# ── FRONT PORCH (x=57–67, y=52–60) ─────────────────────
w_fp_s = create_wall(57, 60, 0, 67, 60, 0, L1, EXT, H1, "FP-S")
w_fp_w = create_wall(57, 52, 0, 57, 60, 0, L1, EXT, H1, "FP-W")
w_fp_e = create_wall(67, 60, 0, 67, 52, 0, L1, EXT, H1, "FP-E")

# ═══════════════════════════════════════════════════════════
# STAGE 2 — FLOORS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 2: FLOORS ===")

# Main wing L1 — x=30–96, y=0–52
smart_floor(L1, 0, 30,  0, 96, 52, exp_w=False)

# Service zone L1 — x=0–30, y=0–52 (minus garage corner)
smart_floor(L1, 0,  0,  0, 30, 52, exp_e=False)

# NO separate garage slab — service zone floor above covers it; separate slab causes overlap

# Back porch — x=30–74, y=-12–0
smart_floor(L1, 0, 30,-12, 74,  0, exp_w=False, exp_e=False, exp_s=True, exp_n=False)

# Front porch — x=57–67, y=52–60
smart_floor(L1, 0, 57, 52, 67, 60, exp_w=False, exp_e=False, exp_n=False)

# L2 floor — x=0–30, y=0–52 (at z=11)
l2_floor = smart_floor(L2, 11, 0, 0, 30, 52)

# Attach all L1 walls under L2 to floor underside so they don't poke through
# Must run AFTER floors are created
print("  Attaching L1 service zone walls to L2 floor underside...")
# Wall IDs recorded here after build — update after each fresh run:
if l2_floor:
    attach_walls_to_roof([w_mw_w, w_sv_w, w_sv_n, w_gar_n, w_gar_e], l2_floor)

# ═══════════════════════════════════════════════════════════
# STAGE 3 — ROOFS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 3: ROOFS ===")

# Main wing — contemporary low shed, CB Roof base z=16
# Slopes N to S (low at S street side, high at N views)
r_main = make_roof("Main wing", 30, 0, 96, 52, CBR,
                   pitch=0.083, slope_style="shed", shed_low_edge=2,
                   oh_n=True, oh_e=True, oh_s=True, oh_w=False)
if r_main:
    attach_walls_to_roof([w_s, w_e, w_n, w_mw_w], r_main)

# Garage has NO separate roof — the L2 floor slab at z=11 IS the garage ceiling.
# A separate garage roof creates a phantom room between z=11 and z=12.
# GAR-N and GAR-E walls terminate at the L2 floor above.

# L2 wing — flat contemporary, L2 Roof z=20
r_l2 = make_roof("L2 wing", 0, 0, 30, 52, L2R,
                 pitch=0.083, slope_style="shed", shed_low_edge=0,
                 oh_n=True, oh_w=True, oh_e=False, oh_s=False)
if r_l2:
    attach_walls_to_roof([w_l2_n, w_l2_w, w_l2_s, w_l2_e], r_l2)

# Back porch — pull south edge 0.4ft back from house N wall (prevents roof protruding into house)
r_bp = make_roof("Back porch", 30, -12, 74, -0.4, L1R,
                 pitch=0.083, slope_style="shed", shed_low_edge=0,
                 oh_n=True, oh_e=True, oh_w=True, oh_s=False)

# Front porch — pull north edge 0.4ft back from house S wall
r_fp = make_roof("Front porch", 57, 52.4, 67, 60, L1R,
                 pitch=0.083, slope_style="shed", shed_low_edge=2,
                 oh_s=True, oh_e=True, oh_w=True, oh_n=False)

# ═══════════════════════════════════════════════════════════
# STAGE 4 — L1 INTERIOR WALLS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 4: L1 INTERIOR WALLS ===")

# Great room / kitchen divider (y=28, x=30–74)
w_gr_kit = create_wall(30, 28, 0, 74, 28, 0, L1, INT, H1, "GR/Kitchen divider")

# Master suite west wall (x=74, y=0–52)
w_mst_w  = create_wall(74, 52, 0, 74,  0, 0, L1, INT, H1, "Master W wall")

# Master bed / bath split (y=36, x=74–96)
w_mst_bb = create_wall(74, 36, 0, 96, 36, 0, L1, INT, H1, "Master bed/bath split")

# Master bath / closet split (y=46, x=74–88)
w_mst_bc = create_wall(74, 46, 0, 88, 46, 0, L1, INT, H1, "Master bath/closet split")

# Service zone internal walls (x=0–30)
# Mudroom: x=0–26, y=30–52 (bottom of service, above garage)
w_mud_n  = create_wall( 0, 30, 0, 26, 30, 0, L1, INT, H1, "Mud N wall")

# Butler pantry: x=0–26, y=14–30
w_bp_s   = create_wall( 0, 14, 0, 26, 14, 0, L1, INT, H1, "Butler pantry S wall")

# Half bath: x=26–30, y=30–42
w_hb_w   = create_wall(26, 42, 0, 26, 30, 0, L1, INT, H1, "Half bath W wall")
w_hb_n   = create_wall(26, 30, 0, 30, 30, 0, L1, INT, H1, "Half bath N wall")

# Laundry L1: x=26–30, y=16–30
w_lau_s  = create_wall(26, 16, 0, 30, 16, 0, L1, INT, H1, "Laundry S wall")
w_lau_w  = create_wall(26, 30, 0, 26, 16, 0, L1, INT, H1, "Laundry W wall")

# Stair: x=0–26, y=0–14
print("  [info] Stair zone x=0–26, y=0–14 — add stairs manually in Revit")

# ═══════════════════════════════════════════════════════════
# STAGE 5 — L2 INTERIOR WALLS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 5: L2 INTERIOR WALLS ===")

# Landing: x=0–30, y=22–32
w_land_n = create_wall( 0, 22, 11, 30, 22, 11, L2, INT, H2, "Landing N")
w_land_s = create_wall(30, 32, 11,  0, 32, 11, L2, INT, H2, "Landing S")

# Bed 3 / Bed 4 divider (x=15, y=0–22)
w_b34    = create_wall(15,  0, 11, 15, 22, 11, L2, INT, H2, "Bed3/Bed4 divider")

# Bath 2 / Bath 3 divider (x=15, y=32–44)
w_ba_div = create_wall(15, 32, 11, 15, 44, 11, L2, INT, H2, "Bath2/Bath3 divider")

# Bath south wall (y=44, x=0–30)
w_ba_s   = create_wall( 0, 44, 11, 30, 44, 11, L2, INT, H2, "Bath S wall")

# ═══════════════════════════════════════════════════════════
# STAGE 6 — DOORS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 6: DOORS ===")

# Front entry (S face main wing, centered x=63)
place_door(w_s, 63, 52, 0, IDOOR, '36" x 96"', label="Front Entry", level=L1)

# Garage OH doors (W face garage) — must flip after placement, tracks face inward by default
d_goh1 = place_door(w_sv_w, 0, 34, 0, GOHD, "10x10", label="Garage OH-1", level=L1)
d_goh2 = place_door(w_sv_w, 0, 46, 0, GOHD, "10x10", label="Garage OH-2", level=L1)
from barnhaus_revit_utils import flip_door
flip_door(d_goh1)
flip_door(d_goh2)

# Garage → Mud man door (E wall garage)
place_door(w_gar_e, 26, 40, 0, IDOOR, '36" x 96"', label="Garage→Mud", level=L1)

# Back porch slider — great room N wall
place_door(w_n, 52, 0, 0, ISLIDE, '8\'-0"W. x 8\'-0"H. 2', label="GR→Porch", level=L1)

# Master patio slider — N wall master zone
place_door(w_n, 85, 0, 0, ISLIDE, '6\'-0"W. x 8\'-0"H.', label="Master→Patio", level=L1)

# Master bedroom door (W wall)
place_door(w_mst_w, 74, 46, 0, IDOOR, '36" x 96"', label="Master door", level=L1)

# Master bath door
place_door(w_mst_bb, 85, 36, 0, IDOOR, '32" x 96"', label="Master bath", level=L1)

# Service zone doors
place_door(w_mw_w,  30, 14, 0, IDOOR, '36" x 96"', label="Pantry→Kitchen", level=L1)
place_door(w_mw_w,  30, 40, 0, IDOOR, '36" x 96"', label="Mud→GR", level=L1)
place_door(w_mud_n, 13, 30, 0, IDOOR, '36" x 96"', label="Mud door", level=L1)
place_door(w_bp_s,  13, 14, 0, IDOOR, '36" x 96"', label="Pantry door", level=L1)
place_door(w_hb_n,  28, 30, 0, IDOOR, '30" x 96"', label="Half bath", level=L1)
place_door(w_lau_w, 26, 23, 0, IDOOR, '36" x 96"', label="Laundry L1", level=L1)

# L2 doors off landing
place_door(w_land_n,  7, 22, 11, IDOOR, '36" x 96"', label="Bed3 door", level=L2)
place_door(w_land_n, 22, 22, 11, IDOOR, '36" x 96"', label="Bed4 door", level=L2)
place_door(w_land_s,  7, 32, 11, IDOOR, '36" x 96"', label="Bath2 door", level=L2)
place_door(w_land_s, 22, 32, 11, IDOOR, '36" x 96"', label="Bath3 door", level=L2)
place_door(w_ba_s,   15, 44, 11, IDOOR, '36" x 96"', label="Laundry L2", level=L2)

# ═══════════════════════════════════════════════════════════
# STAGE 7 — WINDOWS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 7: WINDOWS ===")

# North face — great room view wall
place_window(w_n, 40,  0, 2.5, WFAM, '72" x 36"', "GR N win 1", L1)
place_window(w_n, 62,  0, 2.5, WFAM, '72" x 36"', "GR N win 2", L1)  # moved: was 55, overlapped 8ft slider at x=52
place_window(w_n, 68,  0, 2.5, WFAM, '72" x 36"', "Kitchen N win", L1)

# East face — master bedroom
place_window(w_e, 96, 12, 2.5, WFAM, '48" x 96"', "Master E win 1", L1)
place_window(w_e, 96, 24, 2.5, WFAM, '48" x 96"', "Master E win 2", L1)

# South face — great room + dining
place_window(w_s, 50, 52, 2.5, WFAM, '72" x 36"', "GR S win", L1)

# L2 north face — bedroom windows
place_window(w_l2_n,  7,  0, 13.5, WFAM, '48" x 48"', "Bed3 N win", L2)
place_window(w_l2_n, 22,  0, 13.5, WFAM, '48" x 48"', "Bed4 N win", L2)

# L2 west face
place_window(w_l2_w,  0, 10, 13.5, WFAM, '48" x 48"', "Bed3 W win", L2)
place_window(w_l2_w,  0, 38, 13.5, WFAM, '48" x 48"', "Bed4 W win", L2)

# ═══════════════════════════════════════════════════════════
# STAGE 8 — ROOM LABELS
# ═══════════════════════════════════════════════════════════
print("\n=== STAGE 8: ROOM LABELS ===")

label_rooms([
    {"name": "Great Room",     "x": 52, "y": 14},
    {"name": "Kitchen",        "x": 45, "y": 40},
    {"name": "Dining",         "x": 52, "y": 40},
    {"name": "Master Bedroom", "x": 85, "y": 18},
    {"name": "Master Bath",    "x": 85, "y": 41},
    {"name": "Master Closet",  "x": 81, "y": 49},
    {"name": "Butler Pantry",  "x": 13, "y": 22},
    {"name": "Mud Room",       "x": 13, "y": 41},
    {"name": "Half Bath",      "x": 28, "y": 36},
    {"name": "Laundry",        "x": 28, "y": 23},
    {"name": "Garage",         "x": 13, "y": 42},
], L1, upper_limit_level="Level 2.0")

label_rooms([
    {"name": "Landing",   "x": 15, "y": 27, "z": 11},
    {"name": "Bedroom 3", "x":  7, "y": 11, "z": 11},
    {"name": "Bedroom 4", "x": 22, "y": 11, "z": 11},
    {"name": "Bath 2",    "x":  7, "y": 38, "z": 11},
    {"name": "Bath 3",    "x": 22, "y": 38, "z": 11},
    {"name": "Laundry",   "x": 15, "y": 48, "z": 11},
], L2, upper_limit_level="L2 Roof")

print("\n=== STAGE 9: PORCH POSTS ===")
from barnhaus_revit_utils import place_porch_posts

# Front porch posts — outer edge y=60, 2 corner posts
place_porch_posts(post_xs=[57, 67], post_y=60, level=L1,
                  porch_depth=8, wall_height=11, shed_slopes_toward_larger_y=True)

# Back porch posts — outer edge y=-12, 4 posts evenly spaced
place_porch_posts(post_xs=[30, 44, 59, 74], post_y=-12, level=L1,
                  porch_depth=12, wall_height=11, shed_slopes_toward_larger_y=False)

print("\n=== BUILD COMPLETE ===")
print("Mitchell Madison | 237e8fc6 | L-shape 2-story")
print("Next: fixtures_237e8fc6.py")
