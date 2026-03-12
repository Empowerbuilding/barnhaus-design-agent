"""
build_e670353b_s2.py — STAGE 2: Interior Walls
Submission: e670353b | Mitchell Madison | H-shape | Hill Country

LEFT WING interior layout (x=0→24, y=8→50):
  Master bed:      x=0→24,  y=30→50  (rear/north, far left ✓)
  Master bath:     x=0→14,  y=18→30
  WIC:             x=14→24, y=18→30
  Laundry:         x=0→12,  y=8→18
  Utility/pet:     x=12→18, y=8→18
  Butler pantry:   x=18→24, y=8→18  (near bridge connection)

CENTER BRIDGE interior (x=32→60, y=14→38):
  Open plan — kitchen partition only
  Kitchen zone:    x=32→54, y=14→28
  Dining:          x=54→60, y=14→38
  Great room:      x=32→54, y=28→38

RIGHT WING interior layout (x=68→90, y=8→50):
  Hallway:         x=68→76, y=20→42
  Bed 2:           x=76→90, y=28→50  (ensuite)
  Bath 2:          x=80→90, y=18→28  (ensuite to Bed 2)
  Bed 3:           x=76→90, y=8→18
  Bath 3:          x=68→76, y=8→20   (ensuite to Bed 3)
  Bed 4:           x=68→76, y=42→50  (north end of hallway)
"""

import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils_v2 import *

SUB_ID = "e670353b"

if not health_check():
    print("❌ Bridge not healthy")
    sys.exit(1)

LEVEL  = "Level 1.0"
INT    = WALL["INT"]   # Wall 4.5 Interior"
WING_H  = 9.0
BRIDGE_H = 16.0
UPPER = "Level 2.0"

wall_ids = []

def w(x0, y0, x1, y1, h, label):
    r = create_wall(x0, y0, x1, y1, INT, LEVEL, h, UPPER, label)
    wid = (r.get("result") or {}).get("wall_id")
    status = "✅" if wid else "❌"
    print(f"  {status} {label}: {wid or r.get('error')}")
    if wid: wall_ids.append(wid)
    return wid

print("\n=== STAGE 2: LEFT WING INTERIOR ===")
w(0,  30, 24, 30, WING_H, "LW-master-south")        # master bed south wall
w(0,  18, 24, 18, WING_H, "LW-bath-south")           # bath/WIC south wall
w(14, 18, 14, 30, WING_H, "LW-bath-wic-divider")     # bath vs WIC split
w(12, 8,  12, 18, WING_H, "LW-laundry-util-div")     # laundry vs utility split
w(18, 8,  18, 18, WING_H, "LW-util-butler-div")      # utility vs butler pantry

print("\n=== STAGE 2: CENTER BRIDGE INTERIOR ===")
w(32, 28, 54, 28, BRIDGE_H, "CB-kitchen-living-div") # kitchen/great room split
w(54, 14, 54, 38, BRIDGE_H, "CB-dining-divider")     # dining pocket wall

print("\n=== STAGE 2: RIGHT WING INTERIOR ===")
w(76, 14, 76, 42, WING_H, "RW-hallway-east")         # hallway spine
w(68, 42, 76, 42, WING_H, "RW-bed4-south")           # bed 4 south wall
w(76, 28, 90, 28, WING_H, "RW-bed2-south")           # bed 2 south wall
w(80, 18, 80, 28, WING_H, "RW-bath2-west")           # bath 2 west wall
w(76, 18, 90, 18, WING_H, "RW-bath2-south")          # bath 2 south wall
w(68, 20, 76, 20, WING_H, "RW-bath3-north")          # bath 3 north wall (ensuite bed 3)

print(f"\n✅ STAGE 2 COMPLETE — {len(wall_ids)} interior walls placed")
print("→ Check Revit — room partitions should be visible inside each wing")
print("→ Reply 'stage 3' when ready for doors + windows")
checkpoint_save(SUB_ID, 2, wall_ids)
