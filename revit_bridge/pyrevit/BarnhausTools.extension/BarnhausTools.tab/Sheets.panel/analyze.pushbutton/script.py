# -*- coding: utf-8 -*-
"""
Barnhaus Analyze - exports model data + floor plan image to Supabase for AI analysis.
"""

import json
import os
import urllib2
import urllib
import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import (
    FilteredElementCollector, ViewSheet, ViewPlan, View, Level,
    BuiltInCategory, BuiltInParameter, Wall, FamilyInstance, FamilySymbol,
    WallType, FloorType, RoofType,
    ImageExportOptions, ImageFileType, ImageResolution, ExportRange,
    ElementId
)
from Autodesk.Revit.UI import TaskDialog

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

SUPABASE_URL = "https://hbfjdfxephlczkfgpceg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiZmpkZnhlcGhsY3prZmdwY2VnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTMzNzcxMCwiZXhwIjoyMDU0OTEzNzEwfQ.weXk7CqDqR8XkEpi4kaI_GmHWlkqh6snOMQm-hk48RM"
EXPORT_DIR   = r"C:\Users\mitch\AppData\Roaming\BarnhausAI"

if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)


def sb_post(path, data):
    url = SUPABASE_URL + "/rest/v1/" + path
    req = urllib2.Request(url, json.dumps(data))
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        return json.loads(urllib2.urlopen(req, timeout=15).read())
    except Exception as e:
        return {"error": str(e)}


def sb_patch(path, data, params=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    if params:
        url += "?" + urllib.urlencode(params)
    req = urllib2.Request(url, json.dumps(data))
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    req.get_method = lambda: "PATCH"
    try:
        return json.loads(urllib2.urlopen(req, timeout=15).read())
    except Exception as e:
        return {"error": str(e)}


# --- Collect model data ---

# Sheets
sheets = sorted([{"number": s.SheetNumber, "name": s.Name}
                 for s in FilteredElementCollector(doc).OfClass(ViewSheet)],
                key=lambda x: x["number"])

# Levels
levels = [{"name": l.Name, "elevation": round(l.Elevation, 2)}
          for l in FilteredElementCollector(doc).OfClass(Level)]

# Walls with full geometry
walls = []
for w in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType():
    try:
        c  = w.Location.Curve
        s  = c.GetEndPoint(0)
        e  = c.GetEndPoint(1)
        fn = w.WallType.get_Parameter(BuiltInParameter.FUNCTION_PARAM)
        walls.append({
            "id":       str(w.Id.IntegerValue),
            "type":     w.WallType.Name,
            "function": fn.AsInteger() if fn else 0,
            "length":   round(s.DistanceTo(e), 2),
            "start":    [round(s.X, 2), round(s.Y, 2)],
            "end":      [round(e.X, 2), round(e.Y, 2)]
        })
    except: pass

# Rooms
rooms = []
for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
    try:
        loc = r.Location
        pt  = loc.Point if loc else None
        rooms.append({
            "name":   r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString(),
            "number": r.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString(),
            "area":   round(r.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble(), 1),
            "center": [round(pt.X, 2), round(pt.Y, 2)] if pt else None
        })
    except: pass

# Doors
doors = []
for d in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsNotElementType():
    try:
        pt = d.Location.Point
        doors.append({
            "id":   str(d.Id.IntegerValue),
            "type": d.Name,
            "pos":  [round(pt.X, 2), round(pt.Y, 2)]
        })
    except: pass

# Windows
windows = []
for w in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsNotElementType():
    try:
        pt = w.Location.Point
        windows.append({
            "id":   str(w.Id.IntegerValue),
            "type": w.Name,
            "pos":  [round(pt.X, 2), round(pt.Y, 2)]
        })
    except: pass

# Views (floor plans only)
views = []
for v in FilteredElementCollector(doc).OfClass(View):
    if not v.IsTemplate and isinstance(v, ViewPlan):
        views.append({"name": v.Name, "id": str(v.Id.IntegerValue)})

# Families loaded in project
families = {}
for sym in FilteredElementCollector(doc).OfClass(FamilySymbol).ToElements():
    try:
        cat = sym.Category.Name if sym.Category else "Unknown"
        fam = sym.Family.Name
        name = sym.Name
        if cat not in families:
            families[cat] = []
        entry = fam + " : " + name
        if entry not in families[cat]:
            families[cat].append(entry)
    except: pass

# Also grab wall types, floor types, roof types
wall_types, floor_types, roof_types = [], [], []
for t in FilteredElementCollector(doc).OfClass(WallType).ToElements():
    try: wall_types.append(t.Name)
    except: pass
for t in FilteredElementCollector(doc).OfClass(FloorType).ToElements():
    try: floor_types.append(t.Name)
    except: pass
for t in FilteredElementCollector(doc).OfClass(RoofType).ToElements():
    try: roof_types.append(t.Name)
    except: pass

model_data = {
    "project":  doc.Title,
    "sheets":   sheets,
    "levels":   levels,
    "walls":    walls,
    "rooms":    rooms,
    "doors":    doors,
    "windows":  windows,
    "views":    views,
    "families":    families,
    "wall_types":  wall_types,
    "floor_types": floor_types,
    "roof_types":  roof_types
}

# --- Export floor plan images ---
exported_files = []
floor_plan_views = [v for v in FilteredElementCollector(doc).OfClass(View)
                    if not v.IsTemplate and isinstance(v, ViewPlan)
                    and "column" not in v.Name.lower()
                    and "ceiling" not in v.Name.lower()
                    and "engineering" not in v.Name.lower()]

for view in floor_plan_views[:3]:  # export up to 3 floor plan views
    try:
        out_name = "analyze_" + view.Name.replace(" ", "_").replace("/", "_")
        opts = ImageExportOptions()
        opts.ExportRange = ExportRange.SetOfViews
        opts.SetViewsAndSheets([view.Id])
        opts.ImageResolution = ImageResolution.DPI_150
        opts.FilePath = os.path.join(EXPORT_DIR, out_name)
        opts.HLRandWFViewsFileType = ImageFileType.PNG
        opts.ShadowViewsFileType   = ImageFileType.PNG
        doc.ExportImage(opts)
        # Find actual exported file
        for f in os.listdir(EXPORT_DIR):
            if f.startswith(out_name) and f.endswith(".png"):
                exported_files.append(os.path.join(EXPORT_DIR, f))
                break
    except: pass

# --- Post to Supabase ---
# Clear old state and post new
try:
    # Delete old state rows
    url = SUPABASE_URL + "/rest/v1/revit_state"
    req = urllib2.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    req.get_method = lambda: "DELETE"
    urllib2.urlopen(req, timeout=8)
except: pass

result = sb_post("revit_state", {
    "project_name": doc.Title,
    "model_data":   model_data
})

# --- Show result ---
msg  = "Analysis Complete!\n\n"
msg += "Project: " + doc.Title + "\n"
msg += "Sheets: "  + str(len(sheets))  + "\n"
msg += "Walls: "   + str(len(walls))   + "\n"
msg += "Rooms: "   + str(len(rooms))   + "\n"
msg += "Doors: "   + str(len(doors))   + "\n"
msg += "Windows: " + str(len(windows)) + "\n"
msg += "Floor plan images exported: " + str(len(exported_files)) + "\n\n"
msg += "AI agent can now analyze your model."

TaskDialog.Show("Barnhaus - Analyze", msg)
