#!/usr/bin/env python3
"""
frank_sync.py — Blueprint scans Revit and writes all trade takeoffs to Frank's Supabase.

Usage:
  python3 frank_sync.py <project_id>

Extracts:
  - Instance counts (doors, windows, plumbing, electrical, HVAC, cabinets, columns, etc.)
  - Material SF: sheetrock, PBR panels, floor SF, roof SF, ceiling SF (via material quantities)
  - Wall linear footage by type
"""

import sys
import json
import urllib.request
import urllib.parse

# Frank's Supabase
# Key loaded from environment or local keys file — never hardcoded
import os as _os

FRANK_URL = 'https://stlvgflkgqhtxfxuorvf.supabase.co'

def _load_frank_key():
    # 1. Environment variable (preferred)
    if _os.environ.get('FRANK_SUPABASE_KEY'):
        return _os.environ['FRANK_SUPABASE_KEY']
    # 2. Local keys file (Blueprint workspace)
    _keys_paths = [
        '/home/node/.openclaw/workspace/.frank_keys.json',
        '/home/node/.openclaw/workspace/barnhaus-design-agent/.frank_keys.json',
    ]
    for _kp in _keys_paths:
        if _os.path.exists(_kp):
            with open(_kp) as _f:
                return json.load(_f)['frank_supabase_key']
    raise RuntimeError('FRANK_SUPABASE_KEY not set and no .frank_keys.json found. See Blueprint TOOLS.md.')

FRANK_KEY = _load_frank_key()

FH = {
    'apikey': FRANK_KEY,
    'Authorization': f'Bearer {FRANK_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation',
}

# Thickness constants for SF conversion
THICKNESS = {
    'floor':   0.333,   # 4" slab
    'roof':    0.5,     # 6" avg assembly
    'ceiling': 0.052,   # 5/8" drywall
    'gypsum':  0.042,   # 1/2" drywall
    'stucco':  0.073,   # 7/8" stucco
}

# Count-only categories (instances, not area)
COUNT_CATEGORIES = [
    ('Doors',                 'Doors & Windows'),
    ('Windows',               'Doors & Windows'),
    ('Lighting Fixtures',     'Electrical'),
    ('Electrical Fixtures',   'Electrical'),
    ('Plumbing Fixtures',     'Plumbing'),
    ('Mechanical Equipment',  'HVAC'),
    ('Structural Columns',    'Welder'),
    ('Specialty Equipment',   'Appliance Install'),
    ('Generic Models',        'Plumbing'),
    ('Stairs',                'Custom Stairs'),
]

# Linear-footage categories (sum length_ft per element)
LF_CATEGORIES = [
    ('Railings',  'Metal Railing'),
    ('Gutters',   'Gutters / Downspouts'),
    ('Fascia',    'Fascia / Trim'),
]

# Keywords to classify wall/roof materials
GYPSUM_KEYS   = ['gypsum', 'drywall', 'gwb', 'gyp board', 'sheetrock']
PBR_KEYS      = ['pbr', 'metal panel', 'standing seam', 'corrugated metal', 'steel panel', 'metal roof', 'galvalume']
STUCCO_KEYS   = ['stucco', 'plaster', 'eifs', 'dryvit']
CONCRETE_KEYS = ['concrete', 'cmu', 'masonry', 'block']


def frank_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f'{FRANK_URL}/rest/v1/{path}', data=body, headers=FH)
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def frank_delete(path, params):
    url = f'{FRANK_URL}/rest/v1/{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={**FH, 'Prefer': 'return=minimal'})
    req.get_method = lambda: 'DELETE'
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f'  DELETE warning: {e}')


def _call(rc, tool, payload):
    r = rc.call(tool, payload)
    if not r.get('success'):
        return None
    return r.get('result', {})


def _list_elements(rc, category):
    r = _call(rc, 'revit.list_elements_by_category', {'category': category})
    if r is None:
        return []
    return r.get('elements', r.get('rooms', r.get('items', [])))


def _material_quantities(rc, category):
    """Returns {material_name: volume_cf}"""
    r = _call(rc, 'revit.calculate_material_quantities', {'category': category})
    if r is None:
        return {}
    return {t['material']: t['volume_cf'] for t in r.get('totals', [])}


def _classify_material(mat_name):
    m = mat_name.lower()
    if any(k in m for k in GYPSUM_KEYS):   return 'gypsum'
    if any(k in m for k in PBR_KEYS):      return 'pbr'
    if any(k in m for k in STUCCO_KEYS):   return 'stucco'
    if any(k in m for k in CONCRETE_KEYS): return 'concrete'
    return 'other'


