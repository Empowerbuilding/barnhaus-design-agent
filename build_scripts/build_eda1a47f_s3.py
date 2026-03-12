"""build_eda1a47f_s3.py — Doors + Windows (fresh IDs from this run)"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_door, place_window, flip_door, _call

LEVEL = "Level 1.0"
# S1 wall IDs
lw_s=5953192; lw_w=5953194; lw_e1=5953195
lbz_e=5953198; lbz_w=5953200
cb_s=5953203; cb_n=5953204; cb_cw=5953205; cb_ce=5953207
rbz_w=5953210
rw_s=5953214; rw_n=5953215; rw_e=5953216
gar_s=5953219
# S2 wall IDs
mbed_s=5953453; mbath_e=5953456; wic_e=5953459
kit_div=5953463; mud_div=5953468; bath2_w=5953476; bath3_n=5953480; bath3_w=5953479
bhall_s=5953470

print("=== S3: Doors + Windows ===")

# Exterior doors
place_door(cb_s, 53, 26, 0, "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"', label="FrontEntry", level=LEVEL)
ms = place_door(lw_s, 11, 8, 0, "Exterior_Sliding_Door_3843", '6\'-0"W. x 8\'-0"H.', label="MasterSlider", level=LEVEL)
flip_door(ms)
place_door(cb_n, 53, 54, 0, "Exterior_Sliding_Door_3843", '8\'-0"W. x 8\'-0"H. 2', label="GRSlider", level=LEVEL)
print("✅ Exterior doors")

# Interior doors
place_door(mbed_s,  19, 22, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="MBed-Door",  level=LEVEL)
place_door(mbath_e, 14, 27, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="MBath-Door", level=LEVEL)
place_door(wic_e,   10, 36, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="WIC-Door",   level=LEVEL)
place_door(kit_div,  8, 38, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="Pan-Door",   level=LEVEL)
place_door(mud_div, 11, 49, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="Mud-Door",   level=LEVEL)
place_door(lbz_e,   38, 40, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="LBZ-Door",   level=LEVEL)
place_door(rbz_w,   68, 40, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="RBZ-Door",   level=LEVEL)
place_door(bhall_s, 95, 22, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="Bed2-Door",  level=LEVEL)
place_door(bath2_w, 98, 27, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="Bath2-Door", level=LEVEL)
place_door(bath3_n, 95, 44, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="Bed3-Door",  level=LEVEL)
place_door(bath3_w, 98, 49, 0, "Door-Interior-Single-1_Panel-Wood", '36" x 96"', label="Bath3-Door", level=LEVEL)
print("✅ Interior doors")

# Windows
WIN = "Instance-Window-Fixed"
place_window(lw_w,  0,   15, 2.5, WIN, '48" x 48"', label="LW-W-Win1")
place_window(lw_w,  0,   38, 2.5, WIN, '48" x 48"', label="LW-W-Win2")
place_window(rw_e,  106, 15, 2.5, WIN, '48" x 48"', label="RW-E-Win1")
place_window(rw_e,  106, 40, 2.5, WIN, '48" x 48"', label="RW-E-Win2")
place_window(rw_s,  95,  8,  2.5, WIN, '48" x 48"', label="RW-S-Win1")
place_window(rw_n,  95,  54, 2.5, WIN, '48" x 48"', label="RW-N-Win1")
place_window(cb_s,  44,  26, 2.5, WIN, '48" x 48"', label="CB-S-Win1")
place_window(cb_s,  62,  26, 2.5, WIN, '48" x 48"', label="CB-S-Win2")
place_window(cb_n,  44,  54, 2.5, WIN, '48" x 48"', label="CB-N-Win1")
place_window(cb_n,  62,  54, 2.5, WIN, '48" x 48"', label="CB-N-Win2")
place_window(cb_cw, 38,  33, 11.5, WIN, '60" x 24"', label="Clere-W-Win1")
place_window(cb_cw, 38,  46, 11.5, WIN, '60" x 24"', label="Clere-W-Win2")
place_window(cb_ce, 68,  33, 11.5, WIN, '60" x 24"', label="Clere-E-Win1")
place_window(cb_ce, 68,  46, 11.5, WIN, '60" x 24"', label="Clere-E-Win2")
print("✅ Windows")

# Porch fix — centered on door, back porch in H notch
from barnhaus_revit_utils import make_roof, create_floor, place_porch_posts
WING_R = "Wing Roof"
# Front porch centered on x=53
fp_roof = make_roof("FP-Roof", x0=47, y0=54, x1=59, y1=66, level_name=WING_R, pitch=0.083, shed_low_edge=2, oh_s=True, oh_n=False, oh_w=False, oh_e=False)
create_floor(LEVEL, 0, [(47,54),(59,54),(59,66),(47,66)])
place_porch_posts(post_xs=[48.5, 57.5], post_y=66, level=LEVEL, porch_depth=12, wall_height=10, shed_slopes_toward_larger_y=True)
# Back porch in H notch
bp_roof = make_roof("BP-Roof", x0=38, y0=14, x1=68, y1=26, level_name=WING_R, pitch=0.083, shed_low_edge=0, oh_s=False, oh_n=True, oh_w=False, oh_e=False)
create_floor(LEVEL, 0, [(38,14),(68,14),(68,26),(38,26)])
place_porch_posts(post_xs=[40, 53, 66], post_y=14, level=LEVEL, porch_depth=12, wall_height=10, shed_slopes_toward_larger_y=False)
# Garage doors
gd1 = place_door(gar_s, 6,  78, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D1", level=LEVEL)
gd2 = place_door(gar_s, 18, 78, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D2", level=LEVEL)
gd3 = place_door(gar_s, 30, 78, 0, "Door-Garage-Flush_Panel", "10x10", label="GAR-D3", level=LEVEL)
flip_door(gd1); flip_door(gd2); flip_door(gd3)
print("✅ Porches + garage doors")

print("\n=== S3 COMPLETE — say 'run fixtures' ===")
