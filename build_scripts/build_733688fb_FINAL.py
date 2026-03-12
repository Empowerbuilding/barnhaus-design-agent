"""
build_733688fb_FINAL.py — Full Build Stages 1-4
Submission: 733688fb | Mitchell Madison | 2,750 SF | Contemporary | T-Shape

T-SHAPE GEOMETRY:
  Master zone:   x=0–18,  y=8–44   (11ft walls, low gable)
  Center living: x=18–43, y=8–44   (16ft walls, tall gable — hero elevation)
  Service zone:  x=43–60, y=8–44   (11ft walls, low gable)
  Rear wing:     x=16–43, y=44–76  (11ft walls, shed roof)
  Garage:        x=60–84, y=8–32   (12ft walls, shed roof)
  Front porch:   x=18–43, y=0–8    (shed roof, steel posts)
  Rear porch:    x=16–43, y=76–84  (shed roof, posts)
"""

from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, create_floor,
    make_roof, attach_walls_to_roof,
    place_door, place_window, WIN_FAMILY,
    _call, T
)

LEVEL  = "Level 1.0"
L2     = "Level 2.0"    # z=11
LC     = "L1 Center"    # z=16 (create if needed)
EXT    = 'Wall 7.5" EXT PBR'
INT    = 'Wall 4.5 Interior"'
ISLIDE = "Exterior_Sliding_Door_3843"
ISWING = "Door-Interior-Single-1_Panel-Wood"
GOHD   = "Door-Garage-Flush_Panel"

# Geometry
MX0,MY0,MX1,MY1 = 0,  8,  60, 44
WX0,WY0,WX1,WY1 = 16, 44, 43, 76
GX0,GY0,GX1,GY1 = 60, 8,  84, 32
CX0,CX1         = 18, 43   # center zone

# Ensure L1 Center level exists at 16ft
r = _call("revit.list_levels", {})
existing = [l["name"] for l in r.get("Result",{}).get("levels",[])]
if "L1 Center" not in existing:
    _call("revit.create_level", {"name": "L1 Center", "elevation": 16})
    print("  Created level L1 Center at 16ft")

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 1: EXTERIOR WALLS ===")
# ══════════════════════════════════════════════════════════

# South — 3 segments with different heights
w_s_mast = create_wall(CX0,MY0,0, MX0,MY0,0, LEVEL, EXT, 11.0, "south-master")   # x=18→0
w_s_cent = create_wall(CX1,MY0,0, CX0,MY0,0, LEVEL, EXT, 16.0, "south-center")   # x=43→18 TALL
w_s_svc  = create_wall(MX1,MY0,0, CX1,MY0,0, LEVEL, EXT, 11.0, "south-service")  # x=60→43

# West (master zone, 11ft)
w_west = create_wall(MX0,MY0,0, MX0,MY1,0, LEVEL, EXT, 11.0, "west")

# East (service zone, 11ft) — shared face with garage
w_east = create_wall(MX1,MY1,0, MX1,MY0,0, LEVEL, EXT, 11.0, "east")

# North — split at wing opening (x=16-43)
w_n1 = create_wall(MX0,MY1,0, WX0,MY1,0, LEVEL, EXT, 11.0, "north-left")   # x=0→16
w_n2 = create_wall(WX1,MY1,0, MX1,MY1,0, LEVEL, EXT, 11.0, "north-right")  # x=43→60

# Rear wing
w_ww = create_wall(WX0,WY0,0, WX0,WY1,0, LEVEL, EXT, 11.0, "wing-west")
w_we = create_wall(WX1,WY1,0, WX1,WY0,0, LEVEL, EXT, 11.0, "wing-east")
w_wn = create_wall(WX0,WY1,0, WX1,WY1,0, LEVEL, EXT, 11.0, "wing-north")

# Garage (west face is shared with east wall of main body — skip)
w_gs = create_wall(GX1,GY0,0, GX0,GY0,0, LEVEL, EXT, 12.0, "gar-south")
w_ge = create_wall(GX1,GY0,0, GX1,GY1,0, LEVEL, EXT, 12.0, "gar-east")
w_gn = create_wall(GX0,GY1,0, GX1,GY1,0, LEVEL, EXT, 12.0, "gar-north")

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 1: FLOORS ===")
# ══════════════════════════════════════════════════════════

# T-shape main + wing slab (exterior face offset)
create_floor(LEVEL, 0, [
    (MX0-T, MY0-T), (MX1,    MY0-T),
    (MX1,   MY1+T), (WX1+T,  MY1+T),
    (WX1+T, WY1+T), (WX0-T,  WY1+T),
    (WX0-T, MY1+T), (MX0-T,  MY1+T),
])

