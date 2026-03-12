"""
build_c1e4332c_MAIN.py — Full Build with Saves (Stages 1-4)
Submission: c1e4332c-3c0d-469d-98d3-58cead8632d7
Client: Mitchell Madison | 3750 SF | H-shape | Hill Country

KEY FIX: save_document() called after exterior walls and interior walls
to ensure IDs persist before placing doors/windows.
"""

import sys, json
sys.path.insert(0, '/home/mitch/.openclaw/workspace')

from barnhaus_revit_utils import (
    call, create_wall, create_rect_exterior,
    make_roof, verify_wall_facing, attach_walls_to_roof, label_rooms
)

LEVEL    = "Level 1.0"
EXT      = 'Wall 7.5" EXT PBR'
INT      = 'Wall 4.5 Interior"'
EXT_HALF = 0.3125
WING_H   = 9.0
BRIDGE_H = 16.0
GAR_H    = 12.0
Z        = 0.0

LW_X0, LW_X1 = 0.0, 28.0;  LW_Y0, LW_Y1 = 8.0, 54.0
CB_X0, CB_X1 = 32.0, 60.0; CB_Y0, CB_Y1 = 14.0, 48.0
RW_X0, RW_X1 = 64.0, 92.0; RW_Y0, RW_Y1 = 8.0, 50.0
GAR_X0, GAR_X1 = 0.0, 34.0; GAR_Y0, GAR_Y1 = -18.0, 8.0
FP_X0, FP_X1 = 32.0, 60.0; FP_Y0, FP_Y1 = 0.0, CB_Y0
BP_X0, BP_X1 = 32.0, 60.0; BP_Y0, BP_Y1 = CB_Y1, 60.0

def save():
    r = call('revit.save_document', {})
    print(f"  💾 SAVED: {r.get('Status')}")
    return r

def make_floor(label, pts):
    r = call('revit.create_floor', {'level': LEVEL, 'boundary_points': pts})
    ok = r['Status'] == 'ok'
    fid = r['Result'].get('floor_id') if ok else None
    print(f"  floor [{label}]: {'ok ' + str(fid) if ok else 'ERR ' + r.get('Message','')}")
    return fid

def iwall(sx, sy, ex, ey, label=""):
    return create_wall(sx, sy, Z, ex, ey, Z, LEVEL, INT, height=WING_H, label=label)

def pdoor(wid, x, y, fam, typ, label=""):
    r = call('revit.place_door', {
        'wall_id': wid, 'location': {'x': x, 'y': y, 'z': 0.0},
        'family_name': fam, 'type_name': typ, 'level': LEVEL,
    })
    ok = r['Status'] == 'ok'
    did = r['Result'].get('door_id') if ok else None
    print(f"  door [{label}] @ ({x},{y}): {'ok ' + str(did) if ok else 'ERR ' + r.get('Message','')}")
    return did

def pwin(wid, x, y, z_sill, fam, typ, label=""):
    r = call('revit.place_window', {
        'wall_id': wid, 'location': {'x': x, 'y': y, 'z': z_sill},
        'family_name': fam, 'type_name': typ, 'level': LEVEL,
    })
    ok = r['Status'] == 'ok'
    wid_r = r['Result'].get('window_id') if ok else None
    print(f"  window [{label}] @ ({x},{y}) z={z_sill}: {'ok ' + str(wid_r) if ok else 'ERR ' + r.get('Message','')}")
    return wid_r

ids = {}

# ══════════════════════════════════════════════════════
# S1: LEVELS + FLOORS + EXTERIOR WALLS
# ══════════════════════════════════════════════════════
print("\n" + "="*60)
print("S1: Levels + Floors + Exterior Walls")
print("="*60)

for lname, elev in [('Wing Roof', WING_H), ('Bridge Roof', BRIDGE_H), ('Garage Roof', GAR_H)]:
    r = call('revit.create_level', {'name': lname, 'elevation': elev})
    ok = r['Status'] == 'ok'
    msg = (r.get('Message') or '')
    if ok: print(f"  Level '{lname}': created {r['Result']['level_id']}")
    elif 'unique' in msg.lower(): print(f"  Level '{lname}': already exists ✓")
    else: print(f"  Level '{lname}': ERR {msg}")

