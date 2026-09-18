# Kit Pipeline — Engineering Judgment Rules (code-sourced)

This doc is the citation backing for `tasks/kit_package/judgment.py`, and the
reference Blueprint should use when interpreting kit BOM flags. Verified
against live sources 2026-09-17.

## Span thresholds (roof trusses)

| Span | Regime | Source | Pipeline confidence |
|---|---|---|---|
| ≤ 40 ft | Prescriptive CFS roof framing allowed | **IRC R804** — applies to buildings ≤60 ft perpendicular to truss span, ≤40 ft parallel to truss span | HIGH |
| 40–60 ft | Engineered truss design required; routine for FRAMECAD-class fabricators | IRC R804 exceeded; AISI S214/S240 truss design governs | MEDIUM |
| ≥ 60 ft | Code-mandated **special inspection** of truss bracing during erection; interior bearing or primary steel likely | **IBC 2206.1.3.2** | LOW — treat truss weight as placeholder |
| 80+ ft | Feasible but heavy engineering (Alpine TrusSteel manual shows 80+ ft engineered CFS trusses) | industry practice | LOW |

Calibration note: our empirical truss intensity (4.41 LF/sqft plan) is ground-
truthed at **46.3 ft span** (ASF Allen). The further a span sits from that
point, the less trustworthy the truss weight — regardless of code regime.

**Bounding-box caveat:** `extract.py` derives span from the roof bounding box.
L-shaped, T-shaped, or multi-mass roofs can overstate true clear span. When a
big span triggers LOW confidence, first check the model for interior bearing
walls / multiple roof masses before escalating (Blueprint can do this:
list walls under the ridge line, check `Structural Usage` = Bearing).

## Wall heights

| Height | Regime | Source |
|---|---|---|
| ≤ 10 ft | AISI S230 prescriptive stud tables apply | **AISI S230** (Prescriptive Method for 1-2 Family Dwellings) |
| > 10 ft | Outside stud tables — engineered gauge/spacing (often 54+ mil or 16" o.c.) | AISI S240 design |

Tall great-room/gable walls (16–21 ft) are normal in Barnhaus designs — they
just move those walls from table-lookup to PE-sized. Weight estimate runs
LIGHT on tall walls (we assume the default gauge).

## Openings / headers

| Width | Treatment | Source |
|---|---|---|
| ≤ 4 ft | 600x125x33 lintel (ASF Allen precedent) | fabricator practice |
| 4–6 ft | 600x125x43 lintel | fabricator practice |
| 6–8 ft | 850x125x54 lintel | fabricator practice + AISI S230 header tables end ~8 ft |
| > 8 ft | Hot-rolled header (S/W section), PE-sized; allowance added | ASF Allen used S7x15.3 |

## Fixed reference points (ground truth)
- ASF Allen BOM: 35,510 lbs, 46.3 ft span, validated pipeline output -0.66%
- ASF retail rate: $2.09/lb frame+trusses (Nov 2025)
- IBC/IRC citations verifiable at up.codes (searched: "cold-formed steel
  trusses spanning 60 feet", "Section R804 cold-formed steel roof framing")

## What Blueprint should do with LOW-confidence outputs
1. Check the bbox caveat first (real clear span vs bounding box)
2. Report the number WITH its confidence tier — never strip the caveat
3. Recommend the PE path (Juston Ford) for anything LOW
4. Never present a LOW-confidence ballpark to a customer as a quote

## Standing rule
Numbers come from tables and calibration; **judgment comes from cited code
thresholds; final authority is the PE.** The pipeline's job is to make the
PE's job small, not to replace it.
