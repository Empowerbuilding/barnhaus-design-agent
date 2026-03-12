#!/usr/bin/env python3
"""
Barnhaus Fine-Tuning JSONL Compiler v2
Handles both old schema (overview/rooms/fixtures nested) and new flat schema.
Excludes: mooring (commercial), evergreen (shouse), kennedy (shouse)
"""

import json
import os

EXTRACTIONS_DIR = "/home/mitch/.openclaw/workspace/training_data/raw_extractions"
OUTPUT_FILE = "/home/mitch/.openclaw/workspace/training_data/barnhaus_training_v2.jsonl"

SKIP_SLUGS = {"mooring", "evergreen", "kennedy"}  # commercial or shouse hybrids

SYSTEM_PROMPT = """You are a Barnhaus Steel Builders design expert trained by Michael McAdams. You specialize in steel-frame barndominium and modern farmhouse homes in Texas Hill Country and surrounding areas.

Given a client design brief, you output a detailed spatial layout recommendation covering:
- Footprint shape and approximate dimensions
- Master suite location and configuration
- Public zone layout (kitchen/dining/living flow)
- Secondary bedroom arrangement and bath configuration
- Garage placement and size
- Outdoor living spaces (covered patios, views)
- Ceiling strategy (vaulted zones, ceiling heights)
- Circulation paths (entry sequence, master privacy, bedroom access)
- Roof massing (ridge direction, hero elevation, gable vs eave faces)
- Special features driven by lifestyle signals

Always design for Texas Hill Country conditions: prioritize covered outdoor living, natural light, master privacy, and indoor-outdoor connection. Steel frame construction with standing seam metal roof is standard."""


def extract_fields(plan):
    """Normalize both old and new schema into a common dict."""
    ov = plan.get("overview", {})
    is_old = bool(ov)

    if is_old:
        beds = ov.get("beds") or ov.get("beds_confirmed_l1", "")
        stories = ov.get("stories", 1)
        living_sf = ov.get("living_sf") or ov.get("living_f1_sf") or 0
        total_sf = ov.get("total_sf", 0)
        garage_sf = ov.get("garage_sf", 0)
        carport_sf = ov.get("carport_sf", 0)
        patio_sf = ov.get("patio_sf") or ov.get("patio_rear_sf") or ov.get("covered_patio_sf") or 0
        baths_full = ov.get("full_baths", "")
        baths_half = ov.get("half_baths", "")
        shape = ov.get("footprint_shape", "")
        w = ov.get("footprint_width_ft", "")
        d = ov.get("footprint_depth_ft", "")
        hero = ov.get("hero_elevation", "")
        aesthetic = ov.get("aesthetic", "")
        features = ov.get("special_features", [])
        project = plan.get("project", plan.get("slug", "Unknown"))
        roof = plan.get("roof_massing") or plan.get("roof", {})
        rooms_l1 = plan.get("rooms") or plan.get("rooms_f1", [])
        rooms_l2 = plan.get("rooms_l2", [])
        outdoor = plan.get("outdoor_spaces", [])
        ceiling_heights = {}
        garage_type = ov.get("garage_type", "")
    else:
        beds = plan.get("beds", "")
        stories = plan.get("stories", 1)
        living_sf = plan.get("total_sf_living", 0)
        total_sf = living_sf + plan.get("garage_sf", 0) + plan.get("patio_sf", 0) + plan.get("carport_sf", 0)
        garage_sf = plan.get("garage_sf", 0)
        carport_sf = plan.get("carport_sf", 0)
        patio_sf = plan.get("patio_sf", 0)
        baths_full = plan.get("baths_full", "")
        baths_half = plan.get("baths_half", "")
        shape = plan.get("house_shape", "")
        dims = plan.get("dims_est", {})
        w = dims.get("w", "")
        d = dims.get("d", "")
        hero = plan.get("hero_elevation", "")
        aesthetic = plan.get("aesthetic", "")
        features = plan.get("special_features", [])
        project = plan.get("plan_name") or plan.get("slug", "Unknown")
        roof = plan.get("roof_massing", {})
        rooms_l1 = plan.get("rooms_l1", [])
        rooms_l2 = plan.get("rooms_l2", [])
        outdoor = plan.get("outdoor_spaces", [])
        ceiling_heights = plan.get("ceiling_heights", {})
        garage_type = plan.get("garage", {}).get("type", "") if isinstance(plan.get("garage"), dict) else ""

    return dict(
        beds=beds, stories=stories, living_sf=living_sf, total_sf=total_sf,
        garage_sf=garage_sf, carport_sf=carport_sf, patio_sf=patio_sf,
        baths_full=baths_full, baths_half=baths_half, shape=shape,
        w=w, d=d, hero=hero, aesthetic=aesthetic, features=features,
        project=project, roof=roof, rooms_l1=rooms_l1, rooms_l2=rooms_l2,
        outdoor=outdoor, ceiling_heights=ceiling_heights, garage_type=garage_type,
        plan=plan
    )


