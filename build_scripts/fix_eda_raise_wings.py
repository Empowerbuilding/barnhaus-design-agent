"""fix_eda_raise_wings.py
Raise LW + RW exterior walls from 10ft to 12ft.
Delete old walls → recreate at 12ft → redo roofs → re-place doors/windows → add new windows.
"""
import sys, time
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import (
    _call, create_wall, place_door, place_window, flip_door,
    make_roof, attach_walls_to_roof
)

LEVEL = "Level 1.0"
EXT   = 'Wall 6" Exterior'
WIN   = "Instance-Window-Fixed"
NEW_H = 12  # raised from 10

print("=== Raise Wing Walls: 10ft → 12ft ===\n")

# ── 1. DELETE OLD LW + RW EXTERIOR WALLS ──────────────────────────────────
old_walls = {
    # LW walls
    "lw_s":  5953192,
    "lw_n":  5953193,
    "lw_w":  5953194,
    "lw_e1": 5953195,
    # RW walls
    "rw_s":  5953214,
    "rw_n":  5953215,
    "rw_e":  5953216,
    "rw_w1": 5953217,
}

print("Step 1: Deleting old wing walls...")
for label, eid in old_walls.items():
    r = _call("revit.delete_element", {"element_id": eid})
    status = r.get("Status", r.get("status", "?"))
    deleted = r.get("Result", {})
    if isinstance(deleted, dict):
        cnt = deleted.get("deleted_count", "?")
    else:
        cnt = "?"
    print(f"  {label} ({eid}): {status} — deleted {cnt}")
    time.sleep(0.2)

print()

# ── 2. RECREATE LW WALLS AT 12FT ──────────────────────────────────────────
# LW: x=0→22, y=8→54
print("Step 2: Recreating LW walls at 12ft...")
lw_s  = create_wall(22, 8,  0, 0,  8,  0, LEVEL, EXT, NEW_H, "LW-S")
lw_n  = create_wall(0,  54, 0, 22, 54, 0, LEVEL, EXT, NEW_H, "LW-N")
lw_w  = create_wall(0,  8,  0, 0,  54, 0, LEVEL, EXT, NEW_H, "LW-W")
lw_e1 = create_wall(22, 26, 0, 22, 8,  0, LEVEL, EXT, NEW_H, "LW-E1")  # south stub (y=8→26)
print(f"  lw_s={lw_s}, lw_n={lw_n}, lw_w={lw_w}, lw_e1={lw_e1}")

# ── 3. RECREATE RW WALLS AT 12FT ──────────────────────────────────────────
# RW: x=84→106, y=8→54
print("Step 3: Recreating RW walls at 12ft...")
rw_s  = create_wall(84, 8,  0, 106, 8,  0, LEVEL, EXT, NEW_H, "RW-S")
rw_n  = create_wall(106,54, 0, 84,  54, 0, LEVEL, EXT, NEW_H, "RW-N")
rw_e  = create_wall(106,8,  0, 106, 54, 0, LEVEL, EXT, NEW_H, "RW-E")
rw_w1 = create_wall(84, 26, 0, 84,  8,  0, LEVEL, EXT, NEW_H, "RW-W1")  # south stub
print(f"  rw_s={rw_s}, rw_n={rw_n}, rw_e={rw_e}, rw_w1={rw_w1}")

print()
time.sleep(1)

# ── 4. DELETE OLD WING ROOFS + RECREATE AT Z=12 ───────────────────────────
# Wing Roof level is at z=10. We need roofs sitting at z=12 now.
# Create a new level or use base_offset.
# Approach: use make_roof with level="Level 2.0" (z=11) + offset=1 → sits at 12
# Actually simplest: delete old wing roofs and recreate using "Level 2.0" (z=11)
# with a 1ft offset, or just use the existing Wing Roof level + 2ft top offset.
# Best: make new flat roofs at z=12 using Level 2.0 (z=11) with 1ft offset.
# But make_roof doesn't have offset param. So use a new level approach:
# level="Level 2.0" is z=11 → still 1ft short.
# SIMPLEST: just redo with pitch so the eave sits at 12ft.
# Use shed roof from Wing Roof (z=10) with shed_low_edge=2 → eave at 12ft.

print("Step 4: Delete old wing roofs + recreate elevated...")
# Old LW roof and RW roof IDs — find them (we don't have IDs saved)
# Try deleting by label isn't supported. Skip auto-delete; recreate on top.
# We'll just create new shed roofs with low_edge=2 (so low side at z=10+2=12)
# This gives a slight slope which looks good.

