"""
bom.py — Aggregate framing + truss output into a fabricator-style
Manufacturing Summary (format-matched to ASF/FRAMECAD Structure output)
plus CSV/JSON and a $/lb ballpark.

Fastener ratios calibrated from Allen BOM (35,510 lbs total steel):
    10g-16mm Flathead: 3,128  -> 0.0881 per lb
    10g-19mm XDrive:  21,806  -> 0.6141 per lb

Pricing benchmark (ASF Allen quote, Nov 2025):
    frame + trusses retail = $74,215.50 / 35,510 lbs = $2.09/lb
"""

import csv
import io
import json
from . import profiles as P

FLATHEAD_PER_LB = 0.0881
XDRIVE_PER_LB = 0.6141
RETAIL_RATE_PER_LB = 2.09   # ASF Allen benchmark — update as quotes come in


def _fmt_ft(v: float) -> str:
    whole = int(v)
    inches = round((v - whole) * 12)
    if inches == 12:          # carry: 5.999 ft -> 6'-0", not 5'-12"
        whole, inches = whole + 1, 0
    return f"{whole}'-{inches}\""


# Hot-rolled allowance: ASF added 121.7 LF of S7x15.3 (1,862 lbs) on Allen
# for the >40 ft span condition. When the span flag trips, add an allowance
# line ≈ ridge length x S7 plf so the ballpark isn't structurally light.
HOT_ROLLED_PROFILE = "S7x15.3"


def build_bom(wall_lf: dict, truss_lf: dict, plates: dict,
              flags: list, meta: dict | None = None,
              hot_rolled_lf: float = 0.0) -> dict:
    meta = meta or {}
    tabs = {}

    if hot_rolled_lf > 0:
        wall_lf = dict(wall_lf)
        wall_lf[HOT_ROLLED_PROFILE] = wall_lf.get(HOT_ROLLED_PROFILE, 0.0) + hot_rolled_lf

    def tab_from_lf(lf_map):
        rows = []
        for prof in sorted(lf_map):
            lf = lf_map[prof]
            weight = lf * P.plf(prof)
            rows.append({"material": prof, "qty_lf": round(lf, 1),
                         "weight_lbs": round(weight, 1)})
        return rows

    tabs["Panel.1"] = tab_from_lf(wall_lf)
    tabs["Truss.1"] = tab_from_lf(truss_lf)

    panel_lbs = sum(r["weight_lbs"] for r in tabs["Panel.1"])
    truss_lbs = sum(r["weight_lbs"] for r in tabs["Truss.1"])
    total_lbs = panel_lbs + truss_lbs

    fasteners = {
        "FRAMECAD 10g-16mm Flathead (001539)": int(total_lbs * FLATHEAD_PER_LB),
        "FRAMECAD 10g-19mm XDrive (001236)": int(total_lbs * XDRIVE_PER_LB),
    }

    return {
        "meta": meta,
        "tabs": tabs,
        "plates": plates,
        "fasteners": fasteners,
        "totals": {
            "panel_lbs": round(panel_lbs, 1),
            "truss_lbs": round(truss_lbs, 1),
            "total_lbs": round(total_lbs, 1),
            "ballpark_frame_price_retail": round(total_lbs * RETAIL_RATE_PER_LB, 2),
            "rate_per_lb_used": RETAIL_RATE_PER_LB,
        },
        "flags": flags,
    }


def render_text(bom: dict) -> str:
    m = bom["meta"]
    out = io.StringIO()
    w = out.write
    w("BARNHAUS STEEL BUILDERS — Manufacturing Summary (kit_package v1)\n")
    w(f"Project: {m.get('project','')}    Model: {m.get('model','')}\n")
    w(f"Generated: {m.get('date','')}    Detailer: Blueprint (automated)\n")
    w("=" * 72 + "\n\n")
    for tab, rows in bom["tabs"].items():
        w(f"Summary for Tab {tab}:\n")
        for r in rows:
            w(f"  {r['material']:<28} {_fmt_ft(r['qty_lf']):>14} {r['weight_lbs']:>12.1f} lbs\n")
        w("\n")
    w("Connections:\n")
    for name, qty in {**bom["plates"], **bom["fasteners"]}.items():
        w(f"  {name:<48} {qty:>8}\n")
    t = bom["totals"]
    w("\nJob Summary:\n")
    w(f"  Wall panels: {t['panel_lbs']:>10.1f} lbs\n")
    w(f"  Trusses:     {t['truss_lbs']:>10.1f} lbs\n")
    w(f"  TOTAL STEEL: {t['total_lbs']:>10.1f} lbs\n")
    w(f"  Ballpark frame+truss price @ ${t['rate_per_lb_used']}/lb (retail benchmark): "
      f"${t['ballpark_frame_price_retail']:,.2f}\n")
    if bom["flags"]:
        w("\nENGINEERING FLAGS (verify with PE):\n")
        for f in bom["flags"]:
            w(f"  ⚠ {f}\n")
    return out.getvalue()


def render_csv(bom: dict) -> str:
    out = io.StringIO()
    cw = csv.writer(out)
    cw.writerow(["tab", "material", "qty_lf", "weight_lbs"])
    for tab, rows in bom["tabs"].items():
        for r in rows:
            cw.writerow([tab, r["material"], r["qty_lf"], r["weight_lbs"]])
    for name, qty in {**bom["plates"], **bom["fasteners"]}.items():
        cw.writerow(["Connections", name, qty, ""])
    cw.writerow(["Totals", "TOTAL_STEEL_LBS", "", bom["totals"]["total_lbs"]])
    return out.getvalue()


def save_all(bom: dict, out_dir: str, stem: str = "kit_bom") -> list[str]:
    import os
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for ext, content in [
        (".txt", render_text(bom)),
        (".csv", render_csv(bom)),
        (".json", json.dumps(bom, indent=2)),
    ]:
        p = os.path.join(out_dir, stem + ext)
        with open(p, "w") as f:
            f.write(content)
        paths.append(p)
    return paths
