"""
build_7c01e155.py — Full Build Stages 1-4
Submission: 7c01e155 | Mitchell Madison | 3,250 SF | Contemporary | H-Shape
3 Bed / 3 Bath | 3-Car Garage Left Side-Loaded | Zone Heights L=11 C=16 R=11
"""
from barnhaus_revit_utils import (
    create_wall, create_floor, make_roof, attach_walls_to_roof,
    place_door, place_window, place_porch_posts, create_room,
    _call, T, WIN_FAMILY
)

LEVEL  = "Level 1.0"
L2     = "Level 2.0"   # z=11
LC     = "L1 Center"   # z=16
LP     = "Porch"       # z=9
EXT    = 'Wall 7.5" EXT PBR'
INT    = 'Wall 4.5 Interior"'
ISLIDE = "Exterior_Sliding_Door_3843"
ISWING = "Door-Interior-Single-1_Panel-Wood"
GOHD   = "Door-Garage-Flush_Panel"

# ── GEOMETRY ──────────────────────────────────────────────
LX0,LX1 = 0,  32   # Left wing x
CX0,CX1 = 32, 62   # Center bridge x
RX0,RX1 = 62, 94   # Right wing x
Y0, Y1  = 8,  56   # All wings south/north face
CBY0    = 18        # Center bridge south (recessed — creates breezeway y=8-18)
GAY1    = 30        # Garage / master split

# ── CREATE LEVELS ──────────────────────────────────────────
r = _call("revit.list_levels", {})
existing = [l["name"] for l in r.get("Result",{}).get("levels",[])]
for name, elev in [("L1 Center", 16), ("Porch", 9)]:
    if name not in existing:
        _call("revit.create_level", {"name": name, "elevation": elev})
        print(f"  Created level {name} at {elev}ft")

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 1: EXTERIOR WALLS ===")
# ══════════════════════════════════════════════════════════

# LEFT WING
w_lw_s  = create_wall(LX1,Y0,0, LX0,Y0,0, LEVEL, EXT, 11.0, "lw-south")
w_lw_w  = create_wall(LX0,Y0,0, LX0,Y1,0, LEVEL, EXT, 11.0, "lw-west")
w_lw_n  = create_wall(LX0,Y1,0, LX1,Y1,0, LEVEL, EXT, 11.0, "lw-north")
w_lw_ebw = create_wall(LX1,CBY0,0, LX1,Y0,0, LEVEL, EXT, 11.0, "lw-east-bw")  # breezeway gap only

# CENTER BRIDGE
w_cb_s  = create_wall(CX1,CBY0,0, CX0,CBY0,0, LEVEL, EXT, 16.0, "cb-south")
w_cb_n  = create_wall(CX0,Y1,0,  CX1,Y1,0,  LEVEL, EXT, 16.0, "cb-north")

# RIGHT WING
w_rw_s   = create_wall(RX1,Y0,0,  RX0,Y0,0,  LEVEL, EXT, 11.0, "rw-south")
w_rw_e   = create_wall(RX1,Y0,0,  RX1,Y1,0,  LEVEL, EXT, 11.0, "rw-east")
w_rw_n   = create_wall(RX1,Y1,0,  RX0,Y1,0,  LEVEL, EXT, 11.0, "rw-north")
w_rw_wbw = create_wall(RX0,Y0,0,  RX0,CBY0,0, LEVEL, EXT, 11.0, "rw-west-bw")  # breezeway gap only

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 1: FLOORS ===")
# ══════════════════════════════════════════════════════════

# Main H-shape slab (full rect covers wings + breezeways)
create_floor(LEVEL, 0, [
    (LX0-T, Y0-T), (RX1+T, Y0-T),
    (RX1+T, Y1+T), (LX0-T, Y1+T),
])
# Front porch slab
create_floor(LEVEL, 0, [
    (RX0-T, 0),    (RX1+T, 0),
    (RX1+T, Y0+T), (RX0-T, Y0+T),
])
# Rear porch slab
create_floor(LEVEL, 0, [
    (CX0-T, Y1),   (CX1+T, Y1),
    (CX1+T, Y1+10),(CX0-T, Y1+10),
])

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 1: ROOFS ===")
# ══════════════════════════════════════════════════════════

