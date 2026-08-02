# -*- coding: utf-8 -*-
"""Deletes all room objects from the current Revit project."""
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document

rooms = list(FilteredElementCollector(doc)
             .OfCategory(BuiltInCategory.OST_Rooms)
             .WhereElementIsNotElementType()
             .ToElements())

if not rooms:
    TaskDialog.Show("Purge Rooms", "No rooms found.")
else:
    t = Transaction(doc, "Barnhaus - Purge Rooms")
    t.Start()
    deleted = 0
    for r in rooms:
        try:
            doc.Delete(r.Id)
            deleted += 1
        except: pass
    t.Commit()
    TaskDialog.Show("Purge Rooms", "Deleted " + str(deleted) + " rooms.")
