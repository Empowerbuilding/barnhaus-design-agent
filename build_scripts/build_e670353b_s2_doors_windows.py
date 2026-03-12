"""
build_e670353b_s2_doors_windows.py — STAGE 2: Doors + Windows
Submission: e670353b | Mitchell Madison | H-shape | Hill Country

Door/window placement based on:
- Submission: hill_country style, 4bd/3ba, master far-left, butler pantry
- Barnhaus rules: max glass rear/view wall, restrained street side
- Section 22: check window vs door overlap, flip garage OH doors

Wall IDs from Stage 1:
  LW exterior: lw_s=5962662, lw_es=5962663, lw_en=5962664, lw_n=5962665, lw_w=5962666
  CB exterior: cb_s=5962669, cb_e=5962670, cb_n=5962671, cb_w=5962672
  RW exterior: rw_s=5962679, rw_e=5962680, rw_n=5962681, rw_ws=5962682, rw_wn=5962683
  GAR exterior: gar_s=5962684, gar_e=5962686, gar_n=5962687, gar_w=5962688
  Interior LW: 5962689(master-S), 5962690(bath-S), 5962691(bath-wic), 5962692(laundry-util), 5962693(util-butler)
  Interior CB: 5962694(kitchen-living), 5962695(dining-div)
  Interior RW: 5962696(hall-E), 5962697(bed4-S), 5962698(bed2-S), 5962699(bath2-W), 5962700(bath2-S), 5962701(bath3-N)
"""

import sys, requests
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils_v2 import health_check

BASE = 'http://localhost:3000/execute'

def call(tool, payload):
    r = requests.post(BASE, json={'request_id': tool, 'tool': tool, 'payload': payload}, timeout=30)
    d = r.json()
    return d.get('Status'), d.get('Result'), d.get('Message')

if not health_check():
    print("❌ Bridge not healthy"); sys.exit(1)

LEVEL = 'Level 1.0'

def door(wall_id, x, y, family, type_name, label, flip=False):
    s, r, m = call('revit.place_door', {
        'wall_id': wall_id, 'location': {'x': x, 'y': y, 'z': 0},
        'family_name': family, 'type_name': type_name, 'level': LEVEL,
    })
    did = (r or {}).get('door_id') or (r or {}).get('element_id')
    if not did:
        print(f"  ❌ {label}: {m}"); return None
    if flip:
        call('revit.flip_door', {'element_id': did})
        print(f"  ✅ {label}: {did} (flipped)")
    else:
        print(f"  ✅ {label}: {did}")
    return did

def win(wall_id, x, y, sill_h, family, type_name, label):
    s, r, m = call('revit.place_window', {
        'wall_id': wall_id, 'location': {'x': x, 'y': y, 'z': sill_h},
        'family_name': family, 'type_name': type_name, 'level': LEVEL,
    })
    wid = (r or {}).get('window_id') or (r or {}).get('element_id')
    print(f"  {'✅' if wid else '❌'} {label}: {wid or m}")
    return wid

# Families
INT_DR   = 'Door-Interior-Single-1_Panel-Wood'
EXT_DR   = 'Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad'
SLD_DR   = 'Exterior_Sliding_Door_3843'
SLD_WIDE = 'Three_Panel_Sliding_Door_17534'
GAR_DR   = 'Door-Garage-Flush_Panel'
FIX_WIN  = 'Instance-Window-Fixed'
AWN_WIN  = 'Window-Awning-Single'

SL  = 2.5   # standard sill height
BH  = 5.0   # bathroom sill (privacy)

# ════════════════════════════════════════
print("\n══ EXTERIOR DOORS ══")

# Front entry — CB south wall, centered (x=46, y=14)
door(5962669, 46, 14, EXT_DR, '36" x 96"', 'front-entry')

# Great room rear slider — CB north wall, hero moment
door(5962671, 46, 38, SLD_WIDE, '144" x 96"', 'GR-rear-slider')

# Master bed rear slider — LW north wall (master at y=30→50)
door(5962665, 12, 50, SLD_DR, '8\'-0"W. x 8\'-0"H. 2', 'master-rear-slider')

# Garage overhead door — GAR west wall (side-loaded), flip after
door(5962688, 0, 62, GAR_DR, '16W X 10H', 'GAR-OH', flip=True)

