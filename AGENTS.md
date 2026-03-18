# AGENTS.md - Juanito's Operating Instructions

## Workspace
Your workspace is: `/home/node/.openclaw/workspace/`

## Every Session
1. Read SOUL.md — your identity and mission
2. Read TOOLS.md — your credentials and how to use them
3. Read HEARTBEAT.md — your proactive checks

## Every Heartbeat
Run all checks in HEARTBEAT.md automatically without being asked.

## Design Pipeline — EXACT COMMANDS, NO IMPROVISING

### Step 1: New Submission Alert
Query Supabase for latest submission. Post key details to Discord. Ask Mitch: "Ready to run?"

### Step 2: Run Design Brain
Run this EXACT command — do not modify it:
```bash
cd /home/node/.openclaw/workspace && python3 brain/barnhaus_design_brain.py <submission_id>
```
This saves `designs/design_<id[:8]>.json`

### Step 3: Run Planner
Run this EXACT command — do not modify it:
```bash
cd /home/node/.openclaw/workspace && python3 brain/barnhaus_planner.py <id[:8]>
```
Example: `python3 brain/barnhaus_planner.py 7ae086e1`

The planner does EVERYTHING automatically:
- Validates rooms
- Solves footprint
- Generates PNG floor plan → saves to `designs/floorplan_<id[:8]>.png`
- Generates spec JSON → saves to `designs/spec_<id[:8]>.json`
- Uploads both to Supabase
- Prints two URLs at the end:
  - `Floor plan: https://...`
  - `Spec URL: https://...`

### Step 4: Post to Discord
Post BOTH URLs from the planner output:
- The floor plan image URL as a Discord image embed
- The spec URL as text: "Spec: [url]"
- Include design brief summary
- Ask Mitch: "Approve or request changes?"

### Step 5: On Approval
Post: "✅ Approved. Say 'start revit <id>' to begin Revit execution."

## ⚠️ CRITICAL RULES
- NEVER write your own rendering scripts
- NEVER write your own upload scripts  
- NEVER call any script other than `barnhaus_design_brain.py` and `barnhaus_planner.py`
- If a script doesn't exist, DO NOT create it — ask Mitch instead
- The planner handles ALL rendering and uploading — trust it
