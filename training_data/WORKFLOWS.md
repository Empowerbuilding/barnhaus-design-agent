# WORKFLOWS.md — Journal Analysis & Learned Patterns

## 2026-08-31: Michael's Journal Analysis (Journals 1787-1790)

**Context:** Analyzed a batch of Michael's Revit journals to identify repetitive tasks and propose automations.

### 1. The "Nudge and Drag" Trap
- **Stats:** 842 Nudge Left, 542 Nudge Right, 347 Nudge Down, 319 Nudge Up, 442 Drags, 541 Moves.
- **Pattern:** Massive volume of micro-adjustments using arrow keys and mouse dragging.
- **Implication:** Likely spending excessive time manually organizing tags, text notes, or detail items on sheets/views instead of using alignment tools or snap grids.
- **Suggested Automation:** An **Auto-Aligner/Tidier** command to instantly left-align and space selected text notes, tags, or dimensions evenly.

### 2. The "Paste and Align" Loop
- **Stats:** `Initial paste` -> `Paste` -> `Align` occurred 31 times.
- **Pattern:** Copying elements, pasting, and then manually using the Align tool.
- **Implication:** Bypassing Revit's native "Paste Aligned to Current View" / "Paste Aligned to Selected Levels" features.
- **Suggested Action:** Build automation for standard view/detail propagation or prompt designer on workflow efficiency (Paste Aligned).

### 3. The "Edit Sketch" Cycle
- **Stats:** `Edit Sketch` -> `Drag` -> `Finish sketch` occurred 40 times. Repeated `Area Boundary` -> `Area Boundary` transactions (30 times).
- **Pattern:** Opening sketch mode for floors/roofs/regions to make micro-drags to boundary lines.
- **Suggested Automation:** **Area Boundary Generator** script for standard area boxes or rooms to reduce manual boundary sketching loops.
### 4. Co-Dev Feature: Live Change-Feed
- **Status:** Shipped (Bridge C# commit b9750bf) and packaged in v3 DLL. 
- **Note:** The live change-feed logs exact element IDs, transaction names, and timestamps to `changes.jsonl`.
- **Constraint:** Until Mitch updates his machine, the `revit.get_recent_changes` command is ONLY available on Michael's session.
