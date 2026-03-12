"""
build_3fd426b2.py  —  Mitchell Davis Madison | 3fd426b2
2,800 SF | Two Story | Barndominium | TRUE L-Shape
4 bed | U-shape kitchen + Butler Pantry + Island | His/Hers closets
Open plan L2 | Gable (main + south wing) + Flat (garage)

═══════════════════════════════════════════════════════════════════
DESIGN BRIEF ANALYSIS (from HOME_LAYOUT.md + barnhaus-design-rules.md)
═══════════════════════════════════════════════════════════════════

CIRCULATION PATHS:
  Public:  Front entry (N wall y=42) → Great Room → Kitchen → Courtyard slider
  Private: Entry → Master wall x=18 → Master Bed → South wing (closets/bath)
  Service: Garage (x=48-70) → Shared wall door → Mudroom (SE corner) → Kitchen (NE corner)

ZONE SEQUENCE (west→east):
  [MASTER SUITE: x=0-18] | [GREAT ROOM+KITCHEN: x=18-48] | [GARAGE: x=48-70]
  [CLOSETS+BATH: south wing beneath master]

L-SHAPE DESIGN:
  The L creates a sheltered COURTYARD on the east side (L notch: x=22-48, y=0-20)
  Great room faces the courtyard → hero slider on y=20 wall
  Master bedroom faces WEST (private sunset patio, x=0 wall)
  Entry from NORTH (y=42 = street side)

FOOTPRINT:
  Main wing  (E-W, 2-story): (0,20)→(48,42) = 48×22 = 1,056 SF/floor
  South wing (N-S, 2-story): (0,0)→(22,20)  = 22×20 = 440 SF/floor
  Garage     (1-story):      (48,20)→(70,42) = 22×22 = 484 SF
  Courtyard  (outdoor):      (22,0)→(48,20)  = open L notch
  Per-floor living: 1,496 SF → 2 floors = ~2,800 SF net

L1 MASTER SUITE (spans SW corner of both wings):
  Master Bedroom: (0,20)→(18,42) main wing west end = 18×22 = 396 SF ✓
  His Closet:     (0,10)→(12,20) south wing NW     = 12×10 = 120 SF ✓
  Hers Closet:    (0,0)→(12,10)  south wing SW      = 12×10 = 120 SF ✓
  Master Bath:    (12,0)→(22,20) south wing east     = 10×20 = 200 SF ✓
  Total master suite: 836 SF — luxury 4-component suite

L1 LIVING CORE (main wing center+east):
  Great Room: (18,20)→(48,42) open — 660 SF total open space
    Kitchen zone: NE corner, around (32-48,28-42), open to great room
    Dining: adjacent to kitchen, center-north area
  Butler Pantry: (40,20)→(48,30) = 80 SF, carved from SE corner (service path)

L2 SOUTH WING — Beds 2+4 + Jack-and-Jill Bath:
  Bed 2:    (11,0)→(22,20) = 11×20 = 220 SF ✓
  Bed 4:    (0,10)→(11,20) = 11×10 = 110 SF ✓
  Bath L2A: (0,0)→(11,10)  = 11×10 = 110 SF ✓ (jack-and-jill: Bed2 and Bed4 each have door)

L2 MAIN WING — Landing + Office + Bonus + Bed3 + Bath2:
  Landing:  (0,34)→(48,42)  = 48×8 = 384 SF wide loft (open railing overlooks great room)
  Office:   (0,20)→(16,34)  = 16×14 = 224 SF ✓
  Bonus:    (16,20)→(32,34) = 16×14 = 224 SF ✓
  Bath L2B: (32,20)→(48,27) = 16×7  = 112 SF ✓ (en-suite to Bed3)
  Bed 3:    (32,27)→(48,34) = 16×7  = 112 SF ✓ (minimum, private)

LEVELS:
  Level 1.0:   z=0,  H=11ft
  Level 2.0:   z=11, H=10ft
  L2 Roof:     z=21
  Garage Roof: z=12
"""

