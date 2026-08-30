"""
run.py — Main entry point for the Barnhaus Revit Copilot.

Usage:
    python3 run.py scan              # Scan open Revit model, build state
    python3 run.py qa                # Run QA checks on current state
    python3 run.py qa --fix          # Run QA and auto-fix what's possible
    python3 run.py draft1            # Create Draft 1 sheet bundle
    python3 run.py draft2            # Create Draft 2 sheet bundle
    python3 run.py draft3            # Create Draft 3 sheet bundle
    python3 run.py schedule          # Generate door/window schedule (A105)
    python3 run.py dimensions        # Apply dimension plans
    python3 run.py electrical        # Run electrical plan (A108)
    python3 run.py plumbing          # Run plumbing plan (A109)
    python3 run.py all               # Full run: scan → qa → draft1 → draft2 → draft3
    python3 run.py qa-marks          # Window/Door Type Mark QA — marks vs actual dimensions
    python3 run.py qa-electrical     # Electrical fixture label QA — flag blank Type Marks
    python3 run.py read-dims [kw]    # READ existing dimensions (optionally filter views/sheets by keyword)
    python3 run.py assemble-sheets   # Match views → empty sheets (dry run; add --apply to place)
    python3 run.py export-image <view_id> [out.png]  # Export view/sheet image through the tunnel (vision QA)
    python3 run.py export-tiles <view_id> [out_dir]  # High-res export sliced into vision-ready tiles (sheet QA)
    python3 run.py qa-visual [filter] [--max N] [--fresh] [--include kw] [--exclude kw1,kw2] [--tile-size N] [--workers N]
                                     # Batch vision QA: populated sheets → tiles → PARALLEL vision → findings report
                                     # Unchanged sheets (pixel hash) reuse previous findings; blank tiles skipped
    python3 run.py qa-dims [keyword]  # Dimension consistency QA (mixed planes, line-anchored, duplicates)
    python3 run.py try_delete <id>   # Dry-run delete — captures Revit error messages, always rolls back
    python3 run.py deps <id>         # Dependency map — what is attached to this element ID
    python3 run.py sketch <id>       # Roof sketch inspector — find locked alignment constraints
    python3 run.py inspect <id>      # Deep element inspection — all params, host, joins, bbox
    python3 run.py review [--visual] [--no-scan] [--upload]   # FULL drafter-submission audit → scorecard + punch list + diff vs last review
    python3 run.py suppress <key> [reason]   # Accept a finding — never shows again on this document
    python3 run.py unsuppress <key>          # Re-enable a suppressed finding
    python3 run.py suppressions              # List suppressed findings for current document
    python3 run.py verify <project_name>     # Intent-vs-model check (portal design_intent_items) → PASS/FAIL/NEEDS-HUMAN per item
    python3 run.py weight                    # Model weight report — heavy families, imports, top-20 strip hit list
    python3 run.py standards                 # Run standards.yaml rules (sheet order/naming, views, titleblock)
    python3 run.py gate [project] [--post]   # standards + verify + qa in one shot → GATE: PASS/FAIL (--post → portal juanito-production)
"""

