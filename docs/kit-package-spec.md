# kit_package — CFS Kit BOM Pipeline (Blueprint Phase: Kit Pipeline)

**Business goal:** Barnhaus sells design packages; every buyer needs a steel kit.
Fabricators (e.g. Accurate Steel Fab, Dallas) charge ~$2.09/lb retail for
frame+trusses and take ~5 days to price a raw plan set because a human detailer
must model it in FRAMECAD Structure first. This pipeline generates the
takeoff/BOM directly from the Revit model, so:
1. Same-day ballpark kit quotes for customers (lbs × rate)
2. Fabricators quote from a member schedule instead of raw PDFs (days → hours)
3. With PE-stamped engineering (Juston Ford) on top, fabricators become
   toll-manufacturers → Barnhaus captures detailing + dealer margin.

## Ground truth / calibration source
`workspace research/asf-allen-quote/` (Tony's machine) — ASF "Allen" quote
Nov 2025: BOM.pdf (FRAMECAD Manufacturing Summary), 35,510 lbs, frame+trusses
$74,215.50 (= $2.09/lb). Empirical plf per profile encoded in `profiles.py`.
**The Allen Revit model (`Allen Study Setrvt.rvt`) is the validation target:**
run `python3 run.py kit "Allen"` on that model and compare against ASF's tabs:

| ASF tab | Profile | LF | lbs |
|---|---|---|---|
| Panel.1 | 362S162-43-50 | 5,325.96 | 6,370.4 |
| Panel.1 | 600S162-43-50 | 5,623.92 | 8,805.3 |
| Panel.1 | lintels (3 profiles) | ~38 | 60.8 |
| Panel.1 | S7x15.3 (hot-rolled) | 121.69 | 1,861.8 |
| Truss.1 | 362S162-33-50 | 19,855.04 | 18,411.9 |
| **Total** | | | **35,510.4** |

Acceptance: total lbs within ±10% of 35,510 after calibration; per-tab within ±15%.

## Module layout (`tasks/kit_package/`)
- `profiles.py` — SSMA/FRAMECAD profile catalog. Empirical plf (ASF-derived)
  preferred; computed fallback (developed width × design thickness × 3.4028)
  verified within ~1% of empirical. Default profile selection follows Allen
  precedent: 600S162-43 exterior, 362S162-43 interior, 362S162-33 trusses.
- `framing.py` — wall rules: studs 24" o.c., +2 king +2 jack per opening,
  cripples, 2× length track (aggregated under stud profile per fabricator BOM
  convention), lintels by width band, +5% blocking, prescriptive-limit flags.
- `trusses.py` — fink-style approximation (chords + WEB_FACTOR×span webs),
  gable studs, FRAMECAD plate counts (2 apex/heel + 4 fix per truss — Allen
  ratios). **WEB_FACTOR=1.4 is known-light: Allen truss tab is ~4× textbook
  fink LF. Must be solved against the live Allen model. Do not tune blind.**
- `bom.py` — Manufacturing Summary output (text/CSV/JSON), fastener counts
  (0.0881 flathead + 0.6141 XDrive per lb — Allen ratios), $/lb ballpark.
- `extract.py` — live geometry pull via existing bridge commands only
  (get_all_walls/doors/windows, get_parameter_value, bounding boxes).
  **No DLL changes required for v1.**
- `kit.py` — orchestrators: `run_live(name)` / `run_from_geometry(json)`.
- `fixture_test.py` — offline pipeline test + plf calibration assertions.

## CLI
```
python3 run.py kit "Allen"          # live: extract + BOM + ballpark
python3 run.py kit-geometry Allen   # live: geometry snapshot only
python3 run.py kit-from geo.json    # offline BOM from saved geometry
python3 run.py kit-test             # offline fixture test
```

## Engineering boundary (do not cross)
Output is a **takeoff/estimating package**, not engineering. Member sizing
is by Allen-precedent defaults + AISI S230 prescriptive envelope flags.
Anything flagged (tall walls, >8 ft openings, >40 ft spans) and ALL final
member sizing/connections/bracing go to the PE (Juston Ford) who is the
engineer of record. The BOM header must never claim engineered status.

## Roadmap
1. **v1 (now):** logic on file, fixture-tested offline. ✅
2. **Calibrate (Revit up):** extract Allen → solve WEB_FACTOR + wall-rule
   deltas until ASF tab totals match. Add per-plan geometry snapshots for
   catalog top-sellers (Bastion, Apex, Titan, Spring Mountain).
3. **Package v2:** panel elevation drawings (bridge view exports), load-input
   sheet per county (ASCE 7 wind/snow lookup), PDF assembly.
4. **PE loop:** Juston red-lines first Allen package → corrections become
   rules; define stamp handoff format.
5. **Fabricator loop:** send Blueprint package to ASF (James Hurt) for
   re-quote of Allen; measure turnaround + price delta vs Nov 2025 baseline.
6. **Scale:** kit quote package per catalog plan; wire into Shopify/Vanessa
   flow ("get your kit quote" upsell on every plan sale).
