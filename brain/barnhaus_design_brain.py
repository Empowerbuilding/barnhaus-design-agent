#!/usr/bin/env python3
"""
barnhaus_design_brain.py
Runs a Supabase submission through both fine-tuned models and outputs
a complete design JSON (layout + exterior).

Usage:
  python3 barnhaus_design_brain.py <submission_id_prefix>

Example:
  python3 barnhaus_design_brain.py a3fe564b
"""

import sys
import json
import urllib.request
import urllib.error

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
SUPABASE_URL = "https://hbfjdfxephlczkfgpceg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiZmpkZnhlcGhsY3prZmdwY2VnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTMzNzcxMCwiZXhwIjoyMDU0OTEzNzEwfQ.weXk7CqDqR8XkEpi4kaI_GmHWlkqh6snOMQm-hk48RM"

MODEL_LAYOUT = "ft:gpt-4o-2024-08-06:personal:barnhaus-v4:DI9LtTgM"
MODEL_ELEV   = "ft:gpt-4o-2024-08-06:personal:barnhaus-elev-v2:DI9VoKUx"

LAYOUT_SYSTEM = """You are a Barnhaus Steel Builders layout design expert trained by Michael McAdams. Given a client brief, output a detailed floor plan layout in JSON covering: rooms (name, sf, adjacencies), circulation strategy, footprint dimensions, garage placement, and outdoor spaces."""

ELEV_SYSTEM = """You are a Barnhaus Steel Builders exterior massing and roofline design expert trained by Michael McAdams. Output a JSON object with keys: roof, fenestration, porch, cladding, signature_moves. Design for Texas Hill Country: steel-frame barnhaus aesthetic, indoor-outdoor connection, hero elevation, covered outdoor living."""


# ─────────────────────────────────────────────
# SUPABASE FETCH
# ─────────────────────────────────────────────

def fetch_submission(id_prefix: str) -> dict:
    # First try exact UUID match
    url = f"{SUPABASE_URL}/rest/v1/design_intake_submissions?id=eq.{id_prefix}&select=*"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    })
    with urllib.request.urlopen(req) as r:
        results = json.load(r)
    if results:
        return results[0]
    # Fallback: fetch all and filter by prefix
    url2 = f"{SUPABASE_URL}/rest/v1/design_intake_submissions?select=*"
    req2 = urllib.request.Request(url2, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    })
    with urllib.request.urlopen(req2) as r:
        all_records = json.load(r)
    matches = [r for r in all_records if r.get("id", "").startswith(id_prefix)]
    if not matches:
        raise ValueError(f"No submission found with id prefix: {id_prefix}")
    return matches[0]


# ─────────────────────────────────────────────
# BUILD BRIEF
# ─────────────────────────────────────────────