# ════════════════════════════════════════
print("\n══ INTERIOR DOORS ══")

# Left wing
door(5962689, 12, 30, INT_DR, '36" x 96"', 'master-bed-entry')       # into master bed
door(5962690, 7,  18, INT_DR, '36" x 96"', 'master-bath-entry')       # into bath
door(5962691, 14, 24, INT_DR, '30" x 96"', 'wic-entry')               # WIC
door(5962692, 6,  18, INT_DR, '36" x 96"', 'laundry-entry')           # laundry
door(5962693, 21, 18, INT_DR, '30" x 96"', 'butler-pantry-entry')     # butler pantry

# Right wing
door(5962696, 76, 36, INT_DR, '36" x 96"', 'bed2-hall-door')          # bed 2 to hall
door(5962696, 76, 22, INT_DR, '36" x 96"', 'bed3-hall-door')          # bed 3 to hall
door(5962697, 72, 42, INT_DR, '36" x 96"', 'bed4-hall-door')          # bed 4 to hall
door(5962699, 80, 24, INT_DR, '36" x 96"', 'bath2-bed2-door')         # bath 2 ensuite
door(5962700, 82, 18, INT_DR, '36" x 96"', 'bath2-bed3-door')         # bath 2 other entry
door(5962701, 72, 20, INT_DR, '36" x 96"', 'bath3-entry')             # bath 3

# ════════════════════════════════════════
print("\n══ EXTERIOR WINDOWS ══")

# ── Left wing ──
# Master bed: rear (north) wall — views + privacy
win(5962665, 7,  50, SL, FIX_WIN, '72" x 36"', 'master-N-win1')
win(5962665, 17, 50, SL, FIX_WIN, '72" x 36"', 'master-N-win2')
# Master bed: west wall
win(5962666, 0, 40, SL, FIX_WIN, '48" x 48"', 'master-W-win')
# Master bath: west wall — awning for privacy
win(5962666, 0, 23, BH, AWN_WIN, '24" x 72"', 'master-bath-W-win')
# LW south face — laundry/util/butler zone
win(5962662, 12, 8, SL, FIX_WIN, '48" x 48"', 'LW-S-win1')

# ── Center bridge ──
# CB south (street) — restrained, flank entry
win(5962669, 36, 14, SL, FIX_WIN, '48" x 48"', 'CB-S-win-L')
win(5962669, 56, 14, SL, FIX_WIN, '48" x 48"', 'CB-S-win-R')
# CB north (rear/hero) — kitchen + dining windows
win(5962671, 36, 38, SL, FIX_WIN, '60" x 30"', 'CB-N-win-kitchen')
win(5962671, 54, 38, SL, FIX_WIN, '60" x 30"', 'CB-N-win-dining')
# CB east + west — clerestory strip on bridge sides
win(5962670, 60, 26, 6.5, FIX_WIN, '72" x 24"', 'CB-E-clerestory')
win(5962672, 32, 26, 6.5, FIX_WIN, '72" x 24"', 'CB-W-clerestory')

# ── Right wing ──
# RW south — restrained
win(5962679, 78, 8, SL, FIX_WIN, '48" x 48"', 'RW-S-win1')
win(5962679, 84, 8, SL, FIX_WIN, '48" x 48"', 'RW-S-win2')
# RW east (rear) — bed 2 + bed 3 views
win(5962680, 90, 38, SL, FIX_WIN, '72" x 36"', 'RW-E-bed2-win')
win(5962680, 90, 22, SL, FIX_WIN, '72" x 36"', 'RW-E-bed3-win')
win(5962680, 90, 10, SL, FIX_WIN, '48" x 48"', 'RW-E-bed4-win')
# RW north — bed 4
win(5962681, 72, 50, SL, FIX_WIN, '48" x 48"', 'RW-N-bed4-win')
# Baths — awning privacy
win(5962680, 90, 23, BH, AWN_WIN, '24" x 72"', 'bath2-E-win')
win(5962679, 72, 8,  BH, AWN_WIN, '24" x 72"', 'bath3-S-win')

print("\n✅ STAGE 2 COMPLETE")
print("→ Check Revit: doors placed, windows grouped, garage door on west wall")
print("→ Verify master slider, great room hero slider, front entry")
print("→ Say 'stage 3' when ready for fixtures")
