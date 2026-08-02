# -*- coding: utf-8 -*-
"""
Barnhaus House Builder - 1700 SF Modern Flat
Walls, doors, windows, floor slab, flat roof, bathroom/kitchen fixtures
"""
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *
from Autodesk.Revit.UI import TaskDialog
import Autodesk.Revit.DB.Structure as Structure
from System.Collections.Generic import List

doc = __revit__.ActiveUIDocument.Document

# Heights
CEILING   = 10.0
PARAPET   = 1.0
WALL_H    = CEILING + PARAPET  # 11 ft exterior
INT_H     = CEILING            # 10 ft interior
SLAB_T    = 0.5                # 6" slab

# Layout (all in feet):
# Garage:    x(-24 -> 0),  y(0 -> 24)
# House:     x(0   -> 60), y(0 -> 30)
#   Bed wing:   x(0->20)
#     Bed2:     x(0->12),  y(0->15)
#     Bed3:     x(0->12),  y(15->30)
#     Bath:     x(12->20), y(0->12)
#     Laundry:  x(12->20), y(12->22)
#   Living:     x(20->44), y(0->30)  open plan
#   Master:     x(44->60)
#     M.Closet: x(44->60), y(0->4)
#     M.Bath:   x(44->60), y(4->13)
#     M.Bed:    x(44->60), y(13->30)

EXTERIOR_WALLS = [
    (-24,  0,  60,  0),   # front full
    (  0, 30,  60, 30),   # back house
    ( 60,  0,  60, 30),   # right
    (  0, 24,   0, 30),   # left house above garage
    (-24,  0, -24, 24),   # garage left
    (-24, 24,   0, 24),   # garage back
]

INTERIOR_WALLS = [
    (20,  0, 20, 30),   # bed wing / living
    (44,  0, 44, 30),   # living / master
    ( 0, 15, 12, 15),   # bed2 / bed3
    (12,  0, 12, 22),   # bed / bath
    (12, 12, 20, 12),   # bath / laundry
    (12, 22, 20, 22),   # laundry top
    (44,  4, 60,  4),   # closet / bath
    (44, 13, 60, 13),   # bath / master bed
]

# Doors: (exact XY on wall, facing wall direction, label)
# XY = center of door opening on the wall line
# For walls running along X axis: door at (x, y) on that wall
# For walls running along Y axis: door at (x, y) on that wall
DOOR_PLACEMENTS = [
    # Front entry - center of great room front wall
    (32.0,  0.0, 'Front Entry'),
    # Bed2 door - on bedroom/bath wall
    (12.0,  7.5, 'Bed 2'),
    # Bed3 door - on bedroom/bath wall
    (12.0, 21.0, 'Bed 3'),
    # Bath door - on bath/hall wall
    (16.0,  0.0, 'Bath'),
    # Laundry door
    (16.0, 12.0, 'Laundry'),
    # Master bed door - on living/master wall
    (44.0, 21.0, 'Master Bed'),
    # Master bath door
    (44.0,  8.5, 'Master Bath'),
    # Master closet door
    (44.0,  2.0, 'Master Closet'),
    # Garage door openings (large - will place as openings)
    (-18.0, 0.0, 'Garage Bay 1'),
    ( -6.0, 0.0, 'Garage Bay 2'),
]

# Windows: (cx, cy, wall_normal: 'N'/'S'/'E'/'W', width, sill_h)
WINDOW_PLACEMENTS = [
    # Back wall - great room glass wall
    (26.0, 30.0, 'N', 8.0, 1.0),
    (36.0, 30.0, 'N', 8.0, 1.0),
    # Back wall - master bedroom
    (52.0, 30.0, 'N', 6.0, 2.5),
    # Front - bed 2
    ( 5.0,  0.0, 'S', 3.0, 3.0),
    # Front - bed 3
    ( 5.0, 30.0, 'S', 3.0, 3.0),
    # Right - master
    (60.0, 21.0, 'W', 4.0, 2.5),
    # Left - bed 2 side
    ( 0.0,  7.0, 'E', 3.0, 3.0),
]