# Floors
ids['lw_floor']  = make_floor('LW',  [{'x':LW_X0,'y':LW_Y0},{'x':LW_X1,'y':LW_Y0},{'x':LW_X1,'y':LW_Y1},{'x':LW_X0,'y':LW_Y1}])
ids['lbz_floor'] = make_floor('LBZ', [{'x':LW_X1,'y':LW_Y0},{'x':CB_X0,'y':LW_Y0},{'x':CB_X0,'y':LW_Y1},{'x':LW_X1,'y':LW_Y1}])
ids['cb_floor']  = make_floor('CB',  [{'x':CB_X0,'y':CB_Y0},{'x':CB_X1,'y':CB_Y0},{'x':CB_X1,'y':CB_Y1},{'x':CB_X0,'y':CB_Y1}])
ids['rbz_floor'] = make_floor('RBZ', [{'x':CB_X1,'y':RW_Y0},{'x':RW_X0,'y':RW_Y0},{'x':RW_X0,'y':RW_Y1},{'x':CB_X1,'y':RW_Y1}])
ids['rw_floor']  = make_floor('RW',  [{'x':RW_X0,'y':RW_Y0},{'x':RW_X1,'y':RW_Y0},{'x':RW_X1,'y':RW_Y1},{'x':RW_X0,'y':RW_Y1}])
ids['gar_floor'] = make_floor('GAR', [{'x':GAR_X0,'y':GAR_Y0},{'x':GAR_X1,'y':GAR_Y0},{'x':GAR_X1,'y':GAR_Y1},{'x':GAR_X0,'y':GAR_Y1}])
ids['fp_floor']  = make_floor('FP',  [{'x':FP_X0,'y':FP_Y0},{'x':FP_X1,'y':FP_Y0},{'x':FP_X1,'y':FP_Y1},{'x':FP_X0,'y':FP_Y1}])
ids['bp_floor']  = make_floor('BP',  [{'x':BP_X0,'y':BP_Y0},{'x':BP_X1,'y':BP_Y0},{'x':BP_X1,'y':BP_Y1},{'x':BP_X0,'y':BP_Y1}])

# LW exterior walls (skip east+south)
lw = create_rect_exterior(LW_X0, LW_Y0, LW_X1, LW_Y1, Z, LEVEL, EXT, height=WING_H, label_prefix='LW', skip_faces=['east','south'])
ids['lw_north'] = lw['north']; ids['lw_west'] = lw['west']

# LW east partial walls (at x=28, inset causes geometry errors)
ids['lw_e_top'] = create_wall(28.0, 54.0, Z, 28.0, 48.0, Z, LEVEL, EXT, height=WING_H, label='LW-E-Top')
verify_wall_facing(ids['lw_e_top'], +1, 0, 'LW-E-Top')
ids['lw_e_bot'] = create_wall(28.0, 14.0, Z, 28.0, 8.0, Z, LEVEL, EXT, height=WING_H, label='LW-E-Bot')
verify_wall_facing(ids['lw_e_bot'], +1, 0, 'LW-E-Bot')

# CB walls (skip east+west), BRIDGE_H
cb = create_rect_exterior(CB_X0, CB_Y0, CB_X1, CB_Y1, Z, LEVEL, EXT, height=BRIDGE_H, label_prefix='CB', skip_faces=['east','west'])
ids['cb_south'] = cb['south']; ids['cb_north'] = cb['north']

# RW walls (skip west)
rw = create_rect_exterior(RW_X0, RW_Y0, RW_X1, RW_Y1, Z, LEVEL, EXT, height=WING_H, label_prefix='RW', skip_faces=['west'])
ids['rw_south'] = rw['south']; ids['rw_north'] = rw['north']; ids['rw_east'] = rw['east']

# RW partial west walls — draw SOUTH→NORTH for correct west-facing
ids['rw_w_top'] = create_wall(64.0, CB_Y1, Z, 64.0, RW_Y1-EXT_HALF, Z, LEVEL, EXT, height=WING_H, label='RW-W-Top')
verify_wall_facing(ids['rw_w_top'], -1, 0, 'RW-W-Top')
ids['rw_w_bot'] = create_wall(64.0, RW_Y0+EXT_HALF, Z, 64.0, CB_Y0, Z, LEVEL, EXT, height=WING_H, label='RW-W-Bot')
verify_wall_facing(ids['rw_w_bot'], -1, 0, 'RW-W-Bot')

