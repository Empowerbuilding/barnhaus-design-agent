"""
build_e670353b_clean.py — STAGE 1 (Shell + Roofs + Porches + Posts)
Submission: e670353b | Mitchell Madison | 2,750 SF | H-shape | Hill Country

Rules applied: Sections 16,18,19,21,23,24,27,28,29,30,31,32

Overhang standards (Section 32):
  LW:     1ft S+N+W, no overhang E (breezeway)
  CB:     2ft all 4 sides
  RW:     1ft S+N+E, no overhang W (breezeway)
  GAR:    1ft all 4 sides
  Porch:  2ft eave edge only, no overhang house edge

Wall centerlines inset EXT_HALF=0.3125ft from slab edge (Section 28).
Clerestory walls start at Wing Roof level z=9 (Section 31).
Porch shed_low_edge: back=2 (outer y=48), front=0 (outer y=6) (Section 29).
Porch posts at floor outer edge, top offset = roof_z_at_outer - wing_h (Section 30).
"""

import sys, requests
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils_v2 import health_check

BASE = 'http://localhost:3000/execute'

def call(tool, payload):
    r = requests.post(BASE, json={'request_id': tool, 'tool': tool, 'payload': payload}, timeout=90)
    d = r.json()
    return d.get('Status'), d.get('Result'), d.get('Message')

if not health_check():
    print("❌ Bridge not healthy"); sys.exit(1)

EXT    = 'Wall 7.5" EXT PBR'
INT    = 'Wall 4.5 Interior"'
ROOF_T = '13" Roof No Gyp'
LEVEL  = 'Level 1.0'

EXT_HALF  = 0.3125   # Section 28
WING_H    = 9.0
BRIDGE_H  = 16.0
CLEREST_H = 7.0      # 16 - 9
GAR_H     = 12.0
OV_WING   = 1.0      # Section 32
OV_BRIDGE = 2.0
OV_PORCH  = 2.0

ext_wall_ids = []

def ext_wall(x0, y0, x1, y1, h, label, nx, ny, level=LEVEL):
    s, r, m = call('revit.create_wall', {
        'start_point': {'x': x0, 'y': y0, 'z': 0},
        'end_point':   {'x': x1, 'y': y1, 'z': 0},
        'wall_type': EXT, 'level': level, 'height': h,
    })
    wid = (r or {}).get('wall_id')
    if not wid: print(f"  ❌ {label}: {m}"); return None
    s2, r2, _ = call('revit.get_wall_orientation', {'wall_id': wid})
    ox = round((r2 or {}).get('orientation', {}).get('x', 0))
    oy = round((r2 or {}).get('orientation', {}).get('y', 0))
    if ox != nx or oy != ny:
        call('revit.flip_wall', {'wall_id': wid})
        print(f"  ✅ {label}: {wid} (flipped)")
    else:
        print(f"  ✅ {label}: {wid}")
    ext_wall_ids.append(wid)
    return wid

def int_wall(x0, y0, x1, y1, h, label):
    s, r, m = call('revit.create_wall', {
        'start_point': {'x': x0, 'y': y0, 'z': 0},
        'end_point':   {'x': x1, 'y': y1, 'z': 0},
        'wall_type': INT, 'level': LEVEL, 'height': h,
    })
    wid = (r or {}).get('wall_id')
    print(f"  {'✅' if wid else '❌'} {label}: {wid or m}")
    return wid

def make_floor(pts, label, level=LEVEL):
    s, r, m = call('revit.create_floor', {'boundary_points': pts, 'level': level})
    fid = (r or {}).get('floor_id')
    print(f"  {'✅' if fid else '❌'} {label}: {fid or m} {f'({(r or {}).get(\"area_sf\",\"\")} SF)' if fid else ''}")
    return fid

