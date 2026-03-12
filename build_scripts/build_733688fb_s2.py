"""
build_733688fb_s2.py — Stage 2: Interior Walls
Submission: 733688fb | Mitchell Madison | 2,750 SF | T-Shape

ROOM LAYOUT REFERENCE:
  Main body (x=0-60, y=8-44):
    Master zone (x=0-18):
      Master Bed:    x=0-18,  y=8-34
      Master Bath:   x=0-9,   y=34-44
      His Closet:    x=9-14,  y=34-44
      Her Closet:    x=14-18, y=34-44

    Living zone (x=18-45):
      Living Room:   x=18-45, y=8-30   (open to dining/kitchen)
      Kitchen:       x=18-35, y=30-44
      Dining Room:   x=35-45, y=30-44
      Office:        x=38-45, y=8-18

    Service zone (x=45-60):
      Laundry:       x=45-55, y=36-44
      Mudroom:       x=45-55, y=8-18

  Rear wing (x=16-43, y=44-76):
    Bed 2:           x=16-30, y=44-62
    Bed 3:           x=16-30, y=62-76
    Bath 2:          x=30-43, y=62-76
    Bath 3:          x=30-43, y=44-54
    Closet 2:        x=30-38, y=54-62
    Closet 3:        x=38-43, y=54-62
"""

from barnhaus_revit_utils import create_wall
import time

LEVEL = "Level 1.0"
INT   = 'Wall 4.5 Interior"'
WALL_H = 11.0
GAR_H  = 12.0

print("\n=== STAGE 2: INTERIOR WALLS ===")

# ── MASTER ZONE ──
# Master bed / rest of main body divider (x=18, y=8-44) — already exterior on west, this is east face of master
w_master_e = create_wall(18, 44, 0,  18, 8,  0, LEVEL, INT, WALL_H, "master-east")

# Master bed / bath split (y=34, x=0-18)
w_master_bath = create_wall(0, 34, 0,  18, 34, 0, LEVEL, INT, WALL_H, "master-bath-split")

# His/Her closet divider (x=9, y=34-44)
w_his_her = create_wall(9, 34, 0,  9, 44, 0, LEVEL, INT, WALL_H, "his-her-split")

# His/Her closet boundary (x=14, y=34-44)
w_her_end = create_wall(14, 34, 0,  14, 44, 0, LEVEL, INT, WALL_H, "her-closet-end")

# ── LIVING ZONE ──
# Living / kitchen+dining split (y=30, x=18-45)
w_living_kitchen = create_wall(18, 30, 0,  45, 30, 0, LEVEL, INT, WALL_H, "living-kitchen")

# Kitchen / dining divider (x=35, y=30-44)
w_kit_dining = create_wall(35, 44, 0,  35, 30, 0, LEVEL, INT, WALL_H, "kitchen-dining")

# Office south wall (y=18, x=38-45) — office in SE corner of living zone
w_office_s = create_wall(38, 18, 0,  45, 18, 0, LEVEL, INT, WALL_H, "office-south")

# Office west wall (x=38, y=8-18)
w_office_w = create_wall(38, 8,  0,  38, 18, 0, LEVEL, INT, WALL_H, "office-west")

# ── SERVICE ZONE ──
# Service / living divider (x=45, y=8-44) — full height partition
w_service_w = create_wall(45, 8,  0,  45, 44, 0, LEVEL, INT, WALL_H, "service-west")

# Laundry / mudroom split (y=36, x=45-60) — laundry top, mudroom bottom+garage entry
w_laundry_split = create_wall(45, 36, 0,  60, 36, 0, LEVEL, INT, WALL_H, "laundry-split")

# Mudroom east wall / garage entry (x=55, y=8-36)
w_mudroom_e = create_wall(55, 36, 0,  55, 8,  0, LEVEL, INT, WALL_H, "mudroom-east")

# ── REAR WING ──
# Bed 2 / Bed 3 divider (y=62, x=16-30)
w_bed_split = create_wall(16, 62, 0,  30, 62, 0, LEVEL, INT, WALL_H, "bed2-bed3-split")

# Beds / baths+closets divider (x=30, y=44-76)
w_wing_mid = create_wall(30, 76, 0,  30, 44, 0, LEVEL, INT, WALL_H, "wing-mid")

# Bath 2 / closets split (y=62, x=30-43)
w_bath2_split = create_wall(30, 62, 0,  43, 62, 0, LEVEL, INT, WALL_H, "bath2-split")

# Bath 3 / closet zone split (y=54, x=30-43)
w_bath3_split = create_wall(30, 54, 0,  43, 54, 0, LEVEL, INT, WALL_H, "bath3-split")

# Closet 2 / Closet 3 divider (x=38, y=54-62)
w_closet_split = create_wall(38, 54, 0,  38, 62, 0, LEVEL, INT, WALL_H, "closet-split")

print("\n✅ Stage 2 complete — verify room layout in plan view, then proceed to Stage 3")