def build_brief(f):
    lines = ["Design a new Barnhaus Steel Builders home with the following requirements:"]

    if f["living_sf"]:
        sf_str = f"- Living area: {f['living_sf']:,} SF"
        if f["total_sf"] and f["total_sf"] != f["living_sf"]:
            sf_str += f" (total under roof: ~{int(f['total_sf']):,} SF)"
        lines.append(sf_str)

    if f["beds"]:
        bath_str = f"{f['baths_full']} full" if f["baths_full"] else ""
        if f["baths_half"]:
            bath_str += f", {f['baths_half']} half"
        lines.append(f"- {f['beds']} bedrooms, {bath_str} bathrooms, {f['stories']}-story")

    if f["shape"]:
        dim_str = f" (~{f['w']}ft × {f['d']}ft)" if f["w"] and f["d"] else ""
        lines.append(f"- Footprint: {f['shape']}{dim_str}")

    if f["aesthetic"]:
        lines.append(f"- Style: {f['aesthetic']}")

    parking = f["garage_sf"] or f["carport_sf"]
    parking_type = f["garage_type"] or ("carport" if f["carport_sf"] else "garage")
    try:
        parking_int = int(parking) if parking else 0
    except (ValueError, TypeError):
        parking_int = 0
    if parking_int:
        lines.append(f"- {parking_type.capitalize()}: {parking_int:,} SF")

    if f["patio_sf"]:
        lines.append(f"- Covered outdoor living: {int(f['patio_sf']):,} SF")

    if f["hero"]:
        lines.append(f"- Primary view/hero elevation: {f['hero']}")

    if f["features"]:
        lines.append(f"- Client wants: {', '.join(str(x) for x in f['features'][:6])}")

    return "\n".join(lines)