def build_brief(sub: dict) -> str:
    lines = ["Design a Barnhaus Steel Builders home:"]

    sqft = sub.get("living") or sub.get("sqft")
    stories = sub.get("stories", "single")
    if sqft:
        lines.append(f"- {sqft} SF living area, {stories}-story")

    beds = sub.get("bedrooms")
    baths = sub.get("bathrooms") or sub.get("full_baths")
    half = sub.get("half_baths")
    bath_str = f"{baths} bath" if baths else ""
    if half: bath_str += f" + {half} half"
    if beds:
        lines.append(f"- {beds} bed / {bath_str}")

    shape = sub.get("house_shape")
    if shape: lines.append(f"- Footprint: {shape}")

    style = sub.get("aesthetic_style") or sub.get("style")
    if style: lines.append(f"- Style: {style}")

    cars = sub.get("garage_cars")
    gtype = sub.get("garage_type", "")
    gorient = sub.get("garage_orientation", "")
    if cars and str(cars) != "0":
        garage_str = f"- Garage: {cars}-car {gtype}"
        if gorient: garage_str += f", {gorient}"
        lines.append(garage_str)

    porch = sub.get("porch_type")
    if porch and porch != "none": lines.append(f"- Porch: {porch}")

    features = sub.get("desired_rooms") or {}
    if isinstance(features, dict):
        feat_list = [k.replace("_", " ") for k, v in features.items() if v is True]
        if feat_list:
            lines.append(f"- Features: {', '.join(feat_list[:6])}")

    # ── Site orientation ──────────────────────────────────────────────────
    street = sub.get("street_facing", "")
    view = sub.get("view_facing", "")
    lot = sub.get("lot") or {}
    driveway = lot.get("driveway_approach", "") if isinstance(lot, dict) else ""

    if street: lines.append(f"- Street-facing side: {street}")
    if view:   lines.append(f"- Primary view / hero elevation: {view}")
    if driveway: lines.append(f"- Driveway approach: {driveway}")

    # ── Spatial intent ────────────────────────────────────────────────────
    master_suite = sub.get("master_suite") or {}
    master_loc = master_suite.get("location", "") if isinstance(master_suite, dict) else ""
    garage_attach = sub.get("garage_attachment", "")
    priorities = sub.get("priorities") or []

    if master_loc:    lines.append(f"- Master suite location: {master_loc.replace('_', ' ')}")
    if garage_attach: lines.append(f"- Garage attachment: {garage_attach.replace('_', ' ')}")
    if priorities:    lines.append(f"- Client priorities: {', '.join(priorities)}")

    # ── Bubble layout from intake form Step 11 ────────────────────────────
    bubbles = sub.get("bubbles") or []
    bubble_positions = sub.get("bubble_positions") or {}

    if bubbles:
        lines.append(f"- Client bubble layout (relative room positions): {json.dumps(bubbles)}")
    elif bubble_positions:
        lines.append(f"- Client bubble positions: {json.dumps(bubble_positions)}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# OPENAI CALL
# ─────────────────────────────────────────────

def call_model(model: str, system: str, user: str, max_tokens: int = 1000, temperature: float = 0.2) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req) as r:
        resp = json.load(r)

    content = resp["choices"][0]["message"]["content"]
    finish = resp["choices"][0]["finish_reason"]

    # Try to parse as JSON
    try:
        # Strip markdown code fences if present
        clean = content.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
            clean = clean.rsplit("```", 1)[0]
        return json.loads(clean), finish
    except json.JSONDecodeError:
        return {"raw": content}, finish


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def run(id_prefix: str):
    print(f"\n🔍 Fetching submission: {id_prefix}...")
    sub = fetch_submission(id_prefix)
    print(f"✅ Found: {sub.get('name')} | {sub.get('living')} SF | {sub.get('bedrooms')}bd | {sub.get('house_shape')}")

    brief = build_brief(sub)
    print(f"\n📋 Brief:\n{brief}\n")

    # ── Layout model ──
    print("🏠 Running layout model (v2)...")
    layout, layout_finish = call_model(MODEL_LAYOUT, LAYOUT_SYSTEM, brief, max_tokens=1200, temperature=0.2)
    print(f"   finish_reason: {layout_finish}")
    if layout_finish != "stop":
        print("   ⚠️  Layout did not finish cleanly")

    # ── Elevation model ──
    print("🏗️  Running elevation model...")
    elev, elev_finish = call_model(MODEL_ELEV, ELEV_SYSTEM, brief, max_tokens=800, temperature=0.1)
    print(f"   finish_reason: {elev_finish}")
    if elev_finish != "stop":
        print("   ⚠️  Elevation did not finish cleanly")

    # ── Combine ──
    design = {
        "submission_id": sub.get("id"),
        "name": sub.get("name"),
        "brief": brief,
        "layout": layout,
        "exterior": elev,
    }

    # Save to file
    import os
    designs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "designs")
    os.makedirs(designs_dir, exist_ok=True)
    out_path = os.path.join(designs_dir, f"design_{sub['id'][:8]}.json")
    with open(out_path, "w") as f:
        json.dump(design, f, indent=2)

    print(f"\n✅ Design saved: {out_path}")
    print("\n" + "="*60)
    print("LAYOUT:")
    print(json.dumps(layout, indent=2)[:1500])
    print("\nEXTERIOR:")
    print(json.dumps(elev, indent=2))

    return design


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 barnhaus_design_brain.py <submission_id_prefix>")
        sys.exit(1)
    run(sys.argv[1])
