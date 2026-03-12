# HOME_LAYOUT.md — Residential Design Principles for Barnhaus Builds
*Read this before designing ANY floor plan. These are non-negotiable fundamentals.*

---

## 1. THE GOLDEN RULE: CIRCULATION IS EVERYTHING

Before placing a single room, map how people MOVE through the house. Bad circulation = bad house, no matter how nice the rooms are.

**The three circulation paths in every house:**
1. **Public path** — Entry → Living → Kitchen → Dining → Rear patio
2. **Private path** — Entry → Hallway/Landing → Bedrooms → Bathrooms
3. **Service path** — Garage → Mudroom → Pantry → Kitchen

These paths should NEVER force someone to walk through a private space to reach a public one, or through a bedroom to reach another bedroom. If you can only get to Bed 3 by walking through Bed 2, the layout is broken.

**The front door test:** Stand at the front door. You should be able to see directly into the main living space (great room or living room). You should NOT be able to see directly into a bedroom, bathroom, or laundry room.

---

## 2. ZONING — THE THREE ZONES

Every house has three zones. Separate them cleanly.

```
[PRIVATE ZONE]     [TRANSITION]     [PUBLIC ZONE]     [SERVICE]
Master Suite   ←── Hallway/Entry ──→ Great Room   ←──  Kitchen
Secondary Beds                       Dining              Pantry
Bathrooms                            Living              Mudroom/Laundry
                                     Office (semi)       Garage
```

**Rules:**
- Master suite is ALWAYS at the opposite end from secondary bedrooms (privacy from kids/guests)
- Secondary bedrooms cluster together and share a bathroom zone
- Public zone is adjacent to front entry and rear patio
- Service zone connects garage to kitchen — the "grocery run" path must be short
- Office/study is semi-private: accessible from public zone but has a door

---

## 3. ROOM SIZING — BARNHAUS STANDARDS

These are the actual sizes that appear in Barnhaus plans. Don't deviate significantly.

| Room | Min SF | Target SF | Max SF | Notes |
|---|---|---|---|---|
| Master Bedroom | 200 | 240–320 | 400 | 14×16 to 18×20 typical |
| Master Bath | 100 | 140–200 | 280 | Larger = more luxury features |
| His Closet | 40 | 60–80 | 120 | Walk-in preferred |
| Hers Closet | 50 | 80–120 | 180 | Always bigger than his |
| Master Sitting Room | 80 | 100–140 | 200 | Optional, high-end plans |
| Secondary Bedroom | 110 | 130–180 | 220 | 11×12 to 13×14 |
| Secondary Bath (full) | 70 | 90–120 | 160 | Often jack-and-jill |
| Great Room | 280 | 380–520 | 700 | Must feel large and open |
| Kitchen | 180 | 220–320 | 420 | Island adds 40–60 SF |
| Dining | 100 | 130–180 | 240 | Eat-in or separate |
| Office/Study | 120 | 160–220 | 300 | Needs closet for flex |
| Bonus Room | 150 | 180–280 | 380 | Game/media/flex |
| Butler Pantry | 60 | 80–120 | 160 | On grocery path |
| Mudroom | 60 | 80–120 | 160 | At garage entry |
| Laundry | 60 | 80–100 | 140 | Near bedrooms or mudroom |
| Garage (1-car) | 240 | 280–320 | 360 | 12×22 to 14×24 |
| Garage (2-car) | 440 | 480–560 | 640 | 22×22 to 24×26 |
| Garage (3-car) | 660 | 720–840 | — | 30×24+ |

---

## 4. ADJACENCY MATRIX — WHAT MUST TOUCH WHAT

✅ = Must be adjacent | 🔲 = Should be adjacent | ❌ = Must NOT be adjacent

| Room | Must Touch | Should Touch | Never Touch |
|---|---|---|---|
| Master Bed | Master Bath, His/Hers Closets | Sitting Room, Patio access | Secondary beds, Garage |
| Master Bath | Master Bed, His/Hers Closets | — | Kitchen, Garage |
| His Closet | Master Bed or Master Bath | — | — |
| Hers Closet | Master Bed or Master Bath | — | — |
| Great Room | Dining, Kitchen, Entry | Rear patio, Office | Bedrooms, Baths |
| Kitchen | Dining, Pantry | Great Room, Mudroom | Master Bath, Bedrooms |
| Butler Pantry | Kitchen | Mudroom | Bedrooms |
| Mudroom | Garage, Kitchen | Laundry, Pantry | Bedrooms |
| Secondary Beds | Bathroom in same wing | Each other | Kitchen, Garage |
| Office | Entry/Living zone | — | Baths |
| Bonus Room | Secondary bed wing or L2 landing | — | Master suite |
| Garage | Mudroom | — | Bedrooms, Baths |

---

## 5. HALLWAYS AND CORRIDOR RULES

**Single-story plans:** Use wide "gallery" hallways (min 4ft clear) or open-plan zones. Label the corridor; don't leave dead-end rooms with no visible path.

