#!/usr/bin/env python3
"""
Build elevation training JSONL from extracted elevation JSONs + matching floor plan JSONs.
Each record = floor plan brief (user) + elevation design recommendation (assistant).
"""
import json, os

ELEV_DIR = "/home/mitch/.openclaw/workspace/training_data/elevation_extractions"
PLAN_DIR = "/home/mitch/.openclaw/workspace/training_data/raw_extractions"
OUTPUT = "/home/mitch/.openclaw/workspace/training_data/barnhaus_elevation_training.jsonl"

SYSTEM = """You are a Barnhaus Steel Builders exterior massing and roofline design expert trained by Michael McAdams. Given a client brief, you output a detailed exterior massing recommendation covering: roofline type and pitch, ridge count and direction, volume hierarchy and step-downs, fenestration rhythm and clerestory strategy, porch/overhang logic, and 2-3 specific signature design moves that make the exterior custom and distinctive. Always design for Texas Hill Country: prioritize indoor-outdoor connection, hero/view elevation, covered outdoor living, and the steel-frame barnhaus aesthetic (PBR or standing-seam metal roof, HSS columns, honest structure)."""

def get_brief(plan):
    ov = plan.get("overview", {})
    is_old = bool(ov)
    if is_old:
        beds = ov.get("beds","")
        sf = ov.get("living_sf") or ov.get("total_sf","")
        shape = ov.get("footprint_shape","")
        stories = ov.get("stories",1)
        style = ov.get("aesthetic","")
        hero = ov.get("hero_elevation","")
        garage_sf = ov.get("garage_sf",0) or ov.get("carport_sf",0)
        patio_sf = ov.get("patio_sf","")
        features = ov.get("special_features",[])
        baths = f"{ov.get('full_baths','')} full"
        if ov.get("half_baths"): baths += f", {ov['half_baths']} half"
    else:
        beds = plan.get("beds","")
        sf = plan.get("total_sf_living","")
        shape = plan.get("house_shape","")
        stories = plan.get("stories",1)
        style = plan.get("aesthetic","")
        hero = plan.get("hero_elevation","")
        garage_sf = plan.get("garage_sf",0) or plan.get("carport_sf",0)
        patio_sf = plan.get("patio_sf","")
        features = plan.get("special_features",[])
        baths = f"{plan.get('baths_full','')} full"
        if plan.get("baths_half"): baths += f", {plan['baths_half']} half"

    lines = ["Design the exterior massing and roofline for a Barnhaus Steel Builders home with:"]
    if sf: lines.append(f"- {sf:,} SF living area, {stories}-story" if isinstance(sf,int) else f"- {sf} SF living area, {stories}-story")
    if beds: lines.append(f"- {beds} bed / {baths}")
    if shape: lines.append(f"- Footprint: {shape}")
    if style: lines.append(f"- Style: {style}")
    try:
        if garage_sf: lines.append(f"- Garage/carport: {int(float(garage_sf))} SF")
    except (ValueError, TypeError): pass
    if patio_sf: lines.append(f"- Covered outdoor: {int(patio_sf) if isinstance(patio_sf,(int,float)) else patio_sf} SF")
    if hero: lines.append(f"- Hero/view elevation: {hero}")
    if features: lines.append(f"- Key features: {', '.join(str(f) for f in features[:5])}")
    return "\n".join(lines)

def build_response(elev, plan):
    roof = elev.get("roof", {})
    fen = elev.get("fenestration", {})
    porch = elev.get("porch", {})
    moves = elev.get("signature_moves", [])

    output = {
        "roof": {
            "primary_type": roof.get("primary_type", ""),
            "pitch_main": roof.get("pitch_main", ""),
            "pitch_secondary": roof.get("pitch_secondary", ""),
            "ridge_count": roof.get("ridge_count"),
            "ridge_direction": roof.get("ridge_direction", ""),
            "volume_breaks": roof.get("volume_breaks", ""),
            "garage_roof": roof.get("garage_roof", ""),
            "porch_roof": roof.get("porch_roof", "")
        },
        "fenestration": {
            "grouping_strategy": fen.get("grouping_strategy", ""),
            "clerestory": fen.get("clerestory", ""),
            "hero_elevation": fen.get("hero_elevation", ""),
            "entry_door": fen.get("entry_door", ""),
            "window_roofline_relationship": fen.get("window_roofline_relationship", "")
        },
        "porch": {
            "type": porch.get("type", ""),
            "depth_ft": porch.get("depth_ft", ""),
            "connection": porch.get("connection", ""),
            "fascia": porch.get("fascia", "")
        },
        "cladding": elev.get("cladding", ""),
        "signature_moves": moves[:3]
    }

    return json.dumps(output)

records = []
missing_plans = []

for fname in sorted(os.listdir(ELEV_DIR)):
    if not fname.endswith(".json"): continue
    slug = fname.replace(".json","")

    with open(f"{ELEV_DIR}/{fname}") as f:
        elev = json.load(f)

    # Find matching floor plan
    plan_path = f"{PLAN_DIR}/{slug}.json"
    if not os.path.exists(plan_path):
        missing_plans.append(slug)
        plan = {"slug": slug}
    else:
        with open(plan_path) as f:
            plan = json.load(f)

    brief = get_brief(plan)
    response = build_response(elev, plan)

    records.append({
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": brief},
            {"role": "assistant", "content": response}
        ]
    })
    print(f"  OK: {slug}")

with open(OUTPUT, "w") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

total_chars = sum(len(r["messages"][1]["content"]) + len(r["messages"][2]["content"]) for r in records)
print(f"\n✅ {len(records)} records → {OUTPUT}")
print(f"   Missing floor plans: {missing_plans}")
print(f"   Est tokens: ~{total_chars//4:,}")
print(f"   Est fine-tune cost: ~${total_chars//4 * 0.000025:.2f}")
