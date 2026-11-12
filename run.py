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
    python3 run.py qa-model [--since-mins N] [--must-cover id,id] [--sheet-snapshot f | --sheets-since f [--expect-sheets N] [--expect-viewports N]]
                                     # QA gate after a write phase: names what it looked at; fails when it did not look at what the phase wrote
    python3 run.py qa-marks [--cached] [--max-age-mins N]
                                     # Window/Door Type Mark QA on the OPEN document — marks vs actual dimensions
                                     # (live read; --cached = recent scan of the same document only)
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
    python3 run.py kit [project_name]        # CFS kit BOM from open Revit model (extract + BOM + price ballpark)
    python3 run.py kit-geometry [name]       # Extract kit geometry JSON only (no BOM) — for calibration snapshots
    python3 run.py kit-from <geometry.json>  # OFFLINE: build kit BOM from a saved geometry JSON (no Revit needed)
    python3 run.py kit-test                  # OFFLINE: run kit_package fixture pipeline test
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

    # Offline commands — no Revit bridge required
    if cmd == "kit-from":
        if not flags:
            print("Usage: python3 run.py kit-from <geometry.json>")
            sys.exit(1)
        from tasks.kit_package.kit import run_from_geometry
        run_from_geometry(flags[0])
        return

    if cmd == "kit-test":
        from tasks.kit_package import fixture_test
        fixture_test.main()
        return

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

    elif cmd == "qa-model":
        # Post-placement QA gate (model-work): Component-First discipline, sink
        # seating, ceiling boundaries, duplicates, floating fixtures.
        # --since-mins N  scope to elements added/modified in the last N minutes
        #                    (change feed; falls back to full scan if unreachable)
        # --must-cover a,b  element ids a write phase created or changed: the gate
        #                    FAILS unless every one of them was scanned (a gate that
        #                    looks at nothing must not read as clean). Walls, floors,
        #                    roofs and site are scanned too; an id in no scanned category
        #                    is read by id and named with its real category.
        # Sheet phases (sheets and viewports are counted before and after):
        # --sheet-snapshot <file>  BEFORE the phase writes: save the sheets and viewport
        #                    ids of the open document, then exit
        # --sheets-since <file>    compare the model with that snapshot: sheets and
        #                    viewports created, by id; --expect-sheets N and
        #                    --expect-viewports N fail the gate on a different count
        # Exit code 1 when any 'fix' findings — gate semantics for the runner.
        # Exit code 2 when the gate could not look (bad flags, unreadable model, a
        # snapshot of another document).
        import json as _json
        from qa.model_work_qa import run_model_work_qa
        only_ids = None
        must_cover = None

        def _flag_value(name):
            try:
                v = flags[flags.index(name) + 1]
            except IndexError:
                v = None
            if v is None or v.startswith("--"):
                print(f"{name} needs a value")
                sys.exit(2)
            return v

        if "--sheet-snapshot" in flags:
            from qa import sheet_work_qa as _sq
            _path = _flag_value("--sheet-snapshot")
            try:
                _sq.print_snapshot(_sq.take_snapshot(_path), _path)
            except _sq.SheetReadError as e:
                print(f"❌ Sheet snapshot NOT taken: {e}")
                sys.exit(2)
            sys.exit(0)
        if "--must-cover" in flags:
            try:
                must_cover = {int(x) for x in flags[flags.index("--must-cover") + 1].split(",") if x.strip()}
            except (ValueError, IndexError):
                print("--must-cover needs a comma list of element ids, e.g. --must-cover 1235377,1235380")
                sys.exit(2)
        if "--since-mins" in flags:
            try:
                mins = int(flags[flags.index("--since-mins") + 1])
            except (ValueError, IndexError):
                mins = 60
            from core.revit_client import call as _call
            try:
                resp = _call("revit.get_recent_changes", {"last_n": 200})
                if resp.get("success"):
                    import time as _time, calendar as _calendar
                    cutoff = _time.time() - mins * 60
                    only_ids = set()
                    # The client wraps the bridge answer: the feed is under result.changes.
                    # (It was read from the top level, which is always empty: every scoped
                    # run said "0 changed elements" and passed without looking at anything.)
                    _res = resp.get("result") if isinstance(resp.get("result"), dict) else {}
                    changes = _res.get("changes") or resp.get("changes") or []
                    in_window = 0
                    for ch in changes:
                        ts = ch.get("timestamp", "")
                        try:
                            # feed timestamps are UTC ("...Z"): timegm, not mktime (local time)
                            if ts and _calendar.timegm(_time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) < cutoff:
                                continue
                        except ValueError:
                            pass
                        in_window += 1
                        only_ids.update(ch.get("added", []))
                        only_ids.update(ch.get("modified", []))
                    print(f"Change feed: {len(changes)} entries read, {in_window} in the last {mins} min")
                    if must_cover:
                        only_ids |= must_cover
                    print(f"Scoped to {len(only_ids)} changed elements (last {mins} min)")
                    if not only_ids and "--sheets-since" not in flags:
                        print("No recent changes in window — nothing to gate. ✅")
                        sys.exit(0)
            except Exception as e:
                print(f"(change feed unavailable: {e} — running full placement scan)")
        sheet_report = None
        if "--sheets-since" in flags:
            from qa import sheet_work_qa as _sq
            _expect = {}
            for _name in ("--expect-sheets", "--expect-viewports"):
                if _name in flags:
                    try:
                        _expect[_name] = int(_flag_value(_name))
                    except ValueError:
                        print(f"{_name} needs a whole number")
                        sys.exit(2)
            try:
                sheet_report = _sq.compare(_sq.load_snapshot(_flag_value("--sheets-since")), must_cover=must_cover,
                                           expect_sheets=_expect.get("--expect-sheets"),
                                           expect_viewports=_expect.get("--expect-viewports"))
            except _sq.SheetReadError as e:
                print(f"❌ Sheet QA could NOT look: {e}")
                sys.exit(2)
            _sq.print_report(sheet_report)
            if must_cover:
                # the ids that are sheets or viewports are covered here; the rest go to the element gate
                must_cover = (must_cover - set(sheet_report["covered_ids"])) or None
                if only_ids is not None:
                    only_ids -= set(sheet_report["covered_ids"])
        if sheet_report is not None and not must_cover and "--since-mins" not in flags:
            print("Element gate not run: this call names sheets and viewports only.")
            report = {"scanned": 0, "total": 0, "fix": [], "consider": [], "fyi": [], "not_run": True}
        else:
            report = run_model_work_qa(element_ids=only_ids, must_cover=must_cover)
        if sheet_report is not None:
            report["sheets"] = sheet_report
        # which document, when, and whether the whole model was looked at (read by automation/checks_final.py);
        # a stamp that cannot be written never changes the gate
        try:
            from qa.report_stamp import stamp_model_report
            stamp_model_report(report, full=(only_ids is None and must_cover is None and sheet_report is None
                                             and "--must-cover" not in flags and "--since-mins" not in flags), flags=flags)
        except Exception as _e:
            print(f"(report not stamped: {_e})")
        with open("model_qa_report.json", "w") as f:
            _json.dump(report, f, indent=2)
        print("💾 Report saved to model_qa_report.json")
        if report["fix"] or (sheet_report is not None and sheet_report["fix"]):
            sys.exit(1)



    elif cmd == "look":
        from core.revit_client import call
        import base64
        import time
        import os
        scope = "window"
        if "--full" in flags: scope = "full"
        resp = call("revit.capture_screen", {"scope": scope})
        if resp.get("success"):
            ts = int(time.time())
            os.makedirs("exports", exist_ok=True)
            path = f"exports/screen_{ts}.jpg"
            img_data = base64.b64decode(resp["result"]["image_base64"])
            with open(path, "wb") as f:
                f.write(img_data)
            try:
                from core.fit_image import fit
                fit(path)   # multi-monitor captures can exceed vision limits
            except Exception as e:
                print(f"⚠️ fit_image skipped: {e}")
            print(f"✅ Screen captured ({resp.get('width')}x{resp.get('height')} {resp.get('scope')}) -> {path}")
        else:
            print(f"Error capturing screen: {resp.get('error', resp)}")

    elif cmd == "changes":
        from core.revit_client import call
        last_n = 50
        if "--n" in flags:
            try: last_n = int(flags[flags.index("--n") + 1])
            except: pass
        resp = call("revit.get_recent_changes", {"last_n": last_n})
        if resp.get("success"):
            changes = resp.get("changes", [])
            print(f"--- Recent Model Changes ({len(changes)} recorded) ---")
            for c in changes:
                ts = c.get("timestamp", "")
                tx = c.get("transaction", "")
                added = len(c.get("added", []))
                modified = len(c.get("modified", []))
                deleted = len(c.get("deleted", []))
                print(f"[{ts}] Tx: {tx} | Added: {added} | Modified: {modified} | Deleted: {deleted}")
        else:
            print(f"Error fetching changes: {resp.get('error', resp)}")

    elif cmd == "tag-elevations":
        from tasks.sheets.tag_elevations import run
        run()
    elif cmd == "auto-tidy":
        from tasks.sheets.auto_tidy_tags import run
        run()
    elif cmd == "auto-fit":
        from tasks.sheets.auto_fit import run
        run(flags[0] if flags else None)
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
        # Reports on the OPEN document only (flag 54, 2026-11-11). It used to load
        # project_state.json from the current folder, whatever document that scan
        # was of, and so reported on another project's openings.
        #   default            read the doors and windows of the open model live
        #                      (no project scan, no write)
        #   --cached           use project_state.json, but only when it is a scan of
        #                      the document that is open AND was taken in the last
        #                      10 minutes; otherwise it is refused and the open
        #                      model is read live
        #   --max-age-mins N   the age limit for --cached
        # Exit 2 when the open model cannot be read (never a clean result).
        from qa.opening_marks_qa import (run_opening_marks_qa, state_for_open_document,
                                         OpenModelReadError, CACHE_MAX_AGE_MIN)
        max_age = CACHE_MAX_AGE_MIN
        if "--max-age-mins" in flags:
            try:
                max_age = float(flags[flags.index("--max-age-mins") + 1])
            except (ValueError, IndexError):
                print("--max-age-mins needs a number of minutes, e.g. --max-age-mins 5")
                sys.exit(2)
        try:
            state = state_for_open_document(use_cache="--cached" in flags, max_age_min=max_age)
        except OpenModelReadError as e:
            print(f"❌ qa-marks could not read the open model: {e}")
            print("   NOTHING CHECKED. This is not a result on any document.")
            sys.exit(2)
        _issues = run_opening_marks_qa(state)
        # the same result as a file, with the document and the time (read by automation/checks_final.py);
        # a file that cannot be written never changes what was printed
        try:
            import json as _json
            from qa.report_stamp import marks_report, MARKS_REPORT_FILE
            with open(MARKS_REPORT_FILE, "w") as f:
                _json.dump(marks_report(state, _issues), f, indent=2)
            print(f"💾 Report saved to {MARKS_REPORT_FILE}")
        except Exception as _e:
            print(f"(marks report not saved: {_e})")

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

    elif cmd == "roof":
        from tasks.roof_builder import run_roof
        run_roof(flags)

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

    elif cmd == "kit":
        from tasks.kit_package.kit import run_live
        name = flags[0] if flags else ""
        run_live(name)

    elif cmd == "kit-geometry":
        from tasks.kit_package.extract import extract_to_file
        name = flags[0] if flags else "project"
        import os
        os.makedirs("kit_output", exist_ok=True)
        extract_to_file(f"kit_output/{name.replace(' ', '_').lower()}_geometry.json", name)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
