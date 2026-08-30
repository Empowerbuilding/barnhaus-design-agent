# Blueprint Development Roadmap

**Owners:** Mitch + Michael (co-development, straight-to-master, master = live on the agent)
**Written:** 2026-08-30 · Maintained by Tony

---

## Why This Roadmap Exists

Barnhaus's design pipeline runs 6-10 weeks per contract: Concept → D1 (Michael) → client review → Upworker detail → polish → D2 → Upworker systems → polish → D3 → final set. Michael touches every phase and is the hard constraint on throughput.

Where the time actually bleeds (real examples from our own history):

| Leak | Evidence | Cost |
|---|---|---|
| Client intent missed in a draft | McGee: master suite flip, stone rework, wainscot removal — living in a transcript | Every miss found at client review = full extra loop (~1-2 weeks) |
| Drafter errors found late | Dunn: entire garage missing from submission | Michael hunts errors manually; misses leak to clients |
| Michael as QA bottleneck | He reviews every Upworker pass by hand | Hours not spent on concepts/sales |
| Vacant QA role | "Revit Mechanic" hire ≈ QA/QC + sheet enforcement | $4-6k/mo for pattern-matching work |
| Drafter padding | Forced move to fixed-price milestones | No objective acceptance test = disputes |

**The target:** Juanito (knows what's *supposed* to be in the model) + Blueprint (knows what *is* in the model) close the loop automatically. Expected impact: ~20-30% more projects/year through the same pipeline, Michael's QA time down 70-80%, fixed-price drafting enforceable, Revit Mechanic hire shrunk or delayed.

**What we're NOT building:** auto-generation of building *models* (draft-from-scratch). QA/verification of human-made models has provable ROI this quarter; model generation is a research project. Park it.

**What we ARE building toward (Priority 6):** auto-generation of *documentation* — sheets, elevations, cross-sections. That's the Upworker leg of the pipeline (3-5 days per handoff). Different problem, and the bridge already has the primitives.

---

## Priority 1 — `verify`: Intent-vs-Model Diff ⭐ THE PRODUCT

The McGee flow, automated. Juanito maintains a structured per-project intent checklist (Supabase — Tony builds that side); Blueprint gets a `verify` command that takes the checklist and returns pass/fail per item with element evidence.

**Build (run.py + bridge as needed):**
- `python3 run.py verify <project>` — pulls intent items, runs targeted model queries, emits a pass/fail/unknown report per item
- Targeted query primitives: room location by name + compass region, element existence by category/type/keyword (e.g. wainscot sweeps on exterior walls), parameter checks (SF, counts, materials)
- Report format: one line per item — `✅ Master Suite south: Room "Master" found, south half` / `❌ Wainscot: 14 sweep elements still on exterior walls (ids...)`

**Done when:** a real project (McGee) runs end-to-end — transcript feedback → checklist → verify → correct pass/fails — with zero manual model inspection.

---

## Priority 2 — Kill Tunnel Friction 🔌 ADOPTION DEPENDS ON THIS

Manual `cloudflared tunnel` + `/connect` every session is why the June setup died. If connecting is annoying, nobody connects, and nothing else on this list matters.

**Build:**
- Small per-machine script/tray app (Mitch + Michael): auto-start a tunnel on boot (or Revit launch), auto-register the URL with Blueprint via portal API — zero manual steps
- Blueprint: tunnel health awareness per user; announce whose session/model he's reading (already in bootstrap, keep honoring it)

**Done when:** Michael opens Revit and Blueprint can see his model without Michael typing anything.

---

## Priority 3 — Drafter Submission QA Gate 🚧

Zunaira/Arooba (or any Upworker) submits → Michael opens the file → **one command** runs the standard QA suite → results auto-post to the production task + studio channel via Juanito.

**Build:**
- `python3 run.py gate` — runs the standards checklist (Priority 4 rules file) + verify (Priority 1) + existing qa checks in one shot
- Auto-post: report lands in the relevant `studio-*` channel and the production_tasks record
- Output doubles as the fixed-price acceptance criteria: milestone paid when gate passes

**Done when:** a drafter submission gets gated with zero Michael hunting — he reads a report, not a model.

---

## Priority 4 — Data-Driven Standards Rules 📋

Barnhaus standards (sheet order, sheet naming, titleblocks, required views, layer/type conventions) live in a **rules file** (YAML/JSON) in this repo — Michael edits rules without touching code.

**Build:**
- `standards.yaml` — first pass authored by Michael (this is his institutional knowledge, captured)
- Rule runner in run.py that executes the file against the model via bridge queries
- Rules are versioned with git like everything else

**Done when:** Michael adds a new rule by editing the file, no code change, and the next `gate` run enforces it.

**Ongoing — the Rules Backlog:** the checks we have today are a fraction of what Mitch + Michael carry in their heads. Teaching Blueprint is a continuous process, not a phase:
- `RULES_BACKLOG.md` in this repo — either of you dumps checks in plain English whenever they occur to you ("flag any door within 4\" of a wall corner", "every wet wall needs a plumbing note")
- Converting backlog entries → executable rules is standing dev work; expect this to be a large share of total effort over time
- Rule of thumb: every mistake a drafter makes becomes a rule the same week it's caught

---

## Priority 5 — Model Weight Report 🏋️

550MB files are stalling portal uploads. Make the strip-to-2D effort targeted instead of guesswork.

**Build:**
- `python3 run.py weight` — reports top file-size drivers: heavy families, imported CAD, unused families/types, 3D detail elements that should be 2D
- Output: ranked hit list ("strip these 12 families first")

**Done when:** running it on one of the 550MB files produces a hit list that actually shrinks the file.

---

## Priority 6 — Documentation Automation: Sheets, Elevations, Cross-Sections 📐 THE BIG ONE LONG-TERM

Today, the D2/D3 Upworker legs are humans turning the model into documentation: elevations, cross-sections, detail views, sheet layout — 3-5 days per handoff plus polish. Blueprint generating this directly compresses days → hours and attacks drafter spend + drafter errors at the source.

**Build (incremental — each step is useful alone):**
1. **Sheet formatting:** auto-create the standard Barnhaus sheet set (A100 cover, A101.x plans, elevation/section sheets) with correct titleblocks, naming, and order per `standards.yaml`; place existing views on sheets with consistent positioning
2. **Elevations:** generate the 4 exterior elevations, correct crop/scale, placed and dimensioned
3. **Cross-sections:** section line placement at the right cuts (bearing walls, stairs, roof transitions), generated views, placed on sheets — pairs with the 2D typical cross-section templates (wood + metal framing) already being built for the drafters
4. **Dimensioning pass:** extend the existing exterior/interior dimension commands into the generated views

**Done when:** a D1-complete model can go from "model done" to "reviewable sheet set" in one command, with Michael polishing instead of producing.

**Sequencing note:** start after Priorities 1-2 are live (verify + tunnels prove the loop and build the habit), but pull individual pieces forward whenever they're cheap — sheet formatting especially, since it's mostly `standards.yaml` + existing bridge commands.

---

## Working Agreement

- **Master = live.** Blueprint hard-resets to `origin/master`. Don't push what you haven't run once locally. Experiments → branch, merge when working.
- CI syntax check runs on every push — a red X means do NOT let Blueprint pull.
- Blueprint reports the commit hash after every pull — when something acts weird, the hash tells you which version did it.
- Bridge DLL source: `Empowerbuilding/revit-bridge` (private). DLL changes deploy via the Bridge Updater on each machine — a bad push there breaks only your own machine until fixed.
- Blueprint never edits this repo himself. Script errors → he posts to tony-mitch.

## Division of Labor

| Piece | Who |
|---|---|
| run.py commands (verify, gate, weight), rules runner | Mitch + Michael |
| standards.yaml content | Michael |
| Bridge DLL query primitives | Mitch (+ Michael once ramped) |
| Juanito's structured intent pipeline (Supabase, transcript ingest) | Tony |
| Auto-posting / portal plumbing / channel wiring | Tony |
| Tunnel auto-connect scripts | Tony builds, Mitch + Michael install |