from barnhaus_revit_utils import (
    create_wall, smart_floor, make_roof,
    place_door, place_window,
    label_rooms, layout_kitchen, layout_bath_master,
    attach_walls_to_roof, call, verify_wall_facing
)

print("=" * 65)
print("BUILD: Mitchell Davis Madison | 3fd426b2")
print("2,800 SF | Two Story | Barndominium | TRUE L-Shape")
print("=" * 65)

# ── FOOTPRINT ────────────────────────────────────────────────────
MWX0, MWY0, MWX1, MWY1 = 0, 20, 48, 42   # main wing
SWX0, SWY0, SWX1, SWY1 = 0,  0, 22, 20   # south wing
GX0,  GY0,  GX1,  GY1  = 48, 20, 70, 42  # garage

# ── LEVELS ───────────────────────────────────────────────────────
L1, L2 = "Level 1.0", "Level 2.0"
L2R, GR = "L2 Roof", "Garage Roof"
H1, H2, HG = 11, 10, 12

# ── FAMILIES (all confirmed from REVIT_TEMPLATE.md) ──────────────
EXT   = 'Wall 7.5" EXT PBR'
INT   = 'Wall 4.5 Interior"'
EXT_ENTRY  = "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad"
EXT_SLIDER = "Exterior_Sliding_Door_3843"
EXT_LARGE  = "Three_Panel_Sliding_Door_17534"
INT_DOOR   = "Door-Interior-Single-1_Panel-Wood"
GARAGE_OH  = "Door-Garage-Flush_Panel"
WIN_FIX    = "Instance-Window-Fixed"
WIN_AWN    = "Window-Awning-Single"

SILL1 = 2.5   # L1 sill
SILL2 = 13.5  # L2 sill
SILL_BATH = 5.0  # bath privacy

# =================================================================
print("\n=== PHASE 0: LEVELS ===")
for name, elev in [("Level 2.0", 11), ("L2 Roof", 21), ("Garage Roof", 12)]:
    r = call("revit.create_level", {"name": name, "elevation": elev})
    ok = r["Status"] == "ok" or "unique" in r.get("Message", "").lower()
    print(f"  level [{name} @ z={elev}]: {'ok' if ok else r.get('Message', 'err')}")

# =================================================================
print("\n=== PHASE 1: EXTERIOR WALLS (TRUE L PERIMETER) ===")

print("\n── L1 exterior (clockwise from NW, H=11ft) ──")
w1_n   = create_wall(MWX0, MWY1, 0, MWX1, MWY1, 0, L1, EXT, H1, "L1 north")
verify_wall_facing(w1_n,   0, +1, "L1 north")
w1_e   = create_wall(MWX1, MWY1, 0, MWX1, MWY0, 0, L1, EXT, H1, "L1 east")
verify_wall_facing(w1_e,  +1,  0, "L1 east")
w1_sm  = create_wall(MWX1, MWY0, 0, SWX1, MWY0, 0, L1, EXT, H1, "L1 south-main")  # faces courtyard
verify_wall_facing(w1_sm,  0, -1, "L1 south-main")
w1_swe = create_wall(SWX1, MWY0, 0, SWX1, SWY0, 0, L1, EXT, H1, "SW east")        # inner L edge
verify_wall_facing(w1_swe,+1,  0, "SW east")
w1_s   = create_wall(SWX1, SWY0, 0, SWX0, SWY0, 0, L1, EXT, H1, "L1 south")
verify_wall_facing(w1_s,   0, -1, "L1 south")
w1_w   = create_wall(SWX0, SWY0, 0, MWX0, MWY1, 0, L1, EXT, H1, "L1 west")        # full continuous
verify_wall_facing(w1_w,  -1,  0, "L1 west")

# Interior connector: master suite south / south wing north
w1_conn = create_wall(SWX0, MWY0, 0, SWX1, MWY0, 0, L1, INT, H1, "L1 connector")
print(f"  wall [connector] (0,20)→(22,20): {'ok ' + str(w1_conn) if w1_conn else 'ERR'}")

