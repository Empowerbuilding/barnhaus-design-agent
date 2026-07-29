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
    python3 run.py try_delete <id>   # Dry-run delete — captures Revit error messages, always rolls back
    python3 run.py deps <id>         # Dependency map — what is attached to this element ID
    python3 run.py sketch <id>       # Roof sketch inspector — find locked alignment constraints
    python3 run.py inspect <id>      # Deep element inspection — all params, host, joins, bbox
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

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
