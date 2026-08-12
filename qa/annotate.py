"""
annotate.py — Draw finding highlights on sheet tiles + optional upload.

qa-visual already knows WHERE each finding is (tile + coarse location).
This module turns that into a drafter-ready image: the tile crop with a
red highlight box and a caption strip. Crops are saved to
exports/findings/ and (optionally) uploaded to the CRM Supabase `docs`
bucket so punch lists can embed public URLs.

Upload keys (never hardcoded): env CRM_SUPABASE_URL / CRM_SUPABASE_KEY,
or workspace file ~/.openclaw/workspace/.blueprint_keys.json:
  {"crm_supabase_url": "...", "crm_supabase_key": "..."}
"""

import json
import os

FINDINGS_DIR = os.path.join("exports", "findings")

# Coarse location words → highlight cell in a 3x3 grid of the tile
_ROW = {"top": 0, "center": 1, "middle": 1, "bottom": 2}
_COL = {"left": 0, "center": 1, "middle": 1, "right": 2}


def _location_box(location: str, w: int, h: int):
    """Map 'top-left' style text to a 3x3 grid cell box. None = whole tile."""
    if not location:
        return None
    loc = location.lower()
    row = next((v for k, v in _ROW.items() if k in loc), None)
    col = next((v for k, v in _COL.items() if k in loc), None)
    if row is None and col is None:
        return None
    row = 1 if row is None else row
    col = 1 if col is None else col
    cw, ch = w // 3, h // 3
    return (col * cw, row * ch, (col + 1) * cw, (row + 1) * ch)


def annotate_tile(tile_path: str, findings: list, out_path: str) -> str | None:
    """Draw highlight boxes + caption strip for all findings on one tile."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    if not os.path.exists(tile_path):
        return None

    im = Image.open(tile_path).convert("RGB")
    w, h = im.size
    strip_h = 26 * len(findings) + 12
    canvas = Image.new("RGB", (w, h + strip_h), (255, 255, 255))
    canvas.paste(im, (0, 0))
    draw = ImageDraw.Draw(canvas)

    for n, fnd in enumerate(findings, 1):
        color = (220, 30, 30) if fnd.get("severity") == "error" else (240, 140, 0)
        box = _location_box(fnd.get("location", ""), w, h)
        if box:
            draw.rectangle(box, outline=color, width=6)
            draw.text((box[0] + 8, box[1] + 8), str(n), fill=color)
        else:
            draw.rectangle((3, 3, w - 3, h - 3), outline=color, width=6)
        caption = f"{n}. [{fnd.get('type')}] {(fnd.get('description') or '')[:110]}"
        draw.text((8, h + 8 + (n - 1) * 26), caption, fill=color)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)
    return out_path


def annotate_sheet_findings(tiled: dict, findings: list, sheet_num: str) -> int:
    """Annotate every tile that has findings. Sets crop_path on each finding.
    Call BEFORE tiles are cleaned up. Returns number of crops written."""
    by_tile = {}
    for fnd in findings:
        by_tile.setdefault(fnd.get("tile"), []).append(fnd)

    tile_paths = {f"r{t['row']}c{t['col']}": t.get("path")
                  for t in tiled.get("tiles", [])}
    tile_paths["overview"] = tiled.get("overview")

    count = 0
    for tile_label, flist in by_tile.items():
        src = tile_paths.get(tile_label)
        if not src:
            continue
        out = os.path.join(FINDINGS_DIR,
                           f"{sheet_num.replace('.', '_')}_{tile_label}.png")
        if annotate_tile(src, flist, out):
            for fnd in flist:
                fnd["crop_path"] = out
            count += 1
    return count


# ────────────────────────────────────────────────────────────
# Optional: upload crops to CRM Supabase docs bucket (public)
# ────────────────────────────────────────────────────────────

KEYS_FILE = os.path.expanduser("~/.openclaw/workspace/.blueprint_keys.json")


def _docs_creds():
    url = os.environ.get("CRM_SUPABASE_URL")
    key = os.environ.get("CRM_SUPABASE_KEY")
    if url and key:
        return url.rstrip("/"), key
    try:
        cfg = json.load(open(KEYS_FILE))
        return cfg["crm_supabase_url"].rstrip("/"), cfg["crm_supabase_key"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None, None


def upload_crop(local_path: str, slug: str) -> str | None:
    """Upload one crop to docs bucket → public URL, or None if no creds."""
    import requests
    url, key = _docs_creds()
    if not url or not key:
        return None
    name = os.path.basename(local_path)
    storage_path = f"blueprint/{slug}/{name}"
    with open(local_path, "rb") as f:
        r = requests.post(
            f"{url}/storage/v1/object/docs/{storage_path}",
            headers={"Authorization": f"Bearer {key}", "apikey": key,
                     "Content-Type": "image/png", "x-upsert": "true"},
            data=f.read(), timeout=60)
    if r.status_code in (200, 201):
        return f"{url}/storage/v1/object/public/docs/{storage_path}"
    print(f"   ⚠️  crop upload failed ({r.status_code}): {name}")
    return None


def upload_findings_crops(issues: list, slug: str) -> int:
    """Upload all crops referenced by findings; sets crop_url. Returns count."""
    uploaded, cache = 0, {}
    for i in issues:
        p = i.get("crop_path")
        if not p or not os.path.exists(p):
            continue
        if p not in cache:
            cache[p] = upload_crop(p, slug)
        if cache[p]:
            i["crop_url"] = cache[p]
            uploaded += 1
    return uploaded
