#!/usr/bin/env python3
"""
Scan all plan thumbnails to find which page numbers contain A105 (Front/Back elevations).
Outputs a JSON lookup: {slug: {"front_back": page_num, "left_right": page_num}}
"""
import os, json, re

THUMBS = "/home/mitch/.openclaw/workspace/thumbs"
OUTPUT = "/home/mitch/.openclaw/workspace/training_data/elevation_pages.json"

# All slugs we care about (skip mooring/evergreen/kennedy - shouse/commercial)
SKIP = {"mooring", "evergreen", "kennedy"}

# Get all slugs that have thumbnails
slugs = set()
for f in os.listdir(THUMBS):
    m = re.match(r"^(.+)_p(\d+)\.png$", f)
    if m:
        slugs.add(m.group(1))

slugs = sorted(s for s in slugs if s not in SKIP)

# Get page count per slug
page_counts = {}
for slug in slugs:
    pages = [int(re.match(r".+_p(\d+)\.png", f).group(1))
             for f in os.listdir(THUMBS)
             if re.match(rf"^{re.escape(slug)}_p(\d+)\.png$", f)]
    page_counts[slug] = max(pages) if pages else 0

print(f"Found {len(slugs)} slugs")
for slug in slugs:
    print(f"  {slug}: {page_counts[slug]} pages")

# Save page counts so we know what to scan
with open(OUTPUT.replace(".json", "_counts.json"), "w") as f:
    json.dump(page_counts, f, indent=2)

print(f"\nPage counts saved. Now scan thumbnails manually to find A105/A106 pages.")
print("Based on pattern: A105=Front/Back, A106=Left/Right")
print("For 1-story plans: usually p6/p7")  
print("For 2-story plans: usually p8/p9")