# Fixture placements: (category_name, family_fragment, x, y, rotation_degrees)
# Rotation: 0=facing north, 90=facing east, 180=facing south, 270=facing west
# Rooms: (name, number, center_x, center_y)
# Center point must be inside the enclosed room boundary
ROOMS = [
    ('Bedroom 2',     '101',  6.0,  7.5),
    ('Bedroom 3',     '102',  6.0, 22.5),
    ('Bath',          '103', 16.0,  6.0),
    ('Laundry',       '104', 16.0, 17.0),
    ('Great Room',    '105', 32.0, 15.0),
    ('Master Bed',    '106', 52.0, 21.5),
    ('Master Bath',   '107', 52.0,  8.5),
    ('Master Closet', '108', 52.0,  2.0),
    ('Garage',        '109',-12.0, 12.0),
]

FIXTURES = [
    # Shared Bath (x12-20, y0-12)
    ('Plumbing Fixtures', 'toilet',   14.0,  2.5, 0.0),
    ('Plumbing Fixtures', 'sink',     18.0,  2.5, 0.0),
    ('Plumbing Fixtures', 'tub',      16.0,  9.0, 0.0),
    # Master Bath (x44-60, y4-13)
    ('Plumbing Fixtures', 'toilet',   46.0,  5.5, 0.0),
    ('Plumbing Fixtures', 'sink',     46.0,  7.5, 0.0),
    ('Plumbing Fixtures', 'sink',     46.0,  9.5, 0.0),
    ('Plumbing Fixtures', 'shower',   55.0,  5.5, 0.0),
    ('Plumbing Fixtures', 'tub',      55.0, 10.5, 0.0),
    # Kitchen sink only (appliances need to be loaded separately)
    ('Plumbing Fixtures', 'sink',     36.0, 28.5, 180.0),
]


def get_level(name="Level 1.0"):
    for l in FilteredElementCollector(doc).OfClass(Level).ToElements():
        try:
            if l.Name == name: return l
        except: pass
    levels = list(FilteredElementCollector(doc).OfClass(Level).ToElements())
    return levels[0] if levels else None

def get_wall_type(fragment):
    types = list(FilteredElementCollector(doc).OfClass(WallType).ToElements())
    for t in types:
        try:
            if fragment.lower() in t.Name.lower(): return t
        except: pass
    return types[0] if types else None

def get_floor_type():
    types = list(FilteredElementCollector(doc).OfClass(FloorType).ToElements())
    return types[0] if types else None

def get_roof_type():
    types = list(FilteredElementCollector(doc).OfClass(RoofType).ToElements())
    return types[0] if types else None

def get_symbol(bic, fragment):
    col = (FilteredElementCollector(doc)
           .OfClass(FamilySymbol)
           .OfCategory(bic)
           .ToElements())
    for s in col:
        try:
            if fragment.lower() in s.Name.lower(): return s
            if fragment.lower() in s.Family.Name.lower(): return s
        except: pass
    elems = list(col)
    return elems[0] if elems else None

def make_wall(x1, y1, x2, y2, level, height, wtype):
    line = Line.CreateBound(XYZ(x1, y1, 0), XYZ(x2, y2, 0))
    return Wall.Create(doc, line, wtype.Id, level.Id, height, 0, False, False)

def place_door_at(x, y, level, door_sym, host_wall):
    if not door_sym or not host_wall: return None
    try:
        if not door_sym.IsActive:
            door_sym.Activate()
            doc.Regenerate()
        return doc.Create.NewFamilyInstance(
            XYZ(x, y, 0), door_sym, host_wall, level,
            Structure.StructuralType.NonStructural
        )
    except: return None

def place_window_at(x, y, sill_h, level, win_sym, host_wall):
    if not win_sym or not host_wall: return None
    try:
        if not win_sym.IsActive:
            win_sym.Activate()
            doc.Regenerate()
        inst = doc.Create.NewFamilyInstance(
            XYZ(x, y, 0), win_sym, host_wall, level,
            Structure.StructuralType.NonStructural
        )
        p = inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
        if p: p.Set(sill_h)
        return inst
    except: return None