print("\n── Garage (H=12ft) ──")
w_gn = create_wall(GX0, GY1, 0, GX1, GY1, 0, L1, EXT, HG, "garage north")
verify_wall_facing(w_gn, 0, +1, "garage north")
w_ge = create_wall(GX1, GY1, 0, GX1, GY0, 0, L1, EXT, HG, "garage east")
verify_wall_facing(w_ge, +1, 0, "garage east")
w_gs = create_wall(GX1, GY0, 0, GX0, GY0, 0, L1, EXT, HG, "garage south")
verify_wall_facing(w_gs, 0, -1, "garage south")

print("\n── L2 exterior (same L perimeter, z=11, H=10ft) ──")
w2_n   = create_wall(MWX0, MWY1, 11, MWX1, MWY1, 11, L2, EXT, H2, "L2 north")
verify_wall_facing(w2_n,   0, +1, "L2 north")
w2_e   = create_wall(MWX1, MWY1, 11, MWX1, MWY0, 11, L2, EXT, H2, "L2 east")
verify_wall_facing(w2_e,  +1,  0, "L2 east")
w2_sm  = create_wall(MWX1, MWY0, 11, SWX1, MWY0, 11, L2, EXT, H2, "L2 south-main")
verify_wall_facing(w2_sm,  0, -1, "L2 south-main")
w2_swe = create_wall(SWX1, MWY0, 11, SWX1, SWY0, 11, L2, EXT, H2, "L2 SW east")
verify_wall_facing(w2_swe,+1,  0, "L2 SW east")
w2_s   = create_wall(SWX1, SWY0, 11, SWX0, SWY0, 11, L2, EXT, H2, "L2 south")
verify_wall_facing(w2_s,   0, -1, "L2 south")
w2_w   = create_wall(SWX0, SWY0, 11, MWX0, MWY1, 11, L2, EXT, H2, "L2 west")
verify_wall_facing(w2_w,  -1,  0, "L2 west")
w2_conn = create_wall(SWX0, MWY0, 11, SWX1, MWY0, 11, L2, INT, H2, "L2 connector")
print(f"  wall [L2 connector] (0,20)→(22,20) z=11: {'ok ' + str(w2_conn) if w2_conn else 'ERR'}")

# =================================================================
print("\n=== PHASE 2: INTERIOR WALLS ===")
print("\n── L1 Master suite ──")
# Separates master bedroom (west) from great room (east)
w_mstr_e    = create_wall(18, MWY0, 0, 18, MWY1, 0, L1, INT, H1, "master east")
# South wing: closets (west) from master bath (east)
w_sw_bath_w = create_wall(12, SWY0, 0, 12, MWY0, 0, L1, INT, H1, "SW bath west")
# South wing: his closet (north) from hers closet (south)
w_sw_hhsplit= create_wall(SWX0, 10, 0, 12, 10, 0, L1, INT, H1, "his/hers split")

print("\n── L1 Butler pantry (service path: garage→pantry→kitchen) ──")
w_butler_w  = create_wall(40, MWY0, 0, 40, 30, 0, L1, INT, H1, "butler pantry west")
w_butler_n  = create_wall(40, 30, 0, MWX1, 30, 0, L1, INT, H1, "butler pantry north")

print("\n── L2 South wing (Bed2 east | Bed4+Bath west) ──")
w_l2_sw_div = create_wall(11, SWY0, 11, 11, MWY0, 11, L2, INT, H2, "L2 SW divider")
w_l2_sw_btn = create_wall(SWX0, 10, 11, 11, 10, 11, L2, INT, H2, "L2 SW bath north")

print("\n── L2 Main wing (wide landing + rooms below) ──")
# Landing runs full width at top; rooms below
w_l2_lnds   = create_wall(MWX0, 34, 11, MWX1, 34, 11, L2, INT, H2, "L2 landing south")
# Office east / Bonus west boundary
w_l2_off_e  = create_wall(16, MWY0, 11, 16, 34, 11, L2, INT, H2, "L2 office east")
# Bonus east / Bed3+Bath west boundary
w_l2_bon_e  = create_wall(32, MWY0, 11, 32, 34, 11, L2, INT, H2, "L2 bonus east")
# Bath L2B north (splits bath below from Bed3 above)
w_l2_bath2n = create_wall(32, 27, 11, MWX1, 27, 11, L2, INT, H2, "L2 bath2 north")