def make_roof(pts, level, pitch, slope, label, low_edge=2):
    s, r, m = call('revit.create_roof', {
        'boundary_points': pts, 'roof_type': ROOF_T, 'level': level,
        'pitch': pitch, 'slope_style': slope, 'shed_low_edge': low_edge,
    })
    rid = (r or {}).get('roof_id')
    print(f"  {'✅' if rid else '❌'} {label}: {rid or m}")
    return rid

def attach(wids, rid, label):
    ids = [i for i in wids if i]
    if rid and ids:
        s,r,m = call('revit.attach_walls_to_roof', {'wall_ids': ids, 'roof_id': rid, 'location': 'Top'})
        print(f"  {label}: {'✅' if s=='ok' else '❌'} {m or ''}")

def create_level(elev, name):
    s, r, m = call('revit.create_level', {'elevation': elev, 'name': name})
    print(f"  {name} z={elev}: {'✅' if s=='ok' else f'ℹ️ exists' if 'unique' in (m or '').lower() else f'❌ {m}'}")

# Wall centerline coords (inset EXT_HALF from slab edges)
H = EXT_HALF
LW_S=8+H;  LW_N=50-H; LW_W=0+H;  LW_E=24-H
CB_S=14+H; CB_N=38-H; CB_W=32+H; CB_E=60-H
RW_S=8+H;  RW_N=50-H; RW_W=68+H; RW_E=90-H
GS=50+H;   GN=74-H;   GW=0+H;    GE=24-H
BW_S=14+H; BW_N=38-H

# ════════════════════════════════════════
print("\n══ LEVELS ══")
create_level(9.0,  'Wing Roof')
create_level(12.0, 'Garage Roof')
create_level(16.0, 'Bridge Roof')

# ════════════════════════════════════════
print("\n══ EXTERIOR WALLS ══")
lw_s  = ext_wall(LW_W,LW_S, LW_E,LW_S,  WING_H,   'LW-south',   0,-1)
lw_es = ext_wall(LW_E,LW_S, LW_E,BW_S,  WING_H,   'LW-east-S',  1, 0)
lw_en = ext_wall(LW_E,BW_N, LW_E,LW_N,  WING_H,   'LW-east-N',  1, 0)
lw_n  = ext_wall(LW_E,LW_N, LW_W,LW_N,  WING_H,   'LW-north',   0, 1)
lw_w  = ext_wall(LW_W,LW_N, LW_W,LW_S,  WING_H,   'LW-west',   -1, 0)
bwl_s = ext_wall(LW_E,BW_S, CB_W,BW_S,  WING_H,   'BW-L-south', 0,-1)
bwl_n = ext_wall(LW_E,BW_N, CB_W,BW_N,  WING_H,   'BW-L-north', 0, 1)

cb_s  = ext_wall(CB_W,CB_S, CB_E,CB_S,  BRIDGE_H, 'CB-south',   0,-1)
cb_e  = ext_wall(CB_E,CB_S, CB_E,CB_N,  BRIDGE_H, 'CB-east',    1, 0)
cb_n  = ext_wall(CB_E,CB_N, CB_W,CB_N,  BRIDGE_H, 'CB-north',   0, 1)
cb_w  = ext_wall(CB_W,CB_N, CB_W,CB_S,  BRIDGE_H, 'CB-west',   -1, 0)

# Clerestory: start at Wing Roof level (Section 31)
print("  -- clerestory (Wing Roof base) --")
clr_w = ext_wall(CB_W,CB_S, CB_W,CB_N,  CLEREST_H,'CB-clr-W',  -1, 0, level='Wing Roof')
clr_e = ext_wall(CB_E,CB_N, CB_E,CB_S,  CLEREST_H,'CB-clr-E',   1, 0, level='Wing Roof')

bwr_s = ext_wall(CB_E,BW_S, RW_W,BW_S,  WING_H,   'BW-R-south', 0,-1)
bwr_n = ext_wall(CB_E,BW_N, RW_W,BW_N,  WING_H,   'BW-R-north', 0, 1)

