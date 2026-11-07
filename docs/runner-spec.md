# Runner Spec — "Press Play" Draft Execution (v1, 2026-11-06)

**Goal:** after a client meeting, Mitch reviews ONE compiled work order and says "go".
Blueprint then executes the whole draft (phases, QA, saves, backups) autonomously and
posts a single summary when done / blocked. Mitch's involvement: approve plan, answer
decision cards, receive summary.

## What already exists (do not rebuild)

- Meeting → transcript → design-brain checklist (Juanito, `juanito-design-checklists`)
- Juanito's D2 package: sheet list (WORKFLOW.md v4), decisions w/ verbatim timestamps
- Inspiration bank + palette (`projects/<name>/inspo/`, `inspo_palette.md`)
- Model scan + redline reading (A101.1 notes), RESUME.md pickup files
- Save & Checkpoint doctrine + `qa-model` gate (AGENTS.md, 2026-11-06)
- Vision QA (`export-tiles`, `qa-visual`), bridge 262 commands
- Fresh-session-per-phase pattern (proven on Deubner: resets lost nothing with RESUME.md)

## 1. Work Order (the contract Mitch approves)

`projects/<name>/work_order.json` — compiled by the **compiler** (Blueprint, on request
"compile the work order for <project>"), from: checklist + Juanito package + decisions +
inspo palette + D1 sheet diff + live model scan.

```json
{
  "project": "Deubner",
  "doc": "Deubner D2.rvt",
  "draft": 2,
  "compiled_at": "...",
  "phases": [
    {
      "id": "P1",
      "title": "Roof stack 22in + snow guards",
      "brief": "what to do, references (decision verbatims, sheet targets)",
      "depends_on": [],
      "est_minutes": 25,
      "verify": {"qa_model": true, "vision": "A103 sheet export"}
    },
    {
      "id": "P2",
      "title": "Sheets A100–A101 from model",
      "depends_on": ["P1"],
      "verify": {"qa_model": false, "vision": "sheet tiles"}
    }
  ],
  "decision_points": [
    {"phase": "P3", "question": "rear slider: option A/B/C", "default": "B",
     "source": "transcript 29m14s"}
  ]
}
```

Rules: phases are orderable by dependency, each independently verifiable + savable;
decision points carry a default so the runner can proceed and flag.

## 2. The Gate (preserves the Execution-Gate rule)

The work order is posted to `blueprint-mitch` as a readable plan. **Nothing executes
until Mitch replies "go" (or edits the plan first).** This is the single approval —
stronger than 15 reflexive "go"s. Juanito-originated content still cannot fire anything
by itself.

## 3. Runner (host-side dispatcher, `blueprint_runner.py` on DO host)

- Watches `projects/<name>/work_order.json` + a `runner_state.json` (phase status).
- For the next pending phase: posts a **phase brief** to `blueprint-mitch` as a
  user-sender message (wakes Blueprint): "Execute phase P2 per work_order.json …".
- Blueprint (fresh or existing session): reads work order + RESUME.md → executes →
  `qa-model` gate → save → backup → posts `PHASE_DONE P2 <result>` card.
- Dispatcher sees the card (or the state file update) → marks P2 done → posts next brief.
- **Stop conditions:** decision point reached → post decision card, continue phases that
  don't depend on it; QA fail ×2 → mark blocked, continue independent phases; bridge
  down / wedge signature (command timeout w/ healthy /health) → alert card, pause;
  save fail → hard stop, alert.
- **4am reset compatibility:** dispatcher drives one phase at a time; resets between
  phases are harmless (that's the design). Never resets mid-phase — check session state
  before the 4am reset fires, defer if processing.
- **Morning summary:** when all phases terminal (done/blocked), post the summary card:
  done list, blocked list + why, decisions taken with defaults, backups taken.

## 4. Failure modes to design for (from live incidents)

- Revit dialog wedge (commands timeout, health OK) → dispatcher detects, alerts,
  queues-resume; never silently retries into a wedged queue.
- Tunnel death mid-run → pause + alert; resume when /health answers again.
- Compaction failure mid-phase → RESUME.md + work_order.json make the phase re-entry
  safe; dispatcher re-briefs the same phase after reset.
- Michael's doc open instead of Mitch's → phase briefs always state the expected doc;
  mismatch = pause + alert, never touch the wrong model.

## 5. Build order

1. `work_order.json` schema + compiler prompt section in AGENTS.md (Blueprint compiles)
2. `blueprint_runner.py` dispatcher + state file (Tony, host cron */2)
3. PHASE_DONE card format contract (Blueprint side, AGENTS.md)
4. Pilot: re-run a completed project's plan in a COPY of the .rvt (e.g. Deubner D2 →
   D2-runner-test.rvt) and diff outcomes vs the manual run
5. First live pilot: smallest active project's next draft

## 6. Explicitly out of scope (v1)

- No overnight PDF/email sends to clients; summary goes to portal only
- No multi-project parallelism; one work order active at a time
- No autonomous family downloads mid-run (pre-stage families in the phase brief)
