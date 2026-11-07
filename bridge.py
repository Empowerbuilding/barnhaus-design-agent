#!/usr/bin/env python3
"""
bridge.py — one-line Revit bridge CLI (thin wrapper over core/revit_client.py).

Kills the per-call heredoc: no more `os.environ[...] / sys.path.insert / import`
boilerplate for every single bridge poke. One exec = one call.

URL resolution (first hit wins):
  1. --url <url>
  2. $REVIT_BRIDGE_URL
  3. bridge_sessions.json  (looks in this repo, its parent, and cwd;
       key = --channel, default blueprint-mitch)
  4. http://localhost:3000  (bridge host itself / WSL with mirrored networking)

Usage:
  bridge.py health                                  # bridge + doc + build info
  bridge.py tools                                   # live command catalog (GET /tools)
  bridge.py find <regex>                            # search command names (local)
  bridge.py doc <command>                           # payload schema (local JSON)
  bridge.py call <tool> ['{"json":"payload"}']      # one bridge call
  bridge.py call <tool> --arg k=v --arg k2='["a"]'  # scalar sugar (v = JSON or string)
  bridge.py script <file.py> [--dry-run]            # batch: file runs with rc, call, batch, bboxes, info in scope
  bridge.py batch <cmds.json> [--group] [--stop]    # N sub-commands in ONE round trip (revit.batch_execute)
  (call/batch: stdout capped at --max-chars 4000; --out <file> keeps the full JSON out of context)

Examples:
  bridge.py health
  bridge.py call revit.get_document_info
  bridge.py call revit.list_elements_by_category '{"category":"Casework"}'
  bridge.py call revit.place_family_instance \\
      '{"family_name":"Counter Top","type_name":"24\\" Depth","location":{"x":10,"y":5,"z":0},"level":"Level 1"}'
  bridge.py doc place_family_instance
  bridge.py find 'family|material'

Notes:
  - tool names auto-prefix revit. (bare `place_family_instance` works)
  - exit codes: 0 ok, 1 bridge-reported failure, 2 local usage/schema error
  - schemas come from docs/bridge_schemas.json — regenerate with
    scripts/gen_bridge_schemas.py when revit-bridge changes. `doc` answers
    from that file; VERIFY EXISTENCE against live `tools` before first use
    of anything unfamiliar (installed DLL may be older than the repo).
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = os.path.join(HERE, "docs", "bridge_schemas.json")


def resolve_url(flag_url, channel):
    if flag_url:
        return flag_url, "flag"
    if os.environ.get("REVIT_BRIDGE_URL"):
        return os.environ["REVIT_BRIDGE_URL"], "env"
    for base in (HERE, os.path.dirname(HERE), os.getcwd()):
        p = os.path.join(base, "bridge_sessions.json")
        try:
            with open(p) as fh:
                chans = json.load(fh).get("channels", {})
            if channel in chans:
                return chans[channel], f"bridge_sessions.json[{channel}]"
            if chans:
                k = next(iter(chans))
                return chans[k], f"bridge_sessions.json[{k}] (channel '{channel}' not found)"
        except (OSError, ValueError):
            pass
    return "http://localhost:3000", "default localhost"


def import_client(url):
    os.environ["REVIT_BRIDGE_URL"] = url.rstrip("/")
    sys.path.insert(0, HERE)
    from core import revit_client as rc  # noqa: E402
    return rc


def load_schemas():
    try:
        with open(SCHEMAS) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def norm_tool(name):
    return name if name.startswith("revit.") else "revit." + name


def cmd_health(a):
    import requests
    r = requests.get(a["rc"].HEALTH_URL, timeout=10)
    print(json.dumps(r.json(), indent=1))
    return 0


def cmd_tools(a):
    out = a["rc"].list_tools()
    tools = out.get("tools", [])
    print(f"build={out.get('build')} count={out.get('count')}")
    for t in tools:
        print(" ", t)
    return 0 if out.get("success") else 1


def cmd_find(a):
    pat = re.compile(a["pattern"], re.I)
    schemas = load_schemas()
    if not schemas:
        print("docs/bridge_schemas.json missing — run scripts/gen_bridge_schemas.py",
              file=sys.stderr)
        return 2
    hits = [(c, e["status"]) for c, e in schemas["commands"].items()
            if pat.search(c)]
    for c, status in sorted(hits):
        print(f"  {c}  [{status}]")
    print(f"{len(hits)} match(es)")
    return 0


def cmd_doc(a):
    schemas = load_schemas()
    if not schemas:
        print("docs/bridge_schemas.json missing — run scripts/gen_bridge_schemas.py",
              file=sys.stderr)
        return 2
    want = norm_tool(a["command"])
    entry = schemas["commands"].get(want)
    if entry is None:  # substring fallback
        cands = [c for c in schemas["commands"] if a["command"] in c]
        if len(cands) == 1:
            want, entry = cands[0], schemas["commands"][cands[0]]
        elif cands:
            print(f"ambiguous — matches: {', '.join(sorted(cands))}", file=sys.stderr)
            return 2
    if entry is None:
        print(f"unknown command '{want}' — try `bridge.py find <regex>` "
              f"or live `bridge.py tools`", file=sys.stderr)
        return 2
    print(f"{want}  [{entry['status']}]")
    if entry.get("handler"):
        print(f"  handler: {entry['handler']}"
              + (f"  ({entry['file']})" if entry.get("file") else ""))
    if entry.get("note"):
        print(f"  NOTE: {entry['note']}")
    args = entry.get("args", [])
    if not args:
        print("  args: (none extracted — no payload keys, or scan missed them)")
    else:
        print("  args (* = required):")
        for arg in args:
            line = f"    {'*' if arg['required'] else ' '} {arg['name']}"
            if arg.get("shape"):
                line += f"  — {arg['shape']}"
            print(line)
    if entry["status"] == "parked":
        print("  Do NOT call live — parked commands are not in any DLL.")
    return 0


def build_payload(positional, kv_pairs):
    payload = {}
    if positional:
        try:
            payload = json.loads(positional)
            if not isinstance(payload, dict):
                print("payload JSON must be an object", file=sys.stderr)
                sys.exit(2)
        except ValueError as e:
            print(f"bad payload JSON: {e}", file=sys.stderr)
            sys.exit(2)
    for kv in kv_pairs or []:
        if "=" not in kv:
            print(f"--arg expects k=v, got: {kv}", file=sys.stderr)
            sys.exit(2)
        k, v = kv.split("=", 1)
        try:
            payload[k] = json.loads(v)
        except ValueError:
            payload[k] = v
    return payload


def emit(obj, max_chars, out_file=None):
    """Context hygiene: big results go to a file, stdout gets a capped view."""
    text = json.dumps(obj, default=str)
    if out_file:
        with open(out_file, "w") as fh:
            fh.write(text)
        print(f"[wrote {len(text)} chars -> {out_file}]", file=sys.stderr)
    if max_chars and len(text) > max_chars:
        print(text[:max_chars] + f" ...[truncated {len(text) - max_chars} chars; "
              f"use --full or --out <file>]")
    else:
        print(text)


def cmd_call(a):
    tool = norm_tool(a["tool"])
    payload = build_payload(a.get("payload"), a.get("arg"))
    res = a["rc"].call(tool, payload)
    shown = res if a["full"] else {k: res.get(k) for k in
                                   ("success", "result", "error")}
    emit(shown, 0 if a["full"] else a["max_chars"], a.get("out"))
    return 0 if res.get("success") else 1


def cmd_batch(a):
    """bridge.py batch <commands.json> [--group] [--stop]  — one round trip."""
    with open(a["file"]) as fh:
        cmds = json.load(fh)
    if isinstance(cmds, dict):
        cmds = cmds.get("commands", [])
    res = a["rc"].batch_execute(cmds, stop_on_error=a["stop"],
                                transaction_group=a["group"])
    summary = {k: res.get(k) for k in ("success", "ok", "failed", "error", "rolled_back")}
    summary["errors"] = [r for r in res.get("results", []) if r.get("status") != "ok"][:20]
    emit(summary, a["max_chars"], a.get("out") )
    if a.get("out"):
        emit(res, 0, a["out"])
    return 0 if res.get("success") else 1


def cmd_script(a):
    with open(a["file"]) as fh:
        code = fh.read()
    if a.get("dry_run"):
        a["rc"].DRY_RUN = True
        print("[DRY RUN — no bridge writes]", file=sys.stderr)
    scope = {"rc": a["rc"], "call": a["rc"].call, "batch": a["rc"].batch_execute,
             "bboxes": a["rc"].get_bboxes, "info": a["rc"].get_elements_info,
             "health": a["rc"].health_check, "json": json, "os": os}
    exec(compile(code, a["file"], "exec"), scope)  # noqa: S102
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="bridge base URL (overrides everything)")
    ap.add_argument("--channel", default="blueprint-mitch",
                    help="bridge_sessions.json key (default blueprint-mitch)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")
    sub.add_parser("tools")
    p = sub.add_parser("find"); p.add_argument("pattern")
    p = sub.add_parser("doc"); p.add_argument("command")
    p = sub.add_parser("call")
    p.add_argument("tool")
    p.add_argument("payload", nargs="?", default=None,
                   help="JSON object string")
    p.add_argument("--arg", action="append", metavar="k=v")
    p.add_argument("--full", action="store_true", help="print raw response, uncapped")
    p.add_argument("--max-chars", type=int, default=4000,
                   help="cap stdout (default 4000); full result via --out")
    p.add_argument("--out", help="write full JSON result to this file")
    p = sub.add_parser("batch"); p.add_argument("file", help="JSON list of {tool,payload}")
    p.add_argument("--group", action="store_true", help="one TransactionGroup (no save inside)")
    p.add_argument("--stop", action="store_true", help="stop on first error")
    p.add_argument("--max-chars", type=int, default=4000)
    p.add_argument("--out", help="write full results JSON here")
    p = sub.add_parser("script"); p.add_argument("file")
    p.add_argument("--dry-run", action="store_true", help="rc.DRY_RUN=True: print calls, touch nothing")

    a = vars(ap.parse_args())
    if a["cmd"] in ("find", "doc"):
        a["rc"] = None
    else:
        url, src = resolve_url(a.get("url"), a["channel"])
        a["rc"] = import_client(url)
        print(f"[bridge: {src} {url}]", file=sys.stderr)

    fn = {"health": cmd_health, "tools": cmd_tools, "find": cmd_find,
          "doc": cmd_doc, "call": cmd_call, "batch": cmd_batch,
          "script": cmd_script}[a["cmd"]]
    sys.exit(fn(a))


if __name__ == "__main__":
    main()
