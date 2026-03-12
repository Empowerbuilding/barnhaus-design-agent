"""
build_eda1a47f_s1.py — Mitchell Madison H-Shape Stage 1
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

LEVEL    = "Level 1.0"
WING_R   = "Wing Roof"
BRIDGE_R = "Bridge Roof"
GAR_R    = "Garage Roof"
EXT      = 'Wall 7.5" EXT PBR'
INT      = 'Wall 4.5 Interior"'
EH       = 0.3125

print("=== eda1a47f Stage 1: Exterior Shell ===")

# Check/create Bridge Roof level at z=16
levels = _call("revit.list_levels", {})
level_names = [l["name"] for l in levels.get("Result", {}).get("levels", [])]
print(f"Existing levels: {level_names}")
if "Bridge Roof" not in level_names:
    r = _call("revit.create_level", {"name": "Bridge Roof", "elevation": 16})
    print(f"Created Bridge Roof level: {r}")
else:
    print("Bridge Roof level already exists ✓")

# ── LEFT WING (x=0→22, y=8→54, 10ft) ────────────────────────────────────────
lw_s  = create_wall(0+EH,  8+EH,  0, 22-EH, 8+EH,  0, LEVEL, EXT, height=10, label="LW-S")
lw_n  = create_wall(22-EH, 54-EH, 0, 0+EH,  54-EH, 0, LEVEL, EXT, height=10, label="LW-N")
lw_w  = create_wall(0+EH,  54-EH, 0, 0+EH,  8+EH,  0, LEVEL, EXT, height=10, label="LW-W")
lw_e1 = create_wall(22-EH, 8+EH,  0, 22-EH, 26-EH, 0, LEVEL, EXT, height=10, label="LW-E1")
lw_e2 = create_wall(22-EH, 54-EH, 0, 22-EH, 54-EH, 0, LEVEL, EXT, height=10, label="LW-E2")  # stub — LBZ covers rest
verify_wall_facing(lw_s,  0, -1, "LW-S")
verify_wall_facing(lw_n,  0, +1, "LW-N")
verify_wall_facing(lw_w, -1,  0, "LW-W")
verify_wall_facing(lw_e1,+1,  0, "LW-E1")

# ── LBZ enclosed corridor (x=22→38, y=26→54, 10ft) ──────────────────────────
lbz_s = create_wall(22+EH, 26+EH, 0, 38-EH, 26+EH, 0, LEVEL, EXT, height=10, label="LBZ-S")
lbz_n = create_wall(38-EH, 54-EH, 0, 22+EH, 54-EH, 0, LEVEL, EXT, height=10, label="LBZ-N")
lbz_e = create_wall(38-EH, 26+EH, 0, 38-EH, 54-EH, 0, LEVEL, EXT, height=10, label="LBZ-E")
lbz_w = create_wall(22+EH, 54-EH, 0, 22+EH, 26+EH, 0, LEVEL, INT, height=10, label="LBZ-W")
verify_wall_facing(lbz_s,  0, -1, "LBZ-S")
verify_wall_facing(lbz_n,  0, +1, "LBZ-N")
verify_wall_facing(lbz_e, +1,  0, "LBZ-E")

# ── CENTER BRIDGE base (x=38→68, y=26→54, 10ft base) ────────────────────────
cb_s  = create_wall(38+EH, 26+EH, 0, 68-EH, 26+EH, 0, LEVEL, EXT, height=10, label="CB-S")
cb_n  = create_wall(68-EH, 54-EH, 0, 38+EH, 54-EH, 0, LEVEL, EXT, height=10, label="CB-N")
verify_wall_facing(cb_s,  0, -1, "CB-S")
verify_wall_facing(cb_n,  0, +1, "CB-N")
# Clerestory walls z=10→16 (6ft tall)
cb_cw = create_wall(38+EH, 26+EH, 10, 38+EH, 54-EH, 10, WING_R, EXT, height=6, label="CB-Clere-W")
cb_ce = create_wall(68-EH, 54-EH, 10, 68-EH, 26+EH, 10, WING_R, EXT, height=6, label="CB-Clere-E")
verify_wall_facing(cb_cw, -1,  0, "CB-Clere-W")
verify_wall_facing(cb_ce, +1,  0, "CB-Clere-E")

# ── RBZ enclosed corridor (x=68→84, y=26→54, 10ft) ──────────────────────────
rbz_s = create_wall(68+EH, 26+EH, 0, 84-EH, 26+EH, 0, LEVEL, EXT, height=10, label="RBZ-S")
rbz_n = create_wall(84-EH, 54-EH, 0, 68+EH, 54-EH, 0, LEVEL, EXT, height=10, label="RBZ-N")
rbz_w = create_wall(68+EH, 54-EH, 0, 68+EH, 26+EH, 0, LEVEL, INT, height=10, label="RBZ-W")
rbz_e = create_wall(84-EH, 26+EH, 0, 84-EH, 54-EH, 0, LEVEL, EXT, height=10, label="RBZ-E")
verify_wall_facing(rbz_s,  0, -1, "RBZ-S")
verify_wall_facing(rbz_n,  0, +1, "RBZ-N")
verify_wall_facing(rbz_e, +1,  0, "RBZ-E")

# ── RIGHT WING (x=84→106, y=8→54, 10ft) ─────────────────────────────────────
rw_s  = create_wall(84+EH,  8+EH,  0, 106-EH, 8+EH,  0, LEVEL, EXT, height=10, label="RW-S")
rw_n  = create_wall(106-EH, 54-EH, 0, 84+EH,  54-EH, 0, LEVEL, EXT, height=10, label="RW-N")
rw_e  = create_wall(106-EH, 8+EH,  0, 106-EH, 54-EH, 0, LEVEL, EXT, height=10, label="RW-E")
rw_w1 = create_wall(84+EH,  26-EH, 0, 84+EH,  8+EH,  0, LEVEL, EXT, height=10, label="RW-W1")
rw_w2 = create_wall(84+EH,  54-EH, 0, 84+EH,  54-EH, 0, LEVEL, EXT, height=10, label="RW-W2")  # stub
verify_wall_facing(rw_s,  0, -1, "RW-S")
verify_wall_facing(rw_n,  0, +1, "RW-N")
verify_wall_facing(rw_e, +1,  0, "RW-E")
verify_wall_facing(rw_w1,-1,  0, "RW-W1")

# ── GARAGE (x=0→36, y=54→78, 12ft) ──────────────────────────────────────────
gar_s = create_wall(0+EH,  78-EH, 0, 36-EH, 78-EH, 0, LEVEL, EXT, height=12, label="GAR-S")
gar_n = create_wall(36-EH, 54+EH, 0, 0+EH,  54+EH, 0, LEVEL, EXT, height=12, label="GAR-N")
gar_w = create_wall(0+EH,  54+EH, 0, 0+EH,  78-EH, 0, LEVEL, EXT, height=12, label="GAR-W")
gar_e = create_wall(36-EH, 78-EH, 0, 36-EH, 54+EH, 0, LEVEL, EXT, height=12, label="GAR-E")
verify_wall_facing(gar_s,  0, +1, "GAR-S")
verify_wall_facing(gar_n,  0, -1, "GAR-N")
verify_wall_facing(gar_w, -1,  0, "GAR-W")
verify_wall_facing(gar_e, +1,  0, "GAR-E")

print("✅ Exterior walls placed")

# ── FLOORS ────────────────────────────────────────────────────────────────────
# Single H polygon — note: LBZ/RBZ only span y=26→54, wings span y=8→54
h_poly = [
    (0,8),(22,8),(22,26),(38,26),(38,14),(50,14),(50,26),(68,26),(68,8),
    (84,8),(84,26),(106,26),(106,54),(84,54),(84,26),  # wait — must be simple polygon
]
# Corrected simple polygon for H footprint:
h_poly = [
    (0,8),
    (22,8),(22,26),(38,26),(38,14),(50,14),(50,26),(68,26),(68,8),(84,8),
    (84,54),(68,54),(68,26),(50,26),(50,14),(38,14),(38,26),(22,26),(22,54),
    (0,54),(0,8)
]
# Front porch separate (x=38→50, y=14→26)
fp_poly = [(38,14),(50,14),(50,26),(38,26),(38,14)]
# Back porch separate (x=38→68, y=0→8)
bp_poly = [(38,0),(68,0),(68,8),(38,8),(38,0)]
# Garage separate
gar_poly = [(0,54),(36,54),(36,78),(0,78),(0,54)]

floor_main = create_floor(LEVEL, 0, h_poly)
floor_fp   = create_floor(LEVEL, 0, fp_poly)
floor_bp   = create_floor(LEVEL, 0, bp_poly)
floor_gar  = create_floor(LEVEL, 0, gar_poly)
print("✅ Floors placed")

# ── ROOFS ─────────────────────────────────────────────────────────────────────
lw_roof  = make_roof("LW-Roof",  x0=-1,  y0=7,   x1=23,  y1=55, level_name=WING_R,   pitch=0.333, oh_s=True, oh_n=True, oh_w=True, oh_e=False)
rw_roof  = make_roof("RW-Roof",  x0=83,  y0=7,   x1=107, y1=55, level_name=WING_R,   pitch=0.333, oh_s=True, oh_n=True, oh_e=True, oh_w=False)
cb_roof  = make_roof("CB-Roof",  x0=36,  y0=24,  x1=70,  y1=56, level_name=BRIDGE_R, pitch=0.333, oh_s=True, oh_n=True, oh_w=True, oh_e=True)
gar_roof = make_roof("GAR-Roof", x0=-1,  y0=53,  x1=37,  y1=79, level_name=GAR_R,    pitch=0.083, oh_s=True, oh_n=True, oh_w=True, oh_e=True)
lbz_roof = make_roof("LBZ-Roof", x0=22,  y0=25,  x1=39,  y1=55, level_name=WING_R,   pitch=0.083, oh_s=False, oh_n=True, oh_w=False, oh_e=False)
rbz_roof = make_roof("RBZ-Roof", x0=67,  y0=25,  x1=85,  y1=55, level_name=WING_R,   pitch=0.083, oh_s=False, oh_n=True, oh_w=False, oh_e=False)
fp_roof  = make_roof("FP-Roof",  x0=38,  y0=14,  x1=50,  y1=26, level_name=WING_R,   pitch=0.083, shed_low_edge=0, oh_s=True, oh_n=False, oh_w=False, oh_e=False)
bp_roof  = make_roof("BP-Roof",  x0=38,  y0=0,   x1=68,  y1=8,  level_name=WING_R,   pitch=0.083, shed_low_edge=0, oh_s=False, oh_n=True, oh_w=False, oh_e=False)
print("✅ Roofs placed")

# ── ATTACH WALLS TO ROOFS ─────────────────────────────────────────────────────
attach_walls_to_roof([lw_s, lw_n, lw_w, lw_e1], lw_roof)
attach_walls_to_roof([lbz_s, lbz_n, lbz_e, lbz_w], lbz_roof)
attach_walls_to_roof([cb_s, cb_n, cb_cw, cb_ce], cb_roof)
attach_walls_to_roof([rbz_s, rbz_n, rbz_w, rbz_e], rbz_roof)
attach_walls_to_roof([rw_s, rw_n, rw_e, rw_w1], rw_roof)
attach_walls_to_roof([gar_s, gar_n, gar_w, gar_e], gar_roof)
print("✅ Walls attached to roofs")

# ── PORCH POSTS ───────────────────────────────────────────────────────────────
# Front portico: 2 posts at corners of x=38→50, y=14
place_porch_posts(post_xs=[39.5, 48.5], post_y=14, level=LEVEL, porch_depth=12, wall_height=10, shed_slopes_toward_larger_y=True)
# Back porch: 3 posts along y=0
place_porch_posts(post_xs=[40, 53, 66], post_y=0, level=LEVEL, porch_depth=8, wall_height=10, shed_slopes_toward_larger_y=False)
print("✅ Porch posts placed")

# ── GARAGE OVERHEAD DOORS (south face, y=78) ──────────────────────────────────
gd1 = place_door(gar_s, 6,  78, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D1", level=LEVEL)
gd2 = place_door(gar_s, 18, 78, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D2", level=LEVEL)
gd3 = place_door(gar_s, 30, 78, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D3", level=LEVEL)
flip_door(gd1); flip_door(gd2); flip_door(gd3)
print("✅ Garage doors placed")

print("\n=== STAGE 1 COMPLETE ===")
print("Check Revit 3D — H-shape shell, roofs, garage, porches.")
print("Reply 'run stage 2' when ready.")
