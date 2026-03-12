#!/usr/bin/env python3
import subprocess, os
from PIL import Image

WORKSPACE = "/home/mitch/.openclaw/workspace"
THUMBS = f"{WORKSPACE}/thumbs"

batch1_pdfs = {
    "allen_plans.pdf": "allen",
    "baumgardner_plans.pdf": "baumgardner",
    "bieri_plans.pdf": "bieri",
    "camp_plans.pdf": "camp",
    "carpenter_plans.pdf": "carpenter",
    "de_plans.pdf": "de_lira",
    "delgado_plans.pdf": "delgado",
    "dufrene_plans.pdf": "dufrene",
    "eubank_plans.pdf": "eubank",
    "games_plans.pdf": "games",
    "martinez_plans.pdf": "martinez",
    "mcdermott_plans.pdf": "mcdermott",
    "milner_plans.pdf": "milner",
    "moore_plans.pdf": "moore",
    "mooring_plans.pdf": "mooring",
    "shearer_plans.pdf": "shearer",
    "shirley_plans.pdf": "shirley",
    "slater_plans.pdf": "slater",
    "tallon_plans.pdf": "tallon",
    "tubbs_plans.pdf": "tubbs",
    "veach_plans.pdf": "veach",
    "velazquez_plans.pdf": "velazquez",
    "McDonald Final.pdf": "mcdonald",
}

for pdf_name, slug in batch1_pdfs.items():
    pdf_path = f"{WORKSPACE}/{pdf_name}"
    if not os.path.exists(pdf_path):
        print(f"MISSING: {pdf_name}")
        continue

    existing = [f for f in os.listdir(THUMBS) if f.startswith(f"{slug}_p")]
    if existing:
        print(f"SKIP: {slug} ({len(existing)} pages already)")
        continue

    # Get page count
    r = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
    pages = 0
    for line in r.stdout.split("\n"):
        if line.startswith("Pages:"):
            pages = int(line.split()[-1])

    print(f"Generating {slug}: {pages} pages...", flush=True)

    for page in range(1, pages + 1):
        out = f"{THUMBS}/{slug}_p{page}.png"
        if os.path.exists(out):
            continue
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
            print(f"  p{page} ✓", flush=True)

print("All done.")