# =================================================================
print("\n=== PHASE 3: FLOORS ===")
smart_floor(L1,  0, MWX0, MWY0, MWX1, MWY1)   # L1 main wing
smart_floor(L1,  0, SWX0, SWY0, SWX1, SWY1)   # L1 south wing
smart_floor(L1,  0, GX0,  GY0,  GX1,  GY1)    # garage
smart_floor(L2, 11, MWX0, MWY0, MWX1, MWY1)   # L2 main wing
smart_floor(L2, 11, SWX0, SWY0, SWX1, SWY1)   # L2 south wing

# =================================================================
print("\n=== PHASE 4: DOORS ===")

print("\n── Exterior ──")
# Front entry: centered on north wall
place_door(w1_n, 24, MWY1, 0, EXT_ENTRY, '36" x 96"', label="front entry")
# Master patio: west wall, centered on master bedroom zone (y=20-42, center=31)
place_door(w1_w, 0, 31, 0, EXT_SLIDER, "6'-0\"W. x 8'-0\"H.", label="master patio")
# Courtyard hero slider: great room faces the L-notch courtyard
place_door(w1_sm, 35, MWY0, 0, EXT_LARGE, '120" x 96"', label="courtyard slider")
# Garage OH: east wall
place_door(w_ge, GX1, 31, 0, GARAGE_OH, "16W X 10H", label="garage OH")

print("\n── Service path: garage → mudroom/pantry → kitchen ──")
# Interior door on shared wall x=48 (butler pantry zone at y=20-30, center=25)
r_shared = call("revit.create_wall", {
    "start": {"x": GX0, "y": GY0, "z": 0}, "end": {"x": GX0, "y": GY1, "z": 0},
    "level": L1, "wall_type": INT, "height": HG, "location_line": 2
})
w_shared = r_shared["Result"]["wall_id"] if r_shared["Status"] == "ok" else None
print(f"  wall [garage shared]: {'ok ' + str(w_shared) if w_shared else 'ERR'}")
if w_shared:
    place_door(w_shared, GX0, 25, 0, INT_DOOR, '36" x 96"', label="garage to house")

print("\n── L1 Master suite ──")
# Master entry from great room
place_door(w_mstr_e, 18, 31, 0, INT_DOOR, '36" x 96"', label="master entry")
# Master to his closet: connector wall y=20, center of his closet x=0-12
place_door(w1_conn, 6, MWY0, 0, INT_DOOR, '30" x 96"', label="master to his closet")
# His closet to bath: x=12 wall, center of his zone y=10-20
place_door(w_sw_bath_w, 12, 15, 0, INT_DOOR, '30" x 96"', label="his closet to bath")
# Hers closet to bath: x=12 wall, center of hers zone y=0-10
place_door(w_sw_bath_w, 12, 5, 0, INT_DOOR, '30" x 96"', label="hers closet to bath")
# Butler pantry entry
place_door(w_butler_w, 40, 25, 0, INT_DOOR, '30" x 96"', label="butler pantry")