**Two-story plans:** 
- L1: Provide clear path from entry to each zone (no maze)
- L2: A central landing is the hub. Every L2 room gets its door on the landing.
- **Never place a L2 bedroom door on an exterior wall** — only on hallway/landing walls
- Landing minimum: 8×10 (80 SF). Make it feel intentional — it's the L2 foyer.
- Staircase placement: Near the public zone (great room side), not the master suite end

**Minimum widths:**
- Hallway: 4ft clear (5ft preferred)
- Entry foyer: 6×8 minimum (48 SF)
- Staircase: 4ft wide minimum, 12–14ft long (for standard rise)

---

## 6. CEILING HEIGHTS BY ROOM (Barnhaus standard)

| Room | Height | Notes |
|---|---|---|
| Great Room | Vaulted (follows roof) | This is the money shot — let it breathe |
| Master Bedroom | 10–11 ft | Feels premium |
| Master Bath | 10 ft | |
| His/Hers Closets | 10 ft | |
| Kitchen | 10 ft (or open to great room) | |
| Secondary Bedrooms | 10 ft | |
| Secondary Baths | 9–10 ft | |
| Office/Study | 10 ft | |
| Garage | 12 ft minimum (for 10ft OH door) | 14 ft for RV |
| L2 rooms | 10 ft (wall height) | Ridge will peak higher |

**In Revit:** Great room vaulted ceiling is created by gable/shed roof — the room tag will show floor area, not ceiling height. Note it in comments.

---

## 7. NATURAL LIGHT RULES

**South/rear exposure** (y=0 in build scripts, if south is rear):
- Great room: Maximum glass. This is the view wall. 3–4 large windows + slider.
- Master bedroom: 1–2 large windows (72"×36").
- Dining: Glass preferred.

**North/front exposure** (y=max, street side):
- Restrained. 1–2 windows flanking entry. Don't give the street a view into your living room.
- Small symmetrical windows on bedrooms only.

**East exposure:**
- Kitchens, breakfast nooks, offices — morning light is good here.

**West exposure:**
- Bedrooms (afternoon/sunset), living rooms. Avoid west glass on kitchens (heat).

**L2 rules:**
- Bedrooms: At least one window per room, minimum 48"×48".
- Landing: Borrow light — either a skylight, clerestory, or open rail overlooking great room.
- Bathrooms: Privacy windows only. Awning type at high sill (5ft+).

---

## 8. MASTER SUITE DESIGN STANDARDS

The master suite is the most important room. Buyers decide on it.

**Required components:**
1. Master Bedroom (200–320 SF)
2. Master Bath (140–200 SF) — directly accessible from bedroom, NOT through closet
3. His Closet (60–80 SF) — typically accessed from bath or bedroom
4. Hers Closet (80–120 SF) — larger, can have island dresser
5. Patio access — slider or French doors directly from master bedroom (hero feature)

**Optional (high-end):**
- Sitting/reading nook or room (separate from bedroom)
- Coffee bar (built-in cabinetry near bedroom)
- Private gym/sauna alcove

**Layout rules:**
- His/hers closets flank the entry to the master bath (you walk through them to get to the bath) — OR they flank the master bedroom entry
- Toilet must NOT be visible from bedroom door
- Freestanding tub is positioned as a focal point (visible from entry to bath, under a window)
- Walk-in shower: minimum 4×4 (16 SF), preferably 4×6 or larger
- Double vanity: 6ft minimum length
- Makeup vanity: separate counter space, not competing with main vanity

**Master should feel like a retreat:** private entry, no through-traffic, outdoor access, generous proportions.

---

## 9. KITCHEN DESIGN STANDARDS

**Kitchen layouts available (use kitchen_layout field from brief):**
- **U-shape:** Three walls of cabinets. Most storage. Always include island. Best for 14×16+ spaces.
- **L-shape:** Two walls. Good for open-plan. Island optional.
- **Galley:** Two parallel walls. Long and narrow. No island (too tight).
- **One-wall:** Single wall. Small homes only. Island can compensate.
- **Island (any layout):** Island = additional prep + seating. Always 4ft minimum from surrounding cabinets. Barnhaus standard: always include island when kitchen is 200 SF+.

