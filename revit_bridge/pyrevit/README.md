# BarnhausTools - pyRevit Extension

A pyRevit extension for Autodesk Revit 2025 that automates the standard Barnhaus Design sheet set creation and documentation workflow.

## Installation

1. Copy the `BarnhausTools.extension` folder to your pyRevit extensions directory:
   ```
   C:\Users\mitch\AppData\Roaming\pyRevit-Master\extensions\
   ```

2. Reload pyRevit (pyRevit tab > Reload) or restart Revit.

3. The **BarnhausTools** tab will appear in the Revit ribbon.

## Prerequisites

- Autodesk Revit 2025
- pyRevit installed at `C:\Users\mitch\AppData\Roaming\pyRevit-Master`
- Title block family **"ARCH D 24 X 36 HORIZONTAL"** loaded in the project
- Standard view templates: ELECTRICAL, PLUMBING, SIMPLE, AREA, Level, Section

## Buttons

### Sheets Panel

#### Create Sheet Bundle
Creates the full standard Barnhaus sheet set (up to 35 sheets) in one click.

- Automatically detects project levels (Level 1.0, Level 2.0) to determine which floor-specific sheets to create
- Detects secondary structures (casita/garage) and creates the A200-series sheets
- Skips sheets that already exist (matched by sheet number)
- Shows a summary dialog of created vs skipped sheets

Standard sheet set: A100 through A110 for main house, A201 through A209 for casita.

#### Project Status
Shows a completion dashboard for the standard sheet set.

- Lists all expected sheets with checkmarks for existing and blanks for missing
- Displays completion percentage
- Adapts to project configuration (levels, secondary structures)

### MEP Panel

#### Generate Electrical Plans
Creates electrical plan sheets with views automatically placed.

- Creates A108.1 (Floor 1) and A108.2 (Floor 2, if Level 2.0 exists)
- Finds existing electrical views or creates new ones
- Applies the ELECTRICAL view template
- Sets view scale to 1/8" = 1'-0" (scale factor 96)
- Places views centered on the sheet

#### Generate Plumbing Plans
Creates plumbing plan sheets with views automatically placed.

- Creates A109.2 (Floor 1) and A109.3 (Floor 2, if Level 2.0 exists)
- Finds existing plumbing views or creates new ones
- Applies the PLUMBING view template
- Sets view scale to 1/8" = 1'-0" (scale factor 96)
- Places views centered on the sheet

### Documentation Panel

#### Door & Window Schedule
Creates Revit schedules for doors and windows.

- Door Schedule: Mark, Type, Width, Height, Count
- Window Schedule: Mark, Type, Width, Height, Count
- Places both schedules on sheet A105 (creates A105 if missing)

#### Auto Dimension
Automatically dimensions exterior walls in the active floor plan view.

- Must be run from a floor plan view
- Finds all walls with Function set to "Exterior"
- Creates linear dimensions offset from each wall
- Reports count of dimensions created

## Project Structure

```
BarnhausTools.extension/
  extension.json
  BarnhausTools.tab/
    Sheets.panel/
      sheet_bundle.pushbutton/    - Create Sheet Bundle
      project_status.pushbutton/  - Project Status
    MEP.panel/
      electrical_plan.pushbutton/ - Generate Electrical Plans
      plumbing_plan.pushbutton/   - Generate Plumbing Plans
    Documentation.panel/
      door_window_schedule.pushbutton/ - Door & Window Schedule
      auto_dimension.pushbutton/       - Auto Dimension
```

## Sheet Numbering Convention

| Range | Category |
|-------|----------|
| A100-A100.2 | Cover, Front Face, Site Plan |
| A101.x | Floor Plans (per level) |
| A102.x | Dimension Plans (per level) |
| A103 | Roof Layout |
| A104 | Foundation & Columns |
| A105 | Elevations Sides |
| A106 | Elevations Front/Back |
| A106.x | 3D Views |
| A107-A107.5 | Interior & Structural Elevations |
| A108.x | Electrical Plans (per level) |
| A109.x | Foundation, Plumbing, Control Joints |
| A110 | Take Offs |
| A201-A209 | Secondary Structure (Casita) |
