"""
constants.py — Barnhaus Revit element constants.
All family/type names sourced from revit_template_manifest.json.
Edit here when template changes — one source of truth.
"""

# ─────────────────────────────────────────────
# LEVELS
# ─────────────────────────────────────────────
LEVEL = {
    "L1":       "Level 1.0",
    "L1_ROOF":  "L1 Roof",
    "L2":       "Level 2.0",
    "GAR_ROOF": "Garage Roof",
    "L2_ROOF":  "L2 Roof",
}

# ─────────────────────────────────────────────
# WALL TYPES
# ─────────────────────────────────────────────
WALL = {
    "EXT":  "Wall 7.5\" EXT PBR",
    "INT":  "Wall 4.5 Interior\"",
}

# Wall thickness (half-widths for offset math)
WALL_HALF = {
    "EXT": 0.625,   # 7.5" / 2
    "INT": 0.375,   # 4.5" / 2
}

# ─────────────────────────────────────────────
# FIXTURE OFFSETS (ft)
# ─────────────────────────────────────────────
BASE_CAB_DEPTH   = 2.0    # 24" base cabinet depth
UPPER_CAB_DEPTH  = 1.0    # 12" upper cabinet depth
APPL_DEPTH       = 2.0    # appliance depth (fridge, range, DW)
SINK_HALF_DEPTH  = 0.875  # sink origin is center, 21" total
TOILET_HALF      = 1.25   # toilet origin is center
SHOWER_HALF      = 0.5    # shower placed close to wall

# ─────────────────────────────────────────────
# ROTATION CONVENTION
# Face = direction the FRONT of the fixture points
# ─────────────────────────────────────────────
FACE_TO_ROT = {
    "S":  0,
    "N":  180,
    "E":  90,
    "W":  270,
}

WALL_FACE_TO_FRONT = {
    "N": "S",
    "S": "N",
    "W": "E",
    "E": "W",
}

# ─────────────────────────────────────────────
# DOORS — (family_name, type_name)
# ─────────────────────────────────────────────
DOOR = {
    # Interior
    "int_single":       ("Door-Interior-Single-1_Panel-Wood", "32\" x 96\""),
    "int_single_30":    ("Door-Interior-Single-1_Panel-Wood", "30\" x 96\""),
    "int_single_36":    ("Door-Interior-Single-1_Panel-Wood", "36\" x 96\""),
    "int_single_28":    ("Door-Interior-Single-1_Panel-Wood", "28\""),
    "int_pocket":       ("Door-Interior-Single-Pocket-2_Panel-Wood", "36\" x 96\""),
    "int_barn":         ("Interior_barn_door_18732", "Interior_barn_door_18732"),
    "int_bifold":       ("4_Panel_Bifold_Door_18619", "72\" x 84\""),
    "int_double_slide": ("Door-Interior-Double-Sliding-2_Panel-Wood", "72\" x 96\""),
    "int_opening":      ("Int-Opening-Craftsman_Casing_1726", "36\" x 96\""),
    "int_opening_wide": ("Int-Opening-Craftsman_Casing_1726", "Wide"),
    "int_opening_48":   ("Int-Opening-Craftsman_Casing_1726", "48\""),
    "int_opening_72":   ("Int-Opening-Craftsman_Casing_1726", "72\""),
    # Exterior
    "ext_single":       ("Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", "36\" x 96\""),
    "ext_double_glass": ("Door-Exterior-Double-Full Glass-Wood_Clad", "72\" x 96\""),
    "ext_slide_6":      ("Exterior_Sliding_Door_3843", "6'-0\"W. x 8'-0\"H."),
    "ext_slide_8":      ("Exterior_Sliding_Door_3843", "8'-0\"W. x 8'-0\"H. 2"),
    "ext_3panel_slide": ("Three_Panel_Sliding_Door_17534", "108\" x 84\""),
    "ext_4panel_slide": ("Four_Panel_Sliding_door_11160", "4 panel sliding door 4.00"),
    "ext_anderson":     ("Door-Inswing-Andersen-E_Series-Double", "6080 EXT"),
    # Garage / overhead
    "gar_oh_10x10":     ("Door-Garage-Flush_Panel", "10x10"),
    "gar_oh_10x14":     ("Door-Garage-Flush_Panel", "10x14"),
    "gar_oh_16x10":     ("Door-Garage-Flush_Panel", "16W X 10H"),
    "gar_oh_12x12":     ("Door-Garage-Flush_Panel", "12 X 12"),
    "gar_oh_12x14":     ("Door-Garage-Flush_Panel", "12X14"),
    "gar_oh_glass_10":  ("Overhead_Door_-_Sectional_with_Glass_13396", "10'W X 12'H"),
    "gar_oh_glass_16":  ("Overhead_Door_-_Sectional_with_Glass_13396", "16' W X 8' H"),
    # Bath
    "shower_door":      ("Frameless_Glass_shower_door_19168", "2'-6\" x 8'-0\""),
    "shower_double":    ("Double_Glass_Sliding_Shower_Door_20748", "Interior - Double Sliding Glass Shower Door"),
}