**Kitchen must-haves:**
- Pantry or butler pantry nearby (within 10ft)
- Clear sightline from kitchen to front entry (you see who's at the door)
- Clear sightline from kitchen to living/great room (parent watching kids)
- Refrigerator not next to range (min 3ft apart)
- Sink ideally faces window or great room (not a wall)
- Work triangle (sink–range–fridge): each leg 4–9ft

**Barnhaus kitchen position:** Always in the NE or NW corner of the great room — against one back wall and one side wall, with the island facing the living area.

---

## 10. SECONDARY BEDROOM WING RULES

**Clustering:** All secondary bedrooms must be in the same zone. Never scatter them around the house (one near master, one near garage = bad).

**Bathroom sharing:**
- 2 beds: One full bath, shared (jack-and-jill or en-suite to one room)
- 3 beds: One full bath shared + one half bath, OR two full baths (one en-suite)
- 4 beds on L2: Two full baths on L2

**Jack-and-jill layout:** Bath positioned between two bedrooms, with a door from each bedroom into the bath. Bath has a locking door on each side.

**Door access:** Every bedroom door must open to a hallway, landing, or corridor — never directly into another bedroom.

**Closets:** Every secondary bedroom gets a closet. Minimum 5×5 (25 SF) walk-in, or a reach-in (min 6ft wide).

---

## 11. GARAGE RULES

- Garage door minimum clearance: 10ft height (12ft wall), 16ft wide (2-car)
- Garage floor: sloped 2% toward door for drainage
- Garage connects to house via mudroom ONLY — never directly into kitchen or living space
- Mudroom minimum: 8×10 (80 SF) — bench, hooks, laundry hookups
- If garage is attached: share one wall with the house (the mudroom wall)
- If garage is detached: connected via breezeway (covered walkway)

**Typical garage positions:**
- End of house (linear plan): anchors one end, connected by mudroom
- Side of house (L or U shape): forms one arm of the L/U
- Front of house (modern): recessed behind setback, connected by mudroom

---

## 12. L-SHAPE SPECIFIC RULES

**What makes an L-shape work:**
- The two wings must be clearly readable as distinct volumes from outside
- Wings should be different lengths (not equal — feels like a T, not an L)
- The interior corner of the L creates a **natural sheltered courtyard or patio** — USE THIS
- Don't put bedrooms in the corner — put a window or the rear slider there

**Zone assignment for L-shape (two common patterns):**

Pattern A — Garage as the short arm:
```
[MASTER]──[LIVING/KITCHEN]──[BED WING]
                                  │
                              [GARAGE]  ← short arm
```

Pattern B — Master as the short arm (more private):
```
[MASTER]
    │
[LIVING/KITCHEN]──[BED WING]──[GARAGE]
```

**Courtyard:** The L's inner notch should have a covered porch or patio. This is a signature Barnhaus feature. Open it up with large sliders on both interior-facing walls.

---

## 13. TWO-STORY SPECIFIC RULES

**What goes on each floor:**
- L1: Master suite, great room, kitchen, dining, service zone
- L2: Secondary bedrooms, bonus room, office, bathrooms
- Master ALWAYS on L1 — never upstairs in a Barnhaus

**Staircase:**
- Location: Between great room and secondary bed zone (never at master end)
- Width: 4ft minimum
- Landing at top: 8×10 minimum — this is the L2 hub
- Open rail/overlook into great room is a premium feature — use it

**L2 layout key rule:** Every L2 room has its door on the landing or a hallway that connects to the landing. NEVER L2 bedroom doors on exterior walls.

**What L2 can see from landing:**
- Open rail overlooking great room (vaulted ceiling drama)
- Natural light from clerestory or landing window

---

## 14. FOOTPRINT SIZING GUIDE

For the given total SF, here are typical footprint dimensions:

| Total SF | Stories | Main Body | Wing/Garage | Typical Shape |
|---|---|---|---|---|
| 1,800–2,200 | 1 | 40×36 to 50×36 | 22×22 garage | Rectangle or simple L |
| 2,200–2,800 | 1 | 50×40 to 60×40 | 22×22–24 garage | L-shape or modified rect |
| 2,800–3,500 | 1 or 2 | 55×40 to 70×44 | 24×24 garage | L or U-shape |
| 3,500–4,500 | 1 | 75×50 to 90×54 | 28×26 garage | Large rectangle or U |
| 4,500–5,500 | 1 | 90×54 to 110×54 | 30×26+ garage | Linear or L |
| 2,000–2,800 | 2 | 28×30 to 36×32 per floor | 22×22 garage | Rectangle or L |
| 2,800–4,000 | 2 | 36×32 to 48×36 per floor | 24×24 garage | L or rectangle |

**Depth rule:** Main body depth is almost always 26–36ft. Beyond 36ft feels like a warehouse. Width stretches to hit target SF.

**Proportions:** Aim for width:depth ratio of 1.5:1 to 2.5:1. Square houses feel boxy. Very long narrow houses feel like hallways.

---

## 15. BEFORE YOU WRITE A SINGLE COORDINATE

Ask yourself these questions in order:

1. What is the total SF and how is it split between wings/floors?
2. Where is the front (entry) and rear (view/patio) orientation?
3. Where does the master suite go? (far end from secondary beds, patio access)
4. Where does the garage connect? (end or arm, via mudroom)
5. What is the circulation path from front door to: master, secondary beds, garage?
6. Is the kitchen visible from: front entry? living room? Can the cook see the rear yard?
7. Does every bedroom have: door to hallway (not another bedroom), closet, window?
8. On 2-story: where are the stairs? Does the L2 landing feel intentional?
9. Are the three circulation paths (public, private, service) non-overlapping?
10. Does the layout make sense for how a FAMILY ACTUALLY LIVES IN IT?
