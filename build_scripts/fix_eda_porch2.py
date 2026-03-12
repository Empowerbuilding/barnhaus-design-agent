"""
fix_eda_porch2.py — Fix back porch location + garage door flip
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import _call, make_roof, place_porch_posts, flip_door

LEVEL  = "Level 1.0"
WING_R = "Wing Roof"

print("=== Fix: Back porch + garage doors ===")

# ── Delete wrong back porch roof (was at y=0→8, not connected to house)
r = _call("revit.delete_element", {"element_id": 5953183})
print(f"Deleted old BP roof: {r.get('Status')}")
# Delete old back porch posts
for pid in [5953202, 5953205, 5953207]:
    r = _call("revit.delete_element", {"element_id": pid})
    print(f"Deleted old BP post {pid}: {r.get('Status')}")

# ── New back porch: x=38→68, y=14→26 (in the H notch, connected to CB north face at y=26)
bp_roof = make_roof("BP-Roof", x0=38, y0=14, x1=68, y1=26,
    level_name=WING_R, pitch=0.083,
    shed_low_edge=0,   # low edge at y=14 (outer/north), high at y=26 (house wall)
    oh_s=False, oh_n=True, oh_w=False, oh_e=False)
print(f"New BP roof: {bp_roof}")

# Back porch posts at outer edge y=14
place_porch_posts(post_xs=[40, 53, 66], post_y=14, level=LEVEL,
    porch_depth=12, wall_height=10, shed_slopes_toward_larger_y=False)

print("✅ Back porch rebuilt at y=14→26, connected to CB north wall")

# ── Flip garage doors (un-flip the previous flip — they were wrong direction)
for did in [5953209, 5953212, 5953213]:
    r = flip_door(did)
    print(f"Re-flipped garage door {did}: ok")

print("✅ Garage doors re-flipped")
