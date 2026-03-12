"""
fix_eda_windows.py — Fix clerestory windows + add CB front/back windows
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import _call, place_window

LEVEL = "Level 1.0"
WIN   = "Instance-Window-Fixed"
cb_cw = 5953041
cb_ce = 5953043
cb_s  = 5953039  # CB south / street face (y=26)
cb_n  = 5953040  # CB north / back porch face (y=54)

print("=== Fix: Clerestory windows + CB front/back windows ===")

# Delete old oversized clerestory windows
for wid in [5953315, 5953317]:
    r = _call("revit.delete_element", {"element_id": wid})
    print(f"Deleted window {wid}: {r.get('Status')}")

# Smaller clerestory strip windows — 36"w x 18"h, sill at z=11.5 (centered in 6ft band)
place_window(cb_cw, 38, 32, 11.5, WIN, '36" x 24"', label="Clere-W-Win1")
place_window(cb_cw, 38, 40, 11.5, WIN, '36" x 24"', label="Clere-W-Win2")
place_window(cb_cw, 38, 48, 11.5, WIN, '36" x 24"', label="Clere-W-Win3")
place_window(cb_ce, 68, 32, 11.5, WIN, '36" x 24"', label="Clere-E-Win1")
place_window(cb_ce, 68, 40, 11.5, WIN, '36" x 24"', label="Clere-E-Win2")
place_window(cb_ce, 68, 48, 11.5, WIN, '36" x 24"', label="Clere-E-Win3")
print("✅ Clerestory windows replaced (smaller, 3 per side)")

# CB south wall (street/front) — flanking the front entry door at x=53
place_window(cb_s, 44, 26, 2.5, WIN, '48" x 48"', label="CB-S-Win1")
place_window(cb_s, 62, 26, 2.5, WIN, '48" x 48"', label="CB-S-Win2")
print("✅ CB front windows added (flanking entry)")

# CB north wall (back porch side)
place_window(cb_n, 44, 54, 2.5, WIN, '48" x 48"', label="CB-N-Win1")
place_window(cb_n, 62, 54, 2.5, WIN, '48" x 48"', label="CB-N-Win2")
print("✅ CB back windows added")

print("=== Done ===")