def find_wall_at_point(walls, x, y, tol=2.0):
    """Find the wall whose line passes closest to point (x,y)"""
    best_wall = None
    best_dist = 999
    for w in walls:
        try:
            c = w.Location.Curve
            pt = XYZ(x, y, 0)
            result = c.Project(pt)
            if result and result.Distance < best_dist:
                best_dist = result.Distance
                best_wall = w
        except: pass
    return best_wall if best_dist < tol else None

def make_floor_slab(level, pts):
    floor_type = get_floor_type()
    if not floor_type: return None
    try:
        # Revit 2022+ API: Floor.Create with CurveLoop
        loop = CurveLoop()
        for i in range(len(pts)):
            p1 = XYZ(pts[i][0],   pts[i][1],   0)
            p2 = XYZ(pts[(i+1) % len(pts)][0], pts[(i+1) % len(pts)][1], 0)
            loop.Append(Line.CreateBound(p1, p2))
        loops = List[CurveLoop]([loop])
        return Floor.Create(doc, loops, floor_type.Id, level.Id)
    except Exception as e:
        try:
            # Fallback: old API
            curves = CurveArray()
            for i in range(len(pts)):
                p1 = XYZ(pts[i][0],   pts[i][1],   0)
                p2 = XYZ(pts[(i+1) % len(pts)][0], pts[(i+1) % len(pts)][1], 0)
                curves.Append(Line.CreateBound(p1, p2))
            return doc.Create.NewFloor(curves, floor_type, level, False)
        except: return None

def make_flat_roof(level, pts, height):
    roof_type = get_roof_type()
    if not roof_type: return None
    try:
        # Use extrusion approach - more reliable than FootPrint
        curves = CurveArray()
        for i in range(len(pts)):
            p1 = XYZ(pts[i][0],   pts[i][1],   height)
            p2 = XYZ(pts[(i+1) % len(pts)][0], pts[(i+1) % len(pts)][1], height)
            curves.Append(Line.CreateBound(p1, p2))
        sketch_plane = SketchPlane.Create(
            doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, height))
        )
        mc_arr = ModelCurveArray()
        mc_arr_arr = ModelCurveArrArray()
        for i in range(curves.Size):
            mc = doc.Create.NewModelCurve(curves.get_Item(i), sketch_plane)
            mc_arr.Append(mc)
        mc_arr_arr.Append(mc_arr)
        slope_arrows = ModelCurveArrArray()
        roof = doc.Create.NewFootPrintRoof(mc_arr_arr, level, roof_type, slope_arrows)
        if roof:
            for sid in roof.GetSlopes():
                roof.SetSlope(sid, 0.5 / 12.0)
        return roof
    except: return None


def get_floor_plan_view(level):
    """Get the floor plan view associated with a level."""
    views = FilteredElementCollector(doc).OfClass(ViewPlan).ToElements()
    for v in views:
        try:
            if v.ViewType == ViewType.FloorPlan and v.GenLevel.Id == level.Id:
                return v
        except: pass
    return None

def place_rooms(level):
    """Place rooms using the correct two-step API pattern so area is non-zero."""
    placed = 0
    # Get the last phase (rooms must be associated with a phase)
    phases = doc.Phases
    phase = phases.get_Item(phases.Size - 1)

    # Get floor plan view for this level (needed for room tags)
    plan_view = get_floor_plan_view(level)

    for name, number, cx, cy in ROOMS:
        try:
            # Step 1: create unplaced room attached to phase
            unplaced = doc.Create.NewRoom(phase)
            # Step 2: place it at the UV point — room is now in the model
            room = doc.Create.NewRoom(unplaced, UV(cx, cy))

            # Now parameters are writable — set upper limit + offset
            upper_param = room.get_Parameter(BuiltInParameter.ROOM_UPPER_LEVEL)
            if upper_param and not upper_param.IsReadOnly:
                upper_param.Set(level.Id)

            room.LimitOffset = CEILING   # 10 ft
            room.BaseOffset  = 0.0
            room.Name   = name
            room.Number = number

            # Place room tag in floor plan view
            if plan_view:
                try:
                    doc.Create.NewRoomTag(
                        LinkElementId(room.Id),
                        UV(cx, cy),
                        plan_view.Id
                    )
                except: pass  # tag failure doesn't break the room

            placed += 1
        except: pass

    return placed