r_lw  = make_roof("Left Wing",     LX0,Y0, LX1,Y1, L2, pitch=6/12, slope_style="gable")
r_cb  = make_roof("Center Bridge", CX0,CBY0,CX1,Y1, LC, pitch=10/12, slope_style="gable")
r_rw  = make_roof("Right Wing",    RX0,Y0, RX1,Y1, L2, pitch=6/12, slope_style="gable")
r_fp  = make_roof("Front Porch",   RX0,0,  RX1,Y0, LP, pitch=1/12, slope_style="shed", shed_low_edge=0)
r_rp  = make_roof("Rear Porch",    CX0,Y1, CX1,Y1+10, LP, pitch=1/12, slope_style="shed", shed_low_edge=2)
r_bwl = make_roof("Breezeway-L",   LX1,Y0, CX0,CBY0,  LP, pitch=0, slope_style="flat")
r_bwr = make_roof("Breezeway-R",   CX1,Y0, RX0,CBY0,  LP, pitch=0, slope_style="flat")

print("\n=== STAGE 1: ATTACH WALLS ===")
if r_lw: attach_walls_to_roof([w_lw_s, w_lw_w, w_lw_n, w_lw_ebw], r_lw)
if r_cb: attach_walls_to_roof([w_cb_s, w_cb_n], r_cb)
if r_rw: attach_walls_to_roof([w_rw_s, w_rw_e, w_rw_n, w_rw_wbw], r_rw)

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 2: INTERIOR WALLS ===")
# ══════════════════════════════════════════════════════════

# LEFT WING interiors
w_gar_spl = create_wall(LX0,GAY1,0, LX1,GAY1,0, LEVEL, INT, 11.0, "gar-split")      # y=30 garage/master
w_lw_util = create_wall(9,  GAY1,0, 9,  Y1,  0, LEVEL, INT, 11.0, "util-east")      # x=9 util/master
w_bath_n  = create_wall(9,  40,  0, LX1,40,  0, LEVEL, INT, 11.0, "bath-north")     # y=40 bath/bed split
w_wic_e   = create_wall(24, GAY1,0, 24, 40,  0, LEVEL, INT, 11.0, "wic-east")       # x=24 wic/bath split

# CENTER BRIDGE interiors (connect at x=32/x=62 — no new wall needed, bridge walls ARE the boundary)
w_kd_spl  = create_wall(CX0,36,  0, 48, 36,  0, LEVEL, INT, 11.0, "kitchen-dining") # y=36 split
w_kg_spl  = create_wall(48, CBY0,0, 48, Y1,  0, LEVEL, INT, 11.0, "kitchen-gr")     # x=48 split

# RIGHT WING interiors
w_bed_spl = create_wall(RX0,32,  0, 82, 32,  0, LEVEL, INT, 11.0, "bed2-bed3")      # y=32 split
w_svc_w   = create_wall(82, Y0,  0, 82, Y1,  0, LEVEL, INT, 11.0, "svc-west")       # x=82 service col
w_b3_n    = create_wall(82, 26,  0, RX1,26,  0, LEVEL, INT, 11.0, "bath3-north")    # y=26 bath3/mud
w_mud_b2  = create_wall(82, 44,  0, RX1,44,  0, LEVEL, INT, 11.0, "mud-bath2")      # y=44 mud/bath2

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 3: EXTERIOR DOORS ===")
# ══════════════════════════════════════════════════════════

# Garage OH door — south wall of LW, centered in garage x=0-32 → x=16
place_door(w_lw_s,  16, Y0,  0, GOHD,   '16W X 10H',             label="garage-OH",    level=LEVEL, wall_height=11.0)
# Front entry — south wall of RW, centered at x=78
place_door(w_rw_s,  78, Y0,  0, ISLIDE, '6\'-0"W. x 8\'-0"H.',   label="front-entry",  level=LEVEL)
# Master slider — west wall, y=47 (master bedroom area)
place_door(w_lw_w,  LX0,47,  0, ISLIDE, '6\'-0"W. x 8\'-0"H.',   label="master-slider",level=LEVEL)

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 3: INTERIOR DOORS ===")
# ══════════════════════════════════════════════════════════