import sys
from core.project_state import scan_project, load_state
from core.revit_client import health_check


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd    = sys.argv[1].lower()
    flags  = sys.argv[2:]
    auto_fix = "--fix" in flags

    # Health check first
    if not health_check():
        print("❌ Revit bridge not reachable. Open Revit and connect the addin.")
        sys.exit(1)

    if cmd == "scan":
        scan_project()

    elif cmd == "qa":
        from qa.qa_runner import run_qa, save_report
        state  = load_state()
        report = run_qa(state, auto_fix=auto_fix)
        save_report(report)

    elif cmd == "draft1":
        from tasks.sheets.draft1_bundle import run
        state = scan_project()
        run(state)

    elif cmd == "draft2":
        from tasks.sheets.draft2_bundle import run
        state = scan_project()
        run(state)

    elif cmd == "draft3":
        from tasks.sheets.draft3_bundle import run
        state = scan_project()
        run(state)

    elif cmd == "schedule":
        from tasks.schedules.door_window_schedule import run
        state = scan_project()
        run(state)

    elif cmd == "dimensions":
        from tasks.dimensions.dimension_plans import run
        state = scan_project()
        run(state, level_key='L1')
        # Auto-detect 2-story and dimension L2 if it has rooms
        rooms_l2 = [r for r in state.get('rooms', []) if r.get('area_sf', 0) > 50 and '2' in str(r.get('level', ''))]
        if rooms_l2:
            print(f"\n  🏗️  2-story detected ({len(rooms_l2)} rooms on L2) — dimensioning Level 2...")
            run(state, level_key='L2')

    elif cmd == "electrical":
        from tasks.mep.electrical import run_l1, run_l2
        state = scan_project()
        run_l1(state)
        if state.get("summary", {}).get("is_two_story"):
            run_l2(state)

    elif cmd == "plumbing":
        from tasks.mep.plumbing import run_l1, run_l2
        state = scan_project()
        run_l1(state)
        if state.get("summary", {}).get("is_two_story"):
            run_l2(state)

    elif cmd == "all":
        from qa.qa_runner import run_qa
        from tasks.sheets.draft1_bundle import run as d1
        from tasks.sheets.draft2_bundle import run as d2
        from tasks.sheets.draft3_bundle import run as d3
        from tasks.schedules.door_window_schedule import run as sched
        from tasks.dimensions.dimension_plans import run as dims

        print("\n🚀 Full run starting...\n")
        state = scan_project()

        print("\n── Step 1: QA ──")
        run_qa(state, auto_fix=True)

        # Reload state after potential auto-fixes
        state = scan_project()

        print("\n── Step 2: Draft 1 ──")
        d1(state)

        print("\n── Step 3: Schedule ──")
        sched(state)

        print("\n── Step 4: Dimensions ──")
        dims(state)

        print("\n── Step 5: Draft 2 ──")
        d2(state)

        print("\n── Step 6: Draft 3 ──")
        d3(state)

        print("\n✅ Full run complete.")

    elif cmd == "qa-marks":
        from qa.opening_marks_qa import run_opening_marks_qa
        try:
            state = load_state()
        except FileNotFoundError:
            state = scan_project()
        if state.get("doors") and "type_mark" not in state["doors"][0]:
            print("  State predates type_mark capture — rescanning...")
            state = scan_project()
        run_opening_marks_qa(state)

    elif cmd == "qa-electrical":
        from qa.electrical_qa import run_electrical_qa
        run_electrical_qa()

    elif cmd == "read-dims":
        from tasks.dimensions.read_dimensions import run as read_dims
        keyword = flags[0] if flags else None
        read_dims(keyword)

    elif cmd == "assemble-sheets":
        from tasks.sheets.assemble_sheets import run as assemble
        assemble(apply="--apply" in flags)

    elif cmd == "export-image":
        if not flags:
            print("Usage: python3 run.py export-image <view_id> [out.png]")
            sys.exit(1)
        from core.revit_client import save_view_image
        out = flags[1] if len(flags) > 1 else f"view_{flags[0]}.png"
        save_view_image(int(flags[0]), out, resolution=3000)

    elif cmd == "export-tiles":
        if not flags:
            print("Usage: python3 run.py export-tiles <view_id> [out_dir]")
            sys.exit(1)
        from qa.visual_qa import export_tiles
        out_dir = flags[1] if len(flags) > 1 else "exports"
        export_tiles(int(flags[0]), out_dir)

    elif cmd == "qa-visual":
        from qa.visual_qa import run_visual_qa

        def _flag_val(name):
            if name in flags:
                try: return flags[flags.index(name) + 1]
                except IndexError: return None
            return None

        # Positional filter = first non-flag token that isn't a flag's value
        flag_values = set()
        for fname in ("--max", "--include", "--exclude", "--tile-size", "--workers"):
            v = _flag_val(fname)
            if v is not None:
                flag_values.add(v)
        pos = [f for f in flags if not f.startswith("--") and f not in flag_values]

        def _int_or_none(v):
            try: return int(v)
            except (TypeError, ValueError): return None

        exclude_raw = _flag_val("--exclude")
        run_visual_qa(
            pos[0] if pos else None,
            max_sheets=_int_or_none(_flag_val("--max")),
            fresh="--fresh" in flags,
            include=_flag_val("--include"),
            exclude=[e.strip() for e in exclude_raw.split(",") if e.strip()] if exclude_raw else None,
            tile_size=_int_or_none(_flag_val("--tile-size")),
            workers=_int_or_none(_flag_val("--workers")),
        )

    elif cmd == "qa-dims":
        from qa.dims_qa import run as dims_qa
        dims_qa(flags[0] if flags else None)

    elif cmd == "review":
        from tasks.review import run_review
        run_review(visual="--visual" in flags,
                   no_scan="--no-scan" in flags,
                   upload="--upload" in flags)

    elif cmd in ("suppress", "unsuppress", "suppressions"):
        from core.project_state import load_state as _ls
        from core.snapshots import doc_slug
        from qa import suppressions as supp
        try:
            slug = doc_slug(_ls())
        except FileNotFoundError:
            print("❌ No project_state.json — run a scan or review first.")
            sys.exit(1)
        if cmd == "suppressions":
            supp.show(slug)
        elif cmd == "suppress":
            if not flags:
                print("Usage: python3 run.py suppress <key> [reason]")
                sys.exit(1)
            supp.add(slug, flags[0], " ".join(flags[1:]))
        else:
            if not flags:
                print("Usage: python3 run.py unsuppress <key>")
                sys.exit(1)
            supp.remove(slug, flags[0])

    elif cmd == "study-set":
        from tasks.study_set.study_set import run as study_run
        state = scan_project()
        study_run(state)

    elif cmd == "study-set-export":
        from tasks.study_set.study_set import export_study_set
        export_study_set()

    elif cmd == "try_delete":
        if not flags:
            print("Usage: python3 run.py try_delete <element_id>")
            sys.exit(1)
        from core.revit_client import try_delete
        import json
        result = try_delete(int(flags[0]))
        print(json.dumps(result, indent=2))

    elif cmd == "deps":
        if not flags:
            print("Usage: python3 run.py deps <element_id>")
            sys.exit(1)
        from core.revit_client import get_dependencies
        import json
        result = get_dependencies(int(flags[0]))
        print(json.dumps(result, indent=2))

    elif cmd == "sketch":
        if not flags:
            print("Usage: python3 run.py sketch <element_id>")
            sys.exit(1)
        from core.revit_client import inspect_roof_sketch
        import json
        result = inspect_roof_sketch(int(flags[0]))
        print(json.dumps(result, indent=2))

    elif cmd == "inspect":
        if not flags:
            print("Usage: python3 run.py inspect <element_id>")
            sys.exit(1)
        from core.revit_client import inspect_element
        import json
        result = inspect_element(int(flags[0]))
        print(json.dumps(result, indent=2))

    elif cmd == "verify":
        if not flags:
            print("Usage: python3 run.py verify <project_name>")
            sys.exit(1)
        from intent_queries import run_verify
        run_verify(flags[0])

    elif cmd == "weight":
        from weight_report import run_weight
        run_weight()

    elif cmd == "standards":
        from standards_runner import run_standards
        run_standards()

    elif cmd == "gate":
        from tasks.gate import run_gate
        pos = [f for f in flags if not f.startswith("--")]
        run_gate(project_name=pos[0] if pos else None,
                 post="--post" in flags)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
