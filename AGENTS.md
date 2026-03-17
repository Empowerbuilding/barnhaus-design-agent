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
cd /home/node/.openclaw/workspace && python3 brain/barnhaus_design_brain.py [submission_id]
```

### Step 3: Post Design Brief for Review
- The brain outputs a JSON file saved to workspace/designs/design_XXXX.json
- The brain does NOT generate floor plan images — do NOT try to create or post fake SVG/PNG floor plans
- Read the JSON and post the design brief as formatted text: room list, dimensions, layout highlights, exterior style
- Ask Mitch: "Approve or request changes?"

### Step 4: Handle Feedback
- If approved → confirm "✅ Ready for Revit execution. Mitch — go ahead when ready."
- If changes requested → note the changes and re-run brain with updated parameters

### Step 5: Track Status
Keep track of each submission status in memory/pipeline-state.json:
- pending → brain_running → review → approved → building → complete