place_door(w_gar_spl, 22, GAY1, 0, ISWING, '36" x 96"', label="gar-to-house",  level=LEVEL)
place_door(w_lw_util,  9, 50,   0, ISWING, '36" x 96"', label="master-entry",  level=LEVEL)
place_door(w_bath_n,  20, 40,   0, ISWING, '36" x 96"', label="bath-door",     level=LEVEL)
place_door(w_wic_e,   24, 34,   0, ISWING, '30" x 96"', label="wic-door",      level=LEVEL)
place_door(w_lw_util,  9, 36,   0, ISWING, '30" x 96"', label="util-door",     level=LEVEL)
place_door(w_kg_spl,  48, 28,   0, ISWING, '36" x 96"', label="pantry-door",   level=LEVEL)
place_door(w_bed_spl, 72, 32,   0, ISWING, '36" x 96"', label="bed2-door",     level=LEVEL)
place_door(w_bed_spl, 72, 32,   0, ISWING, '36" x 96"', label="bed3-door",     level=LEVEL)  # same wall, different side
place_door(w_svc_w,   82, 48,   0, ISWING, '30" x 96"', label="bath2-door",    level=LEVEL)
place_door(w_svc_w,   82, 20,   0, ISWING, '30" x 96"', label="bath3-door",    level=LEVEL)
place_door(w_svc_w,   82, 34,   0, ISWING, '36" x 96"', label="mud-door",      level=LEVEL)

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 3: WINDOWS ===")
# ══════════════════════════════════════════════════════════

# LW west — master area (clear of slider at y=47)
place_window(w_lw_w,  LX0, 14, 3.0, WIN_FAMILY, '48" x 48"', label="master-w1")
place_window(w_lw_w,  LX0, 35, 5.0, WIN_FAMILY, '24" x 96"', label="mbath-w")
# LW north
place_window(w_lw_n,  16,  Y1, 3.0, WIN_FAMILY, '48" x 48"', label="lw-north-w")
# CB south — clerestory high on 16ft wall
place_window(w_cb_s,  40,  CBY0, 9.0, WIN_FAMILY, '48" x 48"', label="cb-clerestory-1")
place_window(w_cb_s,  54,  CBY0, 9.0, WIN_FAMILY, '48" x 48"', label="cb-clerestory-2")
# CB north — great room / dining view
place_window(w_cb_n,  38,  Y1,  4.0, WIN_FAMILY, '60" x 48"', label="dining-w")
place_window(w_cb_n,  54,  Y1,  4.0, WIN_FAMILY, '60" x 48"', label="gr-north-w")
# RW south — clear of front entry at x=78 (clear zone x=75-81)
place_window(w_rw_s,  66,  Y0,  3.0, WIN_FAMILY, '48" x 48"', label="bed3-s-w")
place_window(w_rw_s,  88,  Y0,  3.0, WIN_FAMILY, '48" x 48"', label="rw-s-w2")
# RW east
place_window(w_rw_e,  RX1, 20,  3.0, WIN_FAMILY, '48" x 48"', label="bed3-e-w")
place_window(w_rw_e,  RX1, 46,  3.0, WIN_FAMILY, '48" x 48"', label="bed2-e-w")
# RW north
place_window(w_rw_n,  70,  Y1,  3.0, WIN_FAMILY, '48" x 48"', label="bed3-n-w")
place_window(w_rw_n,  86,  Y1,  3.0, WIN_FAMILY, '48" x 48"', label="bed2-n-w")

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 3: PORCH POSTS ===")
# ══════════════════════════════════════════════════════════

# Front porch posts (outer edge y=0.5, span x=62-94)
place_porch_posts([64, 72, 82, 92], 0.5, LEVEL, porch_depth=8, wall_height=11)
# Rear porch posts (outer edge y=65.5, span x=32-62)
place_porch_posts([34, 44, 54, 60], Y1+9.5, LEVEL, porch_depth=10, wall_height=16)

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 4: ROOM LABELS ===")
# ══════════════════════════════════════════════════════════

rooms = [
    ("Garage",          16, 19),
    ("Master Bedroom",  20, 48),
    ("Master Bath",     14, 35),
    ("Walk-In Closet",  26, 35),
    ("Laundry/Utility",  4, 44),
    ("Dining",          40, 27),
    ("Kitchen",         40, 46),
    ("Butler Pantry",   55, 27),
    ("Great Room",      55, 42),
    ("Bedroom 3",       71, 20),
    ("Bedroom 2",       71, 44),
    ("Bath 3",          88, 17),
    ("Mudroom",         88, 34),
    ("Bath 2",          88, 50),
]

for name, x, y in rooms:
    create_room(x, y, 0, LEVEL, name, upper_limit_level=L2)

print("\n✅ Full build complete (Stages 1-4)!")