def build():
    t = Transaction(doc, 'Barnhaus Build House 1700SF')
    t.Start()
    try:
        level    = get_level("Level 1.0")
        ext_type = get_wall_type('exterior') or get_wall_type('generic')
        int_type = get_wall_type('interior') or get_wall_type('partition') or ext_type
        door_sym = get_symbol(BuiltInCategory.OST_Doors, 'single')
        win_sym  = (get_symbol(BuiltInCategory.OST_Windows, 'fixed') or
                    get_symbol(BuiltInCategory.OST_Windows, 'casement') or
                    get_symbol(BuiltInCategory.OST_Windows, ''))

        if not level: raise Exception("No levels found")

        # Build walls
        ext_walls = [make_wall(c[0],c[1],c[2],c[3], level, WALL_H, ext_type) for c in EXTERIOR_WALLS]
        int_walls = [make_wall(c[0],c[1],c[2],c[3], level, INT_H,  int_type) for c in INTERIOR_WALLS]
        all_walls = ext_walls + int_walls

        # Floor slab - L-shaped footprint
        slab_pts = [(-24,0),(60,0),(60,30),(0,30),(0,24),(-24,24)]
        slab = make_floor_slab(level, slab_pts)

        # Flat roof
        roof_pts = [(-24,0),(60,0),(60,30),(0,30),(0,24),(-24,24)]
        roof = make_flat_roof(level, roof_pts, WALL_H)

        # Doors
        doors_placed = 0
        if door_sym:
            for dp in DOOR_PLACEMENTS:
                wall = find_wall_at_point(all_walls, dp[0], dp[1])
                if wall:
                    inst = place_door_at(dp[0], dp[1], level, door_sym, wall)
                    if inst: doors_placed += 1

        # Windows
        windows_placed = 0
        if win_sym:
            for wp in WINDOW_PLACEMENTS:
                wall = find_wall_at_point(ext_walls, wp[0], wp[1])
                if wall:
                    inst = place_window_at(wp[0], wp[1], wp[4], level, win_sym, wall)
                    if inst: windows_placed += 1

        # Rooms
        rooms_placed = place_rooms(level)

        # Fixtures
        fixtures_placed = 0
        bic_map = {
            'Plumbing Fixtures':    BuiltInCategory.OST_PlumbingFixtures,
        }
        for fx in FIXTURES:
            bic = bic_map.get(fx[0])
            if not bic: continue
            sym = get_symbol(bic, fx[1])
            if sym:
                try:
                    if not sym.IsActive:
                        sym.Activate()
                        doc.Regenerate()
                    inst = doc.Create.NewFamilyInstance(
                        XYZ(fx[2], fx[3], 0), sym, level,
                        Structure.StructuralType.NonStructural
                    )
                    if fx[4] != 0:
                        axis = Line.CreateBound(XYZ(fx[2],fx[3],0), XYZ(fx[2],fx[3],1))
                        ElementTransformUtils.RotateElement(
                            doc, inst.Id, axis,
                            fx[4] * 3.14159265 / 180.0
                        )
                    fixtures_placed += 1
                except: pass

        t.Commit()

        msg  = "House built!\n\n"
        msg += "Walls: " + str(len(ext_walls)) + " ext + " + str(len(int_walls)) + " int\n"
        msg += "Floor slab: " + ("Yes" if slab else "Failed") + "\n"
        msg += "Flat roof:  " + ("Yes" if roof else "Failed") + "\n"
        msg += "Doors:   " + str(doors_placed) + " / " + str(len(DOOR_PLACEMENTS)) + "\n"
        msg += "Windows: " + str(windows_placed) + " / " + str(len(WINDOW_PLACEMENTS)) + "\n"
        msg += "Rooms:   " + str(rooms_placed) + " / " + str(len(ROOMS)) + "\n"
        msg += "Fixtures:" + str(fixtures_placed) + " / " + str(len(FIXTURES)) + "\n\n"
        msg += "Total living: ~1,736 SF"
        TaskDialog.Show("Barnhaus - Build House", msg)

    except Exception as e:
        t.RollBack()
        TaskDialog.Show("Barnhaus - Build House ERROR", str(e))

build()
