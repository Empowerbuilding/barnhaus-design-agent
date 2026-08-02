"""
Barnhaus AI Bridge - Windows service script
Run this once: python barnhaus_bridge.py
It polls Supabase for commands and executes them in the open Revit model via pyRevit CLI.
"""

import time
import json
import sys
import os
import subprocess
import urllib.request
import urllib.parse

SUPABASE_URL = "https://hbfjdfxephlczkfgpceg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiZmpkZnhlcGhsY3prZmdwY2VnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTMzNzcxMCwiZXhwIjoyMDU0OTEzNzEwfQ.weXk7CqDqR8XkEpi4kaI_GmHWlkqh6snOMQm-hk48RM"
PYREVIT_CLI  = r"C:\Users\mitch\AppData\Roaming\pyRevit-Master\bin\pyrevit.exe"
SCRIPTS_DIR  = r"C:\Users\mitch\AppData\Roaming\BarnhausAI"
POLL_INTERVAL = 3  # seconds

os.makedirs(SCRIPTS_DIR, exist_ok=True)


def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def sb_get(path, params=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=sb_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        print("GET error:", e)
        return None


def sb_patch(path, data, params=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=sb_headers(), method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        print("PATCH error:", e)
        return None


def sb_post(path, data):
    url = SUPABASE_URL + "/rest/v1/" + path
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=sb_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        print("POST error:", e)
        return None


def mark(cmd_id, status, result=None, error=None):
    data = {"status": status}
    if result is not None: data["result"] = result
    if error  is not None: data["error"]  = str(error)
    sb_patch("revit_commands", data, {"id": "eq." + cmd_id})


def write_script(cmd_type, params, cmd_id):
    """Write a temporary pyRevit script for this command and return its path."""

    script_body = '''# -*- coding: utf-8 -*-
import json, urllib2, urllib, clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog

SUPABASE_URL = "{supabase_url}"
SUPABASE_KEY = "{supabase_key}"
CMD_ID = "{cmd_id}"
PARAMS = {params_json}

def sb_patch(path, data, qp=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    if qp: url += "?" + urllib.urlencode(qp)
    req = urllib2.Request(url, json.dumps(data))
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    req.get_method = lambda: "PATCH"
    try: urllib2.urlopen(req, timeout=8)
    except: pass

def mark(status, result=None, error=None):
    data = {{"status": status}}
    if result is not None: data["result"] = result
    if error  is not None: data["error"]  = str(error)
    sb_patch("revit_commands", data, {{"id": "eq." + CMD_ID}})

doc = __revit__.ActiveUIDocument.Document

'''.format(
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_KEY,
        cmd_id=cmd_id,
        params_json=json.dumps(params)
    )

    # Append command-specific logic
    if cmd_type == "get_model_info":
        script_body += '''
try:
    sheets = sorted([{"number": s.SheetNumber, "name": s.Name}
                     for s in FilteredElementCollector(doc).OfClass(ViewSheet)],
                    key=lambda x: x["number"])
    levels = [{"name": l.Name, "elevation": round(l.Elevation, 2)}
              for l in FilteredElementCollector(doc).OfClass(Level)]
    walls = []
    for w in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType():
        try:
            c = w.Location.Curve
            s = c.GetEndPoint(0)
            e = c.GetEndPoint(1)
            fn = w.WallType.get_Parameter(BuiltInParameter.FUNCTION_PARAM)
            walls.append({"id": str(w.Id.IntegerValue), "type": w.WallType.Name,
                          "function": fn.AsInteger() if fn else 0,
                          "length": round(s.DistanceTo(e), 2),
                          "start": [round(s.X,2), round(s.Y,2)],
                          "end":   [round(e.X,2), round(e.Y,2)]})
        except: pass
    rooms = []
    for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        try:
            rooms.append({"name": r.get_Parameter(BuiltInParameter.ROOM_NAME).AsString(),
                          "number": r.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString(),
                          "area": round(r.get_Parameter(BuiltInParameter.ROOM_AREA).AsDouble(), 1)})
        except: pass
    views = [{"name": v.Name, "id": str(v.Id.IntegerValue)}
             for v in FilteredElementCollector(doc).OfClass(View)
             if not v.IsTemplate and isinstance(v, ViewPlan)]
    mark("done", result={"project": doc.Title, "sheets": sheets,
                          "levels": levels, "walls": walls,
                          "rooms": rooms, "views": views})
except Exception as e:
    mark("error", error=str(e))
'''

    elif cmd_type == "export_view":
        script_body += '''
import os
try:
    view_name = PARAMS.get("view_name", "Level 1.0")
    out_dir = r"C:\\\\Users\\\\mitch\\\\Downloads"
    out_name = "barnhaus_" + view_name.replace(" ", "_")
    target = None
    for v in FilteredElementCollector(doc).OfClass(View):
        if v.Name == view_name and not v.IsTemplate:
            target = v; break
    if not target:
        mark("error", error="View not found: " + view_name)
    else:
        opts = ImageExportOptions()
        opts.ExportRange = ExportRange.SetOfViews
        opts.SetViewsAndSheets([target.Id])
        opts.ImageResolution = ImageResolution.DPI_150
        opts.FilePath = os.path.join(out_dir, out_name)
        opts.HLRandWFViewsFileType = ImageFileType.PNG
        opts.ShadowViewsFileType = ImageFileType.PNG
        doc.ExportImage(opts)
        exported = None
        for f in os.listdir(out_dir):
            if f.startswith(out_name) and f.endswith(".png"):
                exported = os.path.join(out_dir, f); break
        mark("done", result={"file": exported or (out_dir + "\\\\" + out_name + ".png")})
except Exception as e:
    mark("error", error=str(e))
'''

    elif cmd_type == "create_sheets":
        script_body += '''
try:
    sheets_to_create = PARAMS.get("sheets", [])
    tb_id = None
    for tb in FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_TitleBlocks):
        if "ARCH D 24 X 36 HORIZONTAL" in tb.Family.Name:
            if not tb.IsActive: tb.Activate(); doc.Regenerate()
            tb_id = tb.Id; break
    if not tb_id:
        mark("error", error="Title block not found")
    else:
        existing = {s.SheetNumber for s in FilteredElementCollector(doc).OfClass(ViewSheet)}
        created, skipped = [], []
        t = Transaction(doc, "Barnhaus AI - Create Sheets")
        t.Start()
        for s in sheets_to_create:
            num, name = s.get("number",""), s.get("name","")
            if num in existing: skipped.append(num); continue
            sheet = ViewSheet.Create(doc, tb_id)
            sheet.SheetNumber = num
            sheet.Name = name
            created.append(num)
        t.Commit()
        mark("done", result={"created": created, "skipped": skipped})
except Exception as e:
    mark("error", error=str(e))
'''

    elif cmd_type == "create_dimensions":
        script_body += '''
try:
    view_name = PARAMS.get("view_name")
    dims_spec = PARAMS.get("dimensions", [])
    target = None
    for v in FilteredElementCollector(doc).OfClass(View):
        if v.Name == view_name and not v.IsTemplate: target = v; break
    if not target:
        mark("error", error="View not found: " + str(view_name))
    else:
        dim_type = None
        for dt in FilteredElementCollector(doc).OfClass(DimensionType): dim_type = dt; break
        created, errors = 0, []
        t = Transaction(doc, "Barnhaus AI - Dimensions")
        t.Start()
        for ds in dims_spec:
            try:
                sp, ep = ds["start"], ds["end"]
                line = Line.CreateBound(XYZ(float(sp[0]),float(sp[1]),0),
                                        XYZ(float(ep[0]),float(ep[1]),0))
                refs = ReferenceArray()
                for rs in ds.get("refs", []):
                    elem = doc.GetElement(ElementId(int(rs["wall_id"])))
                    if elem:
                        layer = ShellLayerType.Exterior if rs.get("face")=="exterior" else ShellLayerType.Interior
                        fr = HostObjectUtils.GetSideFaces(elem, layer)
                        if fr and fr.Count > 0: refs.Append(fr[0])
                if refs.Size >= 2:
                    doc.Create.NewDimension(target, line, refs); created += 1
            except Exception as ex: errors.append(str(ex))
        t.Commit()
        mark("done", result={"created": created, "errors": errors})
except Exception as e:
    mark("error", error=str(e))
'''

    else:
        script_body += '\nmark("error", error="Unknown command type")\n'

    script_path = os.path.join(SCRIPTS_DIR, "cmd_" + cmd_id[:8] + ".py")
    with open(script_path, "w") as f:
        f.write(script_body)
    return script_path


def run_in_revit(script_path):
    """Run a script in the open Revit 2025 instance via pyRevit CLI."""
    result = subprocess.run(
        [PYREVIT_CLI, "run", script_path, "--revit=2025"],
        capture_output=True, text=True, timeout=120
    )
    return result.returncode, result.stdout, result.stderr


def main():
    print("Barnhaus AI Bridge started. Polling Supabase every " + str(POLL_INTERVAL) + "s...")
    print("Waiting for AI commands...\n")

    while True:
        try:
            cmds = sb_get("revit_commands", {
                "status": "eq.pending",
                "order": "created_at.asc",
                "limit": "1"
            })
            if cmds:
                cmd = cmds[0]
                cmd_id   = cmd["id"]
                cmd_type = cmd["command_type"]
                params   = cmd.get("params") or {}

                print(f"→ Command: {cmd_type} ({cmd_id[:8]})")
                mark(cmd_id, "processing")

                script_path = write_script(cmd_type, params, cmd_id)
                code, out, err = run_in_revit(script_path)
                print(f"  Exit code: {code}")
                if err: print(f"  Stderr: {err[:200]}")

                # Clean up
                try: os.remove(script_path)
                except: pass

        except Exception as e:
            print("Poll error:", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