# Clerestory walls (Wing Roof level, z=9→16)
ids['cb_cl_w'] = create_wall(CB_X0+EXT_HALF, CB_Y0+EXT_HALF, Z, CB_X0+EXT_HALF, CB_Y1-EXT_HALF, Z, 'Wing Roof', EXT, height=7.0, label='CB-Clerest-W')
verify_wall_facing(ids['cb_cl_w'], -1, 0, 'CB-Clerest-W')
ids['cb_cl_e'] = create_wall(CB_X1-EXT_HALF, CB_Y1-EXT_HALF, Z, CB_X1-EXT_HALF, CB_Y0+EXT_HALF, Z, 'Wing Roof', EXT, height=7.0, label='CB-Clerest-E')
verify_wall_facing(ids['cb_cl_e'], +1, 0, 'CB-Clerest-E')

# Garage walls (skip north)
gar = create_rect_exterior(GAR_X0, GAR_Y0, GAR_X1, GAR_Y1, Z, LEVEL, EXT, height=GAR_H, label_prefix='GAR', skip_faces=['north'])
ids['gar_south'] = gar['south']; ids['gar_west'] = gar['west']; ids['gar_east'] = gar['east']
ids['gar_n_sep'] = create_wall(GAR_X0+EXT_HALF, GAR_Y1-EXT_HALF, Z, LW_X1-EXT_HALF, GAR_Y1-EXT_HALF, Z, LEVEL, INT, height=GAR_H, label='GAR-N-FireSep')
ids['gar_n_ext'] = create_wall(LW_X1-EXT_HALF, GAR_Y1-EXT_HALF, Z, GAR_X1-EXT_HALF, GAR_Y1-EXT_HALF, Z, LEVEL, EXT, height=GAR_H, label='GAR-N-Ext')
verify_wall_facing(ids['gar_n_ext'], 0, +1, 'GAR-N-Ext')

# *** SAVE after exterior walls ***
save()

# Roofs
ids['lw_roof']  = make_roof('LW-Roof',  LW_X0, LW_Y0, LW_X1, LW_Y1, 'Wing Roof', overhang=1.0, oh_e=False, pitch=0.0, slope_style='flat')
ids['cb_roof']  = make_roof('CB-Roof',  CB_X0, CB_Y0, CB_X1, CB_Y1, 'Bridge Roof', overhang=2.0, pitch=0.333, slope_style='gable')
ids['rw_roof']  = make_roof('RW-Roof',  RW_X0, RW_Y0, RW_X1, RW_Y1, 'Wing Roof', overhang=1.0, oh_w=False, pitch=0.0, slope_style='flat')
ids['gar_roof'] = make_roof('GAR-Roof', GAR_X0, GAR_Y0, GAR_X1, GAR_Y1, 'Garage Roof', overhang=1.0, pitch=0.0, slope_style='flat')
ids['bp_roof']  = make_roof('BP-Roof',  BP_X0, BP_Y0+0.4, BP_X1, BP_Y1, LEVEL, overhang=2.0, oh_s=False, pitch=0.25, slope_style='shed', shed_low_edge=2)
ids['fp_roof']  = make_roof('FP-Roof',  FP_X0, FP_Y0, FP_X1, FP_Y1-0.4, LEVEL, overhang=2.0, oh_n=False, pitch=0.25, slope_style='shed', shed_low_edge=0)

# Attach walls to roofs
attach_walls_to_roof([w for w in [ids['lw_north'], ids['lw_west'], ids['lw_e_top'], ids['lw_e_bot']] if w], ids['lw_roof'])
attach_walls_to_roof([w for w in [ids['cb_south'], ids['cb_north'], ids['cb_cl_w'], ids['cb_cl_e']] if w], ids['cb_roof'])
attach_walls_to_roof([w for w in [ids['rw_south'], ids['rw_north'], ids['rw_east'], ids['rw_w_top'], ids['rw_w_bot']] if w], ids['rw_roof'])
attach_walls_to_roof([w for w in [ids['gar_south'], ids['gar_west'], ids['gar_east'], ids['gar_n_sep'], ids['gar_n_ext']] if w], ids['gar_roof'])

