# -*- coding: utf-8 -*-
"""
Barnhaus Apply AI - executes pending AI instructions from Supabase.
"""

import json
import urllib2
import urllib
import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import (
    FilteredElementCollector, ViewSheet, ViewPlan, View, Level,
    BuiltInCategory, BuiltInParameter, Wall, Transaction,
    Line, XYZ, ReferenceArray, DimensionType, ElementId,
    HostObjectUtils, ShellLayerType, FamilySymbol, Viewport
)
from Autodesk.Revit.UI import TaskDialog

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

SUPABASE_URL = "https://hbfjdfxephlczkfgpceg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiZmpkZnhlcGhsY3prZmdwY2VnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTMzNzcxMCwiZXhwIjoyMDU0OTEzNzEwfQ.weXk7CqDqR8XkEpi4kaI_GmHWlkqh6snOMQm-hk48RM"


def sb_get(path, params=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    if params: url += "?" + urllib.urlencode(params)
    req = urllib2.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    try: return json.loads(urllib2.urlopen(req, timeout=15).read())
    except: return None


def sb_patch(path, data, params=None):
    url = SUPABASE_URL + "/rest/v1/" + path
    if params: url += "?" + urllib.urlencode(params)
    req = urllib2.Request(url, json.dumps(data))
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    req.get_method = lambda: "PATCH"
    try: return json.loads(urllib2.urlopen(req, timeout=15).read())
    except: return None


def get_title_block_id():
    # Prefer Barnhaus standard, fall back to anything available
    best = None
    for tb in FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_TitleBlocks):
        if not tb.IsActive:
            tb.Activate()
            doc.Regenerate()
        if "ARCH D 24 X 36 HORIZONTAL" in tb.Family.Name:
            return tb.Id
        best = tb.Id  # keep last found as fallback
    return best


def find_sheet(number):
    for s in FilteredElementCollector(doc).OfClass(ViewSheet):
        if s.SheetNumber == number: return s
    return None


def find_view(name):
    for v in FilteredElementCollector(doc).OfClass(View):
        if v.Name == name and not v.IsTemplate: return v
    return None


# --- Fetch pending instructions ---
instructions = sb_get("revit_instructions", {"status": "eq.pending",
                                               "order": "created_at.asc"})

if not instructions:
    TaskDialog.Show("Barnhaus - Apply AI", "No pending AI instructions found.\n\nRun Analyze first, then wait for the AI to generate instructions.")
else:
    tb_id = get_title_block_id()
    results = []
    errors  = []

    t = Transaction(doc, "Barnhaus AI - Apply Instructions")
    t.Start()
    try:
        for instr in instructions:
            iid     = instr["id"]
            itype   = instr["instruction_type"]
            iparams = instr.get("params") or {}

            try:
                # --- CREATE SHEET ---
                if itype == "create_sheet":
                    num  = iparams.get("number", "")
                    name = iparams.get("name", "")
                    if find_sheet(num):
                        results.append("Skipped (exists): " + num)
                    else:
                        # Use ElementId.InvalidElementId if no title block (creates sheet without one)
                        use_tb_id = tb_id if tb_id else ElementId.InvalidElementId
                        sheet = ViewSheet.Create(doc, use_tb_id)
                        sheet.SheetNumber = num
                        sheet.Name = name
                        results.append("Created sheet: " + num + " - " + name)

                # --- PLACE VIEW ON SHEET ---
                elif itype == "place_view":
                    sheet = find_sheet(iparams.get("sheet_number", ""))
                    loc   = iparams.get("location", [1.0, 1.0])
                    # Support view_id or view_name
                    if iparams.get("view_id"):
                        view = doc.GetElement(ElementId(int(iparams["view_id"])))
                    else:
                        view = find_view(iparams.get("view_name", ""))
                    if sheet and view:
                        Viewport.Create(doc, sheet.Id, view.Id,
                                        XYZ(float(loc[0]), float(loc[1]), 0))
                        results.append("Placed " + view.Name + " on " + sheet.SheetNumber)
                    else:
                        errors.append("place_view: sheet or view not found")

                # --- CREATE DIMENSION ---
                elif itype == "create_dimension":
                    view_name = iparams.get("view_name")
                    view = find_view(view_name)
                    if not view:
                        errors.append("create_dimension: view not found: " + str(view_name))
                    else:
                        sp = iparams["start"]
                        ep = iparams["end"]
                        line = Line.CreateBound(XYZ(float(sp[0]), float(sp[1]), 0),
                                                XYZ(float(ep[0]), float(ep[1]), 0))
                        refs = ReferenceArray()
                        for rs in iparams.get("refs", []):
                            elem = doc.GetElement(ElementId(int(rs["wall_id"])))
                            if elem:
                                layer = ShellLayerType.Exterior if rs.get("face") == "exterior" else ShellLayerType.Interior
                                fr = HostObjectUtils.GetSideFaces(elem, layer)
                                if fr and fr.Count > 0: refs.Append(fr[0])
                        if refs.Size >= 2:
                            dim_type = None
                            for dt in FilteredElementCollector(doc).OfClass(DimensionType):
                                dim_type = dt; break
                            doc.Create.NewDimension(view, line, refs)
                            results.append("Created dimension in " + str(view_name))

                # --- DUPLICATE VIEW ---
                elif itype == "duplicate_view":
                    src_name  = iparams.get("source_view_name", "")
                    new_name  = iparams.get("new_view_name", "")
                    src_view  = find_view(src_name)
                    if src_view:
                        from Autodesk.Revit.DB import ViewDuplicateOption
                        new_id = src_view.Duplicate(ViewDuplicateOption.Duplicate)
                        new_view = doc.GetElement(new_id)
                        new_view.Name = new_name
                        results.append("Duplicated: " + new_name)
                    else:
                        errors.append("duplicate_view: not found: " + src_name)

                # --- SET VIEW SCALE ---
                elif itype == "set_view_scale":
                    view = find_view(iparams.get("view_name", ""))
                    if view:
                        view.Scale = int(iparams.get("scale", 96))
                        results.append("Set scale on " + view.Name)

                # --- SET VIEW TEMPLATE ---
                elif itype == "set_view_template":
                    view = find_view(iparams.get("view_name", ""))
                    template_name = iparams.get("template_name", "")
                    if view:
                        for v in FilteredElementCollector(doc).OfClass(View):
                            if v.IsTemplate and v.Name == template_name:
                                view.ViewTemplateId = v.Id
                                results.append("Applied template " + template_name + " to " + view.Name)
                                break

                # Mark as done
                sb_patch("revit_instructions", {"status": "done"}, {"id": "eq." + iid})

            except Exception as ex:
                errors.append(itype + ": " + str(ex))
                sb_patch("revit_instructions", {"status": "error", "error": str(ex)},
                         {"id": "eq." + iid})

        t.Commit()

    except Exception as e:
        t.RollBack()
        TaskDialog.Show("Barnhaus - Apply AI", "Transaction error: " + str(e))
        import sys; sys.exit()

    msg  = "Applied " + str(len(results)) + " instructions\n\n"
    msg += "\n".join(results[:20])
    if errors:
        msg += "\n\nErrors:\n" + "\n".join(errors[:10])
    TaskDialog.Show("Barnhaus - Apply AI", msg)
