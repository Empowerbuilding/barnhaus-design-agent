# REVIT_TEMPLATE.md — Barnhaus Revit Template Catalog
*Auto-generated from bridge query + confirmed types. Use ONLY these exact strings.*

## DOOR FAMILIES & TYPES

### Interior Single Swing
**Family:** `Door-Interior-Single-1_Panel-Wood`
- `36" x 96"` — standard interior (most rooms)
- `32" x 96"` — tight spaces
- `30" x 96"` — closets, pantry
- `28"` — very tight/utility
- `24"` — smallest

### Interior Pocket (disappears into wall)
**Family:** `Door-Interior-Single-Pocket-2_Panel-Wood`
- `36" x 96"` — standard pocket
- `28"` — small pocket

### Interior Barn Door (sliding, surface-mount)
**Family:** `Interior_barn_door_18732`
- `Interior_barn_door_18732` — one type

### Interior Double Sliding
**Family:** `Door-Interior-Double-Sliding-2_Panel-Wood`
- `68" x 84"` — standard double slide
- `72" x 96"` — tall double slide

### Interior Double Pocket
**Family:** `Door-Interior-Double-Pocket-2_Panel-Wood`
- `72" x 96"`

### Interior Bifold (closets)
**Family:** `4_Panel_Bifold_Door_18619`
- `72" x 84"` — standard bifold

### Interior Cased Opening (no door, just casing)
**Family:** `Int-Opening-Craftsman_Casing_1726`
- `36" x 96"` — single opening
- `48"` — medium opening
- `72"` — wide opening
- `Wide` — widest opening

### Exterior Single Entry
**Family:** `Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad`
- `36" x 96"` — standard front entry ← USE THIS for front door
- `36" x 96" Orange` — accent color variant
- `36" x 80"`

### Exterior Double (glass)
**Family:** `Door-Exterior-Double-Full Glass-Wood_Clad`
- `72" x 96"` — double glass entry
- `60" x 96"`
- `8'`

**Family:** `Door-Inswing-Andersen-E_Series-Double`
- `6080 EXT` — Anderson double exterior

### Exterior Sliding (patio)
**Family:** `Exterior_Sliding_Door_3843`
- `6'-0"W. x 8'-0"H.` ← NOTE: no trailing period/quote; exact string matters
- `8'-0"W. x 8'-0"H. 2` — wider slider (hero/great room)

### Multi-Panel Sliding (large openings)
**Family:** `Three_Panel_Sliding_Door_17534`
- `108" x 84"` — 9ft wide
- `108" x 80"`
- `120" x 96"` — 10ft wide, tall
- `120" x 84"`
- `144" x 96"` — 12ft wide, hero wall

**Family:** `Four_Panel_Sliding_door_11160`
- `4 panel sliding door 4.00` — 4 panel, 4ft each panel
- `4 panel sliding door 4.40`
- `4 panel sliding door 2.00`

### Garage Overhead
**Family:** `Door-Garage-Flush_Panel`
- `16W X 10H` — standard 2-car wide ← USE THIS for 2-car garage
- `10x10` — single car, 10ft tall
- `10 X 10 OD GL` — single car glass
- `10x14` — RV height
- `12X14` — oversize RV
- `12 X 12`

**Family:** `Overhead_Door_-_Sectional_with_Glass_13396`
- `16' W X 8' H` — glass sectional, 2-car
- `10'W X 12'H` — single car tall with glass

### Shower Door
**Family:** `Frameless_Glass_shower_door_19168`
- `2'-6" x 8'-0"` — standard frameless glass shower

---

## WINDOW FAMILIES & TYPES

### Fixed Picture Windows (most common — Barndominium style)
**Family:** `Instance-Window-Fixed`
- `72" x 36"` — 6ft wide × 3ft tall ← PRIMARY for living/bedroom/rear
- `60" x 30"` — 5ft wide × 2.5ft tall ← secondary living
- `48" x 48"` — 4ft square ← good for bedrooms, flanking entry
- `48" x 84"` — 4ft wide × 7ft tall ← tall drama window
- `48" x 96"` — 4ft wide × 8ft tall ← floor-to-ceiling drama
- `24" x 96"` — 2ft wide × 8ft tall ← narrow accent/sidelite
- `72" x 24"` — 6ft wide × 2ft tall ← clerestory / high strip
- `72" x 30"` — 6ft wide × 2.5ft tall ← clerestory
- `60" x 24"` — 5ft wide × 2ft tall ← clerestory
- `18" X 18"` — tiny square ← utility/bath privacy
- `12" X 24"` — narrow tall ← utility
- `6080 FX` — 60"×80" fixed

