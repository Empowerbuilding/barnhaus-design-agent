"""
fix_eda_porch.py — Move front porch to correct south side (y=54→66)
"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import _call, make_roof, create_floor, place_porch_posts

LEVEL  = "Level 1.0"
WING_R = "Wing Roof"

print("=== Fix: Move front porch to south face (y=54→66) ===")

# Delete wrong FP roof (5953166) and BP roof (5953183) — BP was placed at y=0→8 which is correct
# Delete wrong FP roof only
r = _call("revit.delete_element", {"element_id": 5953166})
print(f"Deleted wrong FP roof 5953166: {r.get('Status')}")

# Delete wrong FP floor if it was placed (it failed, so skip)
# Delete wrong FP posts (5953198, 5953200)
for pid in [5953198, 5953200]:
    r = _call("revit.delete_element", {"element_id": pid})
    print(f"Deleted wrong post {pid}: {r.get('Status')}")

# Create correct front porch roof — south face of CB, y=54→66, x=38→50
fp_roof = make_roof("FP-Roof", x0=38, y0=54, x1=50, y1=66,
    level_name=WING_R, pitch=0.083,
    shed_low_edge=2,   # low edge at north (y=54 toward house), high at y=66 outer
    oh_s=True, oh_n=False, oh_w=False, oh_e=False)
print(f"New FP roof: {fp_roof}")

# Front porch floor
create_floor(LEVEL, 0, [(38,54),(50,54),(50,66),(38,66),(38,54)])

# Front porch posts at outer edge y=66
place_porch_posts(post_xs=[39.5, 48.5], post_y=66, level=LEVEL,
    porch_depth=12, wall_height=10, shed_slopes_toward_larger_y=True)

print("✅ Front porch fixed — now on south face at y=54→66")
print("Back porch at y=0→8 (north/rear) is correct, no change needed.")
