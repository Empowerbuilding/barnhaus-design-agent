# Barnhaus pyRevit Extension Build Task

## Context
Build a complete pyRevit extension called "BarnhausTools" for Autodesk Revit 2025.

- pyRevit installed at: C:\Users\mitch\AppData\Roaming\pyRevit-Master
- Extensions go in: C:\Users\mitch\AppData\Roaming\pyRevit-Master\extensions
- All scripts use IronPython 2 (pyRevit default) - Python 2 compatible syntax only
- Title block family name: "ARCH D 24 X 36 HORIZONTAL"
- View templates available: ELECTRICAL, PLUMBING, SIMPLE, AREA, Level, Section
- Standard level names: "Level 1.0", "Level 2.0", "Level 3.0", "Level Base"
- pyRevit scripts use __revit__ for UIApplication access, __output__ for output panel

## Study First
Three diagnostic JSON files are in this folder (murrell_diagnostic.json, wirch_diagnostic.json, truelock_diagnostic.json).
Study them carefully to understand the exact sheet structure, family names, and patterns across all 3 real Barnhaus projects before writing any code.

## Folder Structure to Create

```
BarnhausTools.extension/
  extension.json
  BarnhausTools.tab/
    Sheets.panel/
      sheet_bundle.pushbutton/
        script.py
        bundle.yaml
      project_status.pushbutton/
        script.py
        bundle.yaml
    MEP.panel/
      electrical_plan.pushbutton/
        script.py
        bundle.yaml
      plumbing_plan.pushbutton/
        script.py
        bundle.yaml
    Documentation.panel/
      door_window_schedule.pushbutton/
        script.py
        bundle.yaml
      auto_dimension.pushbutton/
        script.py
        bundle.yaml
README.md
```

## Buttons to Build

### Panel: Sheets

**1. sheet_bundle.pushbutton** - "Create Sheet Bundle"
- Analyzes the current model (levels, structures)
- Detects if secondary structure exists (casita/garage) based on model content
- Creates the full standard Barnhaus sheet set using "ARCH D 24 X 36 HORIZONTAL" title block:
  - A100 COVER SHEET
  - A100.1 Front Face
  - A100.2 SITE PLAN
  - A101.1 FLOOR PLAN F1
  - A101.2 FLOOR PLAN F2 (only if Level 2.0 exists)
  - A102.1 DIMENSION PLAN F1
  - A102.2 DIMENSION PLAN F2 (only if Level 2.0)
  - A103 ROOF LAYOUT
  - A104 FOUNDATION & COLUMNS
  - A105 ELEVATIONS SIDES
  - A106 ELEVATIONS FRONT BACK
  - A106.1 3D VIEWS
  - A106.2 3D VIEWS
  - A107 INTERIOR ELEVATIONS
  - A107.1 INTERIOR ELEVATIONS
  - A107.2 INTERIOR ELEVATIONS
  - A107.3 INTERIOR ELEVATIONS
  - A107.4 INTERIOR ELEVATIONS
  - A107.5 STRUCTURAL ELEVATIONS
  - A108.1 ELECTRICAL PLAN
  - A108.2 ELECTRICAL PLAN (if Level 2.0 exists)
  - A109.1 FOUNDATION PLAN
  - A109.2 PLUMBING PLAN
  - A109.3 PLUMBING PLAN (if Level 2.0)
  - A109.4 FOUNDATION PLAN Control Joints
  - A110 TAKE OFFS
  - If secondary structure: A201.1 thru A209 equivalents
- Skips sheets that already exist (check by sheet number)
- Shows TaskDialog summary of what was created vs skipped

**2. project_status.pushbutton** - "Project Status"
- Shows a dialog listing which standard sheets exist vs missing
- Shows completion percentage
- Lists missing sheets so Mitch knows what's left

### Panel: MEP

**3. electrical_plan.pushbutton** - "Generate Electrical Plans"
- Finds floor plan views associated with ELECTRICAL view template or named "Electrical"
- Creates A108.1 sheet (and A108.2 if Level 2.0 exists) if not already present
- Places the appropriate electrical floor plan view on each sheet
- Applies ELECTRICAL view template to the views
- Sets view scale to 1/8" = 1'-0" (scale = 96)

**4. plumbing_plan.pushbutton** - "Generate Plumbing Plans"
- Same pattern but for plumbing
- Creates A109.2 and A109.3 sheets
- Applies PLUMBING view template
- Sets view scale to 1/8" = 1'-0"

### Panel: Documentation

**5. door_window_schedule.pushbutton** - "Door & Window Schedule"
- Creates a Revit Schedule for doors (all door instances, columns: Mark, Type, Width, Height, Count)
- Creates a Revit Schedule for windows (same pattern)
- Places schedules on A105 sheet (creates A105 if missing)

**6. auto_dimension.pushbutton** - "Auto Dimension"
- Uses the active floor plan view (or prompts if not a floor plan)
- Dimensions all exterior walls automatically using Revit's DimensionType
- Uses standard Linear dimension type

## Technical Notes
- Each pushbutton bundle.yaml needs: name, tooltip fields
- extension.json format: {"name": "BarnhausTools", "type": "lib"}
- Wrap all model changes in Transaction(doc, "Barnhaus - [action]")
- Always check existence before creating (sheets by SheetNumber, views by Name)
- Use FilteredElementCollector for all element queries
- Show progress/results via __output__ or TaskDialog
- IronPython 2: use str() not f-strings, print statements not print()

## After Building
Create README.md with install instructions and usage guide for each button.

Then run: openclaw system event --text "Done: Barnhaus pyRevit extension built - all 6 buttons ready" --mode now