# ─────────────────────────────────────────────
# WINDOWS — (family_name, type_name)
# ─────────────────────────────────────────────
WINDOW = {
    # Fixed
    "fx_72x36":  ("Instance-Window-Fixed", "72\" x 36\""),
    "fx_60x24":  ("Instance-Window-Fixed", "60\" x 24\""),
    "fx_48x96":  ("Instance-Window-Fixed", "48\" x 96\""),
    "fx_24x96":  ("Instance-Window-Fixed", "24\" x 96\""),
    "fx_72x24":  ("Instance-Window-Fixed", "72\" x 24\""),
    "fx_72x30":  ("Instance-Window-Fixed", "72\" x 30\""),
    "fx_6080":   ("Instance-Window-Fixed", "6080 FX"),
    "fx_48x48":  ("Instance-Window-Fixed", "48\" x 48\""),
    "fx_60x30":  ("Instance-Window-Fixed", "60\" x 30\""),
    # Transom / clerestory
    "cl_6020":   ("Window-Double_Hung_Transom-Andersen-E_Series", "6020 FX"),
    "cl_5020":   ("Window-Double_Hung_Transom-Andersen-E_Series", "5020 FX"),
    "cl_4040":   ("Window-Double_Hung_Transom-Andersen-E_Series", "4040 FX"),
    "cl_3026":   ("Window-Double_Hung_Transom-Andersen-E_Series", "3026 FX"),
    "cl_4620":   ("Window-Double_Hung_Transom-Andersen-E_Series", "4620 FX"),
    # Single hung (operable)
    "sh_3060":   ("Window-Double_Hung-Andersen-E_Series", "3060 SH"),
    "sh_3050":   ("Window-Double_Hung-Andersen-E_Series", "3050 SH"),
    "sh_3040":   ("Window-Double_Hung_Transom-Andersen-E_Series", "3040 SH"),
    # Awning
    "aw_36x60":  ("Window-Awning-Single", "36\" x 60\""),
    "aw_36x72":  ("Window-Awning-Single", "36\" x 72\""),
    "aw_24x72":  ("Window-Awning-Single", "24\" x 72\""),
    # Casement
    "ca_36x60":  ("Window-Casement-Single_Left", "36\" x 60\""),
}

# ─────────────────────────────────────────────
# CASEWORK (cabinets) — (family_name, type_name)
# ─────────────────────────────────────────────
CABINET = {
    # Base
    "base_dd_36":    ("Base Cabinet-Double Door & 1 Drawer", "36\""),
    "base_dd_30":    ("Base Cabinet-Double Door & 1 Drawer", "30\""),
    "base_dd_24":    ("Base Cabinet-Double Door & 1 Drawer", "24\""),
    "base_sink_36":  ("Base Cabinet-Double Door Sink Unit", "36\""),
    "base_sink_30":  ("Base Cabinet-Double Door Sink Unit", "30\""),
    "base_3drw_36":  ("Base Cabinet-3 Drawers", "36\""),
    "base_3drw_24":  ("Base Cabinet-3 Drawers", "24\""),
    "base_shelf_36": ("Base Cabinet-Shelf Unit", "36\""),
    # Upper
    "upper_dd_36":   ("Upper Cabinet-Double Door-Wall", "36\""),
    "upper_dd_30":   ("Upper Cabinet-Double Door-Wall", "30\""),
    "upper_dd_42":   ("Upper Cabinet-Double Door-Wall", "42\""),
    "upper_sd_24":   ("Upper Cabinet-Single Door-Wall", "24\""),
    # Tall / pantry
    "tall_dd_36":    ("Tall Cabinet-Double Door", "36\""),
    "tall_dd_42":    ("Tall Cabinet-Double Door", "42\""),
    "tall_dd_48":    ("Tall Cabinet-Double Door", "48\""),
    "tall_shelf_36": ("Tall Cabinet-Shelf Unit(2)", "36\""),
    # Vanity
    "van_dd_36":     ("Vanity Cabinet-Double Door & 1 Drawer", "36\""),
    "van_dd_30":     ("Vanity Cabinet-Double Door & 1 Drawer", "30\""),
    "van_sink_36":   ("Vanity Cabinet-Double Door Sink Unit", "36\""),
    "van_sink_30":   ("Vanity Cabinet-Double Door Sink Unit", "30\""),
    "van_3drw_24":   ("Vanity Cabinet-3 Drawers", "24\""),
}

