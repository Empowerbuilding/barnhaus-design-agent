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
  bridge.py script <file.py>                        # batch: file runs with rc + call in scope

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


def cmd_call(a):
    tool = norm_tool(a["tool"])
    payload = build_payload(a.get("payload"), a.get("arg"))
    res = a["rc"].call(tool, payload)
    shown = res if a["full"] else {k: res.get(k) for k in
                                   ("success", "result", "error")}
    print(json.dumps(shown, default=str))
    return 0 if res.get("success") else 1


def cmd_script(a):
    with open(a["file"]) as fh:
        code = fh.read()
    scope = {"rc": a["rc"], "call": a["rc"].call,
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
    p.add_argument("--full", action="store_true", help="print raw response")
    p = sub.add_parser("script"); p.add_argument("file")

    a = vars(ap.parse_args())
    if a["cmd"] in ("find", "doc"):
        a["rc"] = None
    else:
        url, src = resolve_url(a.get("url"), a["channel"])
        a["rc"] = import_client(url)
        print(f"[bridge: {src} {url}]", file=sys.stderr)

    fn = {"health": cmd_health, "tools": cmd_tools, "find": cmd_find,
          "doc": cmd_doc, "call": cmd_call, "script": cmd_script}[a["cmd"]]
    sys.exit(fn(a))


if __name__ == "__main__":
    main()
