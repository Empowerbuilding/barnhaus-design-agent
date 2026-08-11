"""
visual_qa.py — High-res sheet export + tiling for vision QA.

Problem: a 24x36 sheet exported at 1500px is ~42 DPI — dimension text and
4x4 HSS column symbols become 2-4 pixel blobs. Vision models also downscale
large images internally, so one giant export doesn't help either.

Solution: export ONCE at high resolution, then slice into overlapping tiles
sized for what vision models can actually resolve (~1500px each). The agent
inspects the overview + each tile.

Usage:
    python3 run.py export-tiles <view_id> [out_dir]
      → exports at 6000px, writes overview.png + tile_r{row}c{col}.png
"""

import os
from core import revit_client as rc

EXPORT_RES   = 6000   # px, larger dimension — ~167 DPI on a 36" sheet
TILE_TARGET  = 1500   # px per tile edge (sweet spot for vision models)
OVERLAP      = 200    # px overlap so nothing is lost on tile seams
OVERVIEW_RES = 2000   # downscaled full-sheet overview


def export_tiles(view_id: int, out_dir: str = "exports") -> dict:
    """Export a view/sheet at high res and slice into vision-ready tiles."""
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)

    print(f"🖼️  Exporting view {view_id} at {EXPORT_RES}px...")
    full_path = os.path.join(out_dir, f"full_{view_id}.png")
    saved = rc.save_view_image(view_id, full_path, resolution=EXPORT_RES)
    if not saved:
        return {"error": "export failed"}

    im = Image.open(full_path)
    w, h = im.size
    print(f"   Full export: {w}x{h}")

    # Overview (whole sheet, readable layout)
    overview_path = os.path.join(out_dir, f"overview_{view_id}.png")
    scale = OVERVIEW_RES / max(w, h)
    im.resize((int(w * scale), int(h * scale)), Image.LANCZOS).save(overview_path)

    # Tile grid
    step = TILE_TARGET - OVERLAP
    cols = max(1, (w - OVERLAP + step - 1) // step)
    rows = max(1, (h - OVERLAP + step - 1) // step)

    tiles = []
    for r in range(rows):
        for c in range(cols):
            x0 = min(c * step, max(0, w - TILE_TARGET))
            y0 = min(r * step, max(0, h - TILE_TARGET))
            x1 = min(x0 + TILE_TARGET, w)
            y1 = min(y0 + TILE_TARGET, h)
            tile_path = os.path.join(out_dir, f"tile_{view_id}_r{r}c{c}.png")
            im.crop((x0, y0, x1, y1)).save(tile_path)
            tiles.append({"path": tile_path, "row": r, "col": c,
                          "region": [x0, y0, x1, y1]})

    # Remove the giant original — tiles + overview carry everything
    os.remove(full_path)

    print(f"   ✅ {len(tiles)} tiles ({rows}x{cols}) + overview → {out_dir}/")
    print(f"   Inspect: overview first (layout), then each tile for text/symbols.")
    return {"view_id": view_id, "overview": overview_path,
            "grid": f"{rows}x{cols}", "tiles": tiles}