### Awning Windows (crank-open, good for bathrooms/laundry)
**Family:** `Window-Awning-Single`
- `36" x 60"` — 3ft wide × 5ft tall awning
- `36" x 72"` — 3ft wide × 6ft tall awning
- `24" x 72"` — 2ft wide × 6ft tall awning ← bathroom privacy awning

### Double Hung
**Family:** `Window-Double_Hung-Andersen-E_Series`
- `3060 SH` — 30"×60"
- `3050 SH` — 30"×50"

### Casement (side-crank open)
**Family:** `Window-Casement-Single_Left`
- `36" x 60"` — standard casement
- `36" x 53"`
- `36" X 48"`
- `29" x 48"`
- `24" x 36"` — small casement
- `17" x 36"` — narrow casement

---

## WINDOW SELECTION GUIDE

| Location | Recommended | Notes |
|---|---|---|
| Great room rear (hero) | `Instance-Window-Fixed`: `72" x 36"` × 3-4 grouped | Maximum glass, rear wall |
| Great room front | `Instance-Window-Fixed`: `48" x 48"` | Restrained street side |
| Master bedroom | `Instance-Window-Fixed`: `72" x 36"` | Views, privacy |
| Secondary bedrooms | `Instance-Window-Fixed`: `48" x 48"` | Standard |
| Master bath | `Window-Awning-Single`: `24" x 72"` | Privacy + ventilation |
| Secondary bath | `Window-Awning-Single`: `24" x 72"` | Privacy |
| Kitchen | `Instance-Window-Fixed`: `60" x 30"` | Above counter |
| Office/study | `Instance-Window-Fixed`: `48" x 48"` | Standard |
| Clerestory/high strip | `Instance-Window-Fixed`: `72" x 24"` | High on wall |
| Drama/feature | `Instance-Window-Fixed`: `48" x 96"` | Floor to ceiling |

---

## WALL TYPES
*Use exact strings in create_wall calls*

