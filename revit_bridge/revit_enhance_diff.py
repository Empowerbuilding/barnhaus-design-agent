#!/usr/bin/env python3
"""
revit_enhance_diff.py — Compare original vs enhanced Revit screenshot,
extract window/door/wall changes, and auto-generate a Revit patch script.

Usage:
  python3 revit_enhance_diff.py <original_url> <enhanced_url> [output_script.py]

Example:
  python3 revit_enhance_diff.py \
    https://hbfjdfxephlczkfgpceg.supabase.co/.../revit_view1.png \
    https://res.cloudinary.com/.../enhanced.jpg \
    patch_001.py
"""

import sys, os, json, textwrap
from openai import OpenAI

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

DIFF_PROMPT = """
You are comparing two images of the same building:
- IMAGE 1: The original Revit 3D model screenshot (before)
- IMAGE 2: The AI-enhanced photorealistic version (after)

Your job is to identify ONLY the architectural changes the enhancer made that can be replicated in a 3D model. Focus on:
1. NEW windows added (not in original)
2. Windows made LARGER or repositioned
3. Wall heights that appear taller
4. New doors or sliders added

For each change, output a JSON array. Each item must have:
{
  "change_type": "add_window" | "add_door" | "resize_window" | "wall_height",
  "wall_face": "S" | "N" | "E" | "W",  // which face of which wing
  "wing": "LW" | "RW" | "CB" | "GAR",  // left wing, right wing, center bridge, garage
  "position_along_wall_ft": <number>,   // distance from LEFT end of that wall face, in feet
  "sill_height_ft": <number>,           // bottom of window above floor, in feet
  "width_ft": <number>,                 // window/door width in feet
  "height_ft": <number>,                // window/door height in feet
  "notes": "<brief description>"
}

The building layout for reference:
- Left Wing (LW): ~22ft wide, south face is the front of the wing
- Right Wing (RW): ~22ft wide, south face is the front of the wing  
- Center Bridge (CB): ~30ft wide, set back ~18ft from wing fronts, has clerestory
- Garage: attached to LW north side

Return ONLY a valid JSON array. No markdown, no explanation, just the array.
If you cannot determine a precise measurement, estimate based on wall proportions.
If no changes are detectable, return an empty array [].
"""

WINDOW_FAMILIES = {
    "small":  ("Instance-Window-Fixed", '36" x 36"'),
    "medium": ("Instance-Window-Fixed", '48" x 48"'),
    "large":  ("Instance-Window-Fixed", '60" x 72"'),
    "slider": ("Exterior_Sliding_Door_3843", '6\'-0"W. x 8\'-0"H.'),
    "slider_large": ("Exterior_Sliding_Door_3843", '8\'-0"W. x 8\'-0"H. 2'),
}

# Wall coord lookup — maps (wing, face) → wall coord value
# Based on eda1a47f layout: LW x=0→22 y=8→54, RW x=84→106 y=8→54, CB x=38→68 y=26→54
WALL_COORDS = {
    ("LW", "S"): ("y", 8,   0,  22),   # y=8,  x runs 0→22
    ("LW", "N"): ("y", 54,  0,  22),
    ("LW", "W"): ("x", 0,   8,  54),
    ("LW", "E"): ("x", 22,  8,  54),
    ("RW", "S"): ("y", 8,  84, 106),
    ("RW", "N"): ("y", 54, 84, 106),
    ("RW", "E"): ("x", 106, 8,  54),
    ("RW", "W"): ("x", 84,  8,  54),
    ("CB", "S"): ("y", 26, 38,  68),
    ("CB", "N"): ("y", 54, 38,  68),
}

# Wall IDs from current eda1a47f build
WALL_IDS = {
    ("LW", "S"): 5953192,
    ("LW", "N"): 5953193,
    ("LW", "W"): 5953194,
    ("LW", "E"): 5953195,
    ("RW", "S"): 5953214,
    ("RW", "N"): 5953215,
    ("RW", "E"): 5953216,
    ("RW", "W"): 5953217,
    ("CB", "S"): 5953203,
    ("CB", "N"): 5953204,
}


def classify_window(width_ft, height_ft, change_type):
    """Pick the best matching Revit family/type."""
    if change_type == "add_door" or width_ft >= 6:
        if width_ft >= 7:
            return WINDOW_FAMILIES["slider_large"]
        return WINDOW_FAMILIES["slider"]
    if width_ft <= 3.5:
        return WINDOW_FAMILIES["small"]
    if width_ft <= 5:
        return WINDOW_FAMILIES["medium"]
    return WINDOW_FAMILIES["large"]


