"""
build_733688fb_s3.py — Stage 3: Doors + Windows
Submission: 733688fb | Mitchell Madison | 2,750 SF | T-Shape

WALL IDs (from Stage 1+2):
  EXTERIOR:
    main-south:       5947480 (y=8,  x=0-60)
    main-west:        5947481 (x=0,  y=8-44)
    main-east:        5947482 (x=60, y=8-44)
    main-north-left:  5947483 (y=44, x=0-16)
    main-north-right: 5947484 (y=44, x=43-60)
    wing-north:       5947485 (y=76, x=16-43)
    wing-west:        5947486 (x=16, y=44-76)
    wing-east:        5947487 (x=43, y=44-76)
    gar-south:        5947488 (y=8,  x=60-84)
    gar-north:        5947489 (y=32, x=60-84)
    gar-east:         5947490 (x=84, y=8-32)
  INTERIOR:
    master-east:      5947685 (x=18, y=8-44)
    master-bath-split:5947686 (y=34, x=0-18)
    his-her-split:    5947687 (x=9,  y=34-44)
    her-closet-end:   5947688 (x=14, y=34-44)
    living-kitchen:   5947689 (y=30, x=18-45)
    kitchen-dining:   5947690 (x=35, y=30-44)
    office-south:     5947691 (y=18, x=38-45)
    office-west:      5947692 (x=38, y=8-18)
    service-west:     5947693 (x=45, y=8-44)
    laundry-split:    5947694 (y=36, x=45-60)
    mudroom-east:     5947695 (x=55, y=8-36)
    bed2-bed3-split:  5947696 (y=62, x=16-30)
    wing-mid:         5947703 (x=30, y=44-76)
    bath2-split:      5947698 (y=62, x=30-43)
    bath3-split:      5947699 (y=54, x=30-43)
    closet-split:     5947700 (x=38, y=54-62)
"""

from barnhaus_revit_utils import place_door, place_window, WIN_FAMILY
import time

LEVEL  = "Level 1.0"
ISLIDE = "Exterior_Sliding_Door_3843"
ISWING = "Door-Interior-Single-1_Panel-Wood"
GOHD   = "Door-Garage-Flush_Panel"

# Wall IDs
W_MAIN_S   = 5947480
W_MAIN_W   = 5947481
W_MAIN_E   = 5947482
W_MAIN_N1  = 5947483
W_MAIN_N2  = 5947484
W_WING_N   = 5947485
W_WING_W   = 5947486
W_WING_E   = 5947487
W_GAR_S    = 5947488
W_GAR_N    = 5947489
W_GAR_E    = 5947490
W_MAST_E   = 5947685
W_MAST_BTH = 5947686
W_HIS_HER  = 5947687
W_HER_END  = 5947688
W_LIV_KIT  = 5947689
W_KIT_DIN  = 5947690
W_OFF_S    = 5947691
W_OFF_W    = 5947692
W_SVC_W    = 5947693
W_LAUND    = 5947694
W_MUD_E    = 5947695
W_BED_SPL  = 5947696
W_WING_MID = 5947703
W_BATH2    = 5947698
W_BATH3    = 5947699
W_CLOS_SPL = 5947700

print("\n=== STAGE 3: EXTERIOR DOORS ===")

# Front entry — centered on main-south, sliding glass
place_door(W_MAIN_S, 30, 8, 0, ISLIDE, '6\'-0"W. x 8\'-0"H.', label="front-entry", level=LEVEL)

# Master rear slider — on main-west, sliding glass to back yard
place_door(W_MAIN_W, 0, 26, 0, ISLIDE, '6\'-0"W. x 8\'-0"H.', label="master-slider", level=LEVEL)

# Living rear slider — main-north-left side (opens toward wing/back)
place_door(W_MAIN_N1, 8, 44, 0, ISLIDE, '6\'-0"W. x 8\'-0"H.', label="living-rear-slider", level=LEVEL)

# Garage overhead door — gar-south
place_door(W_GAR_S, 72, 8, 0, GOHD, '16W X 10H', label="garage-OH", level=LEVEL, wall_height=12.0)

print("\n=== STAGE 3: INTERIOR DOORS ===")

