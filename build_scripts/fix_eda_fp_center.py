"""Center front porch on front door (x=53) — porch width 12ft → x=47→59"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import _call, make_roof, create_floor, place_porch_posts

LEVEL  = "Level 1.0"
WING_R = "Wing Roof"

# Delete old FP roof (5953217) and posts (5953232, 5953235) and floor (5953358)
for eid in [5953217, 5953232, 5953235, 5953358]:
    r = _call("revit.delete_element", {"element_id": eid})
    print(f"Deleted {eid}: {r.get('Status')}")

# New porch centered on x=53: x=47→59, y=54→66
fp_roof = make_roof("FP-Roof", x0=47, y0=54, x1=59, y1=66,
    level_name=WING_R, pitch=0.083, shed_low_edge=2,
    oh_s=True, oh_n=False, oh_w=False, oh_e=False)
create_floor(LEVEL, 0, [(47,54),(59,54),(59,66),(47,66)])
place_porch_posts(post_xs=[48.5, 57.5], post_y=66, level=LEVEL,
    porch_depth=12, wall_height=10, shed_slopes_toward_larger_y=True)
print("✅ Front porch centered on front door (x=47→59)")
