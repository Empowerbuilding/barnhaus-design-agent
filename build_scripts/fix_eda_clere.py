"""fix_eda_clere.py — Clerestory windows with correct type"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_window

WIN   = "Instance-Window-Fixed"
cb_cw = 5953041
cb_ce = 5953043

place_window(cb_cw, 38, 33, 11.5, WIN, '60" x 24"', label="Clere-W-Win1")
place_window(cb_cw, 38, 46, 11.5, WIN, '60" x 24"', label="Clere-W-Win2")
place_window(cb_ce, 68, 33, 11.5, WIN, '60" x 24"', label="Clere-E-Win1")
place_window(cb_ce, 68, 46, 11.5, WIN, '60" x 24"', label="Clere-E-Win2")
print("✅ Clerestory windows placed (60x24, 2 per side)")
