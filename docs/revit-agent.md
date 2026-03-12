# Revit Design Agent — Full Context

## What This Is
A plan to build an AI agent that works inside Revit on behalf of Mitch/Barnhaus Steel Builders.
Goal: Mitch gets a model to ~30% (basic walls, rooms, roof roughed in), hands it to the agent,
agent takes it to ~90% — all documentation sheets, electrical, plumbing, structural, schedules.

## The Barnhaus Design Process (studied across 3 real projects)

### Phase 1: Concept (before Revit)
A 6-page branded PDF delivered to client:
1. Cover — hero inspiration photo + project name + "By Barnhaus Steel" + Michael McAdams Designer
2. Starting Inspirations — client's Pinterest/reference images + aerial satellite of their actual lot
3. Conceptual Layout — hand-sketched floor plan with room labels, SF totals, client notes baked in
4. Conceptual Shape (Model) — 6 massing model renders from multiple angles + 1 interior shot (basic materials, focus on volume/rooflines)
5. Conceptual Textures — 3 photorealistic renders at dusk with real materials applied (Chaos V-Ray likely)
6. Ideas — designer notes on open decisions + Chaos Cloud 3D model link for client to explore

### Phase 2: Draft 1 (~4-7 sheets)
- A100 Cover Sheet
- A100.2 Site Plan (included in D1 if complex topography — cliff, retaining walls, drainage; otherwise added later)
- A101.1 Floor Plan Level 1
- A101.2 Floor Plan Level 2 (if multi-story)
- A102.1 Dimension Plan L1
- A102.2 Dimension Plan L2 (if multi-story)
- A103 Roof Plan

### Phase 3: Draft 2 (~10-18 sheets, the big visual leap)
Adds:
- A105 Door & Window Schedule
- A106 Exterior Elevations (front)
- A106.1, A106.2 Additional Exterior Elevations
- A107 Interior Elevations (kitchen — wine fridge, marble backsplash, ice maker)
- A107.1 Interior Elevations (master bath / tiled ceiling details)
- A107.2 Interior Elevations (laundry — washer/dryer, open shelves)
- A107.3, A107.4 Additional Interior Elevations
- If project has separate structure (garage/lower level): A201.1 floor plan, A202.1 dims, A204/205 elevations, A206 interior elevations

### Phase 4: Draft 3 (~15-30 sheets, adds MEP + structural)
Adds:
- A104 Structural Column Grid (weld plates for I-beams and HSS columns, slab drops, forms)
- A108.1 Electrical Plan L1 (GFIs in wet areas, appliance connections, floor outlets)
- A108.2 Electrical Plan L2 (if multi-level)
- A109.2 Plumbing Plan L1 (hose bibs, water heater, water softener — often TBD)
- A109.3 Plumbing Plan L2 (if multi-level — wine refrigerator, ice maker locations)
- Additional garage/lower-level MEP sheets if applicable (A207-A209)

### Phase 5: Final
Same sheet count as Draft 3. Refinements and corrections only. No new sheets added typically.

## Sheet Numbering Logic
- A1xx = Main level / primary structure
- A2xx = Second level or separate structure (garage, lower level)
- A10x = Plans (floor, dimensions, roof, structural)
- A10(5) = Schedules
- A10(6)x = Exterior Elevations
- A10(7)x = Interior Elevations
- A10(8)x = Electrical
- A10(9)x = Plumbing

## Standard Notes on Every Sheet
- "BARNHAUS STEEL BUILDERS DOES NOT ENGINEER OR CERTIFY PLANS"
- "ALL EXTERIOR WALLS TO BE 2X6 STUD FRAMING (WITH PROPERLY SPACED STEEL COLUMNS)"
- "ALL INTERIOR WALLS TO BE 2X4 STUD FRAMING"
- "ROOF TO BE STEEL PURLINS SUPPORTED BY STEEL I BEAMS"
- "ENGINEERED FOUNDATION REQUIRED" (on floor plan sheets)
- Print size: ARCH D - 24" x 36" - TO SCALE
- TP Holders @ 26", Vanity Towel Holders @ 56", Shower Towel Holders @ 48" (on dimension plans)
- Color key: Red = Interior Walls, Black = Exterior Walls & Openings, Blue = Slab Measurement

## 3 Projects Studied

