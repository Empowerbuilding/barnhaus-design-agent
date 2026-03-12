#!/usr/bin/env python3
import subprocess, os
from PIL import Image

WORKSPACE = "/home/mitch/.openclaw/workspace"
THUMBS = f"{WORKSPACE}/thumbs"

plans = [
    ("carter.pdf", "carter"),
    ("diveley.pdf", "diveley"),
    ("forseth.pdf", "forseth"),
    ("munhofen.pdf", "munhofen"),
    ("murrell.pdf", "murrell"),
    ("truelock.pdf", "truelock"),
    ("wirch.pdf", "wirch"),
    ("yarbrough.pdf", "yarbrough"),
    ("camp_plans.pdf", "camp"),
    ("martinez_plans.pdf", "martinez"),
    ("mcdermott_plans.pdf", "mcdermott"),
    ("milner_plans.pdf", "milner"),
    ("moore_plans.pdf", "moore"),
    ("shearer_plans.pdf", "shearer"),
    ("shirley_plans.pdf", "shirley"),
    ("slater_plans.pdf", "slater"),
    ("tallon_plans.pdf", "tallon"),
    ("tubbs_plans.pdf", "tubbs"),
    ("veach_plans.pdf", "veach"),
    ("velazquez_plans.pdf", "velazquez"),
]

for pdf_name, slug in plans:
    pdf_path = f"{WORKSPACE}/{pdf_name}"
    if not os.path.exists(pdf_path):
        print(f"MISSING: {pdf_name}")
        continue

    r = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
    pages = 0
    for line in r.stdout.split("\n"):
        if line.startswith("Pages:"):
            pages = int(line.split()[-1])

    # Check which pages already exist
    existing = set()
    for f in os.listdir(THUMBS):
        if f.startswith(f"{slug}_p") and f.endswith(".png"):
            try:
                p = int(f.replace(f"{slug}_p","").replace(".png",""))
                existing.add(p)
            except: pass

    missing = [p for p in range(1, pages+1) if p not in existing]
    if not missing:
        print(f"SKIP: {slug} (all {pages} pages exist)")
        continue

    print(f"Generating {slug}: pages {missing}", flush=True)
    for page in missing:
        out = f"{THUMBS}/{slug}_p{page}.png"
        prefix = f"{THUMBS}/{slug}_p{page}_tmp"
        subprocess.run(
            ["pdftoppm", "-r", "150", "-png", "-f", str(page), "-l", str(page), pdf_path, prefix],
            capture_output=True
        )
        tmp = f"{prefix}-1.png"
        if os.path.exists(tmp):
            img = Image.open(tmp)
            img.thumbnail((1800, 1200))
            img.save(out)
            os.remove(tmp)
            print(f"  {slug} p{page} ✓", flush=True)

print("All done.")