def sync_takeoffs(project_id: str) -> int:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from core import revit_client as rc

    if not rc.health_check():
        print('❌ Revit bridge not reachable.')
        sys.exit(1)

    doc_info = rc.call('revit.health', {})
    doc_name = doc_info.get('result', {}).get('active_document', 'unknown') if doc_info.get('success') else 'unknown'
    print(f'📋 Syncing takeoffs for project {project_id} from "{doc_name}"...\n')

    # ── PRE-SYNC SANITY CHECK ──────────────────────────────────────────────
    print('Pre-sync model health check:')
    warnings = []
    check_cats = ['Walls', 'Roofs', 'Floors', 'Doors', 'Windows', 'Rooms']
    for cat in check_cats:
        els = _list_elements(rc, cat)
        n = len(els)
        flag = ''
        if cat == 'Rooms' and n > 20:
            flag = f' ⚠️  UNUSUAL — {n} rooms likely includes phantom/separator rooms. Verify before sync.'
            warnings.append(f'Rooms: {n} (high — possible phantom rooms)')
        elif cat == 'Walls' and n < 4:
            flag = f' ⚠️  LOW — model may be empty'
            warnings.append(f'Walls: {n} (low)')
        print(f'  {cat:<20} {n:>4} elements{flag}')
    if warnings:
        print(f'\n⚠️  Warnings: {" | ".join(warnings)}')
    else:
        print('  ✅ All counts look reasonable')
    print()

    frank_delete('takeoffs', {'project_id': f'eq.{project_id}', 'source': 'eq.revit_bridge'})

    rows = []

    # ── 0. FOUNDATION SF ─────────────────────────────────────────────────
    print('  [foundation] SF from element Area parameter...')
    found_els = _list_elements(rc, 'Structural Foundations')
    found_sf_by_type = {}
    for el in found_els:
        el_id = el.get('id')
        tname = el.get('type') or el.get('type_name') or el.get('name') or 'Foundation Slab'
        sf = 0.0
        if el_id:
            area_raw = _call(rc, 'revit.get_parameter_value', {'element_id': el_id, 'parameter_name': 'Area'})
            if area_raw:
                val = area_raw.get('value')
                try:
                    sf = float(str(val).replace(',', '').split()[0]) if val else 0.0
                except (ValueError, TypeError):
                    sf = 0.0
        found_sf_by_type[tname] = found_sf_by_type.get(tname, 0.0) + sf
    found_sf_total = sum(found_sf_by_type.values())
    for tname, sf in found_sf_by_type.items():
        if sf > 0:
            rows.append({
                'project_id':  project_id, 'category': 'Structural Foundations',
                'item_type':   tname,
                'quantity':    round(sf, 0),
                'description': f'{round(sf, 0):,.0f} SF concrete slab',
                'trade':       'Foundation', 'source': 'revit_bridge',
                'unit':        'SF', 'notes': f'From {doc_name} — Area parameter',
            })
    print(f'    → {round(found_sf_total):,} SF foundation ({len(found_els)} elements)')

    # ── 1. COUNT-BASED CATEGORIES ─────────────────────────────────────────
    for category, trade in COUNT_CATEGORIES:
        print(f'  [count] {category}...')
        elements = _list_elements(rc, category)
        by_type = {}
        for el in elements:
            tname = (el.get('type') or el.get('type_name') or
                     el.get('family_name') or el.get('name') or 'Unknown')
            by_type[tname] = by_type.get(tname, 0) + 1

        for type_name, count in by_type.items():
            rows.append({
                'project_id':  project_id,
                'category':    category,
                'item_type':   type_name,
                'quantity':    count,
                'description': f'{count}x {type_name}',
                'trade':       trade,
                'source':      'revit_bridge',
                'unit':        'EA',
                'notes':       f'From {doc_name}',
            })
        print(f'    → {len(elements)} elements, {len(by_type)} types')

    # ── 1b. LINEAR-FOOTAGE CATEGORIES ────────────────────────────────────
    for category, trade in LF_CATEGORIES:
        print(f'  [LF] {category}...')
        elements = _list_elements(rc, category)
        lf_by_type = {}
        for el in elements:
            tname = el.get('type') or el.get('type_name') or el.get('name') or 'Unknown'
            lf = float(el.get('length_ft', 0) or 0)
            lf_by_type[tname] = lf_by_type.get(tname, 0) + lf
        for tname, lf in lf_by_type.items():
            rows.append({
                'project_id':  project_id,
                'category':    category,
                'item_type':   tname,
                'quantity':    round(lf, 1),
                'description': f'{round(lf, 1)} LF of {tname}',
                'trade':       trade,
                'source':      'revit_bridge',
                'unit':        'LF',
                'notes':       f'From {doc_name}',
            })
        print(f'    → {len(elements)} elements, {round(sum(lf_by_type.values()), 1)} LF total')

    # ── 2. WALLS — linear footage + material SF ──────────────────────────
    print('  [walls] Linear footage by type...')
    walls = _list_elements(rc, 'Walls')
    lf_by_type = {}
    for w in walls:
        wtype = w.get('type', w.get('wall_type', 'Unknown'))
        lf = float(w.get('length_ft', 0) or 0)
        lf_by_type[wtype] = lf_by_type.get(wtype, 0) + lf

    for wtype, lf in lf_by_type.items():
        rows.append({
            'project_id':  project_id,
            'category':    'Walls',
            'item_type':   wtype,
            'quantity':    round(lf, 1),
            'description': f'{round(lf, 1)} LF of {wtype}',
            'trade':       'Wood Framing',
            'source':      'revit_bridge',
            'unit':        'LF',
            'notes':       f'From {doc_name}',
        })
    print(f'    → {len(walls)} walls, {round(sum(lf_by_type.values()), 1)} LF total')

    print('  [walls] Material quantities (sheetrock, PBR, stucco)...')
    wall_mats = _material_quantities(rc, 'Walls')
    mat_totals = {}  # class -> {mat_name -> sf}
    for mat, vol_cf in wall_mats.items():
        cls = _classify_material(mat)
        thickness = THICKNESS.get(cls, THICKNESS['gypsum'])
        sf = vol_cf / thickness
        if cls not in mat_totals:
            mat_totals[cls] = {}
        mat_totals[cls][mat] = mat_totals[cls].get(mat, 0) + sf

    trade_map = {'gypsum': 'Drywall', 'pbr': 'Roofing', 'stucco': 'Stucco / Ext Finish', 'other': 'Wood Framing'}
    for cls, mats in mat_totals.items():
        for mat_name, sf in mats.items():
            label = {'gypsum': 'Sheetrock', 'pbr': 'PBR Metal Panel', 'stucco': 'Stucco', 'concrete': 'Concrete'}.get(cls, cls.title())
            rows.append({
                'project_id':  project_id,
                'category':    'Walls',
                'item_type':   f'{label} — {mat_name}',
                'quantity':    round(sf, 0),
                'description': f'{round(sf, 0):,.0f} SF of {mat_name}',
                'trade':       trade_map.get(cls, 'Wood Framing'),
                'source':      'revit_bridge',
                'unit':        'SF',
                'notes':       f'Material qty from {doc_name}',
            })
    total_gyp = sum(sum(v.values()) for k, v in mat_totals.items() if k == 'gypsum')
    total_pbr = sum(sum(v.values()) for k, v in mat_totals.items() if k == 'pbr')
    print(f'    → {round(total_gyp):,} SF gypsum, {round(total_pbr):,} SF PBR/metal')

    # ── 3. ROOFS ─────────────────────────────────────────────────────────
    print('  [roofs] Material quantities...')
    roof_mats = _material_quantities(rc, 'Roofs')
    for mat, vol_cf in roof_mats.items():
        cls = _classify_material(mat)
        sf = vol_cf / THICKNESS['roof']
        label = {'pbr': 'PBR Metal Panel', 'gypsum': 'Roof Sheathing/Gyp'}.get(cls, 'Roof Material')
        rows.append({
            'project_id':  project_id,
            'category':    'Roofs',
            'item_type':   f'{label} — {mat}',
            'quantity':    round(sf, 0),
            'description': f'{round(sf, 0):,.0f} SF of {mat} (roof)',
            'trade':       'Roofing',
            'source':      'revit_bridge',
            'unit':        'SF',
            'notes':       f'Material qty from {doc_name}',
        })
    print(f'    → {len(roof_mats)} roof materials')

    # ── 4. FLOORS ────────────────────────────────────────────────────────
    print('  [floors] Material quantities...')
    floor_mats = _material_quantities(rc, 'Floors')
    for mat, vol_cf in floor_mats.items():
        sf = vol_cf / THICKNESS['floor']
        rows.append({
            'project_id':  project_id,
            'category':    'Floors',
            'item_type':   f'Floor — {mat}',
            'quantity':    round(sf, 0),
            'description': f'{round(sf, 0):,.0f} SF of {mat} (floor)',
            'trade':       'Tile & Flooring',
            'source':      'revit_bridge',
            'unit':        'SF',
            'notes':       f'Material qty from {doc_name}',
        })
    print(f'    → {len(floor_mats)} floor materials')

    # ── 5. CEILINGS ──────────────────────────────────────────────────────
    print('  [ceilings] Material quantities...')
    ceiling_mats = _material_quantities(rc, 'Ceilings')
    for mat, vol_cf in ceiling_mats.items():
        sf = vol_cf / THICKNESS['ceiling']
        rows.append({
            'project_id':  project_id,
            'category':    'Ceilings',
            'item_type':   f'Ceiling — {mat}',
            'quantity':    round(sf, 0),
            'description': f'{round(sf, 0):,.0f} SF of {mat} (ceiling)',
            'trade':       'Drywall',
            'source':      'revit_bridge',
            'unit':        'SF',
            'notes':       f'Material qty from {doc_name}',
        })
    print(f'    → {len(ceiling_mats)} ceiling materials')

    # ── 6. ROOMS (area schedule) ─────────────────────────────────────────
    print('  [rooms] Area schedule...')
    rooms = _list_elements(rc, 'Rooms')
    for room in rooms:
        area = float(room.get('area_sf', 0) or 0)
        if area < 5:
            continue
        name = room.get('name', 'Room')
        rows.append({
            'project_id':  project_id,
            'category':    'Rooms',
            'item_type':   name,
            'quantity':    round(area, 0),
            'description': f'{name}: {round(area, 0):,.0f} SF',
            'trade':       'General',
            'source':      'revit_bridge',
            'unit':        'SF',
            'notes':       f'From {doc_name}',
        })
    print(f'    → {len(rooms)} rooms')

    # ── 7. CASEWORK LF (cabinets by linear footage) ────────────────────
    print('  [casework] Cabinet LF from bounding boxes...')
    casework_els = _list_elements(rc, 'Casework')
    cab_lf_by_type = {}
    for el in casework_els:
        tname = el.get('type') or el.get('type_name') or el.get('name') or 'Unknown'
        # Use bounding box width as LF proxy, fall back to length_ft
        lf = float(el.get('length_ft', 0) or el.get('width_ft', 0) or 0)
        if lf == 0:
            lf = 2.0  # default 2 LF if no geometry returned
        cab_lf_by_type[tname] = cab_lf_by_type.get(tname, 0) + lf
    for tname, lf in cab_lf_by_type.items():
        rows.append({
            'project_id':  project_id, 'category': 'Casework',
            'item_type':   f'{tname} — LF',
            'quantity':    round(lf, 1),
            'description': f'{round(lf, 1)} LF of {tname}',
            'trade':       'Cabinets', 'source': 'revit_bridge',
            'unit':        'LF', 'notes': f'From {doc_name}',
        })
    print(f'    → {len(casework_els)} casework elements, {round(sum(cab_lf_by_type.values()), 1)} LF total')

    # ── 8. COUNTERTOP SF (casework material quantities) ────────────────
    print('  [countertops] SF from casework materials...')
    counter_mats = _material_quantities(rc, 'Casework')
    counter_sf_total = 0
    for mat, vol_cf in counter_mats.items():
        mat_lower = mat.lower()
        if any(k in mat_lower for k in ['counter', 'granite', 'quartz', 'marble', 'stone top', 'laminate']):
            sf = vol_cf / (1.5 / 12)  # ~1.5" countertop thickness
            counter_sf_total += sf
            rows.append({
                'project_id':  project_id, 'category': 'Countertops',
                'item_type':   f'Countertop — {mat}',
                'quantity':    round(sf, 0),
                'description': f'{round(sf, 0):,.0f} SF of {mat}',
                'trade':       'Countertops', 'source': 'revit_bridge',
                'unit':        'SF', 'notes': f'From {doc_name}',
            })
    print(f'    → {round(counter_sf_total):,} SF countertop material')

    # ── BATCH INSERT ────────────────────────────────────────────────────
    if rows:
        chunk_size = 50
        inserted = 0
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            frank_post('takeoffs', chunk)
            inserted += len(chunk)
        print(f'\n✅ Synced {inserted} takeoff rows for project {project_id}')
    else:
        print('\n⚠️ No rows to insert — check Revit model has elements.')

    return len(rows)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 frank_sync.py <frank_project_id>')
        sys.exit(1)
    sync_takeoffs(sys.argv[1])