**Exterior walls (7.5" — insulated metal panel system):**
- `Wall 7.5" EXT PBR` ← USE FOR ALL EXTERIOR WALLS

**Interior walls (4.5"):**
- `Wall 4.5 Interior"` ← USE FOR ALL INTERIOR WALLS

---

## EXTERIOR DOOR SELECTION GUIDE

| Location | Family | Type | Notes |
|---|---|---|---|
| Front entry (single) | `Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad` | `36" x 96"` | Standard |
| Front entry (double) | `Door-Exterior-Double-Full Glass-Wood_Clad` | `72" x 96"` | Grand entry |
| Rear/patio (hero) | `Three_Panel_Sliding_Door_17534` | `144" x 96"` | Great room back wall |
| Rear/patio (standard) | `Exterior_Sliding_Door_3843` | `8'-0"W. x 8'-0"H. 2` | Standard patio slider |
| Master patio | `Exterior_Sliding_Door_3843` | `6'-0"W. x 8'-0"H.` | Master bedroom patio |
| Garage (2-car) | `Door-Garage-Flush_Panel` | `16W X 10H` | Standard |
| Garage (1-car) | `Door-Garage-Flush_Panel` | `10x10` | Single |

---

## INTERIOR DOOR SELECTION GUIDE

| Location | Family | Type | Notes |
|---|---|---|---|
| Master bedroom entry | `Door-Interior-Single-1_Panel-Wood` | `36" x 96"` | Standard |
| Secondary bedrooms | `Door-Interior-Single-1_Panel-Wood` | `36" x 96"` | Standard |
| Master bath | `Door-Interior-Single-1_Panel-Wood` | `36" x 96"` | Standard |
| His/hers closets | `Door-Interior-Single-1_Panel-Wood` | `30" x 96"` | Closet |
| Walk-in closet | `Door-Interior-Single-1_Panel-Wood` | `36" x 96"` | If large |
| Pantry | `Door-Interior-Single-1_Panel-Wood` | `30" x 96"` | Closet-style |
| Office | `Door-Interior-Single-1_Panel-Wood` | `36" x 96"` | Standard |
| Utility/laundry | `Door-Interior-Single-1_Panel-Wood` | `32" x 96"` | Standard |
| Shower | `Frameless_Glass_shower_door_19168` | `2'-6" x 8'-0"` | Frameless glass |
| Wide openings (no door) | `Int-Opening-Craftsman_Casing_1726` | `72"` or `Wide` | Great room/kitchen pass |

---

## PLUMBING FIXTURE FAMILIES (confirmed)

**Family:** `Toilet-Domestic-3D` → type: `Toilet-Domestic-3D`
**Family:** `Tub-Free Standing-3D` → types: `30" x 60"`, `3x5`
**Family:** `Tub-Rectangular-3D` → type: `Tub-Rectangular-3D`
**Family:** `Shower_columns_15486` → type: `Shower_columns_15486`
**Family:** `Shower_Head_on_hose_7023` → type: `Shower_Head_on_hose_7023`
**Family:** `Sink Kitchen-Single` → type: `30" x 21"`
**Family:** `Sink Kitchen-Island` → type: `18" x 18"`
**Family:** `Stacked Washer and Dryer` → types: `26"x25" - Private`, `26"x25" - Public`

---

## APPLIANCE FAMILIES (confirmed)

**Family:** `Range-Gas` → types: `30"`, `36"`
**Family:** `Range-36_Inch` → type: `Burners`
**Family:** `Range-48_Inch` → types: `Burners`, `Griddle / Grill`
**Family:** `Hood-Wall` → types: `36"`, `48"`
**Family:** `Dishwasher` → type: `24"`
**Family:** `Refrigerator` → types: `18" LH`, `18" RH`, `24" LH`, `24" RH`
**Family:** `Fridge-Dbl Door` → types: `59" x 30" x 74"`, `59" x 36" x 83"`
**Family:** `Oven-Built-in-Double` → type: `30"`
**Family:** `Oven-Built-in-Microwave` → types: `30"`, `24"`
**Family:** `Washer-Dryer-Stack` → types: `27" x 30"`, `24" x 28"`

---

## CASEWORK FAMILIES (confirmed)

### Base Cabinets
- `Base Cabinet-Double Door & 1 Drawer` → `36"`, `30"`, `24"`, `27"` ← PRIMARY BASE
- `Base Cabinet-Double Door & 2 Drawer` → `30"`, `36"`, `42"`, `48"`
- `Base Cabinet-Double Door Sink Unit` → `36"`, `30"`, `24"`, `27"` ← FOR SINK
- `Base Cabinet-3 Drawers` → `21"`, `27"`, `36"`, `39"`
- `Base Cabinet-Shelf Unit` → `30"`, `36"`, `42"`, `48"`

### Upper Cabinets
- `Upper Cabinet-Double Door-Wall` → `36"`, `30"`, `24"`, `39"` ← PRIMARY UPPER
- `Upper Cabinet-Double Door-Short-Wall` → `42"`, `36"`, `30"`, `24"` ← BATH MIRROR CAB
- `Upper Cabinet-Single Door-Wall` → `18"`, `24"` ← NARROW UPPER

### Tall/Pantry Cabinets
- `Tall Cabinet-Double Door` → `30"`, `36"`, `42"`, `48"` ← PANTRY / LINEN
- `Tall Cabinet-Single Door` → `15"`, `24"`, `30"`, `36"`

### Vanity Cabinets (bathrooms)
- `Vanity Cabinet-Double Door Sink Unit` → `24"`, `27"`, `30"`, `36"` ← VANITY SINK
- `Vanity Cabinet-3 Drawers` → `12"`, `15"`, `18"`, `21"` ← BESIDE VANITY
- `Vanity Cabinet-Double Door & 4 Drawer` → `48"` ← MAKEUP VANITY
- `Vanity Cabinet-Double Door & 2 Drawer` → `30"`, `36"`, `42"`, `48"`
- `Vanity Cabinet-Shelf Unit` → `30"`, `36"`, `42"`, `48"`

---

## CABINET PLACEMENT OFFSETS ← CRITICAL

Cabinets must be placed with their BACK flush to the INTERIOR FACE of the wall.
Faces must point INTO the room, NOT into the wall.

### ✅ ROTATION — CONFIRMED (matches v1 code, ground truth)
```
Cabinets face INTO the room:
  North wall (back to north, face south into room) → rotation=0
  South wall (back to south, face north into room) → rotation=180
  West wall  (back to west,  face east into room)  → rotation=90
  East wall  (back to east,  face west into room)  → rotation=270
```

### Offset formula (back of cabinet flush to interior wall face):
```
North wall y=Y:
  base center   = Y - 1.5   (2ft deep, back at Y, front at Y-2)
  upper center  = Y - 0.5   (1ft deep, back at Y, front at Y-1)
  appliance     = Y - 1.25

South wall y=Y:
  base center   = Y + 1.5
  upper center  = Y + 0.5
  appliance     = Y + 1.25

West wall x=X:
  base center   = X + 1.5
  upper center  = X + 0.5
  appliance     = X + 1.25

East wall x=X:
  base center   = X - 1.5
  upper center  = X - 0.5
  appliance     = X - 1.25
```

### TEST PROCEDURE (run before every fixture script):
```python
# Place ONE base cabinet at north wall, rotation=0, check in Revit
# If face points south (into room) AND back touches wall → rotation=0 is correct
# If face points north (into wall) → switch to rotation=180
# Update this file with the confirmed value before running full fixture script
from barnhaus_revit_utils import place_fixture
place_fixture("Base Cabinet-Double Door & 1 Drawer", "36\"",
              25, NORTH_WALL_Y - 1.5, 0, "Level 1.0", rotation=0, label="TEST-r0")
```

---

## MECHANICAL / SPECIALTY (confirmed)
- `Big_curse_Fan_6276` → `08'-0" Power Foil`, `16'-0" Power Foil` ← large ceiling fan
- `Bathroom_Ceiling_Fan_71` → `Model FV-11VQ2`
- `Fireplace-Gas-Heat&Glo-Fortress` → `FORTRESS-36`
- `HVAC_Fireplaces_Regency-Fireplace_Gas-Stove_RC500E` → `Natural Gas Stove - Black`

---

## PYTHON API — EXACT FUNCTION SIGNATURES
*Copy these exactly. Do NOT guess.*

```python
# WALLS
create_wall(sx, sy, sz, ex, ey, ez, level, wall_type, height=10, label="")
create_rect_exterior(x0, y0, x1, y1, z, level, wall_type, height=10, label_prefix="", skip_faces=None)
create_l_shape_exterior(main_x0, main_y0, main_x1, main_y1, wing_x0, wing_y0, wing_x1, wing_y1, z, level, wall_type, height=10, ...)
create_u_shape_exterior(main_x0, main_y0, main_x1, main_y1, left_x0, left_y0, left_x1, left_y1, right_x0, right_y0, right_x1, right_y1, z, level, wall_type, height=10, ...)
create_garage(gx0, gy0, gx1, gy1, z, level, ext_wall, height=12, garage_cars=2, door_face="south", skip_faces=None, label="Garage")

# FLOORS
smart_floor(level, z, x0, y0, x1, y1, exp_w=True, exp_s=True, exp_e=True, exp_n=True)
# NOTE: NO label= param on smart_floor

# ROOFS
make_roof(label, x0, y0, x1, y1, level_name, roof_type='13" Roof No Gyp', overhang=1.5, pitch=0.0, slope_style="flat", shed_low_edge=2)
# slope_style options: "flat", "gable", "shed"
# For flat roof: pitch=0.0, slope_style="flat"
# For gable: pitch=0.5, slope_style="gable"
# NOTE: NO slope= param — use pitch= instead

# DOORS
place_door(wall_id, x, y, z, family, type_name, label="", wall_axis=None, wall_start=None, wall_end=None, wall_height=None, tight=False, level=None)
# x,y = actual coordinate ON the wall where door is placed
# z = 0 for all doors (floor level)
# Example: place_door(wall_id, 25, 58, 0, "Door-Exterior-...", '36" x 96"', label="front entry")

# WINDOWS  
place_window(wall_id, x, y, z, family=WIN_FAMILY, type_name='60" x 24"', label="", ...)
# x,y = actual coordinate ON the wall
# z = sill height (2.5 for standard L1, 5.0 for bath privacy, 13.5 for L2)
# Example: place_window(wall_id, 16, 58, 2.5, "Instance-Window-Fixed", '48" x 48"', label="great rm N")

# FIXTURES
place_fixture(family, type_name, x, y, z, level, rotation=0, label="")
# z=0 for floor-mounted, rotation in degrees
# NOTE: first 2 args are family+type, THEN x,y,z,level (opposite of place_door/place_window)

# ROOMS
label_rooms(rooms, level, upper_limit_level=None)
# rooms = list of dicts: [{"name": "Kitchen", "x": 15, "y": 38}, ...]  ← NOT tuples
# Always use upper_limit_level="Level 2.0" for L1 single-story
# Always use upper_limit_level="L2 Roof" for L2 rooms

# ATTACH WALLS TO ROOF
attach_walls_to_roof(wall_ids, roof_id, location="Top")
# wall_ids = list of integer IDs
# Returns ok count + skip count

# STAIRS
create_stairs(origin_x, origin_y, bottom_level, top_level, ...)
```

## IMPORT LINE (copy exactly)
```python
from barnhaus_revit_utils import (
    call, create_wall, create_rect_exterior, create_u_shape_exterior,
    create_l_shape_exterior, create_garage,
    smart_floor, make_roof,
    place_door, place_window, place_fixture,
    label_rooms, verify_wall_facing, flip_wall,
    attach_walls_to_roof, create_stairs,
    layout_kitchen, layout_bath_master, layout_bath_standard
)
```