# Garage slab
create_floor(LEVEL, 0, [
    (GX0,    GY0-T), (GX1+T, GY0-T),
    (GX1+T,  GY1+T), (GX0,   GY1+T),
])

# Front porch slab
create_floor(LEVEL, 0, [
    (CX0-T, -T),    (CX1+T, -T),
    (CX1+T, MY0+T), (CX0-T, MY0+T),
])

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 1: ROOFS ===")
# ══════════════════════════════════════════════════════════

r_mast = make_roof("Master Zone",  MX0, MY0, CX0, MY1, L2, pitch=6/12, slope_style="gable")
r_cent = make_roof("Center Tall",  CX0, MY0, CX1, MY1, LC, pitch=10/12, slope_style="gable")
r_svc  = make_roof("Service Zone", CX1, MY0, MX1, MY1, L2, pitch=6/12, slope_style="gable")
r_wing = make_roof("Rear Wing",    WX0, WY0, WX1, WY1, L2, pitch=2/12, slope_style="shed", shed_low_edge=2)
r_gar  = make_roof("Garage",       GX0, GY0, GX1, GY1, L2, pitch=1/12, slope_style="shed", shed_low_edge=1)
r_fp   = make_roof("Front Porch",  CX0, 0,   CX1, MY0, L2, pitch=1/12, slope_style="shed", shed_low_edge=0)
r_rp   = make_roof("Rear Porch",   WX0, WY1, WX1, WY1+8, L2, pitch=1/12, slope_style="shed", shed_low_edge=2)

print("\n=== STAGE 1: ATTACH WALLS ===")
if r_mast: attach_walls_to_roof([w_s_mast, w_west, w_n1], r_mast)
if r_cent: attach_walls_to_roof([w_s_cent], r_cent)
if r_svc:  attach_walls_to_roof([w_s_svc,  w_east, w_n2], r_svc)
if r_wing: attach_walls_to_roof([w_ww, w_we, w_wn], r_wing)
if r_gar:  attach_walls_to_roof([w_gs, w_ge, w_gn], r_gar)

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 2: INTERIOR WALLS ===")
# ══════════════════════════════════════════════════════════

w_mast_e    = create_wall(CX0,MY1,0, CX0,MY0,0, LEVEL, INT, 11.0, "master-east")
w_svc_w     = create_wall(CX1,MY0,0, CX1,MY1,0, LEVEL, INT, 11.0, "service-west")
w_mast_bth  = create_wall( 0, 34, 0,  CX0,34, 0, LEVEL, INT, 11.0, "master-bath")
w_his_her   = create_wall( 9, 34, 0,    9,MY1,0, LEVEL, INT, 11.0, "his-her")
w_her_end   = create_wall(14, 34, 0,   14,MY1,0, LEVEL, INT, 11.0, "her-end")
w_laund     = create_wall(CX1,36, 0,  MX1,36, 0, LEVEL, INT, 11.0, "laundry-split")
w_mud_e     = create_wall(55, 36, 0,   55,MY0,0, LEVEL, INT, 11.0, "mudroom-east")
w_off_s     = create_wall(38, 18, 0,  CX1,18, 0, LEVEL, INT, 11.0, "office-south")
w_off_w     = create_wall(38, MY0,0,   38,18, 0, LEVEL, INT, 11.0, "office-west")
w_bed_spl   = create_wall(WX0,62, 0,   30,62, 0, LEVEL, INT, 11.0, "bed2-bed3")
w_wing_mid  = create_wall(30, WY1,0,   30,WY0,0, LEVEL, INT, 11.0, "wing-mid")
w_bath2     = create_wall(30, 62, 0,  WX1,62, 0, LEVEL, INT, 11.0, "bath2-split")
w_bath3     = create_wall(30, 54, 0,  WX1,54, 0, LEVEL, INT, 11.0, "bath3-split")
w_clos      = create_wall(38, 54, 0,   38,62, 0, LEVEL, INT, 11.0, "closet-split")

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 3: EXTERIOR DOORS ===")
# ══════════════════════════════════════════════════════════

place_door(w_s_cent, 30, MY0, 0, ISLIDE, '6\'-0"W. x 8\'-0"H.', label="front-entry",   level=LEVEL)
place_door(w_west,    0, 26,  0, ISLIDE, '6\'-0"W. x 8\'-0"H.', label="master-slider",  level=LEVEL)
place_door(w_gs,     72, GY0, 0, GOHD,  '16W X 10H',            label="garage-OH",      level=LEVEL, wall_height=12.0)

