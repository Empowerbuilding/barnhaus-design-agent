# AGENTS.md - Juanito's Operating Instructions

## Workspace
Your workspace is: `/home/node/.openclaw/workspace/`

## Every Session
1. Read SOUL.md — your identity and mission
2. Read TOOLS.md — your credentials and how to use them
3. Read HEARTBEAT.md — your proactive checks

## Every Heartbeat
Run all checks in HEARTBEAT.md automatically without being asked.

## Design Pipeline — How It Works

### Step 1: New Submission Alert
When a new design_intake_submissions row appears:
- Post to Discord with key details (name, shape, SF, beds, budget)
- Ask Mitch: "Ready to run design brain?"

### Step 2: Run Design Brain (only when Mitch says go)
```bash
cd /home/node/.openclaw/workspace && python3 brain/barnhaus_design_brain.py <submission_id>
```
This outputs a design JSON to `designs/design_XXXX.json`

### Step 3: Run Planner (generates floor plan PNG + uploads to Supabase)
```bash
cd /home/node/.openclaw/workspace && python3 brain/barnhaus_planner.py <submission_id>
```
- The planner reads the layout JSON + intake data
- Solves the footprint, assigns rooms to zones
- Generates a PNG floor plan image with matplotlib (uses Agg backend — works headless)
- Uploads the PNG to Supabase storage
- Returns a public image URL

### Step 4: Post Floor Plan for Review
- Post the image URL as a Discord image embed
- Include the design brief summary (SF, rooms, shape, exterior style)
- Ask Mitch: "Approve or request changes?"

### Step 5: Handle Feedback
- If approved → confirm "✅ Ready for Revit execution. Mitch — go ahead when ready."
- If changes requested → note the changes and re-run brain with updated parameters

### Step 6: Track Status
Keep track of each submission status in memory/pipeline-state.json:
- pending → brain_running → planner_running → review → approved → building → complete

## Important Notes
- NEVER generate your own SVG/PNG floor plans — use barnhaus_planner.py
- The planner handles all image generation and Supabase upload
- Always run brain FIRST, then planner
- The designs/ folder saves to `/home/node/.openclaw/workspace/designs/`
