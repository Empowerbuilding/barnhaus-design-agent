#!/usr/bin/env python3
"""
gen_bridge_schemas.py — extract per-command payload schemas from the revit-bridge C# source.

Why: GET /tools and BRIDGE_COMMANDS.md list command NAMES only. Payload arg names
have to be re-derived from the DLL source by hand (Blueprint grepped
BridgeCommandFactory.cs ~15x during one 2026-11-04 countertop task). This script
closes that gap: every command's arg names + required/optional, as JSON.

Reads:  sibling revit-bridge checkout (default ../../revit-bridge, override --src)
Writes: docs/bridge_schemas.json

Method:
  1. command -> handler map from switch expressions ('"revit.x" => ExecuteY(')
     and switch statements ('case "revit.x": ... return ExecuteY(')
  2. handler bodies sliced from method-declaration to next method-declaration
  3. args = payload.GetProperty("k") (required) / TryGetProperty("k" (optional)
  4. status from tools.json compiled/parked lists (source greps see parked code
     that never ships in a DLL — trying it live returns "Unknown tool")

Regenerate whenever revit-bridge changes:
  python3 scripts/gen_bridge_schemas.py [--src /path/to/revit-bridge]
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(os.path.dirname(REPO), "revit-bridge")

SWITCH_EXPR = re.compile(r'"(revit\.[a-z_0-9]+)"\s*=>\s*([\w.]+)\(')
SWITCH_CASE = re.compile(
    r'case\s+"(revit\.[a-z_0-9]+)":(?:[^;]{0,200}?)return\s+(\w+)\(', re.S)
METHOD_DECL = re.compile(
    r'^\s*(?:\[[^\]]*\]\s*)*(?:public|private|internal|protected)'
    r'[\w\s<>,\[\]?]*?\s(\w+)\s*\([^)]*\)\s*\{', re.M)
REQ_ARG = re.compile(r'payload\.GetProperty\("([\w.]+)"\)')
OPT_ARG = re.compile(r'payload\.TryGetProperty\("([\w.]+)"')
XYZ_ARG = re.compile(r'ParseXYZ\w*\(\s*payload\.GetProperty\("([\w.]+)"\)')


def git_sha(src):
    try:
        return subprocess.check_output(
            ["git", "-C", src, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None


def collect_cs_files(src):
    root = os.path.join(src, "packages", "revit-bridge-addin", "src")
    if not os.path.isdir(root):
        root = src
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".cs"):
                yield os.path.join(dirpath, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC, help="revit-bridge checkout")
    args = ap.parse_args()
    src = os.path.abspath(args.src)

    tools_json = os.path.join(src, "tools.json")
    compiled, parked = [], []
    if os.path.isfile(tools_json):
        tj = json.load(open(tools_json))
        compiled = tj.get("compiled", [])
        parked = tj.get("parked", [])
    else:
        print(f"WARNING: {tools_json} missing — statuses will be 'unknown'",
              file=sys.stderr)

    cmd_to_method = {}   # "revit.x" -> handler name
    method_bodies = {}   # method name -> (file, body text)

    for path in collect_cs_files(src):
        rel = os.path.relpath(path, src)
        with open(path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()

        for m in SWITCH_EXPR.finditer(content):
            cmd_to_method[m.group(1)] = m.group(2)
        for m in SWITCH_CASE.finditer(content):
            cmd_to_method.setdefault(m.group(1), m.group(2))

        decls = list(METHOD_DECL.finditer(content))
        for i, decl in enumerate(decls):
            name = decl.group(1)
            end = decls[i + 1].start() if i + 1 < len(decls) else len(content)
            method_bodies.setdefault(name, (rel, content[decl.start():end]))

    out = {}
    for cmd in sorted(cmd_to_method):
        method = cmd_to_method[cmd]
        entry = {"handler": method, "status": "unknown", "args": []}
        if cmd in compiled:
            entry["status"] = "compiled"
        elif cmd in parked:
            entry["status"] = "parked"
        # dotted dispatch (Class.Method) — body lookup uses the method segment
        body = method_bodies.get(method.split(".")[-1])
        if body:
            entry["file"], text = body
            xyz = {m.group(1) for m in XYZ_ARG.finditer(text)}
            seen = {}
            for m in REQ_ARG.finditer(text):
                seen.setdefault(m.group(1), {"name": m.group(1),
                                             "required": True})
            for m in OPT_ARG.finditer(text):
                seen.setdefault(m.group(1), {"name": m.group(1),
                                             "required": False})
            for arg in seen.values():
                if arg["name"] in xyz:
                    arg["shape"] = "xyz {x,y,z}"
            entry["args"] = list(seen.values())
        else:
            entry["note"] = "handler body not found — args unknown"
        out[cmd] = entry

    # commands the catalog says compile but dispatch wasn't found for
    for cmd in compiled:
        if cmd not in out:
            out[cmd] = {"status": "compiled",
                        "note": "dispatch not found in source scan — args unknown",
                        "args": []}

    # parked commands: in source, excluded from every DLL (csproj Compile Remove).
    # Listed so `bridge.py doc <name>` can say WHY a live call 404s.
    for cmd in parked:
        if cmd not in out:
            out[cmd] = {"status": "parked",
                        "note": "parked — not compiled into any DLL; live call "
                                "returns Unknown tool. Do not use.",
                        "args": []}

    result = {
        "generated": datetime.datetime.now(datetime.timezone.utc)
                       .strftime("%Y-%m-%d %H:%M UTC"),
        "revit_bridge_commit": git_sha(src),
        "counts": {
            "total": len(out),
            "compiled": sum(1 for e in out.values()
                            if e["status"] == "compiled"),
            "parked": sum(1 for e in out.values()
                          if e["status"] == "parked"),
            "with_args": sum(1 for e in out.values() if e.get("args")),
        },
        "commands": out,
    }

    dest = os.path.join(REPO, "docs", "bridge_schemas.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print(f"OK  {len(out)} commands "
          f"({result['counts']['compiled']} compiled, "
          f"{result['counts']['parked']} parked, "
          f"{result['counts']['with_args']} with extracted args) "
          f"-> {os.path.relpath(dest, REPO)}")


if __name__ == "__main__":
    main()