# Master bed → bath
place_door(W_MAST_BTH, 14, 34, 0, ISWING, '36" x 96"', label="mbath-door", level=LEVEL)

# Master bath → his closet
place_door(W_HIS_HER, 9, 39, 0, ISWING, '30" x 96"', label="his-door", level=LEVEL)

# Master bath → her closet
place_door(W_HER_END, 14, 39, 0, ISWING, '30" x 96"', label="her-door", level=LEVEL)

# Master east → living (main passage from master zone)
place_door(W_MAST_E, 18, 20, 0, ISWING, '36" x 96"', label="master-entry", level=LEVEL)

# Living → kitchen (opening — wide swing)
place_door(W_LIV_KIT, 26, 30, 0, ISWING, '36" x 96"', label="living-kitchen-door", level=LEVEL)

# Kitchen → dining (open pass)
place_door(W_KIT_DIN, 35, 37, 0, ISWING, '36" x 96"', label="kit-dining-door", level=LEVEL)

# Office door
place_door(W_OFF_S, 41, 18, 0, ISWING, '36" x 96"', label="office-door", level=LEVEL)

# Service zone → kitchen
place_door(W_SVC_W, 45, 38, 0, ISWING, '36" x 96"', label="service-entry", level=LEVEL)

# Mudroom → garage
place_door(W_MUD_E, 55, 14, 0, ISWING, '36" x 96"', label="mudroom-garage", level=LEVEL)

# Laundry door
place_door(W_LAUND, 50, 36, 0, ISWING, '30" x 96"', label="laundry-door", level=LEVEL)

# Wing — bed 2 door
place_door(W_WING_MID, 30, 52, 0, ISWING, '36" x 96"', label="bed2-door", level=LEVEL)

# Wing — bed 3 door
place_door(W_WING_MID, 30, 68, 0, ISWING, '36" x 96"', label="bed3-door", level=LEVEL)

# Bath 2 door
place_door(W_BATH2, 36, 62, 0, ISWING, '30" x 96"', label="bath2-door", level=LEVEL)

# Bath 3 door
place_door(W_BATH3, 36, 54, 0, ISWING, '30" x 96"', label="bath3-door", level=LEVEL)

# Closet 2 door
place_door(W_CLOS_SPL, 38, 58, 0, ISWING, '30" x 96"', label="closet2-door", level=LEVEL)

print("\n=== STAGE 3: WINDOWS ===")

# Main south (front) — flanking entry
place_window(W_MAIN_S, 12, 8, 3, WIN_FAMILY, '48" x 48"', label="front-w1", level=LEVEL)
place_window(W_MAIN_S, 48, 8, 3, WIN_FAMILY, '48" x 48"', label="front-w2", level=LEVEL)

# Main west — master bedroom windows
place_window(W_MAIN_W, 0, 16, 3, WIN_FAMILY, '48" x 48"', label="master-w1", level=LEVEL)
place_window(W_MAIN_W, 0, 26, 3, WIN_FAMILY, '48" x 48"', label="master-w2", level=LEVEL)

# Main north-right — dining view
place_window(W_MAIN_N2, 52, 44, 3, WIN_FAMILY, '60" x 24"', label="dining-w1", level=LEVEL)

# Wing north — bedroom view windows
place_window(W_WING_N, 22, 76, 3, WIN_FAMILY, '48" x 48"', label="bed2-w1", level=LEVEL)
place_window(W_WING_N, 36, 76, 3, WIN_FAMILY, '48" x 48"', label="bed3-w1", level=LEVEL)

# Wing west — bed 2 side window
place_window(W_WING_W, 16, 52, 3, WIN_FAMILY, '48" x 48"', label="bed2-side-w", level=LEVEL)

# Wing east — bed 3 side window + bath window
place_window(W_WING_E, 43, 68, 3, WIN_FAMILY, '48" x 48"', label="bed3-side-w", level=LEVEL)
place_window(W_WING_E, 43, 57, 3, WIN_FAMILY, '24" x 96"', label="bath2-w", level=LEVEL)

# Master bath window (west wall, high sill)
place_window(W_MAIN_W, 0, 38, 5, WIN_FAMILY, '24" x 96"', label="mbath-w", level=LEVEL)

print("\n✅ Stage 3 complete — check doors and windows, then proceed to Stage 4 (room labels)")
