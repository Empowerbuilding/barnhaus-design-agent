# Barnhaus Design Agent

AI-powered design automation for Barnhaus Steel Builders. Takes a client intake submission and produces a complete Revit model — walls, floors, roofs, doors, windows, fixtures, and room labels.

## How It Works

1. Client fills out [design intake form](https://design.barnhaussteelbuilders.com)
2. Submission stored in Supabase (`hbfjdfxephlczkfgpceg`, table: `design_intake_submissions`)
3. `barnhaus_design_brain.py` runs the submission through two fine-tuned GPT-4o models:
   - **Layout model** (`barnhaus-v4`) — generates room layout, footprint, circulation
   - **Elevation model** (`barnhaus-elev-v2`) — generates roof, cladding, fenestration
4. Output feeds into staged Revit build scripts that call the local Revit MCP bridge
5. Revit model built automatically: exterior shell → interior walls → doors/windows → fixtures

## Structure

```
brain/                  # Core AI + Revit utility modules
  barnhaus_design_brain.py     # Main entry point — runs fine-tuned models
  barnhaus_planner.py          # Layout planning logic
  barnhaus_revit_utils_v2.py   # Revit bridge helpers (walls, floors, roofs, fixtures)
  scan_revit_template.py       # Scans Revit template for available families/types

build_scripts/          # Per-submission Revit build scripts (staged)
fixtures/               # Per-submission fixture placement scripts

training_data/          # Fine-tuning pipeline
  barnhaus_v3_combined.jsonl          # Floor plan training data (v3/v4)
  barnhaus_elevation_training.jsonl   # Elevation training data
  build_jsonl.py / build_jsonl_v2.py  # Scripts to generate JSONL from extractions
  build_elevation_jsonl.py            # Elevation JSONL builder

revit_bridge/           # PowerShell scripts for Revit MCP bridge management
  rebuild_and_copy.ps1  # Rebuild + deploy bridge DLL
  revit_fix_icons.ps1   # Fix icon crash on startup
```

## Current Fine-Tuned Models

| Model | ID | Trained Tokens | Final Epoch Loss |
|---|---|---|---|
| Floor plan v4 | `ft:gpt-4o-2024-08-06:personal:barnhaus-v4:DI9LtTgM` | 121,896 | 0.56 |
| Elevation v2 | `ft:gpt-4o-2024-08-06:personal:barnhaus-elev-v2:DI9VoKUx` | 156,282 | 0.87 |

## Revit Bridge

The Revit MCP bridge runs locally on Windows and exposes `http://localhost:3000`.
- Health check: `curl http://localhost:3000/health`
- DLL: `C:\ProgramData\RevitMCP\bin\RevitBridge.dll`
- WSL networking requires mirrored mode (`.wslconfig`)

## Usage

```bash
python3 brain/barnhaus_design_brain.py <submission_id_prefix>
```
