# SCREEN EYES RULES (revit.capture_screen)

**Rules (non-negotiable):**
1. **Context-Driven Only:** Capture ONLY when Michael or Mitch is actively working with the agent and it serves the current task — never on a timer, never in the background without explicit coordination.
2. **Phase A (Eyes Only):** Do NOT implement any mouse/keyboard input synthesis. That is Phase B and requires explicit approval from Mitch later.
3. **Data Privacy:** Screenshots may contain personal content — never copy them anywhere outside the OpenClaw workspace (`/home/node/.openclaw/workspace/`), and proactively delete stale screenshots from the `exports/` folder to manage storage and limit exposure.

## Vision Input Limits (hard rule — added 2026-11-01)

The `image` tool (glm-5.3-flash primary, gemini fallbacks) **hard-rejects images over 25,000,000 px**. An oversized export = a failed vision call (2–4 min wasted) followed by a slow deep-model fallback. (2026-11-01 incident: "count the can lights" took 12.6 min because two 5220×6432 zoom crops blew the limit.)

**Rules:**
1. Every image destined for the `image` tool must be fit first: `python3 core/fit_image.py <file> [<file2> ...]` — default caps at 4000 px long edge / 20M px total. `run.py look` and `save_view_image()` now do this automatically.
2. For counting/detail questions on sheets, do NOT export one giant image and hope — export a tight crop of the region (then fit it), or use the tiling pipeline: `python3 run.py export-tiles <view_id>` and inspect the tiles (qa/visual_qa.py pattern: overview + ~1500px tiles).
3. `save_view_image()` fits by default; pass `max_long_edge=None` only when you tile locally afterwards (qa/visual_qa.py does this).

## Atomic Vision Checks (hard rule — added 2026-11-01)

Multi-point "verify 1,2,3,4..." prompts through the `image` tool make glm-5.3-flash
think in 4-16K-char essays: 65-91s per call, sometimes the whole output budget
burns on thinking → zero-character answer → silent retry/fallback. z.ai ignores
`thinking` budget_tokens (tested). This cost ~13 min of pure vision-wait on the
11/1 Miller permit run.

**Rules:**
1. Any visual QA with 2+ checks goes through `qa/vision_checks.py` — atomic
   single-question calls, run in parallel, verdict-tagged `[PASS]/[FAIL]/[UNCLEAR]`,
   auto-retry on empty answers:
   `python3 qa/vision_checks.py <img1> <img2> --check "text:Any colliding annotation text?" --check "title:Title blocks correct?"`
   One `--check` per question. Never bundle points into one prompt.
2. Spatial comparisons (footprint vs plan, geometry matching): export tight crops
   of the two regions first. Full-sheet comparisons are the slowest/hardest case
   for the model (measured: 40-80s or UNCLEAR on full sheets, seconds on crops).
3. glm-4.6v (`--model glm-4.6v`, or `kind "fast:"`) only for coarse checks (blank
   sheets, rough counts) — it compresses images ~65x harder and misses fine detail
   that flash catches (title text, note collisions).
4. UNCLEAR verdicts are honest signals — re-ask with a tighter crop or a more
   specific question; do not re-roll the same question hoping for a different mood.
5. For tile-by-tile sheet inspection at high res, the existing pipeline is still
   king: `run.py export-tiles` + `qa/visual_qa.py` (parallel Gemini workers).