# Porch posts
POST_FAM = 'HSS-Hollow Structural Section-Column'; POST_TYPE = 'HSS6X6X3/16'
for px in [BP_X0+0.5, BP_X0+10.0, BP_X0+19.0, BP_X1-0.5]:
    r = call('revit.place_family_instance', {'family_name': POST_FAM, 'type_name': POST_TYPE, 'location': {'x': px, 'y': BP_Y1, 'z': 0}, 'level': LEVEL})
    print(f"  BP post x={px:.1f}: {r.get('Status')}")
for px in [FP_X0+0.5, FP_X0+10.0, FP_X0+19.0, FP_X1-0.5]:
    r = call('revit.place_family_instance', {'family_name': POST_FAM, 'type_name': POST_TYPE, 'location': {'x': px, 'y': FP_Y0, 'z': 0}, 'level': LEVEL})
    print(f"  FP post x={px:.1f}: {r.get('Status')}")

save()
print("✅ S1 DONE\n")

# ══════════════════════════════════════════════════════
# S2: INTERIOR WALLS
# ══════════════════════════════════════════════════════
print("="*60); print("S2: Interior Walls"); print("="*60)

ids['lw_mb_s']    = iwall(LW_X0, 38, 16, 38, 'MasterBed-South')
ids['lw_mba_s']   = iwall(LW_X0, 26, 16, 26, 'MasterBath-South')
ids['lw_m_e']     = iwall(16, 26, 16, LW_Y1, 'Master-East')
ids['lw_wic_s']   = iwall(LW_X0, 18, 12, 18, 'WIC-South')
ids['lw_wic_e']   = iwall(12, 18, 12, 26, 'WIC-East')
ids['lw_kitch_s'] = iwall(14, 36, LW_X1, 36, 'Kitchen-South')
ids['lw_kitch_w'] = iwall(14, 36, 14, LW_Y1, 'Kitchen-West')
ids['lw_din_s']   = iwall(14, 22, LW_X1, 22, 'Dining-South')
ids['lw_din_w']   = iwall(14, 22, 14, 36, 'Dining-West')
ids['lw_pan_w']   = iwall(14, LW_Y0, 14, 22, 'Pantry-West')
ids['lw_pan_s']   = iwall(14, 14, LW_X1, 14, 'Pantry-South')
ids['lw_lndry_e'] = iwall(10, 10, 10, 18, 'Laundry-East')
ids['lw_lndry_s'] = iwall(LW_X0, 10, 10, 10, 'Laundry-South')
ids['lw_mud_n']   = iwall(10, 16, 22, 16, 'Mudroom-North')
ids['lw_mud_e']   = iwall(22, LW_Y0, 22, 16, 'Mudroom-East')

ids['rw_hall_n']  = iwall(RW_X0, 16, RW_X1, 16, 'RW-Hall-North')
ids['rw_bed2_s']  = iwall(RW_X0, 34, 80, 34, 'Bed2-South')
ids['rw_bed2_e']  = iwall(80, 36, 80, RW_Y1, 'Bed2-East-Bath2-W')
ids['rw_bath2_s'] = iwall(80, 36, RW_X1, 36, 'Bath2-South')
ids['rw_bed3_e']  = iwall(80, 16, 80, 36, 'Bed3-East-Bath3-W')
ids['rw_wic2_s']  = iwall(RW_X0, 46, 72, 46, 'Bed2-WIC-South')
ids['rw_wic2_e']  = iwall(72, 46, 72, RW_Y1, 'Bed2-WIC-East')
ids['rw_wic3_n']  = iwall(RW_X0, 24, 72, 24, 'Bed3-WIC-North')
ids['rw_wic3_e']  = iwall(72, 16, 72, 24, 'Bed3-WIC-East')

# *** SAVE after interior walls ***
save()
print("✅ S2 DONE\n")

# ══════════════════════════════════════════════════════
# S3: DOORS + WINDOWS (using saved IDs)
# ══════════════════════════════════════════════════════
print("="*60); print("S3: Doors + Windows"); print("="*60)

