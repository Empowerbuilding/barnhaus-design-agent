"""
build_c1e4332c_s1.py — Mitchell Madison H-Shape Stage 1
Exterior walls, floors, roofs, porch posts, garage
create_wall(sx, sy, sz, ex, ey, ez, level, wall_type, height, label)
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    _call, create_wall, verify_wall_facing, make_roof,
    attach_walls_to_roof, create_floor, place_porch_posts,
    place_door, flip_door
)

LEVEL   = "Level 1.0"
WING_R  = "Wing Roof"
BRIDGE_R= "Bridge Roof"
GAR_R   = "Garage Roof"
EXT     = 'Wall 7.5" EXT PBR'
INT     = 'Wall 4.5 Interior"'
EH      = 0.3125

print("=== Stage 1: Exterior Shell ===")

# ── LEFT WING (x=0→28, y=8→54, 9ft) ─────────────────────────────────────────
lw_s  = create_wall(0+EH,  8+EH,  0,  28-EH, 8+EH,  0, LEVEL, EXT, height=9, label="LW-S")
lw_n  = create_wall(28-EH, 54-EH, 0,  0+EH,  54-EH, 0, LEVEL, EXT, height=9, label="LW-N")
lw_w  = create_wall(0+EH,  54-EH, 0,  0+EH,  8+EH,  0, LEVEL, EXT, height=9, label="LW-W")
lw_e1 = create_wall(28-EH, 8+EH,  0,  28-EH, 14-EH, 0, LEVEL, EXT, height=9, label="LW-E1")
lw_e2 = create_wall(28-EH, 48+EH, 0,  28-EH, 54-EH, 0, LEVEL, EXT, height=9, label="LW-E2")
verify_wall_facing(lw_s,  0, -1, "LW-S")
verify_wall_facing(lw_n,  0, +1, "LW-N")
verify_wall_facing(lw_w, -1,  0, "LW-W")
verify_wall_facing(lw_e1,+1,  0, "LW-E1")
verify_wall_facing(lw_e2,+1,  0, "LW-E2")

# ── LBZ enclosed corridor (x=28→38, y=14→48, 9ft) ───────────────────────────
lbz_s = create_wall(28+EH, 14+EH, 0,  38-EH, 14+EH, 0, LEVEL, EXT, height=9, label="LBZ-S")
lbz_n = create_wall(38-EH, 48-EH, 0,  28+EH, 48-EH, 0, LEVEL, EXT, height=9, label="LBZ-N")
lbz_e = create_wall(38-EH, 14+EH, 0,  38-EH, 48-EH, 0, LEVEL, EXT, height=9, label="LBZ-E")
lbz_w = create_wall(28+EH, 48-EH, 0,  28+EH, 14+EH, 0, LEVEL, INT, height=9, label="LBZ-W")
verify_wall_facing(lbz_s,  0, -1, "LBZ-S")
verify_wall_facing(lbz_n,  0, +1, "LBZ-N")
verify_wall_facing(lbz_e, +1,  0, "LBZ-E")

# ── CENTER BRIDGE base (x=38→58, y=14→48, 9ft) ───────────────────────────────
cb_s  = create_wall(38+EH, 14+EH, 0,  58-EH, 14+EH, 0, LEVEL, EXT, height=9, label="CB-S")
cb_n  = create_wall(58-EH, 48-EH, 0,  38+EH, 48-EH, 0, LEVEL, EXT, height=9, label="CB-N")
verify_wall_facing(cb_s,  0, -1, "CB-S")
verify_wall_facing(cb_n,  0, +1, "CB-N")

# Clerestory walls (z=9 base, height=7)
cb_cw = create_wall(38+EH, 14+EH, 9,  38+EH, 48-EH, 9, WING_R, EXT, height=7, label="CB-Clere-W")
cb_ce = create_wall(58-EH, 48-EH, 9,  58-EH, 14+EH, 9, WING_R, EXT, height=7, label="CB-Clere-E")
verify_wall_facing(cb_cw, -1,  0, "CB-Clere-W")
verify_wall_facing(cb_ce, +1,  0, "CB-Clere-E")

# ── RBZ enclosed corridor (x=58→68, y=14→48, 9ft) ───────────────────────────
rbz_s = create_wall(58+EH, 14+EH, 0,  68-EH, 14+EH, 0, LEVEL, EXT, height=9, label="RBZ-S")
rbz_n = create_wall(68-EH, 48-EH, 0,  58+EH, 48-EH, 0, LEVEL, EXT, height=9, label="RBZ-N")
rbz_w = create_wall(58+EH, 48-EH, 0,  58+EH, 14+EH, 0, LEVEL, INT, height=9, label="RBZ-W")
rbz_e = create_wall(68-EH, 14+EH, 0,  68-EH, 48-EH, 0, LEVEL, EXT, height=9, label="RBZ-E")
verify_wall_facing(rbz_s,  0, -1, "RBZ-S")
verify_wall_facing(rbz_n,  0, +1, "RBZ-N")
verify_wall_facing(rbz_e, +1,  0, "RBZ-E")

# ── RIGHT WING (x=68→96, y=8→50, 9ft) ───────────────────────────────────────
rw_s  = create_wall(68+EH, 8+EH,  0,  96-EH, 8+EH,  0, LEVEL, EXT, height=9, label="RW-S")
rw_n  = create_wall(96-EH, 50-EH, 0,  68+EH, 50-EH, 0, LEVEL, EXT, height=9, label="RW-N")
rw_e  = create_wall(96-EH, 8+EH,  0,  96-EH, 50-EH, 0, LEVEL, EXT, height=9, label="RW-E")
rw_w1 = create_wall(68+EH, 14-EH, 0,  68+EH, 8+EH,  0, LEVEL, EXT, height=9, label="RW-W1")
rw_w2 = create_wall(68+EH, 50-EH, 0,  68+EH, 48+EH, 0, LEVEL, EXT, height=9, label="RW-W2")
verify_wall_facing(rw_s,  0, -1, "RW-S")
verify_wall_facing(rw_n,  0, +1, "RW-N")
verify_wall_facing(rw_e, +1,  0, "RW-E")
verify_wall_facing(rw_w1,-1,  0, "RW-W1")
verify_wall_facing(rw_w2,-1,  0, "RW-W2")

# ── GARAGE (x=0→34, y=-18→8, 12ft) ──────────────────────────────────────────
gar_s = create_wall(0+EH,  -18+EH, 0,  34-EH, -18+EH, 0, LEVEL, EXT, height=12, label="GAR-S")
gar_n = create_wall(34-EH,  8-EH,  0,  0+EH,   8-EH,  0, LEVEL, EXT, height=12, label="GAR-N")
gar_w = create_wall(0+EH,   8-EH,  0,  0+EH,  -18+EH, 0, LEVEL, EXT, height=12, label="GAR-W")
gar_e = create_wall(34-EH, -18+EH, 0,  34-EH,  8-EH,  0, LEVEL, EXT, height=12, label="GAR-E")
verify_wall_facing(gar_s,  0, -1, "GAR-S")
verify_wall_facing(gar_n,  0, +1, "GAR-N")
verify_wall_facing(gar_w, -1,  0, "GAR-W")
verify_wall_facing(gar_e, +1,  0, "GAR-E")

print("✅ All exterior walls placed")

# ── FLOORS ────────────────────────────────────────────────────────────────────
# Single polygon — full H perimeter including porches
h_poly = [
    (0,8),(28,8),(28,14),(38,14),(38,6),(58,6),(58,14),(68,14),
    (68,8),(96,8),(96,50),(68,50),(68,48),(58,48),(58,58),
    (38,58),(38,48),(28,48),(28,54),(0,54),(0,8),
]
floor_main = create_floor(LEVEL, 0, h_poly)

gar_poly = [(0,-18),(34,-18),(34,8),(0,8),(0,-18)]
floor_gar = create_floor(LEVEL, 0, gar_poly)
print("✅ Floors placed")

# ── ROOFS ─────────────────────────────────────────────────────────────────────
OV = 1.0
OV_CB = 2.0

lw_roof = make_roof("LW-Roof",
    x0=0-OV, y0=8-OV, x1=28+OV, y1=54+OV,
    level_name=WING_R, pitch=0.333,
    oh_s=True, oh_n=True, oh_w=True, oh_e=False)

rw_roof = make_roof("RW-Roof",
    x0=68-OV, y0=8-OV, x1=96+OV, y1=50+OV,
    level_name=WING_R, pitch=0.333,
    oh_s=True, oh_n=True, oh_e=True, oh_w=False)

cb_roof = make_roof("CB-Roof",
    x0=38-OV_CB, y0=14-OV_CB, x1=58+OV_CB, y1=48+OV_CB,
    level_name=BRIDGE_R, pitch=0.333,
    oh_s=True, oh_n=True, oh_w=True, oh_e=True)

gar_roof = make_roof("GAR-Roof",
    x0=0-OV, y0=-18-OV, x1=34+OV, y1=8+OV,
    level_name=GAR_R, pitch=0.083,
    oh_s=True, oh_n=True, oh_w=True, oh_e=True)

fp_roof = make_roof("FP-Roof",
    x0=38, y0=6, x1=58, y1=14,
    level_name=WING_R, pitch=0.083,
    shed_low_edge=0,
    oh_s=True, oh_n=False, oh_w=False, oh_e=False)

bp_roof = make_roof("BP-Roof",
    x0=38, y0=48, x1=58, y1=58,
    level_name=WING_R, pitch=0.083,
    shed_low_edge=2,
    oh_s=False, oh_n=True, oh_w=False, oh_e=False)

print("✅ Roofs placed")

# ── ATTACH WALLS TO ROOFS ─────────────────────────────────────────────────────
attach_walls_to_roof([lw_s, lw_n, lw_w, lw_e1, lw_e2], lw_roof)
attach_walls_to_roof([rw_s, rw_n, rw_e, rw_w1, rw_w2], rw_roof)
attach_walls_to_roof([cb_s, cb_n, cb_cw, cb_ce], cb_roof)
attach_walls_to_roof([lbz_s, lbz_n, lbz_e, lbz_w], lw_roof)
attach_walls_to_roof([rbz_s, rbz_n, rbz_w, rbz_e], rw_roof)
attach_walls_to_roof([gar_s, gar_n, gar_w, gar_e], gar_roof)
print("✅ Walls attached to roofs")

# ── PORCH POSTS ───────────────────────────────────────────────────────────────
place_porch_posts(post_xs=[39.5, 48, 56.5], post_y=6,  level=LEVEL, porch_depth=8,  wall_height=9, shed_slopes_toward_larger_y=True)
place_porch_posts(post_xs=[39.5, 48, 56.5], post_y=58, level=LEVEL, porch_depth=10, wall_height=9, shed_slopes_toward_larger_y=False)
print("✅ Porch posts placed")

# ── GARAGE OVERHEAD DOORS ─────────────────────────────────────────────────────
gd1 = place_door(gar_s, 6,  -18, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D1", level=LEVEL)
gd2 = place_door(gar_s, 17, -18, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D2", level=LEVEL)
gd3 = place_door(gar_s, 28, -18, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D3", level=LEVEL)
flip_door(gd1); flip_door(gd2); flip_door(gd3)
print("✅ Garage doors placed")

print("\n=== STAGE 1 COMPLETE ===")
print("Check Revit 3D — H-shape shell, roofs, garage, porches.")
print("Reply 'stage 2' when ready to continue.")
