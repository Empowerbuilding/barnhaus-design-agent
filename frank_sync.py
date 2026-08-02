#!/usr/bin/env python3
"""
frank_sync.py — Blueprint scans Revit for all trade categories needed by Frank's RFQ system,
then writes the results to Frank's Supabase takeoffs table.

Usage:
  python3 frank_sync.py <project_id>

project_id is Frank's Supabase project UUID.
"""

import sys
import json
import urllib.request
import urllib.parse

# Frank's Supabase
FRANK_URL = 'https://stlvgflkgqhtxfxuorvf.supabase.co'
FRANK_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0bHZnZmxrZ3FodHhmeHVvcnZmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTQ0MDExMCwiZXhwIjoyMDkxMDE2MTEwfQ.nZ3Fu0bw36mp1HMyiCdiuKdFJX8koU9jbuYpvj7f0WM'

FH = {
    'apikey': FRANK_KEY,
    'Authorization': f'Bearer {FRANK_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation',
}

# Categories where we also want total area (SF) in addition to instance count
AREA_CATEGORIES = {'Walls', 'Roofs', 'Floors', 'Ceilings'}

# All categories Frank needs for RFQs, mapped to trade
FRANK_CATEGORIES = [
    ('Doors',                   'Doors & Windows'),
    ('Windows',                 'Doors & Windows'),
    ('Lighting Fixtures',       'Electrical'),
    ('Electrical Fixtures',     'Electrical'),
    ('Plumbing Fixtures',       'Plumbing'),
    ('Mechanical Equipment',    'HVAC'),
    ('Casework',                'Cabinets'),
    ('Roofs',                   'Roofing'),
    ('Floors',                  'Tile & Flooring'),
    ('Ceilings',                'Drywall'),
    ('Structural Columns',      'Welder'),
    ('Structural Foundations',  'Foundation'),
    ('Specialty Equipment',     'Appliance Install'),
    ('Walls',                   'Wood Framing'),
    ('Generic Models',          'Plumbing'),
]


def frank_get(path, params=None):
    url = f'{FRANK_URL}/rest/v1/{path}'
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=FH)
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


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


def sync_takeoffs(project_id: str) -> int:
    """Scan all Frank trade categories from Revit and write to Frank's takeoffs table."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from core import revit_client as rc

    if not rc.health_check():
        print('❌ Revit bridge not reachable. Open Revit with the project loaded first.')
        sys.exit(1)

    print(f'🔍 Syncing takeoffs for project {project_id}...')

    # Clear existing bridge-sourced takeoffs for this project
    frank_delete('takeoffs', {'project_id': f'eq.{project_id}', 'source': 'eq.revit_bridge'})

    rows = []
    for category, trade in FRANK_CATEGORIES:
        print(f'  [{trade}] {category}...')
        raw = rc.call('revit.list_elements_by_category', {'category': category})
        elements = raw.get('result', {}).get('elements', []) if raw.get('success') else []

        # Count by type; also track area (SF) for area categories
        by_type = {}
        area_by_type = {}  # type_name -> total SF
        for el in elements:
            tname = el.get('type') or el.get('type_name') or el.get('name') or 'Unknown'
            by_type[tname] = by_type.get(tname, 0) + 1

            if category in AREA_CATEGORIES:
                el_id = el.get('id')
                if el_id:
                    area_raw = rc.call('revit.get_parameter_value', {
                        'element_id': el_id,
                        'parameter_name': 'Area',
                    })
                    if area_raw.get('success'):
                        val = area_raw.get('result')
                        try:
                            area_sf = float(str(val).replace(',', '').split()[0]) if val else 0.0
                            area_by_type[tname] = area_by_type.get(tname, 0.0) + area_sf
                        except (ValueError, TypeError):
                            pass

        for type_name, count in by_type.items():
            rows.append({
                'project_id':  project_id,
                'category':    category,
                'item_type':   type_name,
                'quantity':    count,
                'description': f'{count}x {type_name} — from Revit model',
                'trade':       trade,
                'source':      'revit_bridge',
                'unit':        'EA',
                'notes':       'Extracted via Revit bridge',
            })

        # Add area SF rows for Wall/Roof/Floor/Ceiling types
        for type_name, total_sf in area_by_type.items():
            if total_sf > 0:
                rows.append({
                    'project_id':  project_id,
                    'category':    category,
                    'item_type':   f'{type_name} — Area',
                    'quantity':    round(total_sf, 1),
                    'description': f'{round(total_sf, 1)} SF of {type_name} — from Revit model',
                    'trade':       trade,
                    'source':      'revit_bridge',
                    'unit':        'SF',
                    'notes':       'Area extracted via Revit bridge',
                })

        total = len(elements)
        area_total = sum(area_by_type.values())
        area_str = f', {round(area_total, 1)} SF total' if area_total else ''
        print(f'    → {total} elements, {len(by_type)} types{area_str}')

    # Batch insert (Supabase accepts arrays)
    if rows:
        chunk_size = 50
        inserted = 0
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            frank_post('takeoffs', chunk)
            inserted += len(chunk)
        print(f'\n✅ Synced {inserted} takeoff rows to Frank\'s Supabase for project {project_id}')

    return len(rows)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 frank_sync.py <frank_project_id>')
        sys.exit(1)
    sync_takeoffs(sys.argv[1])
