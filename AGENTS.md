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

### Step 3: Run Planner (generates floor plan PNG + spec JSON + uploads both to Supabase)
```bash
cd /home/node/.openclaw/workspace && python3 brain/barnhaus_planner.py <submission_id>
```
The planner does ALL of the following automatically:
- Validates room sizes and adjacencies
- Solves the footprint with exact zone coordinates
- Assigns all rooms to zones with x/y/w/d coordinates
- Routes circulation (foyer, gallery hall, bed corridor, service path)
- Generates a color-coded PNG floor plan
- Generates a fully resolved `spec_XXXX.json` with:
  - Exact room coordinates (x0,y0,x1,y1) for every room
  - Exterior wall coordinates with EXT_HALF offsets applied
  - Interior wall positions derived from room adjacencies
  - Door positions at midpoint of every shared wall
  - Window positions on rear/view walls
  - Footprint polygon
  - Revit config (wall types, levels, heights)
- Uploads both PNG and spec JSON to Supabase storage
- Prints the public URLs for both

### Step 4: Post Floor Plan for Review
- Post the Supabase PNG URL as a Discord image embed
- Include the design brief summary (SF, rooms, shape, exterior style)
- Include any violations found (room too small, adjacency issues)
- Ask Mitch: "Approve or request changes?"

### Step 5: Handle Feedback
- If approved → post: "✅ Design approved. Spec ready at: [spec_url] — say 'start revit [id]' to begin execution."
- If changes requested → note the changes, re-run brain with updated parameters, then re-run planner

### Step 6: Track Status
Keep track of each submission status in memory/pipeline-state.json:
- pending → brain_running → planner_running → review → approved → building → complete

## Important Notes
- NEVER generate your own floor plan images — always use barnhaus_planner.py
- The spec JSON is what Mitch's local Revit agent uses — never skip generating it
- Always run brain FIRST, then planner
- The spec_url goes to Mitch when design is approved so he can pass it to his local agent