# ─────────────────────────────────────────────
# PLUMBING — (family_name, type_name)
# ─────────────────────────────────────────────
PLUMBING = {
    "toilet":        ("Toilet-Domestic-3D", "Toilet-Domestic-3D"),
    "tub_rect":      ("Tub-Rectangular-3D", "Tub-Rectangular-3D"),
    "tub_freestand": ("Tub-Free Standing-3D", "30\" x 60\""),
    "sink_kitchen":  ("Sink Kitchen-Single", "30\" x 21\""),
    "sink_island":   ("Sink Kitchen-Island", "18\" x 18\""),
    "sink_vanity":   ("Sink Vanity-Square", "20\" x 18\""),
    "washer_dryer":  ("Washer-Dryer-Stack", "27\" x 30\""),
    "shower_col":    ("Shower_columns_15486", "Shower_columns_15486"),
}

# ─────────────────────────────────────────────
# STRUCTURAL COLUMNS — (family_name, type_name)
# ─────────────────────────────────────────────
COLUMN = {
    "hss6x6":  ("HSS-Hollow Structural Section-Column", "HSS6X6X3/16"),
    "hss4x4":  ("HSS-Hollow Structural Section-Column", "HSS4X4X3/8"),
    "wf_W10":  ("W-Wide Flange-Column", "W10X12"),
}

# ─────────────────────────────────────────────
# LIGHTING — (family_name, type_name)
# ─────────────────────────────────────────────
LIGHTING = {
    "recessed_6in":    ("Downlight - Recessed Can", "6\" Incandescent - 120V"),
    "ceiling_fan":     ("Ceiling_Fan_With_Light_15608", "Type 1"),
    "gooseneck_ext":   ("gooseneck_exterior_wall_light_19146", "100W - 120V"),
}

# ─────────────────────────────────────────────
# QA THRESHOLDS — min clearances (ft)
# Source: IRC code + Barnhaus design rules
# ─────────────────────────────────────────────
QA = {
    "door_latch_wall_min":      0.5,    # 6" wall on latch side
    "door_swing_clear_min":     3.0,    # clear space in door swing arc
    "kitchen_aisle_min":        3.5,    # 42" between facing cabinet runs
    "kitchen_aisle_preferred":  4.0,    # 48" preferred
    "toilet_side_wall_min":     1.25,   # 15" center to wall (IRC)
    "toilet_side_preferred":    1.5,    # 18" preferred
    "toilet_front_clear_min":   2.0,    # 24" in front of toilet
    "shower_min_width":         3.0,    # 36" min shower width
    "shower_min_depth":         3.0,    # 36" min shower depth
    "hallway_min_width":        3.0,    # 36" min hallway
    "bedroom_min_width":        10.0,   # 10ft min bedroom width
    "closet_walkin_min_depth":  5.0,    # 5ft to be usable as walk-in
    "egress_door_min_width":    2.833,  # 34" door = 32" clear (egress)
}

# ─────────────────────────────────────────────
# ROOM NORMS — min/target/max SF
# Source: HOME_LAYOUT.md Section 3
# ─────────────────────────────────────────────
ROOM_NORMS = {
    "Master Bedroom":      {"min": 200, "target_lo": 240, "target_hi": 320, "max": 400},
    "Master Bathroom":     {"min": 100, "target_lo": 140, "target_hi": 200, "max": 280},
    "Master Bath":         {"min": 100, "target_lo": 140, "target_hi": 200, "max": 280},
    "His Closet":          {"min": 40,  "target_lo": 60,  "target_hi": 80,  "max": 120},
    "Hers Closet":         {"min": 50,  "target_lo": 80,  "target_hi": 120, "max": 180},
    "Master Closet":       {"min": 40,  "target_lo": 60,  "target_hi": 120, "max": 180},
    "Master Sitting Room": {"min": 80,  "target_lo": 100, "target_hi": 140, "max": 200},
    "Bedroom":             {"min": 110, "target_lo": 130, "target_hi": 180, "max": 220},
    "Bathroom":            {"min": 70,  "target_lo": 90,  "target_hi": 120, "max": 160},
    "Great Room":          {"min": 280, "target_lo": 380, "target_hi": 520, "max": 700},
    "Kitchen":             {"min": 88,  "target_lo": 180, "target_hi": 320, "max": 420},
    "Dining Room":         {"min": 100, "target_lo": 130, "target_hi": 180, "max": 240},
    "Dining":              {"min": 100, "target_lo": 130, "target_hi": 180, "max": 240},
    "Office":              {"min": 120, "target_lo": 160, "target_hi": 220, "max": 300},
    "Bonus Room":          {"min": 150, "target_lo": 180, "target_hi": 280, "max": 380},
    "Butler Pantry":       {"min": 60,  "target_lo": 80,  "target_hi": 120, "max": 160},
    "Pantry":              {"min": 40,  "target_lo": 60,  "target_hi": 120, "max": 160},
    "Mudroom":             {"min": 60,  "target_lo": 80,  "target_hi": 120, "max": 160},
    "Laundry":             {"min": 60,  "target_lo": 80,  "target_hi": 100, "max": 140},
    "Laundry Room":        {"min": 60,  "target_lo": 80,  "target_hi": 100, "max": 140},
    "Foyer":               {"min": 48,  "target_lo": 48,  "target_hi": 100, "max": 150},
    "Garage":              {"min": 240, "target_lo": 280, "target_hi": 560, "max": 840},
    "Outdoor Living":      {"min": 100, "target_lo": 200, "target_hi": 400, "max": 600},
    "Porch":               {"min": 100, "target_lo": 200, "target_hi": 400, "max": 600},
}

