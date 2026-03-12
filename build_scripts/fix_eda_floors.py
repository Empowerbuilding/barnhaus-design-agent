"""fix_eda_floors.py — Correct H-shape floors"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_floor

LEVEL = "Level 1.0"

print("=== Placing floors ===")

# Main H polygon — simple, no repeated vertices, no self-intersections
# LW(x=0→22) + connection bar(x=22→84,y=26→54) + RW(x=84→106)
h_poly = [
    (0,8),(22,8),(22,26),(84,26),(84,8),(106,8),
    (106,54),(0,54),(0,8)
]
create_floor(LEVEL, 0, h_poly)

# Back porch — in H notch, x=38→68, y=14→26
create_floor(LEVEL, 0, [(38,14),(68,14),(68,26),(38,26),(38,14)])

# Front porch — x=38→50, y=54→66
create_floor(LEVEL, 0, [(38,54),(50,54),(50,66),(38,66),(38,54)])

# Garage — x=0→36, y=54→78
create_floor(LEVEL, 0, [(0,54),(36,54),(36,78),(0,78),(0,54)])

print("=== Done ===")
