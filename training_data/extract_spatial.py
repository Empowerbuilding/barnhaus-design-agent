#!/usr/bin/env python3
"""
extract_spatial.py — Convert barnhaus JSONL layout descriptions → spatial coordinates

Reads barnhaus_v3_combined.jsonl, uses GPT-4o to convert each natural-language
layout description into structured room_coords, outputs spatial_training.jsonl

Usage:
    python3 extract_spatial.py
    python3 extract_spatial.py --dry-run   # test first 3 records only
    python3 extract_spatial.py --resume    # skip already-processed records
"""

import json
import os
import sys
import time
from pathlib import Path
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

INPUT_FILE = Path(__file__).parent / "barnhaus_v3_combined.jsonl"
OUTPUT_FILE = Path(__file__).parent / "spatial_training.jsonl"
ERRORS_FILE = Path(__file__).parent / "spatial_errors.jsonl"

SYSTEM_PROMPT = """You are a spatial layout parser for architectural floor plans.

Given a Barnhaus Steel Builders layout description, extract structured room coordinates.

Rules:
- Footprint origin is always (0, 0) at bottom-left
- Coordinates are in FEET
- x increases east, y increases north
- Derive actual dimensions from the footprint shape and SF mentioned
- Place rooms proportionally within the footprint
- Rooms must not overlap (except intentional open-plan zones)
- Master suite goes at one end (usually rear/private), garage at opposite end or side wing

Output ONLY a valid JSON object with this exact structure:
{
  "footprint": {"shape": "rectangle|L|T|H|U", "width": <ft>, "depth": <ft>},
  "rooms": {
    "Master Bedroom": {"x0": <ft>, "y0": <ft>, "x1": <ft>, "y1": <ft>, "sf": <int>, "zone": "master"},
    "Master Bathroom": {"x0": <ft>, "y0": <ft>, "x1": <ft>, "y1": <ft>, "sf": <int>, "zone": "master"},
    ...
  }
}

Zone values: "master", "beds", "living", "service"
Include all rooms mentioned. Skip mechanical/utility rooms.
No markdown, no explanation — just the JSON object.
"""

def extract_brief(record: dict) -> tuple[str, str]:
    """Extract user brief and assistant layout from a training record."""
    messages = record.get("messages", [])
    user_content = ""
    assistant_content = ""
    for msg in messages:
        if msg["role"] == "user":
            user_content = msg["content"]
        elif msg["role"] == "assistant":
            assistant_content = msg["content"]
    return user_content, assistant_content


def parse_spatial(brief: str, layout: str, record_idx: int) -> dict | None:
    """Call GPT-4o to convert layout description to room coordinates."""
    prompt = f"""DESIGN BRIEF:
{brief}

LAYOUT DESCRIPTION:
{layout}

Convert this layout to structured room coordinates as specified."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        text = response.choices[0].message.content.strip()
        # Strip markdown if present
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        return parsed
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error on record {record_idx}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ API error on record {record_idx}: {e}")
        return None


def build_training_record(brief: str, spatial: dict) -> dict:
    """Build a fine-tuning record: brief → spatial coords."""
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a Barnhaus spatial layout engine. Given a design brief, output structured room coordinates as JSON."
            },
            {
                "role": "user",
                "content": brief
            },
            {
                "role": "assistant",
                "content": json.dumps(spatial, indent=2)
            }
        ]
    }


def main():
    dry_run = "--dry-run" in sys.argv
    resume = "--resume" in sys.argv

    # Load existing output for resume
    processed_briefs = set()
    if resume and OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                rec = json.loads(line)
                brief = rec["messages"][1]["content"]
                processed_briefs.add(brief[:100])  # first 100 chars as key
        print(f"Resuming — {len(processed_briefs)} already processed")

    # Load input
    records = []
    with open(INPUT_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if dry_run:
        records = records[:3]
        print(f"DRY RUN — processing {len(records)} records")
    else:
        print(f"Processing {len(records)} records...")

    success = 0
    errors = 0

    with open(OUTPUT_FILE, "a" if resume else "w") as out_f, \
         open(ERRORS_FILE, "a" if resume else "w") as err_f:

        for i, record in enumerate(records):
            brief, layout = extract_brief(record)
            if not brief or not layout:
                continue

            # Skip if already processed
            if brief[:100] in processed_briefs:
                print(f"  [{i+1}/{len(records)}] skipping (already done)")
                continue

            print(f"  [{i+1}/{len(records)}] extracting spatial...", end=" ", flush=True)

            spatial = parse_spatial(brief, layout, i)

            if spatial and "rooms" in spatial:
                training_rec = build_training_record(brief, spatial)
                out_f.write(json.dumps(training_rec) + "\n")
                out_f.flush()
                success += 1
                room_count = len(spatial.get("rooms", {}))
                shape = spatial.get("footprint", {}).get("shape", "?")
                print(f"✅ {room_count} rooms, {shape}")
            else:
                err_f.write(json.dumps({"idx": i, "brief": brief[:200], "layout": layout[:200]}) + "\n")
                errors += 1
                print(f"❌ failed")

            # Rate limit — 3 RPM on gpt-4o fine-tune tier, be safe
            if not dry_run:
                time.sleep(1)

    print(f"\nDone: {success} success, {errors} errors")
    print(f"Output: {OUTPUT_FILE}")
    if errors:
        print(f"Errors: {ERRORS_FILE}")


if __name__ == "__main__":
    main()
