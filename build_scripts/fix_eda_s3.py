"""
fix_eda_s3.py — Add missing front entry door + all windows with correct family names
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_door, place_window

LEVEL = "Level 1.0"
cb_s  = 5953039
lw_w  = 5953030
rw_e  = 5953052
rw_s  = 5953050
rw_n  = 5953051
cb_cw = 5953041
cb_ce = 5953043

print("=== Fix S3: Front entry door + windows ===")

# Front entry door
place_door(cb_s, 53, 26, 0,
    "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"',
    label="FrontEntry", level=LEVEL)
print("✅ Front entry door placed")

# Windows — family: Instance-Window-Fixed
WIN = "Instance-Window-Fixed"
place_window(lw_w, 0, 15, 2.5, WIN, '48" x 48"', label="LW-W-Win1")
place_window(lw_w, 0, 38, 2.5, WIN, '48" x 48"', label="LW-W-Win2")
place_window(rw_e, 106, 15, 2.5, WIN, '48" x 48"', label="RW-E-Win1")
place_window(rw_e, 106, 40, 2.5, WIN, '48" x 48"', label="RW-E-Win2")
place_window(rw_s,  95,  8, 2.5, WIN, '48" x 48"', label="RW-S-Win1")
place_window(rw_n,  95, 54, 2.5, WIN, '48" x 48"', label="RW-N-Win1")

# Clerestory — high strip windows
place_window(cb_cw, 38, 35, 11, WIN, '72" x 24"', label="Clere-W-Win")
place_window(cb_ce, 68, 35, 11, WIN, '72" x 24"', label="Clere-E-Win")

print("✅ All windows placed")
print("=== Done ===")
