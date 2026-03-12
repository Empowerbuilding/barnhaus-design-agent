"""
build_c1e4332c_s1b.py — Stage 1 continuation
Walls already placed. This adds: missing corridor walls, floors, roofs, posts, garage doors.
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    _call, create_wall, verify_wall_facing, make_roof,
    attach_walls_to_roof, create_floor, place_porch_posts,
    place_door, flip_door
)

LEVEL    = "Level 1.0"
WING_R   = "Wing Roof"
BRIDGE_R = "Bridge Roof"
GAR_R    = "Garage Roof"
EXT      = 'Wall 7.5" EXT PBR'
INT      = 'Wall 4.5 Interior"'
EH       = 0.3125

# Wall IDs from first run
lw_s=5952307; lw_n=5952308; lw_w=5952309; lw_e1=5952310; lw_e2=5952311
lbz_s=5952312; lbz_n=5952313; lbz_e=5952314
cb_s=5952316; cb_n=5952317; cb_cw=5952318; cb_ce=5952319
rbz_s=5952320; rbz_n=5952321; rbz_e=5952322
rw_s=5952324; rw_n=5952325; rw_e=5952326; rw_w1=5952327; rw_w2=5952328
gar_s=5952330; gar_n=5952331; gar_w=5952333; gar_e=5952334

print("=== Stage 1b: Completing shell ===")

# ── Missing corridor walls (failed due to wrong type name) ────────────────────
lbz_w = create_wall(28+EH, 48-EH, 0, 28+EH, 14+EH, 0, LEVEL, INT, height=9, label="LBZ-W")
rbz_w = create_wall(58+EH, 48-EH, 0, 58+EH, 14+EH, 0, LEVEL, INT, height=9, label="RBZ-W")

# ── FLOORS ────────────────────────────────────────────────────────────────────
h_poly = [
    (0,8),(28,8),(28,14),(38,14),(38,6),(58,6),(58,14),(68,14),
    (68,8),(96,8),(96,50),(68,50),(68,48),(58,48),(58,58),
    (38,58),(38,48),(28,48),(28,54),(0,54),(0,8),
]
floor_main = create_floor(LEVEL, 0, h_poly)
floor_gar  = create_floor(LEVEL, 0, [(0,-18),(34,-18),(34,8),(0,8),(0,-18)])
print("✅ Floors placed")

# ── ROOFS ─────────────────────────────────────────────────────────────────────
lw_roof = make_roof("LW-Roof",  x0=-1, y0=7,  x1=29, y1=55, level_name=WING_R,   pitch=0.333, oh_s=True, oh_n=True, oh_w=True, oh_e=False)
rw_roof = make_roof("RW-Roof",  x0=67, y0=7,  x1=97, y1=51, level_name=WING_R,   pitch=0.333, oh_s=True, oh_n=True, oh_e=True, oh_w=False)
cb_roof = make_roof("CB-Roof",  x0=36, y0=12, x1=60, y1=50, level_name=BRIDGE_R, pitch=0.333, oh_s=True, oh_n=True, oh_w=True, oh_e=True)
gar_roof= make_roof("GAR-Roof", x0=-1, y0=-19,x1=35, y1=9,  level_name=GAR_R,    pitch=0.083, oh_s=True, oh_n=True, oh_w=True, oh_e=True)
fp_roof = make_roof("FP-Roof",  x0=38, y0=6,  x1=58, y1=14, level_name=WING_R,   pitch=0.083, shed_low_edge=0, oh_s=True, oh_n=False, oh_w=False, oh_e=False)
bp_roof = make_roof("BP-Roof",  x0=38, y0=48, x1=58, y1=58, level_name=WING_R,   pitch=0.083, shed_low_edge=2, oh_s=False, oh_n=True, oh_w=False, oh_e=False)
print("✅ Roofs placed")

# ── ATTACH WALLS TO ROOFS ─────────────────────────────────────────────────────
attach_walls_to_roof([lw_s, lw_n, lw_w, lw_e1, lw_e2], lw_roof)
attach_walls_to_roof([lbz_s, lbz_n, lbz_e, lbz_w], lw_roof)
attach_walls_to_roof([cb_s, cb_n, cb_cw, cb_ce], cb_roof)
attach_walls_to_roof([rbz_s, rbz_n, rbz_w, rbz_e], rw_roof)
attach_walls_to_roof([rw_s, rw_n, rw_e, rw_w1, rw_w2], rw_roof)
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
print("Reply 'stage 2' when ready.")