# ─────────────────────────────────────────────
# ADJACENCY RULES
# Source: HOME_LAYOUT.md Section 4
# ─────────────────────────────────────────────
MUST_TOUCH = {
    "Master Bedroom":  ["Master Bathroom", "Master Bath", "Master Closet", "His Closet", "Hers Closet"],
    "Master Bathroom": ["Master Bedroom"],
    "Master Bath":     ["Master Bedroom"],
    "His Closet":      ["Master Bedroom", "Master Bathroom", "Master Bath"],
    "Hers Closet":     ["Master Bedroom", "Master Bathroom", "Master Bath"],
    "Master Closet":   ["Master Bedroom", "Master Bathroom", "Master Bath"],
    "Great Room":      ["Dining Room", "Dining", "Kitchen"],
    "Kitchen":         ["Dining Room", "Dining", "Pantry", "Butler Pantry"],
    "Butler Pantry":   ["Kitchen"],
    "Mudroom":         ["Garage"],
    "Garage":          ["Mudroom"],
}

MUST_NOT_TOUCH = {
    "Master Bedroom":  ["Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5", "Garage"],
    "Master Bathroom": ["Kitchen", "Garage"],
    "Master Bath":     ["Kitchen", "Garage"],
    "Great Room":      ["Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5"],
    "Kitchen":         ["Master Bathroom", "Master Bath", "Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5"],
    "Garage":          ["Bedroom 2", "Bedroom 3", "Bedroom 4", "Bedroom 5", "Master Bedroom", "Master Bathroom", "Master Bath"],
}

# ─────────────────────────────────────────────
# BARNHAUS SHEET STANDARDS
# Source: revit-agent.md
# ─────────────────────────────────────────────
SHEETS = {
    "draft1": [
        {"number": "A100",   "name": "Cover Sheet"},
        {"number": "A101.1", "name": "Floor Plan Level 1"},
        {"number": "A102.1", "name": "Dimension Plan L1"},
        {"number": "A103",   "name": "Roof Plan"},
    ],
    "draft2_additions": [
        {"number": "A105",   "name": "Door & Window Schedule"},
        {"number": "A106",   "name": "Exterior Elevations - Front"},
        {"number": "A106.1", "name": "Exterior Elevations - Left"},
        {"number": "A106.2", "name": "Exterior Elevations - Right / Rear"},
        {"number": "A107",   "name": "Interior Elevations - Kitchen"},
        {"number": "A107.1", "name": "Interior Elevations - Master Bath"},
        {"number": "A107.2", "name": "Interior Elevations - Laundry"},
    ],
    "draft3_additions": [
        {"number": "A104",   "name": "Structural Column Grid"},
        {"number": "A108.1", "name": "Electrical Plan L1"},
        {"number": "A109.2", "name": "Plumbing Plan L1"},
    ],
    "two_story_additions": [
        {"number": "A101.2", "name": "Floor Plan Level 2"},
        {"number": "A102.2", "name": "Dimension Plan L2"},
        {"number": "A108.2", "name": "Electrical Plan L2"},
        {"number": "A109.3", "name": "Plumbing Plan L2"},
    ],
}

STANDARD_NOTES = [
    "BARNHAUS STEEL BUILDERS DOES NOT ENGINEER OR CERTIFY PLANS",
    "ALL EXTERIOR WALLS TO BE 2X6 STUD FRAMING (WITH PROPERLY SPACED STEEL COLUMNS)",
    "ALL INTERIOR WALLS TO BE 2X4 STUD FRAMING",
    "ROOF TO BE STEEL PURLINS SUPPORTED BY STEEL I BEAMS",
    "ENGINEERED FOUNDATION REQUIRED",
]

DIMENSION_COLOR_KEY = {
    "interior_walls": "Red",
    "exterior_walls_openings": "Black",
    "slab_measurement": "Blue",
}
