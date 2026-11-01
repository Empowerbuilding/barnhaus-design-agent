"""
fit_image.py — Guarantee images are small enough for vision models.

The `image` tool (glm-5.3-flash primary, gemini fallbacks) HARD-REJECTS
images over 25,000,000 px. An oversized export means a failed vision call
(2-4 min wasted) followed by a slow deep-model fallback. The 2026-11-01
"count the can lights" turn took 12.6 min for exactly this reason: two
5220x6432 zoom crops blew the limit and the turn fell back to deep analysis.

CLI:
    python3 core/fit_image.py exports/foo.png [more.png ...] [--max-edge 4000]

Library:
    from core.fit_image import fit
    fit("exports/foo.png")   # returns True if it resized
"""
import sys

MAX_LONG_EDGE = 4000        # px — worst-case total 16M px, comfortable margin
MAX_PIXELS    = 20_000_000  # hard vision limit is 25M — stay under it


def fit(path: str, max_long_edge: int = MAX_LONG_EDGE,
         max_pixels: int = MAX_PIXELS) -> bool:
    """Downscale `path` in place if it exceeds vision input limits.
    Returns True if the image was resized, False if it was already fine."""
    from PIL import Image
    resample = getattr(Image, "Resampling", Image).LANCZOS
    with Image.open(path) as im:
        w, h = im.size
        long_edge = max(w, h)
        if long_edge <= max_long_edge and w * h <= max_pixels:
            return False
        scale = min(max_long_edge / long_edge,
                    (max_pixels / (w * h)) ** 0.5,
                    1.0)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        out = im.resize((nw, nh), resample)
        if path.lower().endswith((".jpg", ".jpeg")) and out.mode not in ("RGB", "L"):
            out = out.convert("RGB")
        out.save(path)
    print(f"📐 fit_image: {w}x{h} -> {nw}x{nh} ({path})")
    return True


if __name__ == "__main__":
    argv = sys.argv[1:]
    edge = MAX_LONG_EDGE
    if "--max-edge" in argv:
        i = argv.index("--max-edge")
        edge = int(argv[i + 1])
        del argv[i:i + 2]
    if not argv:
        print(__doc__)
        sys.exit(1)
    for p in argv:
        fit(p, max_long_edge=edge)
