# Barnhaus Revit Copilot

AI-powered Revit documentation automation for Barnhaus Steel Builders.

You do the modeling. This handles everything else.

---

## What It Does

| Command | What happens |
|---|---|
| `scan` | Reads the open Revit model — rooms, walls, doors, windows, views, sheets |
| `qa` | Checks for door swing conflicts, cabinet clearances, room sizing, off-axis walls |
| `qa --fix` | Same as QA + auto-fixes what it can (flip door swings, snap walls to axis) |
| `draft1` | Creates A100, A101.1, A102.1, A103 — places floor plan views on sheets |
| `draft2` | Creates A105, A106, A106.1, A106.2, A107, A107.1, A107.2 — elevations + schedules |
| `draft3` | Creates A104, A108.1, A109.2 — structural grid + electrical + plumbing plans |
| `schedule` | Generates door & window schedule (A105) |
| `dimensions` | Applies 3-string dimension system to floor plans |
| `electrical` | Auto-places GFIs, dedicated circuits, recessed cans, smoke detectors, ceiling fans |
| `plumbing` | Tags fixtures, places hose bibs, adds water heater/softener callouts |
| `all` | Full run: scan → QA → Draft 1 → 2 → 3 |

All commands are idempotent — safe to run twice, skips what already exists.

---

## Prerequisites

1. **Revit open** with the MCP bridge addin loaded
   - Addin DLL: `C:\ProgramData\RevitMCP\bin\RevitBridge.dll`
   - Bridge source: `C:\Users\mitch\Autodesk-Revit-MCP-Server`
   - Connect via the Revit ribbon button → bridge starts on `http://localhost:3000`

2. **Python 3.11+** with `requests` installed:
   ```bash
   pip install requests
   ```

3. **Rooms placed and named** in Revit before running QA or documentation tasks.
   The agent reads room names to understand the program — "Master Bedroom", "Kitchen", etc.

---

## Usage

```bash
# From WSL or Windows terminal, in this repo directory:

python3 run.py scan          # Start here — scan open project
python3 run.py qa            # Check for issues
python3 run.py qa --fix      # Check and auto-fix
python3 run.py draft1        # Build Draft 1 sheets
python3 run.py draft2        # Build Draft 2 sheets
python3 run.py draft3        # Build Draft 3 (MEP + structural)
python3 run.py all           # Everything in one shot
```

---

## Repo Structure

```
core/
  revit_client.py       Low-level MCP bridge calls (all Revit API goes through here)
  constants.py          Family names, wall types, room norms, sheet standards, QA thresholds
  project_state.py      Scans open Revit model → project_state.json

qa/
  door_qa.py            Door swing conflicts, latch clearance, egress width
  room_qa.py            Room sizing, adjacency rules, circulation checks
  cabinet_qa.py         Kitchen aisles, toilet clearances, shower dimensions
  model_integrity.py    Off-axis walls, short walls, unclosed rooms
  qa_runner.py          Runs all checks, prints report, applies auto-fixes

tasks/
  sheets/
    draft1_bundle.py    A100, A101.1, A102.1, A103
    draft2_bundle.py    A105, A106-A106.2, A107-A107.2
    draft3_bundle.py    A104, A108.1, A109.2
  schedules/
    door_window_schedule.py   Generates A105
  dimensions/
    dimension_plans.py  3-string exterior dimension system
  mep/
    electrical.py       GFIs, circuits, cans, fans, smoke detectors
    plumbing.py         Fixture tags, hose bibs, equipment callouts

docs/
  barnhaus-design-rules.md    Full Barnhaus design rulebook (40+ sections)
  HOME_LAYOUT.md              Residential design principles, room sizing, adjacency matrix
  REVIT_TEMPLATE.md           Family names and types in the Barnhaus template
  revit-agent.md              Architecture notes and design decisions

reference/
  revit_template_manifest.json    Live scan of Revit template (families, types, levels)
  murrell_diagnostic.json         Real project data — Murrell build
  truelock_diagnostic.json        Real project data — Truelock build
  wirch_diagnostic.json           Real project data — Wirch build
```

---

## QA Severity Levels

| Level | Meaning |
|---|---|
| 🔴 **fix** | Must address — code violation or clear error |
| 🟡 **consider** | Best practice violation — worth reviewing |
| 🔵 **fyi** | Informational — no action required |

Auto-fixable issues (door swings, off-axis walls) are marked with ⚡ in the report.

---

## Barnhaus Sheet Standard

| Draft | Sheets |
|---|---|
| Draft 1 | A100 Cover, A101.1 Floor Plan L1, A102.1 Dim Plan L1, A103 Roof Plan |
| Draft 2 | + A105 Schedule, A106/A106.1/A106.2 Exterior Elevs, A107/A107.1/A107.2 Interior Elevs |
| Draft 3 | + A104 Structural Grid, A108.1 Electrical L1, A109.2 Plumbing L1 |
| Two-story adds | A101.2, A102.2, A108.2, A109.3 |

---

## Claude Code Integration (MCP)

To use with Claude Code, add to your MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "revit": {
      "command": "C:\\Users\\mitch\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
      "args": ["-m", "revit_mcp_server.mcp_server"],
      "env": {
        "MCP_REVIT_WORKSPACE_DIR": "C:\\Users\\mitch\\Documents",
        "MCP_REVIT_ALLOWED_DIRECTORIES": "C:\\Users\\mitch\\Documents",
        "MCP_REVIT_BRIDGE_URL": "http://127.0.0.1:3000",
        "MCP_REVIT_MODE": "bridge"
      }
    }
  }
}
```

Bridge source: `C:\Users\mitch\Autodesk-Revit-MCP-Server`