def position_to_coord(wing, face, position_along_ft):
    """Convert position_along_wall to actual x or y coordinate."""
    info = WALL_COORDS.get((wing, face))
    if not info:
        return None
    axis, coord, start, end = info
    # position_along is from LEFT end of the wall as viewed from outside
    # For S/N walls: left = smaller x; for E/W walls: left = smaller y
    actual = start + position_along_ft
    return actual


def generate_script(changes, output_path):
    lines = [
        '"""Auto-generated Revit patch from enhance_diff — eda1a47f"""',
        "import sys",
        "sys.path.insert(0, '/home/mitch/.openclaw/workspace')",
        "from barnhaus_revit_utils import place_window, place_door, flip_door",
        "",
        "LEVEL = 'Level 1.0'",
        "WIN   = 'Instance-Window-Fixed'",
        "",
        "print('=== Applying enhance diff patch ===')",
        "",
    ]

    placed = 0
    skipped = 0

    for i, c in enumerate(changes):
        wing      = c.get("wing", "").upper()
        face      = c.get("wall_face", "").upper()
        pos       = c.get("position_along_wall_ft", 0)
        sill      = c.get("sill_height_ft", 2.5)
        width     = c.get("width_ft", 4)
        height    = c.get("height_ft", 4)
        ctype     = c.get("change_type", "add_window")
        notes     = c.get("notes", "")

        wall_id = WALL_IDS.get((wing, face))
        coord   = position_to_coord(wing, face, pos)

        if wall_id is None or coord is None:
            lines.append(f"# SKIP [{i}] {wing}-{face}: no wall ID mapped — {notes}")
            skipped += 1
            continue

        info = WALL_COORDS[(wing, face)]
        axis = info[0]  # 'x' or 'y'
        wall_coord_val = info[1]

        if axis == "y":
            wx, wy = coord, wall_coord_val
        else:
            wx, wy = wall_coord_val, coord

        family, type_name = classify_window(width, height, ctype)
        label = f"DIFF-{wing}-{face}-{i}"

        if "door" in ctype or "slider" in family.lower():
            lines.append(f"# [{i}] {notes}")
            lines.append(f"d = place_door({wall_id}, {wx}, {wy}, 0, '{family}', '{type_name}', label='{label}', level=LEVEL)")
            lines.append(f"# flip_door(d)  # uncomment if door faces wrong way")
        else:
            lines.append(f"# [{i}] {notes}")
            lines.append(f"place_window({wall_id}, {wx}, {wy}, {sill}, WIN, '{type_name}', label='{label}')")

        lines.append("")
        placed += 1

    lines.append(f"print('=== Patch complete: {placed} placed, {skipped} skipped ===')")

    script = "\n".join(lines)
    with open(output_path, "w") as f:
        f.write(script)

    return placed, skipped


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 revit_enhance_diff.py <original_url> <enhanced_url> [output.py]")
        sys.exit(1)

    original_url = sys.argv[1]
    enhanced_url = sys.argv[2]
    output_path  = sys.argv[3] if len(sys.argv) > 3 else "patch_enhance.py"

    print(f"Comparing:\n  ORIGINAL: {original_url}\n  ENHANCED: {enhanced_url}")
    print("Sending to GPT-4o vision for diff analysis...")

    client = OpenAI(api_key=OPENAI_KEY)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text",       "text": DIFF_PROMPT},
                {"type": "image_url",  "image_url": {"url": original_url, "detail": "high"}},
                {"type": "image_url",  "image_url": {"url": enhanced_url, "detail": "high"}},
            ]
        }],
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()
    print(f"\nRaw GPT response:\n{raw}\n")

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])

    try:
        changes = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse JSON response: {e}")
        print("Raw output saved to diff_raw.txt")
        with open("diff_raw.txt", "w") as f:
            f.write(raw)
        sys.exit(1)

    print(f"Detected {len(changes)} changes:")
    for c in changes:
        print(f"  [{c.get('change_type')}] {c.get('wing')}-{c.get('wall_face')} pos={c.get('position_along_wall_ft')}ft  {c.get('width_ft')}x{c.get('height_ft')}ft  — {c.get('notes')}")

    placed, skipped = generate_script(changes, output_path)
    print(f"\n✅ Script written to: {output_path}")
    print(f"   {placed} placements, {skipped} skipped (unmapped walls)")
    print(f"\nReview it, then run: python3 {output_path}")


if __name__ == "__main__":
    main()
