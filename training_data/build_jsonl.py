#!/usr/bin/env python3
"""
Barnhaus Fine-Tuning JSONL Compiler
Converts raw extraction JSONs → OpenAI fine-tuning JSONL
"""

import json
import os
import re

EXTRACTIONS_DIR = "/home/mitch/.openclaw/workspace/training_data/raw_extractions"
OUTPUT_FILE = "/home/mitch/.openclaw/workspace/training_data/barnhaus_training.jsonl"

SYSTEM_PROMPT = """You are a Barnhaus Steel Builders design expert trained by Michael McAdams. You specialize in steel-frame barndominium and modern farmhouse homes in Texas Hill Country and surrounding areas.

Given a client design brief, you output a detailed spatial layout recommendation covering:
- Footprint shape and approximate dimensions
- Master suite location and configuration
- Public zone layout (kitchen/dining/living flow)
- Secondary bedroom arrangement and bath configuration
- Garage placement and size
- Outdoor living spaces (covered patios, outdoor kitchen, views)
- Ceiling strategy (vaulted zones, ceiling heights)
- Circulation paths (entry sequence, master privacy, bedroom access)
- Roof massing (ridge direction, hero elevation, gable vs eave faces)
- Special features driven by lifestyle signals

Always design for Texas Hill Country conditions: prioritize covered outdoor living, natural light, master privacy, and indoor-outdoor connection. Steel frame construction with standing seam metal roof is standard."""


def build_brief(plan: dict) -> str:
    """Build a client brief from extracted plan data — simulates what a real intake submission looks like."""
    ov = plan.get("overview", {})
    
    lines = ["Design a new Barnhaus Steel Builders home with the following requirements:"]
    
    # Size
    living = ov.get("living_sf") or ov.get("living_f1_sf")
    if living:
        total = ov.get("total_sf", "")
        lines.append(f"- Living area: {living:,} SF (total under roof: {total:,} SF)" if total else f"- Living area: {living:,} SF")
    
    # Program
    beds = ov.get("beds") or ov.get("beds_confirmed_l1", "")
    baths_full = ov.get("full_baths", "")
    baths_half = ov.get("half_baths", "")
    stories = ov.get("stories", 1)
    if beds:
        bath_str = f"{baths_full} full" + (f", {baths_half} half" if baths_half else "")
        lines.append(f"- {beds} bedrooms, {bath_str} bathrooms, {stories}-story")
    
    # Shape
    shape = ov.get("footprint_shape", "")
    if shape:
        lines.append(f"- Footprint: {shape}")
    
    # Style / aesthetic
    aesthetic = ov.get("aesthetic", "")
    if aesthetic:
        lines.append(f"- Style: {aesthetic}")
    
    # Garage
    garage_sf = ov.get("garage_sf", 0)
    garage_type = ov.get("garage_type", "")
    if garage_sf:
        lines.append(f"- Garage: {garage_type} ({garage_sf:,} SF)" if garage_type else f"- Garage: {garage_sf:,} SF")
    
    # Outdoor
    patio_keys = ["patio_sf", "patio_rear_sf", "covered_patio_sf"]
    patio = next((ov[k] for k in patio_keys if ov.get(k)), None)
    if patio:
        lines.append(f"- Covered outdoor living: {patio:,} SF minimum")
    
    # Hero / view
    hero = ov.get("hero_elevation", "")
    if hero:
        lines.append(f"- Primary view/hero elevation: {hero}")
    
    # Special features
    features = ov.get("special_features", [])
    if features:
        lines.append(f"- Client wants: {', '.join(features[:6])}")
    
    # Design quality signals
    dq = plan.get("design_quality", {})
    if isinstance(dq, dict):
        notes = dq.get("notes", "")
        if notes:
            lines.append(f"- Design priorities: {notes[:200]}")
    
    return "\n".join(lines)