rw_s  = ext_wall(RW_W,RW_S, RW_E,RW_S,  WING_H,   'RW-south',   0,-1)
rw_e  = ext_wall(RW_E,RW_S, RW_E,RW_N,  WING_H,   'RW-east',    1, 0)
rw_n  = ext_wall(RW_E,RW_N, RW_W,RW_N,  WING_H,   'RW-north',   0, 1)
rw_ws = ext_wall(RW_W,RW_S, RW_W,BW_S,  WING_H,   'RW-west-S', -1, 0)
rw_wn = ext_wall(RW_W,BW_N, RW_W,RW_N,  WING_H,   'RW-west-N', -1, 0)

gar_s = ext_wall(GW,GS, GE,GS,  GAR_H, 'GAR-south',  0,-1)
gar_e = ext_wall(GE,GS, GE,GN,  GAR_H, 'GAR-east',   1, 0)
gar_n = ext_wall(GE,GN, GW,GN,  GAR_H, 'GAR-north',  0, 1)
gar_w = ext_wall(GW,GN, GW,GS,  GAR_H, 'GAR-west',  -1, 0)

# ════════════════════════════════════════
print("\n══ INTERIOR WALLS ══")
int_wall(0,30,  24,30,  WING_H,   'LW-master-south')
int_wall(0,18,  24,18,  WING_H,   'LW-bath-south')
int_wall(14,18, 14,30,  WING_H,   'LW-bath-wic-div')
int_wall(12,8,  12,18,  WING_H,   'LW-laundry-util-div')
int_wall(18,8,  18,18,  WING_H,   'LW-util-butler-div')
int_wall(32,28, 54,28,  BRIDGE_H, 'CB-kitchen-living')
int_wall(54,14, 54,38,  BRIDGE_H, 'CB-dining-div')
int_wall(76,14, 76,42,  WING_H,   'RW-hall-east')
int_wall(68,42, 76,42,  WING_H,   'RW-bed4-south')
int_wall(76,28, 90,28,  WING_H,   'RW-bed2-south')
int_wall(80,18, 80,28,  WING_H,   'RW-bath2-west')
int_wall(76,18, 90,18,  WING_H,   'RW-bath2-south')
int_wall(68,20, 76,20,  WING_H,   'RW-bath3-north')

# ════════════════════════════════════════
print("\n══ FLOORS ══")
make_floor([  # Full H polygon
    {'x':0,'y':8},{'x':24,'y':8},{'x':24,'y':14},{'x':68,'y':14},
    {'x':68,'y':8},{'x':90,'y':8},{'x':90,'y':50},{'x':68,'y':50},
    {'x':68,'y':38},{'x':24,'y':38},{'x':24,'y':50},{'x':0,'y':50},
], 'H-main-floor')
make_floor([{'x':0,'y':50},{'x':24,'y':50},{'x':24,'y':74},{'x':0,'y':74}], 'GAR-floor')
make_floor([{'x':35,'y':38},{'x':57,'y':38},{'x':57,'y':48},{'x':35,'y':48}], 'BP-floor')
make_floor([{'x':41,'y':6}, {'x':51,'y':6}, {'x':51,'y':14},{'x':41,'y':14}], 'FP-floor')

# ════════════════════════════════════════
print("\n══ ROOFS (Section 32 overhang standards) ══")
OW = OV_WING; OB = OV_BRIDGE

lw_roof  = make_roof([  # 1ft S+N+W, no E
    {'x':0-OW,'y':8-OW}, {'x':24,'y':8-OW},
    {'x':24,'y':50+OW},  {'x':0-OW,'y':50+OW},
], 'Wing Roof', 0.333, 'gable', 'LW-roof')

rw_roof  = make_roof([  # 1ft S+N+E, no W
    {'x':68,'y':8-OW},   {'x':90+OW,'y':8-OW},
    {'x':90+OW,'y':50+OW},{'x':68,'y':50+OW},
], 'Wing Roof', 0.333, 'gable', 'RW-roof')