print("\n── L2 doors (all open to landing or connector) ──")
# Bed 2: L2 connector wall y=20 at x=16 (center of bed2 x=11-22)
place_door(w2_conn, 16, MWY0, 11, INT_DOOR, '36" x 96"', label="L2 bed2")
# Bed 4: L2 connector wall y=20 at x=5 (center of bed4 x=0-11)
place_door(w2_conn, 5, MWY0, 11, INT_DOOR, '36" x 96"', label="L2 bed4")
# Bath L2A from Bed 2 (jack-and-jill): x=11 divider at y=5 (bath center y=0-10)
place_door(w_l2_sw_div, 11, 5, 11, INT_DOOR, '30" x 96"', label="L2 bath from bed2")
# Bath L2A from Bed 4: y=10 wall at x=5 (center of bed4/bath boundary)
place_door(w_l2_sw_btn, 5, 10, 11, INT_DOOR, '30" x 96"', label="L2 bath from bed4")
# Office: landing wall y=34 at x=8
place_door(w_l2_lnds, 8, 34, 11, INT_DOOR, '36" x 96"', label="L2 office")
# Bonus: landing wall y=34 at x=24
place_door(w_l2_lnds, 24, 34, 11, INT_DOOR, '36" x 96"', label="L2 bonus")
# Bed 3: landing wall y=34 at x=40
place_door(w_l2_lnds, 40, 34, 11, INT_DOOR, '36" x 96"', label="L2 bed3")
# Bath L2B en-suite: y=27 wall at x=40 (center of bed3 x=32-48)
place_door(w_l2_bath2n, 40, 27, 11, INT_DOOR, '30" x 96"', label="L2 bath2 to bed3")

# =================================================================
print("\n=== PHASE 5: WINDOWS ===")
# Per REVIT_TEMPLATE.md confirmed types only

# ── L1 exterior ──
# Master west (private sunset wall — max glass)
place_window(w1_w, 0, 31, SILL1, WIN_FIX, '72" x 36"', label="master W")

# L1 north (front — restrained, flanking entry only)
place_window(w1_n, 8,  MWY1, SILL1, WIN_FIX, '48" x 48"', label="entry N1")
place_window(w1_n, 40, MWY1, SILL1, WIN_FIX, '48" x 48"', label="great rm N")

# Great room courtyard wall (hero exposure — flanking the big slider at x=35)
place_window(w1_sm, 26, MWY0, SILL1, WIN_FIX, '72" x 36"', label="GR court W1")
place_window(w1_sm, 44, MWY0, SILL1, WIN_FIX, '72" x 36"', label="GR court W2")

# Kitchen east wall
place_window(w1_e, MWX1, 36, SILL1, WIN_FIX, '60" x 30"', label="kitchen E")

# Master bath: privacy window on south wing east face (faces courtyard)
place_window(w1_swe, SWX1, 10, SILL_BATH, WIN_AWN, '24" x 72"', label="bath court")

# ── L2 exterior ──
# L2 south wing: Bed 2 south (over courtyard direction)
place_window(w2_s, 16, SWY0, SILL2, WIN_FIX, '72" x 36"', label="L2 bed2 S")
# L2 west: Bed 2 west + Bed 4 west + Bath privacy
place_window(w2_w, 0, 15, SILL2, WIN_FIX, '72" x 36"', label="L2 bed2 W")
place_window(w2_w, 0, 5,  SILL_BATH, WIN_AWN, '24" x 72"', label="L2 bath W")

# L2 main wing north (landing/office/bed3 — restrained)
place_window(w2_n, 8,  MWY1, SILL2, WIN_FIX, '72" x 36"', label="L2 office N")
place_window(w2_n, 24, MWY1, SILL2, WIN_FIX, '48" x 48"', label="L2 bonus N")
place_window(w2_n, 40, MWY1, SILL2, WIN_FIX, '72" x 36"', label="L2 bed3 N")

# L2 east (Bed 3)
place_window(w2_e, MWX1, 31, SILL2, WIN_FIX, '72" x 36"', label="L2 bed3 E")

# L2 bath2 privacy: south-main wall at z=11 (bath faces L notch courtyard)
place_window(w2_sm, 40, MWY0, SILL2 + 2.5, WIN_AWN, '24" x 72"', label="L2 bath2 court")

# =================================================================
print("\n=== PHASE 6: ROOFS ===")
# Main wing gable (ridge E-W, slopes N+S) — creates vaulted great room ceiling
r_main = make_roof("Main wing", MWX0, MWY0, MWX1, MWY1, L2R,
                   pitch=0.5, slope_style="gable", overhang=2.0)
if r_main:
    attach_walls_to_roof([w2_n, w2_e, w2_sm, w2_w], r_main)

# South wing gable (ridge N-S, slopes E+W) — master suite volume
r_sw = make_roof("South wing", SWX0, SWY0, SWX1, SWY1, L2R,
                 pitch=0.5, slope_style="gable", overhang=2.0)