def build_layout_response(plan: dict) -> str:
    """Build the assistant layout response from extracted plan data."""
    ov = plan.get("overview", {})
    lines = [f"## Barnhaus Layout: {plan.get('project', 'Unknown')}"]
    lines.append("")
    
    # Footprint
    shape = ov.get("footprint_shape", "")
    w = ov.get("footprint_width_ft", "")
    d = ov.get("footprint_depth_ft", "")
    if shape:
        dim_str = f" (~{w}ft × {d}ft)" if w and d else ""
        lines.append(f"**Footprint:** {shape}{dim_str}")
    
    # Roof
    roof = plan.get("roof_massing") or plan.get("roof", {})
    if isinstance(roof, dict):
        style = roof.get("primary_style") or roof.get("style", "")
        ridge = roof.get("ridge_direction", "")
        hero = roof.get("hero_elevation") or ov.get("hero_elevation", "")
        ceiling = roof.get("ceiling_features", [])
        if style:
            lines.append(f"**Roof:** {style}" + (f", ridge runs {ridge}" if ridge else ""))
        if hero:
            lines.append(f"**Hero elevation:** {hero}")
        if ceiling:
            if isinstance(ceiling, list):
                lines.append(f"**Ceiling strategy:** {'; '.join(str(c) for c in ceiling[:4])}")
            else:
                lines.append(f"**Ceiling strategy:** {ceiling}")
    
    lines.append("")
    
    # Master suite
    fixtures = plan.get("fixtures", {})
    master = fixtures.get("master_suite", {})
    rooms = plan.get("rooms") or plan.get("rooms_f1", [])
    master_room = next((r for r in rooms if "master" in r.get("name","").lower() and "bath" not in r.get("name","").lower() and "closet" not in r.get("name","").lower()), None)
    
    lines.append("**Master Suite:**")
    if master_room:
        loc = master_room.get("notes","")
        dim = master_room.get("dims_est","")
        ceil = master_room.get("ceiling") or master_room.get("ceiling_ft","")
        lines.append(f"- Bedroom: {dim + ', ' if dim else ''}{loc[:100] if loc else ''}")
        if ceil:
            lines.append(f"- Ceiling: {ceil}")
    if master:
        if isinstance(master, dict):
            bed_wall = master.get("bed_wall","")
            closet = master.get("closet") or master.get("his_closet","") or master.get("her_closet","")
            ensuite = master.get("ensuite") or master.get("ensuite_connection","")
            if bed_wall:
                lines.append(f"- Bed wall: {bed_wall}")
            if closet:
                lines.append(f"- Closet: {closet}")
            if ensuite:
                lines.append(f"- Ensuite: {str(ensuite)[:120]}")
    
    lines.append("")
    
    # Kitchen
    kitchen = fixtures.get("kitchen", {})
    if kitchen and isinstance(kitchen, dict):
        lines.append("**Kitchen:**")
        island = kitchen.get("island", {})
        if island:
            if isinstance(island, dict):
                orient = island.get("orientation","")
                size = island.get("size","")
                feat = island.get("features",[])
                lines.append(f"- Island: {size + ', ' if size else ''}{orient + ', ' if orient else ''}{', '.join(feat) if feat else ''}")
            else:
                lines.append(f"- Island: {island}")
        range_wall = kitchen.get("range", {})
        if range_wall and isinstance(range_wall, dict):
            lines.append(f"- Range: {range_wall.get('wall','')}" + (f" ({range_wall.get('feature','')})" if range_wall.get('feature') else ""))
        pantry = kitchen.get("pantry", {})
        if pantry:
            if isinstance(pantry, dict):
                lines.append(f"- Pantry: {pantry.get('type','')}")
            else:
                lines.append(f"- Pantry: {pantry}")
        lines.append("")
    
    # Rooms summary
    public_rooms = [r for r in rooms if any(k in r.get("name","").lower() for k in ["living","dining","kitchen","great","foyer"])]
    bed_rooms = [r for r in rooms if "bed" in r.get("name","").lower() and "master" not in r.get("name","").lower()]
    
    if public_rooms:
        lines.append("**Public Zone:**")
        for r in public_rooms[:4]:
            name = r.get("name","")
            dim = r.get("dims_est","")
            ceil = r.get("ceiling") or (f"{r.get('ceiling_ft')}ft" if r.get("ceiling_ft") else "")
            notes = r.get("notes","")
            parts = [name]
            if dim: parts.append(dim)
            if ceil: parts.append(str(ceil))
            if notes: parts.append(notes[:80])
            lines.append(f"- {' | '.join(parts)}")
        lines.append("")
    
    if bed_rooms:
        lines.append("**Secondary Bedrooms:**")
        for r in bed_rooms[:4]:
            name = r.get("name","")
            dim = r.get("dims_est","")
            notes = r.get("notes","")
            line = f"- {name}"
            if dim: line += f" ({dim})"
            if notes: line += f": {notes[:80]}"
            lines.append(line)
        lines.append("")
    
    # Hallways
    hallways = plan.get("hallways", [])
    if hallways:
        lines.append("**Circulation:**")
        for h in hallways[:3]:
            if isinstance(h, dict):
                name = h.get("name","")
                htype = h.get("type","")
                connects = h.get("connects",[])
                width = h.get("width_ft","")
                parts = []
                if name: parts.append(name)
                if htype: parts.append(htype)
                if width: parts.append(f"{width}ft wide")
                if connects and isinstance(connects, list): parts.append("→ ".join(str(c) for c in connects[:3]))
                lines.append(f"- {' | '.join(parts)}")
        lines.append("")
    
    # Outdoor
    outdoor = plan.get("outdoor_spaces", [])
    if outdoor:
        lines.append("**Outdoor Living:**")
        for o in outdoor[:3]:
            if isinstance(o, dict):
                name = o.get("name","")
                sf = o.get("sf","")
                covered = o.get("covered","")
                loc = o.get("location","")
                feats = o.get("features",[])
                line = f"- {name}"
                if sf: line += f" ({sf} SF)"
                if covered: line += f", {covered}"
                if loc: line += f", {loc}"
                if feats and isinstance(feats, list): line += f" — {', '.join(str(f) for f in feats[:3])}"
                lines.append(line)
        lines.append("")
    
    # Circulation narrative
    circ = plan.get("circulation", {})
    if circ and isinstance(circ, dict):
        lines.append("**Circulation Strategy:**")
        entry = circ.get("entry","")
        path_master = circ.get("path_to_master","")
        path_sec = circ.get("path_to_secondary_beds","") or circ.get("path_to_secondary","")
        pub_flow = circ.get("public_flow","")
        privacy = circ.get("master_privacy","")
        if entry: lines.append(f"- Entry: {str(entry)[:120]}")
        if path_master: lines.append(f"- Path to master: {str(path_master)[:120]}")
        if path_sec: lines.append(f"- Secondary beds: {str(path_sec)[:120]}")
        if pub_flow: lines.append(f"- Public flow: {str(pub_flow)[:120]}")
        if privacy and str(privacy).isdigit(): lines.append(f"- Master privacy score: {privacy}/5")
        lines.append("")
    
    # Design quality
    dq = plan.get("design_quality", {})
    if dq and isinstance(dq, dict):
        notes = dq.get("notes","")
        if notes:
            lines.append(f"**Design Notes:** {notes[:300]}")
    
    return "\n".join(lines)