### Truelock (Empower Building branding, not Barnhaus)
- 229 Restless Wind, Spring Branch, TX
- 2-story, 6,868 SF total (4,317 SF living + 932 SF garage + patios/unfinished)
- Level 1: Master, Kitchen, Great Room, Study, Guest, Mud, Foyer — 11'6" ceilings
- Level 2: 4 beds, Game Room, Bonus Room, Kitchenette, Terrace
- Roof: 6:12 pitch throughout
- 4 drafts → 18 sheets final

### Wirch (Barnhaus branding)
- Modern Desert aesthetic
- Single-story, 5,032 SF (2,643 SF living + 1,622 SF garage + patios)
- Rooms: Master, Kitchen, Living, Dining, Office, Beds 2-3, Salon, Golf Sim, Utility
- Roof: mixed 1:12, 2:12, 3:12 (very low slope — modern desert look)
- Had concept PDF: client's inspiration was Barnhaus "Horizon" model
- 4 drafts → 16 sheets final

### Murrell (Barnhaus branding)
- Scandinavian Modern aesthetic — dark metal siding, wood accents, massive glass gable
- Multi-level on cliff site — retaining walls, drainage, cliff edge, car lift in garage
- 5,464 SF total (4,693 SF living + 771 SF garage)
- Features: Golf sim, bar, salon, sun room, art wall question, ALL ELECTRIC, pool table, car lift
- Master: his/hers closets, sunroom, fireplace, coffee bar, makeup vanity, freestanding tub
- Inspiration: client Pinterest saves (dark barndominium, glass gable, mountain settings)
- Most complex project: 30 sheets final, A200 series for garage/lower level
- Roof: 8:12, 5:12, 10:12 mixed + flush roof-to-wall (no soffits) sections

## Design Brief → Build Script Field Mappings
*How to interpret new intake form fields when generating a build script*

### Footprint
- `footprint_width` + `footprint_depth` → use directly as MX1, MY1 in layout constants
  - If null (client chose preset, not custom): use preset defaults:
    - compact → 40×50, standard → 50×60, large → 60×70, xl → 70×80
  - Always add garage as a separate volume extending from MX1

### Garage
- `garage_cars` → size the garage volume:
  - 1 car → 22×24 (528 SF), 2 car → 24×24 (576 SF), 3 car → 36×24 (864 SF), 4+ car → 48×24 (1,152 SF)
- `garage_type` → attached (share a wall with mud room) or detached (separate structure, breezeway)
- `garage_load` → side-load: garage doors on side wall (GX0 or GX1 face); front-load: doors on GY0 face

### Master Suite Location
- `master_location`:
  - west → master at x=0 end (MX0 side), service/garage at MX1 end
  - east → master at MX1 end, living core at MX0 end (mirror layout)
  - rear-center → master centered on Y axis, rear of plan

### Level 2 Scope (two-story only)
- `l2_scope`:
  - all-bedrooms → all secondary beds + baths go to L2, L1 has master + living core only
  - game-plus-bedrooms → game room + secondary beds on L2
  - bonus-only → just bonus/flex space on L2, secondary beds stay on L1

### Roof
- `roof_pitch` → set actual pitch for roof geometry:
  - 1:12 → near-flat (modern desert), 3:12 → low slope, 6:12 → standard gable
  - 8:12 → steep, 10:12 → very steep (Scandinavian)
- `roof_style` → gable/single-slope/flat/parapet → determines roof shape logic

### Ceiling Heights
- `great_room_vaulted` (boolean) → if true, great room walls go to L1 Roof height (z=10+), vaulted follows roofline
- `master_ceiling_height` → master bed wall height (10, 11, or 12 ft)
- `secondary_ceiling_height` → all secondary bed/bath walls (9, 10, 11, or 12 ft)
- Default living core (kitchen, dining): 10 ft unless vaulted

### Bathrooms
- `full_baths` → count of full bath rooms to create (shower + tub + toilet + vanity)
- `half_baths` → count of powder rooms (toilet + vanity only, ~6×6 ft)
- Rule: 1 full bath always in master suite, remaining full baths distributed to secondary beds
- Half baths go in service corridor near living core

### Rear Patio
- `rear_patio_depth` → extend rear patio walls to this depth (ft) from MY1 outward
  - Default if null: 12 ft deep

