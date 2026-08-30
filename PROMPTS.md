# PROMPTS.md — Phased Prompt Sequence for Blueprint Development

Companion to `ROADMAP.md`. The roadmap says *what* and *why*; this file is the
*run sheet* — the exact prompts to fire (to Tony, unless noted), in order,
with prerequisites and what "done" looks like for each. Run one phase at a
time; don't start a phase until the previous one's expected output exists.

Code for Phases 2–4 already exists on the `dev/verify` branch (UNTESTED — see
`DEV_NOTES.md` there). Those phases are desk sessions to validate + merge,
not greenfield builds.

---

## Phase 0 — Unblock Michael (2 prompts)

Michael can't co-develop until he's in the repos/channels and his machine has
the bridge stack. Two prompts, second one only after he replies to the first.

### Prompt 0.1 — Invites + onboarding package

> **Run:** "Tony — send Michael the Blueprint onboarding package: GitHub org
> invite to Empowerbuilding (barnhaus-design-agent + revit-bridge repos),
> portal access, and a short written setup overview (what Blueprint is, how
> master=live works, where ROADMAP.md / RULES_BACKLOG.md live). Draft the
> email for my approval first."

- **Prerequisites:** Michael's GitHub username + email confirmed.
- **Expected output:** Draft email for approval → sent; Michael accepts org
  invite; he replies confirming access and a time for the install session.

### Prompt 0.2 — Diagnostic + install session (after his reply)

> **Run:** "Tony — Michael's ready. Walk him through the bridge install live:
> run the environment diagnostic on his machine (Revit version, .NET, admin
> rights, cloudflared), then install the RevitBridge DLL via the Bridge
> Updater, start a tunnel, and confirm Blueprint can read his open model with
> `get_document_info`. Log any machine-specific quirks to REVIT_BRIDGE.md."

- **Prerequisites:** Prompt 0.1 complete; Michael at his machine with Revit
  installed; a scheduled window (~1 hr).
- **Expected output:** Bridge healthy on Michael's machine; Blueprint reads
  his active document by name; quirks documented.

---

## Phase 1 — Tunnel Auto-Connect (Roadmap Priority 2)

### Prompt 1.1 — Build the auto-connect script

> **Run:** "Tony — build the tunnel auto-connect for Mitch + Michael's
> machines: a startup script/tray task that launches cloudflared on boot (or
> Revit launch), captures the tunnel URL, and writes it to Blueprint's
> `bridge_sessions.json` via the portal API under the right channel key —
> zero manual steps. Deliver as an installer/instructions I can run on both
> machines."

- **Prerequisites:** Phase 0 done (both machines have working manual tunnels).
- **Expected output:** Script + install steps for both machines; after
  reboot, Blueprint sees a fresh tunnel URL without anyone pasting anything;
  Blueprint announces whose session/model he's reading.

---

## Phase 2 — Verify (Roadmap Priority 1 ⭐)

Three prompts: Juanito's intent pipeline, then the desk session validating
the query primitives, then the McGee end-to-end.

### Prompt 2.1 — Intent pipeline (Tony/Juanito side)

> **Run:** "Tony — build Juanito's structured intent pipeline: create the
> `design_intent_items` table in the portal Supabase (id uuid, project_name,
> item, category, check_type, check_params jsonb, status, source, details
> jsonb, created_at, updated_at) and have Juanito convert client
> transcripts/feedback into rows with check_type ∈ room_region /
> element_present / element_absent / manual. Seed it with the McGee items
> (master suite flip, stone rework, wainscot removal)."

- **Prerequisites:** none (portal side only).
- **Expected output:** Table live; McGee rows seeded; Juanito's ingest
  documented.

### Prompt 2.2 — Desk session: validate query primitives

> **Run:** "Tony — desk session on the dev/verify branch: with a model open
> and the tunnel up, run `python3 run.py standards`, `weight`, and the
> intent_queries primitives one by one. Fix the bridge response-shape
> assumptions listed in DEV_NOTES.md (element dict keys, Rooms result key,
> Title Blocks category). Provision the portal key in Blueprint's container."

- **Prerequisites:** dev/verify branch (exists), Phase 1 tunnel up, any real
  model open (Open Home V2 fine).
- **Expected output:** All DEV_NOTES.md assumption checkboxes ticked or
  fixed; primitives return correct rooms/ids/regions on a known model.

### Prompt 2.3 — McGee end-to-end

> **Run:** "Tony — run `python3 run.py verify McGee` against the McGee model
> with Juanito's seeded intent rows. Confirm every line's PASS/FAIL matches
> what we know is true in the model, confirm statuses land back in Supabase,
> then merge dev/verify to master."