def main():
    records = []
    skipped = []
    
    files = sorted(os.listdir(EXTRACTIONS_DIR))
    
    for fname in files:
        if not fname.endswith(".json"):
            continue
        
        slug = fname.replace(".json", "")
        fpath = os.path.join(EXTRACTIONS_DIR, fname)
        
        with open(fpath) as f:
            plan = json.load(f)
        
        # Skip commercial (mooring event center)
        note = plan.get("extraction_note","")
        if "commercial" in note.lower():
            skipped.append(slug)
            print(f"  SKIP (commercial): {slug}")
            continue
        
        # Skip low-confidence extractions
        if "low-confidence" in note.lower() or "site plan only" in note.lower():
            skipped.append(slug)
            print(f"  SKIP (low confidence): {slug}")
            continue
        
        brief = build_brief(plan)
        layout = build_layout_response(plan)
        
        record = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": brief},
                {"role": "assistant", "content": layout}
            ]
        }
        
        records.append(record)
        print(f"  OK: {slug} ({len(brief)} brief chars, {len(layout)} layout chars)")
    
    # Write JSONL
    with open(OUTPUT_FILE, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    
    print(f"\n✅ Wrote {len(records)} training records to {OUTPUT_FILE}")
    print(f"   Skipped: {skipped}")
    
    # Quick validation
    total_tokens_est = sum(
        len(r["messages"][0]["content"]) + len(r["messages"][1]["content"]) + len(r["messages"][2]["content"])
        for r in records
    ) // 4  # rough token estimate (4 chars per token)
    
    print(f"   Estimated total tokens: ~{total_tokens_est:,}")
    print(f"   Estimated fine-tune cost (gpt-4o): ~${total_tokens_est * 0.000025:.2f}")

if __name__ == "__main__":
    main()
