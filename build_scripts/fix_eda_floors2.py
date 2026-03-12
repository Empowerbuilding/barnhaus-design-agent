"""Floors as 3 simple rectangles + porch + garage"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import create_floor
LEVEL = "Level 1.0"
# Left wing
create_floor(LEVEL, 0, [(0,8),(22,8),(22,54),(0,54)])
# Center connector (LBZ+CB+RBZ)
create_floor(LEVEL, 0, [(22,26),(84,26),(84,54),(22,54)])
# Right wing
create_floor(LEVEL, 0, [(84,8),(106,8),(106,54),(84,54)])
# Back porch (in H notch)
create_floor(LEVEL, 0, [(38,14),(68,14),(68,26),(38,26)])
# Front porch (centered on door)
create_floor(LEVEL, 0, [(47,54),(59,54),(59,66),(47,66)])
# Garage
create_floor(LEVEL, 0, [(0,54),(36,54),(36,78),(0,78)])
print("done")
