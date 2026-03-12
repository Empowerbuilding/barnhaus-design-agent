"""fix_eda_windows2.py — Add windows matching AI-enhanced design
AI analysis of enhanced images shows:
- LW south: 2 large windows (master bed faces south)
- LW west end wall: 1 window centered
- LW north: 2 windows (mudroom/pantry side)
- RW north: 3 windows (bed wing, currently only 1)
- RW east end wall: 1 window centered
- RW west (inner): 2 windows on hallway side
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_window

LEVEL = "Level 1.0"
WIN = "Instance-Window-Fixed"

# Wall IDs from S1
lw_s  = 5953192   # LW south wall (y=8),  x: 0→22
lw_n  = 5953193   # LW north wall (y=54), x: 0→22
lw_w  = 5953194   # LW west end wall (x=0), y: 8→54
rw_n  = 5953215   # RW north wall (y=54), x: 84→106
rw_e  = 5953216   # RW east end wall (x=106), y: 8→54
rw_w1 = 5953217   # RW west inner wall (x=84), y: 8→54

print("=== Adding windows to match AI design ===")

# LW south wall — master bedroom, 2 large windows evenly spaced
place_window(lw_s,  7, 8,  2.5, WIN, '48" x 48"', label="LW-S-Win1")
place_window(lw_s, 15, 8,  2.5, WIN, '48" x 48"', label="LW-S-Win2")
print("✅ LW south: 2 windows")

# LW west end wall — 1 centered window (end of master wing)
place_window(lw_w,  0, 31, 2.5, WIN, '48" x 48"', label="LW-W-End-Win")
print("✅ LW west end: 1 window")

# LW north wall — 2 windows (mudroom / pantry side)
place_window(lw_n,  7, 54, 2.5, WIN, '48" x 48"', label="LW-N-Win1")
place_window(lw_n, 15, 54, 2.5, WIN, '48" x 48"', label="LW-N-Win2")
print("✅ LW north: 2 windows")

# RW north wall — AI showed 3 windows (bed wing facing driveway/front)
# Already have 1 at x=95; add 2 more
place_window(rw_n,  88, 54, 2.5, WIN, '48" x 48"', label="RW-N-Win2")
place_window(rw_n, 101, 54, 2.5, WIN, '48" x 48"', label="RW-N-Win3")
print("✅ RW north: +2 windows (3 total)")

# RW east end wall — 1 centered window
place_window(rw_e, 106, 31, 2.5, WIN, '48" x 48"', label="RW-E-End-Win")
print("✅ RW east end: 1 window")

# RW west inner wall (hallway side) — 2 windows
place_window(rw_w1, 84, 20, 2.5, WIN, '48" x 48"', label="RW-W-Win1")
place_window(rw_w1, 84, 38, 2.5, WIN, '48" x 48"', label="RW-W-Win2")
print("✅ RW west inner: 2 windows")

print("\n=== Window additions complete ===")
print("Added: 2 (LW-S) + 1 (LW-W-end) + 2 (LW-N) + 2 (RW-N) + 1 (RW-E-end) + 2 (RW-W) = 10 new windows")
