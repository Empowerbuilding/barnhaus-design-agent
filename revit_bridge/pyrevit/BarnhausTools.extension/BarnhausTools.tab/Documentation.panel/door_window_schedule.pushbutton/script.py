# -*- coding: utf-8 -*-
"""Create Door and Window schedules and place them on sheet A105."""

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    BuiltInParameter,
    ViewSheet,
    ViewSchedule,
    ScheduleSheetInstance,
    FamilySymbol,
    Transaction,
    ElementId,
    XYZ,
)
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document

TITLE_BLOCK_NAME = "ARCH D 24 X 36 HORIZONTAL"
TARGET_SHEET = "A105"


def get_title_block_id():
    collector = FilteredElementCollector(doc).OfClass(FamilySymbol)\
        .OfCategory(BuiltInCategory.OST_TitleBlocks)
    for tb in collector:
        if tb.Family.Name == TITLE_BLOCK_NAME:
            if not tb.IsActive:
                tb.Activate()
                doc.Regenerate()
            return tb.Id
    return None


def find_sheet(sheet_number):
    """Find a sheet by number."""
    collector = FilteredElementCollector(doc).OfClass(ViewSheet)
    for sheet in collector:
        if sheet.SheetNumber == sheet_number:
            return sheet
    return None


def find_schedule_by_name(name):
    """Check if a schedule with the given name already exists."""
    collector = FilteredElementCollector(doc).OfClass(ViewSchedule)
    for vs in collector:
        if vs.Name == name:
            return vs
    return None


def add_schedulable_field(definition, field_name):
    """Add a field to the schedule definition by name if available."""
    field_count = definition.GetSchedulableFields().Count
    for i in range(field_count):
        sf = definition.GetSchedulableFields()[i]
        if sf.GetName(doc) == field_name:
            definition.AddField(sf)
            return True
    return False


def create_door_schedule():
    """Create a door schedule."""
    schedule_name = "Door Schedule"
    existing = find_schedule_by_name(schedule_name)
    if existing is not None:
        return existing

    schedule = ViewSchedule.CreateSchedule(
        doc,
        ElementId(int(BuiltInCategory.OST_Doors))
    )
    schedule.Name = schedule_name

    definition = schedule.Definition
    desired_fields = ["Mark", "Type", "Width", "Height", "Count"]
    for field_name in desired_fields:
        add_schedulable_field(definition, field_name)

    return schedule


def create_window_schedule():
    """Create a window schedule."""
    schedule_name = "Window Schedule"
    existing = find_schedule_by_name(schedule_name)
    if existing is not None:
        return existing

    schedule = ViewSchedule.CreateSchedule(
        doc,
        ElementId(int(BuiltInCategory.OST_Windows))
    )
    schedule.Name = schedule_name

    definition = schedule.Definition
    desired_fields = ["Mark", "Type", "Width", "Height", "Count"]
    for field_name in desired_fields:
        add_schedulable_field(definition, field_name)

    return schedule


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

tb_id = get_title_block_id()

t = Transaction(doc, "Barnhaus - Door & Window Schedules")
t.Start()
try:
    # Create schedules
    door_sched = create_door_schedule()
    window_sched = create_window_schedule()

    # Find or create the target sheet
    sheet = find_sheet(TARGET_SHEET)
    if sheet is None:
        if tb_id is not None:
            sheet = ViewSheet.Create(doc, tb_id)
            sheet.SheetNumber = TARGET_SHEET
            sheet.Name = "ELEVATIONS SIDES"

    if sheet is not None:
        # Place door schedule on upper portion of sheet
        if door_sched is not None:
            door_point = XYZ(1.5, 1.4, 0)
            try:
                ScheduleSheetInstance.Create(doc, sheet.Id, door_sched.Id, door_point)
            except Exception:
                pass  # Schedule may already be placed

        # Place window schedule on lower portion
        if window_sched is not None:
            window_point = XYZ(1.5, 0.6, 0)
            try:
                ScheduleSheetInstance.Create(doc, sheet.Id, window_sched.Id, window_point)
            except Exception:
                pass

    t.Commit()
except Exception as e:
    t.RollBack()
    TaskDialog.Show("Barnhaus - Schedules", "Error: " + str(e))
    import sys
    sys.exit()

msg = "Door & Window Schedules\n"
msg += "=" * 40 + "\n\n"

if door_sched is not None:
    msg += "Door Schedule: Created/Found\n"
else:
    msg += "Door Schedule: Failed\n"

if window_sched is not None:
    msg += "Window Schedule: Created/Found\n"
else:
    msg += "Window Schedule: Failed\n"

if sheet is not None:
    msg += "\nPlaced on sheet " + TARGET_SHEET + " - " + sheet.Name + "\n"
else:
    msg += "\nWarning: Could not find or create sheet " + TARGET_SHEET + "\n"

TaskDialog.Show("Barnhaus - Schedules", msg)
