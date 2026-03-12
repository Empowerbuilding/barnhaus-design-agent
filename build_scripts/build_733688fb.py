"""
build_733688fb.py — Stage 1: Exterior Shell
Submission: 733688fb | Mitchell Madison | 2,750 SF | Contemporary | T-Shape
Stages: 1=shell, 2=interior walls, 3=doors/windows, 4=room labels
Stage 5 (fixtures) → fixtures_733688fb.py

T-SHAPE GEOMETRY:
  Main body:   x=0–60,  y=8–44
  Rear wing:   x=16–43, y=44–76
  Garage:      x=60–84, y=8–32  (attached right)
  Front porch: x=0–60,  y=0–8
  Rear porch:  x=16–43, y=76–84
"""

from barnhaus_revit_utils import (
    create_wall, create_rect_exterior, create_garage,
    smart_floor, create_floor, make_roof,
    attach_walls_to_roof, verify_wall_facing,
    call, T, WIN
)
import time

LEVEL  = "Level 1.0"
L2     = "Level 2.0"
EXT    = 'Wall 7.5" EXT PBR'
GAR_H  = 12.0
WALL_H = 11.0
PITCH  = 4/12

MX0, MY0, MX1, MY1 = 0,  8,  60, 44
WX0, WY0, WX1, WY1 = 16, 44, 43, 76
GX0, GY0, GX1, GY1 = 60, 8,  84, 32

print("\n=== STAGE 1: EXTERIOR WALLS ===")

# Main body — use create_rect_exterior, skip east (shared with garage)
main_walls = create_rect_exterior(MX0, MY0, MX1, MY1, 0, LEVEL, EXT, WALL_H,
                                   label_prefix="main", skip_faces=["east", "north"])

# Main body east wall (shared face with garage — single wall)
w_main_e = create_wall(MX1, MY1, 0, MX1, MY0, 0, LEVEL, EXT, WALL_H, "main-east")
verify_wall_facing(w_main_e, +1, 0, "main-east")

# Main body north wall split into two segments (wing opening x=16–43)
w_main_n1 = create_wall(MX0, MY1, 0, WX0, MY1, 0, LEVEL, EXT, WALL_H, "main-north-left")
verify_wall_facing(w_main_n1, 0, +1, "main-north-left")
w_main_n2 = create_wall(WX1, MY1, 0, MX1, MY1, 0, LEVEL, EXT, WALL_H, "main-north-right")
verify_wall_facing(w_main_n2, 0, +1, "main-north-right")

# Rear wing — skip south (open to main body)
wing_walls = create_rect_exterior(WX0, WY0, WX1, WY1, 0, LEVEL, EXT, WALL_H,
                                   label_prefix="wing", skip_faces=["south"])

# Garage — skip west (shared with main body east wall)
gar_walls = create_rect_exterior(GX0, GY0, GX1, GY1, 0, LEVEL, EXT, GAR_H,
                                  label_prefix="gar", skip_faces=["west"])

print("\n=== STAGE 1: FLOORS ===")

# T-shape polygon (main body + rear wing as one slab — no overlap)
main_floor_pts = [
    (MX0, MY0), (MX1, MY0), (MX1, MY1),
    (WX1, MY1), (WX1, WY1), (WX0, WY1),
    (WX0, MY1), (MX0, MY1),
]
f_main = create_floor(LEVEL, 0, main_floor_pts)

# Garage slab (separate polygon)
f_gar = create_floor(LEVEL, 0, [(GX0,GY0),(GX1,GY0),(GX1,GY1),(GX0,GY1)])

print("\n=== STAGE 1: ROOFS ===")

r_main = make_roof("Main Body", MX0, MY0, MX1, MY1, L2,
                   pitch=PITCH, slope_style="gable")
r_wing = make_roof("Rear Wing", WX0, WY0, WX1, WY1, L2,
                   pitch=2/12, slope_style="shed", shed_low_edge=2)
r_gar  = make_roof("Garage", GX0, GY0, GX1, GY1, L2,
                   pitch=1/12, slope_style="shed", shed_low_edge=1)

print("\n=== STAGE 1: ATTACH WALLS TO ROOFS ===")

main_wall_ids = [v for v in [main_walls.get("south"), main_walls.get("west"),
                              w_main_e, w_main_n1, w_main_n2] if v]
if r_main:
    attach_walls_to_roof(main_wall_ids, r_main)

wing_wall_ids = [v for v in [wing_walls.get("west"), wing_walls.get("east"),
                              wing_walls.get("north")] if v]
if r_wing:
    attach_walls_to_roof(wing_wall_ids, r_wing)

gar_wall_ids = [v for v in [gar_walls.get("south"), gar_walls.get("east"),
                             gar_walls.get("north")] if v]
if r_gar:
    attach_walls_to_roof(gar_wall_ids, r_gar)

print("\n✅ Stage 1 complete — take 3D screenshot before Stage 2")