def build_response(f):
    plan = f["plan"]
    lines = [f"## Barnhaus Layout: {f['project']}", ""]

    # Footprint + dimensions
    if f["shape"]:
        dim_str = f" (~{f['w']}ft × {f['d']}ft)" if f["w"] and f["d"] else ""
        lines.append(f"**Footprint:** {f['shape']}{dim_str}")

    # Roof
    roof = f["roof"]
    if isinstance(roof, dict):
        style = roof.get("primary_style") or roof.get("style", "")
        ridge = roof.get("ridge_direction", "")
        hero = roof.get("hero_elevation") or f["hero"]
        if style:
            lines.append(f"**Roof:** {style}" + (f", ridge runs {ridge}" if ridge else ""))
        if hero:
            lines.append(f"**Hero elevation:** {hero}")

    # Ceiling strategy
    ch = f["ceiling_heights"]
    if ch:
        highlights = []
        for k, v in list(ch.items())[:4]:
            highlights.append(f"{k.replace('_', ' ')}: {v}")
        lines.append(f"**Ceiling strategy:** {'; '.join(highlights)}")

    lines.append("")

    # Master suite
    master = next((r for r in f["rooms_l1"] if "master" in r.get("name","").lower()
                   and "bath" not in r.get("name","").lower()
                   and "closet" not in r.get("name","").lower()), None)
    if master:
        lines.append("**Master Suite:**")
        sf = master.get("sf_approx") or master.get("sf", "")
        ceil = master.get("ceiling", "")
        notes = master.get("notes", "")
        line = f"- Bedroom: {sf} SF" if sf else "- Bedroom:"
        if ceil: line += f", {ceil} ceiling"
        if notes: line += f" — {notes[:100]}"
        lines.append(line)

        # Ensuite + closet
        ensuite = next((r for r in f["rooms_l1"] if "ensuite" in r.get("name","").lower() or "m bath" in r.get("name","").lower() or "master bath" in r.get("name","").lower()), None)
        closet = next((r for r in f["rooms_l1"] if "closet" in r.get("name","").lower() and "master" in r.get("name","").lower()), None)
        if ensuite:
            en_notes = ensuite.get("notes","")
            lines.append(f"- Ensuite: {en_notes[:100] if en_notes else str(ensuite.get('sf_approx','')) + ' SF'}")
        if closet:
            cl_notes = closet.get("notes","")
            lines.append(f"- Closet: walk-in{', ' + cl_notes[:80] if cl_notes else ''}")
        lines.append("")

    # Public zone
    public_names = ["great", "living", "dining", "kitchen", "foyer"]
    public = [r for r in f["rooms_l1"] if any(k in r.get("name","").lower() for k in public_names)]
    if public:
        lines.append("**Public Zone:**")
        for r in public[:5]:
            name = r.get("name","")
            sf = r.get("sf_approx") or r.get("sf","")
            ceil = r.get("ceiling","")
            notes = r.get("notes","")
            parts = [name]
            if sf: parts.append(f"{sf} SF")
            if ceil: parts.append(str(ceil))
            if notes: parts.append(notes[:80])
            lines.append(f"- {' | '.join(str(p) for p in parts)}")
        lines.append("")

    # Secondary beds
    sec_beds = [r for r in f["rooms_l1"] if "bed" in r.get("name","").lower()
                and "master" not in r.get("name","").lower()
                and "embedded" not in r.get("name","").lower()]
    if f["rooms_l2"]:
        sec_beds += [r for r in f["rooms_l2"] if "bed" in r.get("name","").lower()
                     and "master" not in r.get("name","").lower()]
    if sec_beds:
        lines.append("**Secondary Bedrooms:**")
        for r in sec_beds[:4]:
            name = r.get("name","")
            sf = r.get("sf_approx") or r.get("sf","")
            ceil = r.get("ceiling","")
            notes = r.get("notes","")
            line = f"- {name}"
            if sf: line += f" ({sf} SF)"
            if ceil: line += f", {ceil}"
            if notes: line += f": {notes[:80]}"
            lines.append(line)
        lines.append("")

    # Garage / parking
    garage_info = plan.get("garage")
    if garage_info and isinstance(garage_info, dict):
        lines.append("**Garage/Parking:**")
        gtype = garage_info.get("type","attached garage")
        gsf = garage_info.get("size_sf") or f["garage_sf"] or f["carport_sf"]
        gcap = garage_info.get("capacity","")
        gceil = garage_info.get("ceiling","")
        gdoors = garage_info.get("doors",[])
        gline = f"- {gtype.title()}"
        if gsf: gline += f": {gsf} SF"
        if gcap: gline += f", {gcap}"
        if gceil: gline += f", {gceil} ceiling"
        lines.append(gline)
        if gdoors and isinstance(gdoors, list):
            lines.append(f"- Doors: {', '.join(str(d) for d in gdoors[:3])}")
        lines.append("")

    # Outdoor spaces
    outdoor = f["outdoor"]
    if outdoor:
        lines.append("**Outdoor Living:**")
        for o in outdoor[:4]:
            if isinstance(o, dict):
                name = o.get("name","")
                sf = o.get("sf") or o.get("sf_approx","")
                lvl = o.get("level","")
                notes = o.get("notes","")
                line = f"- {name}"
                if sf: line += f" ({sf} SF)"
                if lvl and lvl != 1: line += f" (L{lvl})"
                if notes: line += f" — {notes[:80]}"
                lines.append(line)
        lines.append("")

    # Special features
    if f["features"]:
        lines.append(f"**Special Features:** {', '.join(str(x) for x in f['features'][:8])}")

    return "\n".join(lines)


def main():
    records = []
    skipped = []

    files = sorted(os.listdir(EXTRACTIONS_DIR))

    for fname in files:
        if not fname.endswith(".json"):
            continue

        slug = fname.replace(".json", "")

        if slug in SKIP_SLUGS:
            skipped.append(slug)
            print(f"  SKIP: {slug}")
            continue

        fpath = os.path.join(EXTRACTIONS_DIR, fname)
        with open(fpath) as fp:
            plan = json.load(fp)

        # Skip if marked commercial/low-confidence in old schema
        note = plan.get("extraction_note","")
        if "commercial" in note.lower() or "site plan only" in note.lower():
            skipped.append(slug)
            print(f"  SKIP (note): {slug}")
            continue

        f = extract_fields(plan)
        brief = build_brief(f)
        response = build_response(f)

        record = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": brief},
                {"role": "assistant", "content": response}
            ]
        }

        records.append(record)
        print(f"  OK: {slug} ({len(brief)} / {len(response)} chars)")

    with open(OUTPUT_FILE, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    total_chars = sum(
        len(r["messages"][0]["content"]) + len(r["messages"][1]["content"]) + len(r["messages"][2]["content"])
        for r in records
    )
    est_tokens = total_chars // 4

    print(f"\n✅ Wrote {len(records)} records → {OUTPUT_FILE}")
    print(f"   Skipped: {skipped}")
    print(f"   Est. tokens: ~{est_tokens:,}")
    print(f"   Est. fine-tune cost (gpt-4o-2024-08-06): ~${est_tokens * 0.000025:.2f}")


if __name__ == "__main__":
    main()