cb_roof  = make_roof([  # 2ft all sides
    {'x':32-OB,'y':14-OB}, {'x':60+OB,'y':14-OB},
    {'x':60+OB,'y':38+OB}, {'x':32-OB,'y':38+OB},
], 'Bridge Roof', 0.333, 'gable', 'CB-roof')

bwl_roof = make_roof([{'x':24,'y':14},{'x':32,'y':14},{'x':32,'y':38},{'x':24,'y':38}],
                     'Wing Roof', 0.0, 'flat', 'BW-L-roof')
bwr_roof = make_roof([{'x':60,'y':14},{'x':68,'y':14},{'x':68,'y':38},{'x':60,'y':38}],
                     'Wing Roof', 0.0, 'flat', 'BW-R-roof')

gar_roof = make_roof([  # 1ft all sides
    {'x':0-OW,'y':50-OW},  {'x':24+OW,'y':50-OW},
    {'x':24+OW,'y':74+OW}, {'x':0-OW,'y':74+OW},
], 'Garage Roof', 0.167, 'shed', 'GAR-roof')

# Porch roofs: overhang on eave edge only (Section 29)
bp_roof  = make_roof([  # back porch: low at y=48+OV (outer eave)
    {'x':35,'y':38}, {'x':57,'y':38},
    {'x':57,'y':48+OV_PORCH}, {'x':35,'y':48+OV_PORCH},
], 'Wing Roof', 0.167, 'shed', 'BP-roof', low_edge=2)

fp_roof  = make_roof([  # front porch: low at y=6-OV (outer eave)
    {'x':41,'y':6-OV_PORCH}, {'x':51,'y':6-OV_PORCH},
    {'x':51,'y':14}, {'x':41,'y':14},
], 'Wing Roof', 0.167, 'shed', 'FP-roof', low_edge=0)

# ════════════════════════════════════════
print("\n══ ATTACH WALLS TO ROOFS (Section 31) ══")
attach([lw_s,lw_es,lw_en,lw_n,lw_w,bwl_s,bwl_n], lw_roof, 'LW')
attach([cb_s,cb_e,cb_n,cb_w],                     cb_roof, 'CB')
attach([clr_w,clr_e],                             cb_roof, 'CB-clr')
attach([rw_s,rw_e,rw_n,rw_ws,rw_wn,bwr_s,bwr_n], rw_roof, 'RW')
attach([gar_s,gar_e,gar_n,gar_w],                 gar_roof,'GAR')

# ════════════════════════════════════════
print("\n══ PORCH POSTS (Section 30) ══")
post_ids = []
BP_DEPTH = 10.0; FP_DEPTH = 8.0; PITCH = 0.167
for label, px, py, top_z in [
    ('BP-L', 35.5, 48, WING_H - BP_DEPTH*PITCH),
    ('BP-M', 46.0, 48, WING_H - BP_DEPTH*PITCH),
    ('BP-R', 56.5, 48, WING_H - BP_DEPTH*PITCH),
    ('FP-L', 41.5, 6,  WING_H - FP_DEPTH*PITCH),
    ('FP-R', 50.5, 6,  WING_H - FP_DEPTH*PITCH),
]:
    s,r,m = call('revit.place_family_instance', {
        'family_name': 'HSS-Hollow Structural Section-Column',
        'type_name': 'HSS6X6X3/16',
        'location': {'x': px, 'y': py, 'z': 0}, 'level': LEVEL
    })
    eid = (r or {}).get('element_id') or (r or {}).get('instance_id')
    print(f"  {'✅' if eid else '❌'} {label}: {eid or m}")
    if eid: post_ids.append((label, eid, top_z))

for label, eid, top_z in post_ids:
    call('revit.set_parameter_value', {
        'element_id': eid, 'parameter_name': 'Top Offset', 'value': top_z - WING_H})

print(f"\n✅ STAGE 1 COMPLETE — {len(ext_wall_ids)} ext walls")
print("→ Verify 3D: H-shape, overhangs, porches, posts")
print("→ Say 'stage 2' for doors + windows")
