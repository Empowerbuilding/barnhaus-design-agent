"""
build_c1e4332c_s2b.py — Stage 2 retry: missing left wing interior walls
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_wall

LEVEL = "Level 1.0"
INT   = 'Wall 4.5 Interior"'

print("=== Stage 2b: Left wing interior walls (retry) ===")

create_wall(0,  38, 0, 16, 38, 0, LEVEL, INT, height=9, label="MBed-S")
create_wall(16, 38, 0, 16, 54, 0, LEVEL, INT, height=9, label="MBed-E")
create_wall(0,  26, 0, 12, 26, 0, LEVEL, INT, height=9, label="MBath-S")
create_wall(12, 26, 0, 12, 38, 0, LEVEL, INT, height=9, label="MBath-E")
create_wall(0,  18, 0,  8, 18, 0, LEVEL, INT, height=9, label="WIC-S")
create_wall(8,  18, 0,  8, 26, 0, LEVEL, INT, height=9, label="WIC-E")
create_wall(24, 14, 0, 24, 48, 0, LEVEL, INT, height=9, label="MHall-W")
create_wall(12, 26, 0, 24, 26, 0, LEVEL, INT, height=9, label="Kit-S")
create_wall(0,  18, 0, 12, 18, 0, LEVEL, INT, height=9, label="Pan-N")
create_wall(12, 14, 0, 12, 18, 0, LEVEL, INT, height=9, label="Pan-E")
create_wall(0,  14, 0,  8, 14, 0, LEVEL, INT, height=9, label="Mud-N")
create_wall(8,   8, 0,  8, 14, 0, LEVEL, INT, height=9, label="Mud-E")

print("=== Done ===")