WIN_F = 'Instance-Window-Fixed'; WIN_A = 'Window-Awning-Single'
D_EXT = 'Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad'
D_SL6 = 'Exterior_Sliding_Door_3843'
D_MUL = 'Three_Panel_Sliding_Door_17534'
D_INT = 'Door-Interior-Single-1_Panel-Wood'
D_OPEN = 'Int-Opening-Craftsman_Casing_1726'
D_OH  = 'Door-Garage-Flush_Panel'
SILL = 2.5; SILL_CL = 9.5

# Exterior doors
ids['front_door']    = pdoor(ids['cb_south'], 46, CB_Y0, D_EXT, '36" x 96"', 'Front-Entry')
ids['gr_slider']     = pdoor(ids['cb_north'], 46, CB_Y1, D_MUL, '144" x 96"', 'GreatRm-Rear')
ids['master_slider'] = pdoor(ids['lw_north'], 8, LW_Y1, D_SL6, "6'-0\"W. x 8'-0\"H.", 'Master-Patio')
ids['kitch_slider']  = pdoor(ids['lw_north'], 21, LW_Y1, D_SL6, "6'-0\"W. x 8'-0\"H.", 'Kitchen-Back')

# Garage OH doors + flip
ids['ohd1'] = pdoor(ids['gar_south'], 5, GAR_Y0, D_OH, '10x10', 'OHD-1')
ids['ohd2'] = pdoor(ids['gar_south'], 16, GAR_Y0, D_OH, '10x10', 'OHD-2')
ids['ohd3'] = pdoor(ids['gar_south'], 27, GAR_Y0, D_OH, '10x10', 'OHD-3')
for k in ['ohd1','ohd2','ohd3']:
    if ids[k]:
        r = call('revit.flip_door', {'element_id': ids[k]})
        print(f"  flip OHD {ids[k]}: {r.get('Status')}")

# Interior doors
pdoor(ids['lw_m_e'],     16, 42, D_INT, '36" x 96"', 'MasterBed')
pdoor(ids['lw_mb_s'],     8, 38, D_INT, '36" x 96"', 'MasterBath')
pdoor(ids['lw_mba_s'],    6, 26, D_INT, '30" x 96"', 'WIC')
pdoor(ids['lw_kitch_s'], 21, 36, D_OPEN, '72"', 'Kitch-Dining-Open')
pdoor(ids['lw_din_s'],   20, 22, D_INT, '30" x 96"', 'Pantry')
pdoor(ids['lw_lndry_e'], 10, 14, D_INT, '32" x 96"', 'Laundry')
pdoor(ids['gar_n_sep'],  16, GAR_Y1, D_INT, '36" x 96"', 'Mudroom-Garage')
pdoor(ids['lw_mud_n'],   16, 16, D_INT, '36" x 96"', 'Mudroom-House')
pdoor(ids['rw_hall_n'],  72, 16, D_INT, '36" x 96"', 'Bed2')
pdoor(ids['rw_hall_n'],  70, 16, D_INT, '36" x 96"', 'Bed3')
pdoor(ids['rw_bed2_e'],  80, 42, D_INT, '36" x 96"', 'Bath2')
pdoor(ids['rw_bed3_e'],  80, 24, D_INT, '36" x 96"', 'Bath3')
pdoor(ids['rw_wic2_e'],  72, 48, D_INT, '30" x 96"', 'WIC2')
pdoor(ids['rw_wic3_e'],  72, 20, D_INT, '30" x 96"', 'WIC3')