### Special Rooms (desired_rooms)
- golf_simulator → 20×30 min, ideally in garage wing or L2
- bar_wet_bar → add to living core or game room adjacency
- wine_room → small dedicated room (~8×10) off pantry or dining
- media_room → requires L2 or bonus room, blackout walls
- salon → ~10×12, near secondary bath cluster
- safe_room → ~8×8, hidden off master closet or service corridor
- workshop → in garage wing, separate from car bays

### Aesthetic → Revit Decisions
- modern-desert → low pitch (1:12-3:12), flat parapet sections, no overhangs
- scandinavian → steep pitch (8:12-10:12), large glass gable end, dark exterior
- barndominium → gable roof, exposed structure, wide-open living core
- hill-country → 6:12 gable, covered porch priority, limestone accent zones
- industrial → flat/parapet, tall windows, exposed steel frame zones

### Vision Analysis → Build Decisions
*Cross-reference `vision_analysis` array against form inputs when building script*

**How to use it:**
1. Read all `vision_analysis` entries from the submission
2. Tally the most common: style, roof type, materials, standout elements
3. Use to CONFIRM or OVERRIDE form selections:

**Roof pitch override:**
- If 2+ images show flat/near-flat roofs → bias toward 1:12-3:12 even if form said "gable"
- If 2+ images show steep pitched roofs → bias toward 8:12-10:12
- If images conflict with form selection → use form selection but note the conflict

**Window sizing:**
- Images with "floor-to-ceiling windows" or "large windows" → increase window height (sill lower, head higher)
- Images with "clerestory" → add clerestory band to great room walls
- Images with "minimal windows" → keep windows smaller and fewer

**Overhang / soffit:**
- Images with "no soffits" or flush roof-to-wall → set overhang = 0
- Images with "deep overhangs" or "covered porch" priority → set overhang = 2-4 ft

**Massing complexity:**
- Images with "L-shape" or "offset volumes" → plan for compound footprint (add bump-out)
- Images with "simple box" → keep footprint rectangular

**Garage treatment:**
- Images where garage is clearly subordinate/hidden → enforce side-load regardless of form
- Images with front-facing garage → honor form selection

**Conflict resolution rule:**
- Form inputs win for room count, SF, ceiling heights (client knows what they need)
- Vision analysis wins for aesthetic/architectural character decisions (client shows what they love)
- When in doubt, note the conflict in build script comments and ask Mitch before running

## The Agent Plan

### Phase 1 — pyRevit Scripts (immediate, starts when RVT is received)
Install pyRevit on Mitch's Windows machine. I write Python scripts using Revit API, Mitch runs them with one click inside Revit.

Priority scripts to build first (after analyzing RVT):
1. **Auto-electrical** — reads wet rooms + appliance locations + exterior walls → places GFIs, outlets, appliance connections → creates A108 sheet
2. **Auto-plumbing** — reads fixture placements → places hose bibs, water heater/softener callouts → creates A109 sheet
3. **Door/window schedule** — extracts all doors/windows from model → generates A105 table in standard Barnhaus format
4. **Auto-dimension** — applies standard dimension style to all walls in one click

### Phase 2 — Sheet Bundle Automation
Scripts that create full draft stage sheet sets:
- "Draft 2 Bundle" — creates all A106/A107 sheets, places views, sets scales/crops to match Barnhaus template
- "Draft 3 Bundle" — creates A104/A108/A109 sheets
- Calibrated to Mitch's specific title block, view templates, and annotation styles

### Phase 3 — Live Bridge (medium term, ~2-3 weeks after Phase 1)
Small local REST server running alongside Revit → connected via n8n → I send commands directly → results come back to me. Eliminates manual script paste/run loop. Full conversational agent experience.

## What Mitch Always Owns
- Concept creation and client design decisions
- Initial floor plan layout (walls, rooms, basic model)
- Client meetings and feedback loop
- Final review and approval

## What the Agent Takes Over
- Everything from "model roughed in" → "ready for builder"
- All MEP plans, structural grid, schedules, sheet setup, dimensions
- Interior and exterior elevation view placement
- Revisions from client feedback

## Next Steps
1. Mitch sends a finished .RVT file
2. I analyze: families loaded, title block, view templates, typical layers, annotation styles
3. Build first pyRevit scripts matched to Mitch's exact Revit setup
4. Test on a real project, iterate
5. Build toward Phase 2 sheet bundles
6. Eventually Phase 3 live bridge
