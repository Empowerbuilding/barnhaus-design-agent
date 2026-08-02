# -*- coding: utf-8 -*-
"""Show project status - which standard sheets exist vs missing."""

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    ViewSheet,
    Level,
)
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document


def get_existing_sheet_numbers():
    """Return a set of sheet numbers already in the project."""
    collector = FilteredElementCollector(doc).OfClass(ViewSheet)
    numbers = set()
    for sheet in collector:
        numbers.add(sheet.SheetNumber)
    return numbers


def has_level(name):
    """Check if a level with the given name exists."""
    collector = FilteredElementCollector(doc).OfClass(Level)
    for lvl in collector:
        if lvl.Name == name:
            return True
    return False


def detect_secondary_structure():
    """Check for casita/garage/secondary structure views."""
    from Autodesk.Revit.DB import View
    collector = FilteredElementCollector(doc).OfClass(View)
    keywords = ["casita", "garage", "adu", "guest house", "secondary"]
    for v in collector:
        vname = v.Name.lower()
        for kw in keywords:
            if kw in vname:
                return True
    return False


def build_expected_sheets():
    """Build list of expected (number, name) tuples."""
    has_f2 = has_level("Level 2.0")
    has_secondary = detect_secondary_structure()

    sheets = [
        ("A100", "COVER SHEET"),
        ("A100.1", "Front Face"),
        ("A100.2", "SITE PLAN"),
        ("A101.1", "FLOOR PLAN F1"),
    ]
    if has_f2:
        sheets.append(("A101.2", "FLOOR PLAN F2"))

    sheets.append(("A102.1", "DIMENSION PLAN F1"))
    if has_f2:
        sheets.append(("A102.2", "DIMENSION PLAN F2"))

    sheets.extend([
        ("A103", "ROOF LAYOUT"),
        ("A104", "FOUNDATION & COLUMNS"),
        ("A105", "ELEVATIONS SIDES"),
        ("A106", "ELEVATIONS FRONT BACK"),
        ("A106.1", "3D VIEWS"),
        ("A106.2", "3D VIEWS"),
        ("A107", "INTERIOR ELEVATIONS"),
        ("A107.1", "INTERIOR ELEVATIONS"),
        ("A107.2", "INTERIOR ELEVATIONS"),
        ("A107.3", "INTERIOR ELEVATIONS"),
        ("A107.4", "INTERIOR ELEVATIONS"),
        ("A107.5", "STRUCTURAL ELEVATIONS"),
        ("A108.1", "ELECTRICAL PLAN"),
    ])
    if has_f2:
        sheets.append(("A108.2", "ELECTRICAL PLAN"))

    sheets.append(("A109.1", "FOUNDATION PLAN"))
    sheets.append(("A109.2", "PLUMBING PLAN"))
    if has_f2:
        sheets.append(("A109.3", "PLUMBING PLAN"))

    sheets.append(("A109.4", "FOUNDATION PLAN Control Joints"))
    sheets.append(("A110", "TAKE OFFS"))

    if has_secondary:
        sheets.extend([
            ("A201.1", "CASITA FLOOR PLANS"),
            ("A202.1", "CASITA DIMENSION PLANS"),
            ("A203", "ROOF & COLUMN PLACEMENT"),
            ("A204", "ELEVATIONS SIDES"),
            ("A205", "ELEVATIONS FRONT BACK"),
            ("A206", "3D VIEWS"),
            ("A207", "INTERIOR ELEVATIONS"),
            ("A208", "CASITA ELECTRICAL PLANS"),
            ("A209", "CASITA PLUMBING PLANS"),
        ])

    return sheets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

existing = get_existing_sheet_numbers()
expected = build_expected_sheets()

found = []
missing = []

for number, name in expected:
    label = number + " - " + name
    if number in existing:
        found.append(label)
    else:
        missing.append(label)

total = len(expected)
done = len(found)
if total > 0:
    pct = int(round(100.0 * done / total))
else:
    pct = 0

msg = "Project Status\n"
msg += "=" * 40 + "\n\n"
msg += "Completion: " + str(done) + " / " + str(total) + " sheets (" + str(pct) + "%)\n\n"

if found:
    msg += "--- Existing Sheets ---\n"
    for s in found:
        msg += "  [x] " + s + "\n"
    msg += "\n"

if missing:
    msg += "--- Missing Sheets ---\n"
    for s in missing:
        msg += "  [ ] " + s + "\n"
else:
    msg += "All standard sheets are present!\n"

TaskDialog.Show("Barnhaus - Project Status", msg)