print("\n=== STAGE 3: INTERIOR DOORS ===")
place_door(w_mast_e,   CX0, 20, 0, ISWING, '36" x 96"', label="master-entry",   level=LEVEL)
place_door(w_mast_bth, 14,  34, 0, ISWING, '36" x 96"', label="mbath-door",     level=LEVEL)
place_door(w_his_her,   9,  39, 0, ISWING, '30" x 96"', label="his-door",       level=LEVEL)
place_door(w_her_end,  14,  39, 0, ISWING, '30" x 96"', label="her-door",       level=LEVEL)
place_door(w_off_s,    41,  18, 0, ISWING, '36" x 96"', label="office-door",    level=LEVEL)
place_door(w_svc_w,    CX1, 38, 0, ISWING, '36" x 96"', label="service-entry",  level=LEVEL)
place_door(w_mud_e,    55,  14, 0, ISWING, '36" x 96"', label="mudroom-garage", level=LEVEL)
place_door(w_laund,    50,  36, 0, ISWING, '30" x 96"', label="laundry-door",   level=LEVEL)
place_door(w_wing_mid, 30,  52, 0, ISWING, '36" x 96"', label="bed2-door",      level=LEVEL)
place_door(w_wing_mid, 30,  68, 0, ISWING, '36" x 96"', label="bed3-door",      level=LEVEL)
place_door(w_bath2,    36,  62, 0, ISWING, '30" x 96"', label="bath2-door",     level=LEVEL)
place_door(w_bath3,    36,  54, 0, ISWING, '30" x 96"', label="bath3-door",     level=LEVEL)
place_door(w_clos,     38,  58, 0, ISWING, '30" x 96"', label="closet-door",    level=LEVEL)

print("\n=== STAGE 3: WINDOWS ===")
# South wall — clear of front-entry door (x=30, 6ft wide = x=27-33). Windows at x=10 and x=50
place_window(w_s_mast,  10, MY0, 3.0, WIN_FAMILY, '48" x 48"', label="front-w1")
place_window(w_s_svc,   50, MY0, 3.0, WIN_FAMILY, '48" x 48"', label="front-w2")
# Tall center south — clerestory windows high on center wall (clear of sliding door)
place_window(w_s_cent,  22, MY0, 9.0, WIN_FAMILY, '48" x 48"', label="clerestory-w1")
place_window(w_s_cent,  38, MY0, 9.0, WIN_FAMILY, '48" x 48"', label="clerestory-w2")
# West wall — master slider at y=26. Windows at y=14 and y=38 (clear)
place_window(w_west,     0, 14,  3.0, WIN_FAMILY, '48" x 48"', label="master-w1")
place_window(w_west,     0, 38,  5.0, WIN_FAMILY, '24" x 96"', label="mbath-w")
# North
place_window(w_n2,      52, MY1, 3.0, WIN_FAMILY, '60" x 24"', label="dining-w")
# Wing
place_window(w_wn,      22, WY1, 3.0, WIN_FAMILY, '48" x 48"', label="bed2-w")
place_window(w_wn,      36, WY1, 3.0, WIN_FAMILY, '48" x 48"', label="bed3-w")
place_window(w_ww,      WX0,52,  3.0, WIN_FAMILY, '48" x 48"', label="bed2-side-w")
place_window(w_we,      WX1,68,  3.0, WIN_FAMILY, '48" x 48"', label="bed3-side-w")
place_window(w_we,      WX1,50,  4.0, WIN_FAMILY, '24" x 96"', label="bath-w")

# ══════════════════════════════════════════════════════════
print("\n=== STAGE 4: ROOM LABELS ===")
# ══════════════════════════════════════════════════════════
from barnhaus_revit_utils import create_room

rooms = [
    ("Master Bedroom",  9,  20),
    ("Master Bath",     5,  38),
    ("His Closet",     11,  39),
    ("Her Closet",     16,  39),
    ("Great Room",     30,  18),
    ("Kitchen",        26,  36),
    ("Dining",         39,  36),
    ("Office",         41,  13),
    ("Laundry",        52,  40),
    ("Mudroom",        50,  13),
    ("Bedroom 2",      23,  52),
    ("Bedroom 3",      23,  68),
    ("Bath 2",         36,  68),
    ("Bath 3",         36,  49),
    ("Closet 2",       34,  58),
    ("Garage",         72,  20),
]

for name, x, y in rooms:
    create_room(x, y, 0, LEVEL, name, upper_limit_level=L2)

print("\n✅ Full build complete (Stages 1-4) — take 3D screenshot!")
