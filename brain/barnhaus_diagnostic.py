import sys
import json
import traceback

out_path = r"C:\Users\mitch\Downloads\barnhaus_diagnostic.json"
log_path = r"C:\Users\mitch\Downloads\barnhaus_diagnostic_log.txt"
model_path = r"C:\Users\mitch\Downloads\Murrell - Final Revised.rvt"

log = []

def logit(msg):
    log.append(str(msg))
    print(str(msg))

try:
    logit("Starting diagnostic...")

    import clr
    clr.AddReference('RevitAPI')
    from Autodesk.Revit.DB import (
        FilteredElementCollector, ViewSheet, View, Level, Family,
        BuiltInCategory, BuiltInParameter, OpenOptions, ModelPath,
        FilePath
    )

    logit("RevitAPI loaded OK")

    app = __revit__.Application
    logit("Got Application")

    # Open the model
    logit("Opening model: " + model_path)
    open_opts = OpenOptions()
    open_opts.DetachFromCentralOption = open_opts.DetachFromCentralOption.DoNotDetach
    file_path = FilePath(model_path)
    doc = app.OpenDocumentFile(file_path, open_opts)
    logit("Model opened: " + str(doc.Title))

    data = {
        "project_title": str(doc.Title),
        "sheets": [],
        "view_templates": [],
        "families": [],
        "title_blocks": [],
        "levels": [],
        "rooms": []
    }

    # Sheets
    try:
        for sheet in FilteredElementCollector(doc).OfClass(ViewSheet):
            data["sheets"].append({
                "number": sheet.SheetNumber,
                "name": sheet.Name
            })
        data["sheets"].sort(key=lambda x: x["number"])
        logit("Sheets: " + str(len(data["sheets"])))
    except Exception as e:
        logit("Sheet error: " + str(e))

    # Title blocks
    try:
        seen = set()
        for tb in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_TitleBlocks).WhereElementIsNotElementType():
            tb_type = doc.GetElement(tb.GetTypeId())
            if tb_type:
                name = tb_type.FamilyName
                if name not in seen:
                    seen.add(name)
                    data["title_blocks"].append(name)
        logit("Title blocks: " + str(data["title_blocks"]))
    except Exception as e:
        logit("Title block error: " + str(e))

    # View templates
    try:
        for v in FilteredElementCollector(doc).OfClass(View):
            if v.IsTemplate:
                data["view_templates"].append(v.Name)
        logit("View templates: " + str(len(data["view_templates"])))
    except Exception as e:
        logit("View template error: " + str(e))

    # Levels
    try:
        for lvl in FilteredElementCollector(doc).OfClass(Level):
            data["levels"].append({"name": lvl.Name, "elevation_ft": round(lvl.Elevation, 2)})
        logit("Levels: " + str(data["levels"]))
    except Exception as e:
        logit("Level error: " + str(e))

    # Families
    try:
        for fam in FilteredElementCollector(doc).OfClass(Family):
            cat = fam.FamilyCategory.Name if fam.FamilyCategory else "Unknown"
            data["families"].append({"name": fam.Name, "category": cat})
        logit("Families: " + str(len(data["families"])))
    except Exception as e:
        logit("Family error: " + str(e))

    # Rooms
    try:
        for room in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
            try:
                name_p = room.get_Parameter(BuiltInParameter.ROOM_NAME)
                num_p = room.get_Parameter(BuiltInParameter.ROOM_NUMBER)
                area_p = room.get_Parameter(BuiltInParameter.ROOM_AREA)
                data["rooms"].append({
                    "name": name_p.AsString() if name_p else "",
                    "number": num_p.AsString() if num_p else "",
                    "area_sqft": round(area_p.AsDouble(), 1) if area_p else 0
                })
            except:
                pass
        logit("Rooms: " + str(len(data["rooms"])))
    except Exception as e:
        logit("Room error: " + str(e))

    doc.Close(False)

    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2)
    logit("SUCCESS - JSON written to " + out_path)

except Exception as e:
    logit("FATAL ERROR: " + str(e))
    logit(traceback.format_exc())

finally:
    with open(log_path, 'w') as f:
        f.write('\n'.join(log))