- **Prerequisites:** Prompts 2.1 + 2.2 done; McGee model available.
- **Expected output:** Correct pass/fails with zero manual model inspection;
  rows updated to verified/failed with evidence in details; branch merged,
  CI green.

---

## Phase 3 — Standards + Gate (Roadmap Priorities 3–4)

### Prompt 3.1 — Author standards.yaml with Michael

> **Run (to Michael, with Tony assisting):** "Michael — fill in
> standards.yaml on master: the canonical Barnhaus sheet order, the sheet
> numbering grammar, the minimum required views for a submittable set, and
> the exact titleblock family name. Every TODO in the file tells you what
> goes where. Commit directly — it's data, not code."

- **Prerequisites:** Phase 2 merged (runner is live); Michael onboarded.
- **Expected output:** standards.yaml with zero TODOs; `python3 run.py
  standards` enforces his rules on the next run.

### Prompt 3.2 — Gate on a real submission

> **Run:** "Tony — next Upworker submission: Michael opens the file, runs
> `python3 run.py gate <project> --post`, and we review the posted report in
> juanito-production together. Tune the verdict rules (what fails the gate
> vs. what's a note) based on that session."

- **Prerequisites:** 3.1 done; a live drafter submission.
- **Expected output:** One command produces the combined
  standards+verify+QA report with GATE: PASS/FAIL; report lands in the
  portal channel; Michael reads a report instead of hunting a model.

---

## Phase 4 — Weight (Roadmap Priority 5)

### Prompt 4.1 — Weight report on a 550MB file

> **Run:** "Tony — open one of the 550MB problem files and run `python3
> run.py weight`. Strip the top of the hit list (imports first, then heavy
> families), re-save, and record before/after file size. If the report's
> blind spots (per-family byte size, purge-unused) blocked real wins, spec
> the DLL commands needed and add them to the bridge backlog."

- **Prerequisites:** Phase 2 merged (weight command lives on dev/verify).
- **Expected output:** Measured MB reduction on a real file; either "hit
  list was enough" or a concrete DLL command spec.

---

## Phase 5 — Documentation Automation (Roadmap Priority 6, one session each)

Run these as four separate sessions, in order — each is useful alone.

### Prompt 5.1 — Sheets

> **Run:** "Tony — build `run.py make-sheets`: create the standard Barnhaus
> sheet set per standards.yaml (cover, plans, elevation/section sheets) with
> correct titleblocks, naming, order, and place existing views with
> consistent positioning. Validate on a D1-complete model."

- **Prerequisites:** Phase 3 done (standards.yaml authored — sheets are
  driven by it).
- **Expected output:** Empty-but-correct sheet set generated in one command;
  gate's sheet rules pass on it.

### Prompt 5.2 — Elevations

> **Run:** "Tony — build elevation generation: 4 exterior elevations with
> correct crop/scale, placed on their sheets per standards.yaml. Known bridge
> gap: elevation-view dimensions are broken — scope that separately."

- **Prerequisites:** 5.1 done.
- **Expected output:** 4 placed, correctly cropped elevations on a real model.

### Prompt 5.3 — Sections

> **Run:** "Tony — build cross-section generation: section lines at the right
> cuts (bearing walls, stairs, roof transitions), generated views placed on
> sheets. Pair with the 2D typical cross-section templates the drafters use."

- **Prerequisites:** 5.2 done.
- **Expected output:** Sections generated + placed; Michael judges cut
  placement acceptable.

### Prompt 5.4 — Dimensions

> **Run:** "Tony — extend the existing dimension commands into the generated
> views: exterior/interior dimension passes on the new plans and (bridge
> permitting) elevations. Close the loop: model done → reviewable sheet set
> in one command."

- **Prerequisites:** 5.1–5.3 done.
- **Expected output:** `run.py all`-style single command from D1-complete
  model to a reviewable, dimensioned sheet set; Michael polishes instead of
  produces.

---

## Standing Prompt — Rules Backlog Conversion (run weekly, forever)

> **Run:** "Tony — sweep RULES_BACKLOG.md: convert every pending plain-English
> entry into an executable rule (standards.yaml entry or run.py/qa check),
> move it to the Converted section with the commit hash, and note anything
> that needs new bridge DLL support."

- **Prerequisites:** Phase 3 live (rules have somewhere to go).
- **Expected output:** Pending section trends toward empty; every converted
  entry cites its commit; drafter mistakes become rules the same week
  they're caught.