# Windows (after save, wall IDs are stable)
# LW north
pwin(ids['lw_north'], 14, LW_Y1, SILL, WIN_F, '72" x 36"', 'MasterBed-N')
pwin(ids['lw_north'], 27, LW_Y1, SILL, WIN_F, '48" x 48"', 'Kitchen-N')
# LW west
pwin(ids['lw_west'], 0, 46, SILL, WIN_F, '72" x 36"', 'MasterBed-W')
pwin(ids['lw_west'], 0, 32, SILL, WIN_A, '24" x 72"', 'MasterBath-W')
# CB south (flanking front door at x=46)
pwin(ids['cb_south'], 38, CB_Y0, SILL, WIN_F, '48" x 48"', 'CB-S-L')
pwin(ids['cb_south'], 54, CB_Y0, SILL, WIN_F, '48" x 48"', 'CB-S-R')
# CB north (hero rear, flanking 12ft slider at x=46)
pwin(ids['cb_north'], 35, CB_Y1, SILL, WIN_F, '72" x 36"', 'CB-N-L')
pwin(ids['cb_north'], 57, CB_Y1, SILL, WIN_F, '72" x 36"', 'CB-N-R')
# Clerestory
pwin(ids['cb_cl_w'], CB_X0, 24, SILL_CL, WIN_F, '72" x 24"', 'Clerest-W1')
pwin(ids['cb_cl_w'], CB_X0, 38, SILL_CL, WIN_F, '72" x 24"', 'Clerest-W2')
pwin(ids['cb_cl_e'], CB_X1, 24, SILL_CL, WIN_F, '72" x 24"', 'Clerest-E1')
pwin(ids['cb_cl_e'], CB_X1, 38, SILL_CL, WIN_F, '72" x 24"', 'Clerest-E2')
# RW
pwin(ids['rw_north'], 72, RW_Y1, SILL, WIN_F, '48" x 48"', 'Bed2-N')
pwin(ids['rw_east'], RW_X1, 42, SILL, WIN_F, '72" x 36"', 'Bed2-E')
pwin(ids['rw_east'], RW_X1, 48, SILL, WIN_A, '24" x 72"', 'Bath2-E')
pwin(ids['rw_east'], RW_X1, 25, SILL, WIN_F, '72" x 36"', 'Bed3-E')
pwin(ids['rw_east'], RW_X1, 19, SILL, WIN_A, '24" x 72"', 'Bath3-E')
pwin(ids['rw_south'], 78, RW_Y0, SILL, WIN_F, '48" x 48"', 'RW-S-Hall')

save()
print("✅ S3 DONE\n")

# ══════════════════════════════════════════════════════
# S4: ROOM LABELS
# ══════════════════════════════════════════════════════
print("="*60); print("S4: Room Labels"); print("="*60)

rooms = [
    {"name": "Master Bedroom", "x": 8.0,  "y": 46.0},
    {"name": "Master Bath",    "x": 8.0,  "y": 32.0},
    {"name": "Walk-in Closet", "x": 6.0,  "y": 22.0},
    {"name": "Kitchen",        "x": 21.0, "y": 46.0},
    {"name": "Dining",         "x": 21.0, "y": 29.0},
    {"name": "Pantry",         "x": 21.0, "y": 18.0},
    {"name": "Laundry",        "x": 5.0,  "y": 14.0},
    {"name": "Mudroom",        "x": 16.0, "y": 12.0},
    {"name": "Hall",           "x": 20.0, "y": 30.0},
    {"name": "Great Room",     "x": 46.0, "y": 31.0},
    {"name": "Bedroom 2",      "x": 72.0, "y": 42.0},
    {"name": "Bath 2",         "x": 86.0, "y": 43.0},
    {"name": "WIC 2",          "x": 68.0, "y": 48.0},
    {"name": "Bedroom 3",      "x": 72.0, "y": 25.0},
    {"name": "Bath 3",         "x": 86.0, "y": 25.0},
    {"name": "WIC 3",          "x": 68.0, "y": 20.0},
    {"name": "Hall",           "x": 78.0, "y": 12.0},
    {"name": "Garage",         "x": 17.0, "y": -9.0},
    {"name": "Covered Porch",  "x": 46.0, "y": 54.0},
    {"name": "Covered Entry",  "x": 46.0, "y": 7.0},
]
label_rooms(rooms, LEVEL, upper_limit_level="Level 2.0")

save()
print("✅ S4 DONE\n")

# Save IDs for fixtures
with open('/tmp/c1e4332c_ids.json', 'w') as f:
    # Convert None values to 0 for JSON
    clean = {k: (v if v is not None else 0) for k, v in ids.items()}
    json.dump(clean, f, indent=2)
print("✅ IDs saved to /tmp/c1e4332c_ids.json")
print("\n🏁 FULL BUILD COMPLETE")
print("Next: run fixtures_c1e4332c.py after visual confirmation in Revit")