if r_sw:
    attach_walls_to_roof([w2_s, w2_w, w2_swe], r_sw)

# Garage flat
make_roof("Garage", GX0, GY0, GX1, GY1, GR, pitch=0.01, slope_style="flat")

# =================================================================
print("\n=== PHASE 7: STAIRS ===")
# Staircase: center of main wing near great room/landing transition
r = call("revit.create_stair", {
    "level": L1, "top_level": L2, "x": 22, "y": 30, "z": 0,
    "width": 4.0, "label": "main stair"
})
print(f"  stair [main stair @ 22,30]: {'ok' if r.get('Status')=='ok' else '⚠️  MANUAL PLACEMENT in Revit'}")

# =================================================================
print("\n=== PHASE 8: ROOM LABELS ===")
# NOTE: upper_limit_level="Level 2.0" for L1 (z=11 = actual wall top)
# Fixes 0 SF issue by bounding rooms to the real top of L1 walls

print("\n── L1 Rooms ──")
label_rooms([
    {"name": "Master Bedroom", "x": 9,  "y": 31},   # (0-18, 20-42) = 396 SF
    {"name": "His Closet",     "x": 6,  "y": 15},   # (0-12, 10-20) = 120 SF
    {"name": "Hers Closet",    "x": 6,  "y": 5},    # (0-12, 0-10)  = 120 SF
    {"name": "Master Bath",    "x": 17, "y": 10},   # (12-22, 0-20) = 200 SF
    {"name": "Great Room",     "x": 27, "y": 25},   # (18-40, 20-30) open
    {"name": "Dining",         "x": 27, "y": 37},   # (18-32, 30-42) open
    {"name": "Kitchen",        "x": 42, "y": 37},   # (32-48, 28-42) NE corner
    {"name": "Butler Pantry",  "x": 44, "y": 25},   # (40-48, 20-30)
    {"name": "Garage",         "x": 59, "y": 31},
], L1, upper_limit_level="Level 2.0")

print("\n── L2 Rooms ──")
label_rooms([
    {"name": "Bedroom 2",    "x": 16, "y": 10, "z": 11},  # (11-22, 0-20) = 220 SF
    {"name": "Bedroom 4",    "x": 5,  "y": 15, "z": 11},  # (0-11, 10-20) = 110 SF
    {"name": "Bath L2",      "x": 5,  "y": 5,  "z": 11},  # (0-11, 0-10)  = 110 SF
    {"name": "Landing",      "x": 24, "y": 38, "z": 11},  # (0-48, 34-42) = 384 SF
    {"name": "Office/Study", "x": 8,  "y": 27, "z": 11},  # (0-16, 20-34) = 224 SF
    {"name": "Bonus Room",   "x": 24, "y": 27, "z": 11},  # (16-32, 20-34)= 224 SF
    {"name": "Bedroom 3",    "x": 40, "y": 31, "z": 11},  # (32-48, 27-34)= 112 SF
    {"name": "Bath L2B",     "x": 40, "y": 24, "z": 11},  # (32-48, 20-27)= 112 SF
], L2, upper_limit_level="L2 Roof")

# =================================================================
print("\n=== PHASE 9: FIXTURES (skipped — run fixtures_3fd426b2.py separately) ===")

print(f"\n✅ Build complete — Mitchell Davis Madison (3fd426b2)")
print(f"   TRUE L-Shape | 2,800 SF | Barndominium | Gable+Gable+Flat | 4 bed")
print(f"\n⚠️  MANUAL STEPS:")
print(f"   1. Stairs at (20-24, 28-36) — Level 1 floor plan")
print(f"   2. Open railing on landing south edge (y=34, L2) overlooking great room")
print(f"   3. Courtyard (x=22-48, y=0-20) is intentional outdoor L-notch space")
print(f"\nMaster suite circuit: Entry → Master Bed → His Closet → Bath → Hers Closet")
print(f"Service path: Garage → Shared wall door → Butler Pantry → Kitchen")
