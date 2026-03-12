"""
build_e670353b_s3_fixtures.py — STAGE 3: Fixtures
Submission: e670353b | Mitchell Madison | H-shape | Hill Country | 4bd/3ba

Zones:
  Left Wing  (x=0→24,  y=8→50):  Master bed/bath/WIC, laundry, utility, butler pantry
  Center Bridge (x=32→60, y=14→38): Great room, kitchen, dining, powder room
  Right Wing (x=68→90, y=8→50): Hall, bed2/3/4, bath2, bath3

Rotation convention (confirmed empirically — Section 26):
  0   → faces SOUTH (-Y)
  180 → faces NORTH (+Y)
  90  → faces WEST  (-X)
  270 → faces EAST  (+X)

Origin by type (Section 26):
  Cabinets/appliances: back face → depth offset not needed (depth=0)
  Toilets: center → offset 1.25ft from wall
  Showers: center → offset 0.5ft from wall
"""

import sys, requests
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils_v2 import health_check

BASE = 'http://localhost:3000/execute'
LEVEL = 'Level 1.0'

def call(tool, payload):
    r = requests.post(BASE, json={'request_id': tool, 'tool': tool, 'payload': payload}, timeout=30)
    d = r.json()
    return d.get('Status'), d.get('Result'), d.get('Message')

if not health_check():
    print("❌ Bridge not healthy"); sys.exit(1)

def fix(family, ftype, x, y, rot, label, level=LEVEL):
    s, r, m = call('revit.place_family_instance', {
        'family_name': family, 'type_name': ftype,
        'location': {'x': x, 'y': y, 'z': 0},
        'level': level, 'rotation': rot,
    })
    eid = (r or {}).get('instance_id') or (r or {}).get('element_id')
    print(f"  {'✅' if eid else '❌'} {label}: {eid or m}")
    return eid

# Cabinet families
BASE_CAB  = 'Base Cabinet-Double Door & 1 Drawer'
UPPER_CAB = 'Upper Cabinet-Double Door'
SINK_KIT  = 'Sink Kitchen-Single'
SINK_LAV  = 'Sink Lavatory-Oval'
TOILET    = 'Toilet-Residential'
SHOWER    = 'Shower-Square'
TUB       = 'Tub-Rectangular'
FRIDGE    = 'Refrigerator'
RANGE     = 'Range'
DW        = 'Dishwasher'
WASHER    = 'Washer'
DRYER     = 'Dryer'
VANITY    = 'Vanity'

# ══════════════════════════════════════
print("\n══ KITCHEN (Center Bridge, x=32→60, y=28→38) ══")
# North wall y=38: sink centered, upper cabs flanking
fix(SINK_KIT,  'Single',  46,   37.1, 0,   'kit-sink')           # faces south, back to north wall
fix(BASE_CAB,  '36"',     40,   37.1, 0,   'kit-base-W')
fix(BASE_CAB,  '36"',     52,   37.1, 0,   'kit-base-E')
fix(UPPER_CAB, '36"',     40,   37.5, 0,   'kit-upper-W')
fix(UPPER_CAB, '36"',     52,   37.5, 0,   'kit-upper-E')

# Island — center of kitchen zone
fix(BASE_CAB,  '36"',     43,   33,   0,   'kit-island-W')
fix(BASE_CAB,  '36"',     49,   33,   0,   'kit-island-E')

# East wall: range + DW
fix(RANGE,     '30"',     58.1, 33,   270, 'kit-range')           # faces east, back to east wall
fix(DW,        '24"',     58.1, 30,   270, 'kit-DW')

# Fridge — south wall corner near pantry
fix(FRIDGE,    'Standard',34,   28.9, 180, 'kit-fridge')          # faces north, back to south wall

print("\n══ DINING (Center Bridge, x=32→54, y=14→28) ══")
# Dining table not a Revit fixture — skip, room will be labeled

print("\n══ GREAT ROOM (Center Bridge, x=54→60, y=14→38) ══")
# No fixtures in great room — open floor plan

print("\n══ MASTER BED (Left Wing, x=0→24, y=30→50) ══")
# Bed centered against east interior wall (x=24 zone wall)
# No bed family — skip, room label handles it

print("\n══ MASTER BATH (Left Wing, x=0→14, y=18→30) ══")
# West wall — dual vanity
fix(VANITY,    '60"',     1.5,  25,   270, 'mbath-vanity')        # faces east, back to west wall
# Freestanding tub — center of bath
fix(TUB,       '60"',     7,    24,   0,   'mbath-tub')
# Walk-in shower — NE corner
fix(SHOWER,    '36"',     12,   28.5, 0,   'mbath-shower')
# Toilet — south wall
fix(TOILET,    'Standard',7,    18.9, 180, 'mbath-toilet')        # faces north

print("\n══ WIC (Left Wing, x=14→24, y=18→30) ══")
# Built-in rods/shelves not in Revit families — skip

print("\n══ LAUNDRY (Left Wing, x=0→12, y=8→18) ══")
fix(WASHER,    'Standard',2,    16.9, 0,   'laundry-washer')      # back to north wall (y=18 int wall)
fix(DRYER,     'Standard',5,    16.9, 0,   'laundry-dryer')

print("\n══ BATH 2 (Right Wing, x=80→90, y=18→28) ══")
fix(VANITY,    '48"',     88.5, 24,   90,  'bath2-vanity')        # back to east wall
fix(SHOWER,    '36"',     88.5, 20,   90,  'bath2-shower')
fix(TOILET,    'Standard',84,   18.9, 180, 'bath2-toilet')        # faces north, south wall

print("\n══ BATH 3 (Right Wing, x=68→76, y=8→20) ══")
fix(VANITY,    '36"',     72,   9.0,  0,   'bath3-vanity')        # back to south wall
fix(TOILET,    'Standard',74,   9.0,  0,   'bath3-toilet')
fix(SHOWER,    '36"',     69.5, 15,   270, 'bath3-shower')        # back to west wall

print("\n✅ STAGE 3 COMPLETE")
print("→ Check: kitchen island, range wall, master bath layout, secondary baths")
print("→ Say 'stage 4' for room labels")
