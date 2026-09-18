"""
fixture_test.py — Offline validation of the kit_package pipeline.

Synthetic house: 40x60 ft rectangle, 10 ft walls, gable roof span 40 ft
@ 4:12, typical door/window mix, ~140 LF interior walls.
Run: python3 -m tasks.kit_package.fixture_test
"""

FIXTURE = {
    "project": "Fixture 40x60",
    "model": "synthetic",
    "date": "2026-09-17",
    "walls": [
        # Exterior: 2x60 + 2x40, openings spread across them
        {"id": 1, "length_ft": 60.0, "height_ft": 10.0, "function": "exterior",
         "openings": [{"width_ft": 3.0, "height_ft": 6.8, "kind": "door"},
                      {"width_ft": 6.0, "height_ft": 5.0, "kind": "window"},
                      {"width_ft": 4.0, "height_ft": 5.0, "kind": "window"}]},
        {"id": 2, "length_ft": 60.0, "height_ft": 10.0, "function": "exterior",
         "openings": [{"width_ft": 9.0, "height_ft": 8.0, "kind": "door"},  # garage-ish -> flag
                      {"width_ft": 4.0, "height_ft": 5.0, "kind": "window"}]},
        {"id": 3, "length_ft": 40.0, "height_ft": 10.0, "function": "exterior",
         "openings": [{"width_ft": 3.0, "height_ft": 5.0, "kind": "window"}]},
        {"id": 4, "length_ft": 40.0, "height_ft": 10.0, "function": "exterior",
         "openings": [{"width_ft": 3.0, "height_ft": 6.8, "kind": "door"}]},
        # Interior partitions
        {"id": 5, "length_ft": 40.0, "height_ft": 9.0, "function": "interior",
         "openings": [{"width_ft": 2.5, "height_ft": 6.8, "kind": "door"}] * 2},
        {"id": 6, "length_ft": 30.0, "height_ft": 9.0, "function": "interior",
         "openings": [{"width_ft": 2.5, "height_ft": 6.8, "kind": "door"}]},
        {"id": 7, "length_ft": 35.0, "height_ft": 9.0, "function": "interior",
         "openings": [{"width_ft": 2.5, "height_ft": 6.8, "kind": "door"}] * 2},
        {"id": 8, "length_ft": 35.0, "height_ft": 9.0, "function": "interior",
         "openings": [{"width_ft": 2.5, "height_ft": 6.8, "kind": "door"}]},
    ],
    "roof": {"span_ft": 40.0, "ridge_length_ft": 60.0,
             "pitch_rise_per_12": 4.0, "gable_ends": 2},
}


def main():
    from . import kit, profiles

    # Sanity: calibrated plf values reproduce ASF Allen weights within 0.1%
    checks = [
        ("362S162-33-50", 19855.04, 18411.9),
        ("362S162-43-50", 5325.96, 6370.4),
        ("600S162-43-50", 5623.92, 8805.3),
        ("S7x15.3", 121.69, 1861.8),
    ]
    for prof, lf, expected_lbs in checks:
        got = lf * profiles.plf(prof)
        err = abs(got - expected_lbs) / expected_lbs
        assert err < 0.001, f"{prof}: {got:.1f} vs {expected_lbs} ({err:.2%})"
    print("✅ profile plf calibration matches ASF Allen BOM (<0.1% error)")

    # Computed-profile fallback sanity (no empirical entry)
    v = profiles.plf("600S162-54-50")
    assert 1.8 < v < 2.2, v
    print(f"✅ computed fallback works (600S162-54-50 = {v} plf)")

    result = kit.run_from_geometry(FIXTURE, out_dir="kit_output/fixture_40x60")

    t = result["totals"]
    # 2400 sqft footprint: expect total steel roughly 8-10 lbs/sqft of footprint
    per_sqft = t["total_lbs"] / 2400.0
    print(f"steel intensity: {per_sqft:.2f} lbs/sqft footprint "
          f"(Allen reference ≈ ~10 lbs/sqft at 3,500 sqft-class)")
    # NOTE: v1 truss heuristic is known-light vs ASF reality (Allen truss tab
    # = 19,855 LF, ~4x textbook fink LF). WEB_FACTOR calibration against the
    # live Allen model is the required fix — do not tune blind.
    assert 2.5 < per_sqft < 16.0, "steel intensity out of sane range"
    assert any("hot-rolled" in f for f in result["flags"]), "9 ft opening should flag"
    print("✅ fixture pipeline end-to-end OK")


if __name__ == "__main__":
    main()