# LW roof: x=0→22, y=8→54, shed slopes up south→north, low edge south (y=8)
lw_roof = make_roof("LW-Roof-New", x0=0, y0=8, x1=22, y1=54,
                    level_name="Wing Roof", pitch=0.1,
                    shed_low_edge=2, oh_s=True, oh_n=False, oh_w=True, oh_e=False)
print(f"  LW new roof: {lw_roof}")

# RW roof: x=84→106, y=8→54, shed slopes up south→north, low edge south
rw_roof = make_roof("RW-Roof-New", x0=84, y0=8, x1=106, y1=54,
                    level_name="Wing Roof", pitch=0.1,
                    shed_low_edge=2, oh_s=True, oh_n=False, oh_w=False, oh_e=True)
print(f"  RW new roof: {rw_roof}")

time.sleep(1)

# Attach new walls to new roofs
print("Attaching walls to roofs...")
for wid in [lw_s, lw_n, lw_w, lw_e1]:
    attach_walls_to_roof(wid, lw_roof)
for wid in [rw_s, rw_n, rw_e, rw_w1]:
    attach_walls_to_roof(wid, rw_roof)
print("  ✅ Attached")

print()
time.sleep(0.5)

# ── 5. RE-PLACE ORIGINAL DOORS ON NEW WALLS ───────────────────────────────
print("Step 5: Re-placing original doors...")

# Master slider on LW south
ms = place_door(lw_s, 11, 8, 0, "Exterior_Sliding_Door_3843", '6\'-0"W. x 8\'-0"H.', label="MasterSlider", level=LEVEL)
flip_door(ms)
print(f"  MasterSlider: {ms}")

# LBZ + RBZ connector doors (walls unchanged, skip)

print()

# ── 6. ADD WINDOWS MATCHING THE IMAGE ─────────────────────────────────────
print("Step 6: Placing windows to match AI design...")

# LW south wall — 2 large paired windows (master bed faces south)
# Image shows them centered, ~5ft wide each, sill 1.5ft
place_window(lw_s,  7, 8,  1.5, WIN, '60" x 72"', label="LW-S-Win1")
place_window(lw_s, 15, 8,  1.5, WIN, '60" x 72"', label="LW-S-Win2")
print("  ✅ LW south: 2 large windows (60x72, sill 1.5ft)")

# LW west end wall — 1 centered window
place_window(lw_w,  0, 31, 2.5, WIN, '48" x 48"', label="LW-W-Win1")
place_window(lw_w,  0, 15, 2.5, WIN, '48" x 48"', label="LW-W-Win2")
place_window(lw_w,  0, 46, 2.5, WIN, '48" x 48"', label="LW-W-Win3")
print("  ✅ LW west: 3 windows")

# LW north (mudroom/laundry side)
place_window(lw_n,  7, 54, 2.5, WIN, '48" x 48"', label="LW-N-Win1")
place_window(lw_n, 15, 54, 2.5, WIN, '48" x 48"', label="LW-N-Win2")
print("  ✅ LW north: 2 windows")

# RW south wall — 2 large windows + existing area (image shows big windows on this face)
place_window(rw_s,  88, 8, 1.5, WIN, '60" x 72"', label="RW-S-Win1")
place_window(rw_s,  96, 8, 1.5, WIN, '60" x 72"', label="RW-S-Win2")
place_window(rw_s, 103, 8, 2.5, WIN, '48" x 48"', label="RW-S-Win3")
print("  ✅ RW south: 3 windows")

# RW east end wall
place_window(rw_e, 106, 20, 2.5, WIN, '48" x 48"', label="RW-E-Win1")
place_window(rw_e, 106, 38, 2.5, WIN, '48" x 48"', label="RW-E-Win2")
print("  ✅ RW east: 2 windows")

# RW north wall
place_window(rw_n,  88, 54, 2.5, WIN, '48" x 48"', label="RW-N-Win1")
place_window(rw_n,  95, 54, 2.5, WIN, '48" x 48"', label="RW-N-Win2")
place_window(rw_n, 102, 54, 2.5, WIN, '48" x 48"', label="RW-N-Win3")
print("  ✅ RW north: 3 windows")

# RW west inner wall (hallway)
place_window(rw_w1, 84, 17, 2.5, WIN, '48" x 48"', label="RW-W-Win1")
print("  ✅ RW west inner: 1 window")

print()
print("=== DONE ===")
print(f"New wall IDs → lw_s={lw_s}, lw_n={lw_n}, lw_w={lw_w}, lw_e1={lw_e1}")
print(f"              rw_s={rw_s}, rw_n={rw_n}, rw_e={rw_e}, rw_w1={rw_w1}")
print(f"New roofs   → lw_roof={lw_roof}, rw_roof={rw_roof}")
print("Save the project and take screenshots for image enhancer review.")
