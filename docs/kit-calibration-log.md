# kit_package — Calibration Log

Running record of every calibration round against ground-truth fabricator data.
Companion docs: `kit-package-spec.md` (architecture + roadmap),
`asf-allen-quote-analysis.md` (the answer key).

---

## Ground truth: ASF "Allen" production BOM (Nov 2025)
FRAMECAD Structure v11.1.12.0 output, detailer PAVAN. 35,510.4 lbs total.
Frame+trusses quoted $74,215.50 = **$2.09/lb retail benchmark**.

| Tab | Profile | LF | lbs |
|---|---|---|---|
| Panel.1 | 362S162-43-50 | 5,325.96 | 6,370.4 |
| Panel.1 | 600S162-43-50 | 5,623.92 | 8,805.3 |
| Panel.1 | 3 lintel profiles | ~38 | 60.8 |
| Panel.1 | S7x15.3 hot-rolled | 121.69 | 1,861.8 |
| Truss.1 | 362S162-33-50 | 19,855.04 | 18,411.9 |

Plates: 92 apex/heel + 184 fix (= 46 trusses). Screws: 3,128 flathead + 21,806 XDrive.

## Allen model extraction (2026-09-17, live via Blueprint)
81 walls (43 ext / 38 int), 28 doors, 21 windows.
Roof bbox: 46.3 ft span × 97.3 ft ridge, 5.4:12 pitch.
Ext wall LF 570 / int wall LF 350. Wall heights include 12 ft and 20 ft
sections (correctly flagged as beyond prescriptive envelope).

---

## Round 0 — first blind run (commit 3918d2e)
**Result: 19,490 lbs vs 35,510 = -45%**

| Component | Ours | ASF | Delta |
|---|---|---|---|
| 362 panels | 4,157.5 | 6,370.4 | -35% |
| 600 panels | 7,736.9 | 8,805.3 | **-12%** |
| Trusses | 7,587.8 | 18,411.9 | -59% |
| Hot-rolled | 0 (flagged only) | 1,861.8 | missing |

Findings:
1. **Truss heuristic 2.7x light.** ASF: 46 trusses @ ~24" o.c. over 97.3 ft
   ridge, 432 LF/truss = 9.32× span. FRAMECAD trusses = boxed/doubled chords
   + dense webs, nothing like textbook fink (~3.4× span).
2. **Openings: only 2/49 resolved** — Width/Height live on the door/window
   TYPE, not instance. Missing king/jack/cripple/lintel framing across model.
3. Exterior 600 walls -12% blind = wall rules fundamentally sound.
4. First run also exposed O(openings×walls) bbox fallback → 10-min agent
   timeout (fixed with bbox cache, one call per element max).

## Round 1 — calibrated (commit 4bd4582), offline re-run on same geometry
**Result: 32,186 lbs vs 35,510 = -9.4%** (inside ±10% spec target)

Changes:
- `trusses.py`: empirical intensity model — **4.41 LF/sqft roof plan**
  (= 19,855 / (46.3 × 97.3)). Gable framing folded into the factor.
  ⚠ single-point calibration; re-fit when second fabricator BOM lands.
- `kit.py`/`bom.py`: hot-rolled allowance when long-span flag trips:
  **1.25 × ridge LF of S7x15.3** → derived 122 LF / 1,861 lbs vs ASF's
  121.7 / 1,861.8 (exact match on Allen).
- `extract.py`: type-param fallback for opening widths + skip reporting.

| Component | Ours | ASF | Delta |
|---|---|---|---|
| Trusses | 18,422.7 | 18,411.9 | **+0.06%** |
| Hot-rolled | 1,860.9 | 1,861.8 | **exact** |
| CFS panels | 11,910 | 15,236 | -22% (openings not yet in geometry) |
| **TOTAL** | **32,186** | **35,510** | **-9.4%** |

## Round 2 — pending: re-extraction with opening type-param fix
Expectation: 47 more openings attach → king/jack studs + cripples + lintels
close most of the remaining panel gap. Target: within ±5% total.

Remaining known gaps after round 2 (candidates if still short):
- Interior stud spacing: ASF may run 16" o.c. interior (we assume 24")
- ASF panel tab may include ceiling battens/furring in the 362-43 bucket
- Wall-function misclassification (600 vs 362 assignment) for edge walls

---

## Calibration rules
1. Never tune blind — every constant change must trace to a fabricator BOM
   line or a published standard (SSMA/AISI/AISC).
2. Empirical beats computed: profile plf from production BOMs > formula.
3. One knob per round; re-run; log the delta here.
4. Every new fabricator quote (ASF re-quote, FrameTek, US Frame Factory…)
   becomes a new answer key — add it to this log and re-fit.
5. Acceptance: ±10% total lbs (spec), stretch ±5%. Ballpark pricing quality;
   NOT engineering — PE (Juston Ford) owns all final sizing.
