#!/usr/bin/env python3
"""
blueprint_runner.py — "Press play" dispatcher for Blueprint work orders.

Runs on the DO host (cron */2, flock'd). Orchestrates approved work orders:
  - Finds projects/<name>/work_order.json in the blueprint-openclaw container
  - Dispatches phase briefs to blueprint-mitch (user-sender, wakes Blueprint)
  - Advances on phase signals (projects/<name>/phase_signals.jsonl, written by
    Blueprint per the Phase Execution Contract in AGENTS.md)
  - Stop conditions: blocked / decision signals, stalls (alert + one re-brief),
    save failures (hard stop)
  - Re-brief guard (2026-11-15): a phase that looks stalled is NOT re-briefed while
    projects/<name>/phase_heartbeat.json shows it alive, and the signal file is read
    again right before any re-brief or stall-block is posted (see rebrief_decision)
  - Phase pack (2026-11-15): right before every dispatch (first brief and re-brief) the
    phase pack is built in the container (automation/phase_pack.py); with a pack the
    dispatch message names the pack as the phase's input, without one it is the brief
    text as before (see build_pack, dispatch_text). The phase class of the work order
    goes into the state, the log and the message (see model_class_for)
  - Posts the summary card when all phases reach a terminal state

NEVER talks to Revit or the bridge. Only portal messages + container files.
Does nothing until a work_order.json exists with approved: true.

State: /root/blueprint_runner_state.json (offsets + phase statuses)
Log:   /root/blueprint_runner.log
"""

import json
import os
import subprocess
import sys
import time
import datetime

STATE_PATH = "/root/blueprint_runner_state.json"
CONTAINER = "blueprint-openclaw"
CHANNEL = "blueprint-mitch"
ALERT_CHANNEL = "tony-alerts"
ORG_ID = "1c466ccb-ef35-4ba4-bf00-5fcabf20edec"
ENV_FILE = "/root/design-brain/env.sh"
PROJECTS_DIR = "/home/node/.openclaw/workspace/projects"
STALL_MIN_MINUTES = 45   # hard ceiling floor regardless of est_minutes
IDLE_MIN_MINUTES = 10    # no gateway activity at all -> re-brief after this
ORPHAN_MIN_MINUTES = 30  # gateway alive but phase unsignaled -> re-brief after this

# ---- re-brief guard (fix list item 12, 2026-11-15) ----
# Seen on 2026-11-14/15 (D0, D1, P5-105, P5-104): a phase that ran longer than the stall
# rules above was briefed a second time although it was working, and the second brief
# reached the agent right after its done line. Two guards, both decided in the pure
# function rebrief_decision():
#   1. In-flight marker. Blueprint writes projects/<name>/phase_heartbeat.json
#      {"phase", "at" (UTC ISO), "step"} at phase start and during long steps
#      (workspace tool: automation/phase_heartbeat.py). A heartbeat for the dispatched
#      phase younger than HEARTBEAT_FRESH_MINUTES = the phase is alive: no re-brief, the
#      phase is watched as "done-pending". Alive past the ceiling below: ONE alert, still
#      no re-brief. Stale / missing / unreadable / other phase: the rules above, unchanged.
#   2. Right before a re-brief (or a stall-block) is posted, the signal file is read
#      again. A signal for that phase is processed as a signal; nothing is posted.
ORDER_STOP_FILE = "ORDER_STOPPED.json"   # in the project folder: the owner stopped this order -> never dispatch it
HEARTBEAT_FILE = "phase_heartbeat.json"
HEARTBEAT_FRESH_MINUTES = 12     # heartbeat younger than this -> phase alive, no re-brief
HEARTBEAT_BEAT_EVERY_MINUTES = 8  # what the brief asks of the agent (must stay below the line above)
HEARTBEAT_SKEW_SECONDS = 120     # tolerated: heartbeat stamped this much ahead of the runner clock,
                                 # or this much before the first brief of the phase
ALIVE_CEILING_FACTOR = 3         # alive phase: one alert once it has run longer than
ALIVE_CEILING_MIN_MINUTES = 120  #   max(ALIVE_CEILING_FACTOR x est_minutes, this many minutes)
SIGNAL_STATUSES = ("done", "blocked", "awaiting_decision", "pending")

# ---- phase pack, phase class, fresh session (second pass, 2026-11-15) ----
# Right before EVERY dispatch of a phase (first brief and re-brief) the runner builds the
# phase pack in the container:
#     python3 automation/phase_pack.py --project <folder name> --phase <id> --write
# It writes projects/<folder>/briefs/<id>.pack.md: one self-contained input for the phase
# (brief, work order slice, lessons that apply, state, open items, recipes). Its State part
# is as of the minute it is built, which is why it is built here and not at compile time.
#   - command ended with exit 0 AND the file is there afterwards: the dispatch message
#     names the pack as the input of the phase (pack_brief).
#   - command failed, did not end in time, or the file is not there: the dispatch message
#     is the brief text as before (brief) and the reason goes to the log.
# A failed pack never stops a dispatch.
WORKSPACE_DIR = PROJECTS_DIR.rsplit("/", 1)[0]
PACK_TOOL = WORKSPACE_DIR + "/automation/phase_pack.py"
PACK_TIMEOUT_SECONDS = 60        # the tool took well under a second on a 470 KB work order
# Phase class. A newly compiled work order carries on each phase "phase_class"
# ("judgment" | "mechanical") and "phase_class_reason". Missing or unknown = "judgment".
PHASE_CLASSES = ("judgment", "mechanical")
DEFAULT_PHASE_CLASS = "judgment"
PHASE_CLASS_REASON_CUT = 200     # characters of the reason kept in state, log and message
# Model per phase class. LEFT EMPTY ON PURPOSE. The person who owns the gateway fills it,
# for example {"judgment": "<model id>", "mechanical": "<model id>"}, and wires the session
# model pinning on the gateway side. The runner has NO pinning mechanism. With this map
# empty the runner behaves exactly as without it. With an entry for the class of a phase,
# the runner only writes that model id into the phase state ("model_wanted") and the log
# line; it does not change which model runs the phase.
MODEL_BY_CLASS = {}
# The sentence a dispatch message carries when a pack exists. The runner does not create
# sessions: a new session per dispatch is the gateway owner's side.
FRESH_SESSION_NOTE = "This phase is meant to start in a fresh session with only this pack."

# ---- token telemetry, filled from OUTSIDE the turn (M2 condition 3, 2026-11-11) ----
# The agent cannot read its own token use from inside a turn. The gateway writes one
# "model.completed" event per run into the trajectory store, at the END of the run,
# with data.usage {input, output, cacheRead, cacheWrite, total}. After a phase signals,
# the runner sums those events for the run(s) that STARTED between the phase's dispatch
# and its signal, and appends one line to projects/<name>/phase_usage.jsonl.
# (The signal file itself is not rewritten: the runner reads it by byte offset.)
USAGE_SESSION_KEY = "agent:main:portal:channel:blueprint-mitch"
USAGE_DB = "/home/node/.openclaw/agents/main/agent/openclaw-agent.sqlite"
USAGE_START_SLACK_S = 10      # the run may start a moment before the runner stamps dispatched_at
USAGE_GIVE_UP_MINUTES = 30    # no finished run found this long after the signal -> record that, stop trying
# Runs inside the container (python3 -, args: start_ms end_ms session_key db_path). Read-only.
USAGE_SCRIPT = r"""
import json, sqlite3, sys
start_ms, end_ms, key, db = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
out = {"ok": False, "runs": 0, "complete": False}
try:
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
    like = '%"sessionKey":"' + key + '"%'
    # runs of this session that have an event inside the window
    cand = [r[0] for r in c.execute(
        "select distinct run_id from trajectory_runtime_events where created_at between ? and ? and event_json like ?",
        (start_ms, end_ms, like))]
    runs = []
    for rid in cand:
        first = c.execute("select min(created_at) from trajectory_runtime_events where run_id = ?", (rid,)).fetchone()[0]
        if first is not None and start_ms <= first <= end_ms:      # the run STARTED in the window
            runs.append(rid)
    tot = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "total": 0}
    calls = 0; models = set(); done = 0
    for rid in runs:
        got = False
        for (ej,) in c.execute(
                "select event_json from trajectory_runtime_events where run_id = ? and event_json like ?",
                (rid, '%"type":"model.completed"%')):
            e = json.loads(ej)
            if e.get("type") != "model.completed" or e.get("sessionKey") != key:
                continue
            u = (e.get("data") or {}).get("usage") or {}
            tot["input"] += int(u.get("input") or 0); tot["output"] += int(u.get("output") or 0)
            tot["cache_read"] += int(u.get("cacheRead") or 0); tot["cache_write"] += int(u.get("cacheWrite") or 0)
            tot["total"] += int(u.get("total") or 0)
            calls += 1; got = True
            if e.get("modelId"): models.add(e["modelId"])
        done += 1 if got else 0
    out = {"ok": True, "runs": len(runs), "runs_completed": done, "complete": bool(runs) and done == len(runs),
           "model_completed_events": calls, "models": sorted(models), "usage": tot, "run_ids": runs[:8]}
except Exception as e:
    out = {"ok": False, "error": str(e)[:200], "runs": 0, "complete": False}
print(json.dumps(out))
"""


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_env():
    """Source design-brain env.sh for PORTAL_KEY (never hardcode keys)."""
    try:
        out = subprocess.run(["bash", "-c", f". {ENV_FILE} && echo $PORTAL_KEY"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception as e:
        log(f"FATAL: could not source {ENV_FILE}: {e}")
        sys.exit(1)


def portal_post(key, channel, content, wake):
    import urllib.request
    body = json.dumps({
        "channel_id": channel,
        "org_id": ORG_ID,
        "sender_type": "user",
        "sender_name": "BlueprintRunner",
        "content": content,
        "processed": not wake,
    }).encode()
    req = urllib.request.Request(
        "https://xqvnpcxyyxxxydescfzw.supabase.co/rest/v1/portal_messages",
        data=body,
        headers={"apikey": key, "Authorization": "Bearer " + key,
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status == 201


def docker_read(path):
    """Read a file from the blueprint container. None if missing."""
    try:
        out = subprocess.run(["docker", "exec", CONTAINER, "cat", path],
                             capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return None
        return out.stdout
    except Exception:
        return None


def query_usage(start_epoch, end_epoch):
    """Sum model.completed usage for the session's run(s) that started in [start, end].
    -> dict from USAGE_SCRIPT, or None when the container could not be asked."""
    try:
        out = subprocess.run(
            ["docker", "exec", "-i", CONTAINER, "python3", "-",
             str(int(start_epoch * 1000)), str(int(end_epoch * 1000)), USAGE_SESSION_KEY, USAGE_DB],
            input=USAGE_SCRIPT, capture_output=True, text=True, timeout=40)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def docker_append(path, line):
    """Append one line to a file in the blueprint container. True when it was written."""
    try:
        out = subprocess.run(
            ["docker", "exec", "-i", CONTAINER, "sh", "-c", 'cat >> "$1"', "sh", path],
            input=line.rstrip("\n") + "\n", capture_output=True, text=True, timeout=15)
        return out.returncode == 0
    except Exception:
        return False


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def fill_usage(name, proj):
    """Token telemetry for phases that have signalled (see the block at the top).
    One line per phase goes to projects/<name>/phase_usage.jsonl; the signal file is untouched.
    The gateway writes the usage when the run ENDS, which is after the signal line, so a
    phase is retried on later passes until its run is complete (or USAGE_GIVE_UP_MINUTES)."""
    now = time.time()
    for pid, st in proj.get("phases", {}).items():
        if "usage" in st or st.get("signal_epoch") is None:
            continue
        start = st.get("first_dispatched_at") or st.get("dispatched_at")
        if not start:
            continue
        sig_at = st["signal_epoch"]
        res = query_usage(start - USAGE_START_SLACK_S, sig_at)
        rec = None
        if res and res.get("ok") and res.get("complete"):
            u = res.get("usage") or {}
            rec = {"llm_tokens": u.get("total"), "llm": dict(u, runs=res.get("runs"),
                                                             model_completed_events=res.get("model_completed_events"),
                                                             models=res.get("models", [])),
                   "note": ("usage of the run(s) of this session that STARTED between dispatch and signal; "
                            "a human message handled inside that window is counted too"
                            + ("; %d runs (re-brief or an interleaved message)" % res["runs"] if (res.get("runs") or 0) > 1 else ""))}
        elif now - sig_at > USAGE_GIVE_UP_MINUTES * 60:
            why = ("the trajectory store could not be read" if not res or not res.get("ok")
                   else "no run of the session started between dispatch and signal" if not res.get("runs")
                   else "the run has no model.completed event")
            rec = {"llm_tokens": None, "llm": None,
                   "note": f"not filled: {why} ({USAGE_GIVE_UP_MINUTES} min after the signal)"
                           + (f": {res.get('error')}" if res and res.get("error") else "")}
        if rec is None:
            continue                      # run not finished yet: try again on the next pass
        rec = dict({"phase": pid, "order_key": proj.get("order_key"), "dispatched_at": _iso(start),
                    "signal_at": _iso(sig_at), "filled_at": _iso(now), "filled_by": "blueprint_runner (host)"}, **rec)
        if docker_append(f"{PROJECTS_DIR}/{name}/phase_usage.jsonl", json.dumps(rec)):
            st["usage"] = {"llm_tokens": rec["llm_tokens"], "filled_at": rec["filled_at"]}
            log(f"{name}: usage {pid} -> {rec['llm_tokens']} tokens ({rec['note'][:60]})")
        # not written: leave it for the next pass


def find_work_orders():
    """Return {project_name: work_order_dict} for every project with one."""
    try:
        out = subprocess.run(
            ["docker", "exec", CONTAINER, "sh", "-c",
             f"ls -d {PROJECTS_DIR}/*/ 2>/dev/null"],
            capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return {}
    except Exception:
        return {}
    orders = {}
    for line in out.stdout.strip().splitlines():
        name = line.rstrip("/").split("/")[-1]
        if not name or name.startswith(("_", "--")):
            continue
        raw = docker_read(f"{PROJECTS_DIR}/{name}/work_order.json")
        if not raw:
            continue
        try:
            wo = json.loads(raw)
        except json.JSONDecodeError:
            log(f"⚠️ {name}: work_order.json is invalid JSON — skipping (alerting)")
            continue
        if isinstance(wo, dict) and wo.get("phases"):
            orders[name] = wo
    return orders


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            return json.load(open(STATE_PATH))
        except Exception:
            pass
    return {"projects": {}}


def save_state(state):
    tmp = STATE_PATH + ".tmp"
    json.dump(state, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE_PATH)


def read_signals(name, offset):
    """Read new phase_signals.jsonl lines since byte offset. Returns (lines, new_offset)."""
    path = f"{PROJECTS_DIR}/{name}/phase_signals.jsonl"
    raw = docker_read(path)
    if raw is None:
        return [], offset
    data = raw.encode()
    if len(data) < offset:
        # the signals file is SHORTER than what was already read: it was replaced or
        # truncated. Its old content is gone, so read it from the start.
        log(f"{name}: phase_signals.jsonl shrank ({len(data)} < {offset}) — reading from the start")
        offset = 0
    if len(data) <= offset:
        return [], offset
    new = data[offset:].decode(errors="replace")
    lines = []
    for ln in new.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            lines.append(json.loads(ln))
        except json.JSONDecodeError:
            log(f"⚠️ {name}: unparseable signal line skipped: {ln[:80]}")
    return lines, len(data)


def recent_gateway_activity(minutes=6):
    """True if the gateway dispatched/responded anything recently (any channel).
    Proxy for 'the system is alive' — used to distinguish a dead turn from
    active work before re-briefing."""
    try:
        out = subprocess.run(
            ["docker", "logs", CONTAINER, "--since", f"{minutes}m"],
            capture_output=True, text=True, timeout=20)
        blob = (out.stdout or "") + (out.stderr or "")
        return ("Dispatching" in blob) or ("Response written" in blob)
    except Exception:
        return True  # can't tell — be conservative, assume active


def order_key(wo):
    """Identity of ONE compiled work order: when it was compiled (+ its fingerprint when
    it has one). A recompile, or a different order written to the same file, has another
    key. Hand-written orders without compiled_at fall back to their phase list."""
    ca = str(wo.get("compiled_at") or "").strip()
    if ca and not ca.startswith("..."):
        return ca + "|" + str(wo.get("fingerprint") or "")
    return "phases:" + ",".join(f"{p.get('id')}={p.get('title')}" for p in wo.get("phases", []))


def _iso_epoch(s):
    """'2026-11-11T19:57:04Z' -> epoch seconds (UTC). None when it does not parse."""
    import calendar
    try:
        return calendar.timegm(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return None


def start_new_order_if_any(name, wo, proj):
    """A project folder that FINISHED one work order becomes dispatchable again when a
    different work order appears in it (intake order, then build orders; 2D then 3D).

    Only a FINISHED folder is reset. While an order is running, a recompile keeps the
    phase statuses by id exactly as before (amendment mid-run), and a blocked phase is
    still re-queued with a 'pending' signal. Returns True when a new run was started.
    """
    key = order_key(wo)
    old = proj.get("order_key")
    if old == key:
        return False
    if not proj.get("finished"):
        proj["order_key"] = key          # first sight, or a recompile mid-run: unchanged behaviour
        return False
    if old is None:
        # state written before order keys existed: it is a new order only if it was
        # compiled AFTER everything the finished run did (else: the same order, keep it finished)
        compiled = _iso_epoch(wo.get("compiled_at"))
        last = max([s.get("dispatched_at") or 0 for s in proj["phases"].values()] + [0])
        if compiled is None or compiled <= last:
            proj["order_key"] = key
            return False
    proj.setdefault("history", []).append({
        "order_key": old, "closed_at": time.time(),
        "phases": {p: s.get("status") for p, s in proj["phases"].items()}})
    proj["history"] = proj["history"][-10:]
    proj["phases"] = {}
    proj["finished"] = False
    proj["order_key"] = key
    log(f"{name}: NEW work order in a finished folder (was {old}, now {key}) — "
        f"phase states reset, {len(wo.get('phases', []))} phase(s) pending")
    return True


def phase_states(state, name, wo):
    """Merge runner state with work order phases (runner state wins)."""
    proj = state["projects"].setdefault(name, {"offset": 0, "phases": {}})
    start_new_order_if_any(name, wo, proj)
    for ph in wo["phases"]:
        pid = ph["id"]
        proj["phases"].setdefault(pid, {"status": "pending"})
    return proj


def deps_done(wo, proj, phase):
    for dep in phase.get("depends_on", []):
        st = proj["phases"].get(dep, {}).get("status")
        if st != "done":
            return False
    return True


def brief(name, wo, phase):
    verify = phase.get("verify", {})
    v = []
    if verify.get("qa_model"):
        v.append("qa-model gate REQUIRED")
    if verify.get("vision"):
        v.append(f"vision check: {verify['vision']}")
    # Typed work orders (schema work-order/2.0, compiler v2) keep each phase's brief in a
    # file: projects/<name>/briefs/<phase_id>.md, named on the phase as brief_path
    # (workspace-relative). Additive: a phase without brief_path gets exactly the old message.
    brief_path = phase.get("brief_path")
    brief_line = ""
    if isinstance(brief_path, str) and brief_path.strip():
        brief_line = (f"\nBrief file: {brief_path.strip()} — read it from disk FIRST; it is the "
                      f"full brief for this phase (work items, targets, checks in force, signal line).")
    return (
        f"▶️ RUNNER — execute phase {phase['id']} of work order "
        f"projects/{name}/work_order.json (\"{phase['title']}\").\n"
        f"Follow the Phase Execution Contract in AGENTS.md: read RESUME.md + the "
        f"work order first, execute the phase, run the QA gate, SAVE, take the "
        f"phase backup, append your signal to projects/{name}/phase_signals.jsonl, "
        f"then post the PHASE_DONE card."
        + brief_line
        + (f"\nVerification: {'; '.join(v)}." if v else "")
        + (f"\nDecision points in this phase: use the documented default and flag."
           if any(d.get("phase") == phase["id"] for d in wo.get("decision_points", []))
           else "")
        + (f"\nHeartbeat: run python3 automation/phase_heartbeat.py beat {name} {phase['id']} "
           f"\"<step>\" at phase start and again before and after each long step, at least "
           f"every {HEARTBEAT_BEAT_EVERY_MINUTES} minutes. The runner does not re-brief a phase "
           f"whose heartbeat is younger than {HEARTBEAT_FRESH_MINUTES} minutes.")
    )


def model_class_for(phase):
    """Phase class of ONE phase dict of a work order: "judgment" or "mechanical".
    A missing or unknown value (and a phase that is not a dict) is "judgment"."""
    value = phase.get("phase_class") if isinstance(phase, dict) else None
    if isinstance(value, str) and value in PHASE_CLASSES:
        return value
    return DEFAULT_PHASE_CLASS


def phase_class_is_set(phase):
    """True when the work order names a class the runner knows on this phase."""
    value = phase.get("phase_class") if isinstance(phase, dict) else None
    return isinstance(value, str) and value in PHASE_CLASSES


def phase_class_reason_for(phase):
    """Why the phase has the class model_class_for() gives: the reason of the work order
    when the class is set there, else what the runner found instead. One line, cut."""
    value = phase.get("phase_class") if isinstance(phase, dict) else None
    if value is None or value == "":
        return (f"no phase_class on this phase in the work order; "
                f"{DEFAULT_PHASE_CLASS} is the default")
    if not phase_class_is_set(phase):
        return (f"phase_class {str(value)[:40]!r} in the work order is not a class the "
                f"runner knows; {DEFAULT_PHASE_CLASS} is the default")
    reason = phase.get("phase_class_reason")
    if isinstance(reason, str) and reason.strip():
        return " ".join(reason.split())[:PHASE_CLASS_REASON_CUT]
    return "the work order gives no reason"


def phase_class_line(phase):
    """The ONE line a dispatch message carries about the class (same form as in the brief file)."""
    return f"Phase class: {model_class_for(phase)} ({phase_class_reason_for(phase)})"


def model_for_class(phase_class):
    """Model id the gateway owner put into MODEL_BY_CLASS for this class; None while the
    map is empty. The runner only records it; it pins nothing."""
    model = MODEL_BY_CLASS.get(phase_class)
    return str(model) if model else None


def fresh_session_note():
    """The sentence a dispatch message carries when a pack exists."""
    return FRESH_SESSION_NOTE


def pack_rel_path(name, pid):
    """Where phase_pack.py --write puts the pack, relative to the workspace."""
    return f"projects/{name}/briefs/{pid}.pack.md"


def pack_command(name, pid):
    """The command that builds the pack of one phase, run in the container."""
    return ["docker", "exec", CONTAINER, "python3", PACK_TOOL,
            "--project", str(name), "--phase", str(pid), "--write"]


def run_pack_command(name, pid):
    """Run pack_command() in the container. -> (exit code, last line the tool printed).
    Exit code None = the command could not be run or did not end in time. Never raises."""
    try:
        out = subprocess.run(pack_command(name, pid), capture_output=True, text=True,
                             timeout=PACK_TIMEOUT_SECONDS)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:200]
    said = ((out.stderr or "").strip() or (out.stdout or "").strip()).splitlines()
    return out.returncode, (said[-1].strip()[:200] if said else "")


def build_pack(name, pid):
    """Build the pack of one phase and check that the file is there afterwards.
    -> {"ok": bool, "path": workspace-relative pack path, "why": reason when not ok}.
    Never raises: every failure is a reason, and the caller dispatches without a pack."""
    rel = pack_rel_path(name, pid)
    try:
        code, said = run_pack_command(name, pid)
        if code is None:
            why = f"the pack command could not be run or did not end ({said})"
        elif code != 0:
            why = f"the pack command ended with exit {code}" + (f" ({said})" if said else "")
        else:
            raw = docker_read(f"{WORKSPACE_DIR}/{rel}")
            if raw is None:
                why = f"the pack command ended with exit 0 but {rel} is not there"
            elif not raw.strip():
                why = f"the pack command ended with exit 0 but {rel} is empty"
            else:
                return {"ok": True, "path": rel, "why": ""}
    except Exception as e:
        why = f"the pack step raised {type(e).__name__}: {e}"[:240]
    return {"ok": False, "path": rel, "why": why}


def prepare_dispatch(name, phase):
    """Right before a dispatch (first brief or re-brief): build the pack, read the class.
    -> {"pack": pack path or None, "pack_why": reason when there is no pack,
        "phase_class", "phase_class_reason", "model_wanted" (None while MODEL_BY_CLASS is empty)}.
    A pack that was not built is logged here with its reason. Never raises."""
    pid = phase.get("id") if isinstance(phase, dict) else None
    built = build_pack(name, pid)
    if not built["ok"]:
        log(f"{name}: {pid} pack not built: {built['why']}. Without a pack the dispatch "
            f"message is the brief text as before.")
    cls = model_class_for(phase)
    return {"pack": built["path"] if built["ok"] else None,
            "pack_why": "" if built["ok"] else built["why"],
            "phase_class": cls, "phase_class_reason": phase_class_reason_for(phase),
            "model_wanted": model_for_class(cls)}


def record_dispatch(st, prep):
    """Write what prepare_dispatch() found into the runner state of the phase."""
    st["phase_class"] = prep["phase_class"]
    st["phase_class_reason"] = prep["phase_class_reason"]
    for k, v in (("pack", prep.get("pack")), ("pack_note", prep.get("pack_why")),
                 ("model_wanted", prep.get("model_wanted"))):
        if v:
            st[k] = v
        else:
            st.pop(k, None)


def dispatch_note(prep):
    """The part of a dispatch log line about class, model map and pack."""
    note = f"class {prep['phase_class']} ({prep['phase_class_reason']})"
    if prep.get("model_wanted"):
        note += f"; MODEL_BY_CLASS names {prep['model_wanted']}, the runner does not pin it"
    if prep.get("pack"):
        return note + f"; pack {prep['pack']}"
    return note + "; no pack, brief text as before"


def pack_brief(name, wo, phase, pack_path):
    """Text of a dispatch when the pack was built: the pack is the input of the phase.
    Kept from brief(), same words: the first line (phase id, work order, title), the
    signal file, the QA gate, the Verification line, the decision line, the Heartbeat line.
    Left out: "read RESUME.md + the work order first" and the Brief file line (the pack
    holds the brief)."""
    verify = phase.get("verify", {})
    v = []
    if verify.get("qa_model"):
        v.append("qa-model gate REQUIRED")
    if verify.get("vision"):
        v.append(f"vision check: {verify['vision']}")
    return (
        f"▶️ RUNNER — execute phase {phase['id']} of work order "
        f"projects/{name}/work_order.json (\"{phase['title']}\").\n"
        f"Your input is {pack_path}. Read it first. Do not open work_order.json or "
        f"RESUME.md whole: the pack holds the brief, the work order slice, the lessons "
        f"that apply, the state, the open items and the recipes for this phase. The runner "
        f"built it right before this message; its State part is as of that minute.\n"
        f"{fresh_session_note()}\n"
        f"{phase_class_line(phase)}\n"
        f"Follow the Phase Execution Contract in AGENTS.md: execute the phase, run the QA "
        f"gate, SAVE, take the phase backup, append your signal to "
        f"projects/{name}/phase_signals.jsonl, then post the PHASE_DONE card."
        + (f"\nVerification: {'; '.join(v)}." if v else "")
        + (f"\nDecision points in this phase: use the documented default and flag."
           if any(d.get("phase") == phase["id"] for d in wo.get("decision_points", []))
           else "")
        + (f"\nHeartbeat: run python3 automation/phase_heartbeat.py beat {name} {phase['id']} "
           f"\"<step>\" at phase start and again before and after each long step, at least "
           f"every {HEARTBEAT_BEAT_EVERY_MINUTES} minutes. The runner does not re-brief a phase "
           f"whose heartbeat is younger than {HEARTBEAT_FRESH_MINUTES} minutes.")
    )


def dispatch_text(name, wo, phase, prep=None):
    """Text of a first brief. With a pack: pack_brief(). Without one: brief(), word for
    word as before, plus ONE last line with the phase class when the work order names a
    class on the phase (a work order without classes gets exactly the old text)."""
    if prep and prep.get("pack"):
        return pack_brief(name, wo, phase, prep["pack"])
    text = brief(name, wo, phase)
    if prep is not None and phase_class_is_set(phase):
        text += "\n" + phase_class_line(phase)
    return text


def rebrief(name, wo, phase, st, decision, prep=None):
    """Text of a RE-brief: says that it is one, and what to read before doing anything.
    The first brief of the phase follows it unchanged. With a pack (prep from
    prepare_dispatch) the pack message follows instead, and RESUME.md is not read whole."""
    pid = phase["id"]
    first = st.get("first_dispatched_at") or st.get("dispatched_at")
    since = _iso(first) if first else "the first brief of this phase"
    sig = f"projects/{name}/phase_signals.jsonl"
    return (
        f"🔁 RUNNER RE-BRIEF — phase {pid} of work order projects/{name}/work_order.json. "
        f"This is a re-brief, not a new phase: the runner read no signal for {pid} in "
        f"{decision.get('age_min', 0):.0f} min ({decision.get('why') or 'stalled'}; "
        f"{decision.get('heartbeat_note') or 'heartbeat not read'}).\n"
        f"FIRST read {sig}. If it holds a valid done, blocked or awaiting_decision line for "
        f"{pid} with \"at\" later than {since} (the first brief of this phase): the phase is "
        f"closed. Do no work and append no second line; the runner reads that line on its "
        f"next pass. Reply in one line.\n"
        + (f"If there is no such line: see what already landed before you write anything "
           f"(in RESUME.md read only the part about {pid}, do not open the file whole), do "
           f"not redo it, finish what is left, then append the signal.\n"
           f"The brief follows. Its pack was built for this re-brief.\n\n"
           if prep and prep.get("pack") else
           f"If there is no such line: read RESUME.md to see what already landed, do not redo "
           f"it, finish what is left, then append the signal.\n"
           f"The first brief follows.\n\n")
        + dispatch_text(name, wo, phase, prep)
    )


def summarize(key, name, wo, proj):
    done = [p for p, s in proj["phases"].items() if s["status"] == "done"]
    blocked = [(p, s.get("note", "")) for p, s in proj["phases"].items()
               if s["status"] == "blocked"]
    decisions = [(p, s.get("note", "")) for p, s in proj["phases"].items()
                 if s["status"] == "awaiting_decision"]
    msg = (f"🏁 Work order **{name}** ({wo.get('doc', '?')}) — all phases terminal.\n"
           f"✅ Done: {len(done)}/{len(proj['phases'])}")
    if blocked:
        msg += "\n🚫 Blocked:\n" + "\n".join(f"  • {p}: {n}" for p, n in blocked)
    if decisions:
        msg += "\n❓ Awaiting your decision:\n" + "\n".join(f"  • {p}: {n}" for p, n in decisions)
    # Backups are file copies on the user's machine (the Projects\\_backups folder next to
    # the .rvt); each phase names its own in the note of its signal line.
    msg += (f"\nDetails: projects/{name}/ · backups: named in each phase's signal note "
            f"(projects/{name}/phase_signals.jsonl)")
    portal_post(key, CHANNEL, msg, wake=True)
    log(f"{name}: summary posted ({len(done)} done, {len(blocked)} blocked, "
        f"{len(decisions)} decisions)")


def read_heartbeat(name):
    """projects/<name>/phase_heartbeat.json (written by automation/phase_heartbeat.py).
    -> the parsed JSON value; None when the file is missing or the container could not
    be asked; the string "unreadable" when the file is there but is not JSON."""
    raw = docker_read(f"{PROJECTS_DIR}/{name}/{HEARTBEAT_FILE}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return "unreadable"


def rebrief_constants():
    """The constants the stall / re-brief decision uses, read from the module at call time."""
    return {"STALL_MIN_MINUTES": STALL_MIN_MINUTES, "IDLE_MIN_MINUTES": IDLE_MIN_MINUTES,
            "ORPHAN_MIN_MINUTES": ORPHAN_MIN_MINUTES,
            "HEARTBEAT_FRESH_MINUTES": HEARTBEAT_FRESH_MINUTES,
            "HEARTBEAT_SKEW_SECONDS": HEARTBEAT_SKEW_SECONDS,
            "ALIVE_CEILING_FACTOR": ALIVE_CEILING_FACTOR,
            "ALIVE_CEILING_MIN_MINUTES": ALIVE_CEILING_MIN_MINUTES}


def stall_reason(age_min, est, system_alive, consts=None):
    """The stall rules as they were before 2026-11-15, unchanged. Pure.
    age_min: minutes since the last brief of the phase. -> reason text, None = not stalled."""
    c = consts or rebrief_constants()
    idle_dead = (not system_alive) and age_min > c["IDLE_MIN_MINUTES"]
    orphaned = system_alive and age_min > c["ORPHAN_MIN_MINUTES"]
    hard_ceiling = age_min > max(2 * est, c["STALL_MIN_MINUTES"])
    if idle_dead:
        return "no-gateway-activity"
    if orphaned:
        return "orphaned (activity but no signal)"
    if hard_ceiling:
        return "hard ceiling"
    return None


def heartbeat_state(now, pid, st, heartbeat, consts=None):
    """Classify the heartbeat for the dispatched phase pid. Pure.
    -> (state, age_min or None, note for people). Only state "fresh" means alive; every
    other state (missing, unreadable, other-phase, future, before-brief, stale) does not."""
    c = consts or rebrief_constants()
    if heartbeat is None:
        return "missing", None, "no heartbeat file"
    if not isinstance(heartbeat, dict):
        return "unreadable", None, "heartbeat file not readable"
    if str(heartbeat.get("phase", "")) != str(pid):
        return ("other-phase", None,
                "heartbeat is for another phase (%s)" % str(heartbeat.get("phase", "?"))[:40])
    at = _iso_epoch(heartbeat.get("at"))
    if at is None:
        return "unreadable", None, "heartbeat has no readable time"
    age_min = (now - at) / 60.0
    skew = c["HEARTBEAT_SKEW_SECONDS"]
    if now - at < -skew:
        return "future", age_min, "heartbeat time is %.0f min ahead of the runner clock" % -age_min
    first = st.get("first_dispatched_at") or st.get("dispatched_at")
    if first and at < first - skew:
        return "before-brief", age_min, "heartbeat is older than the first brief of this phase"
    if age_min <= c["HEARTBEAT_FRESH_MINUTES"]:
        return "fresh", age_min, "heartbeat %.0f min old" % max(age_min, 0)
    return "stale", age_min, "heartbeat stale, %.0f min old" % age_min


def rebrief_decision(now, pid, st, est, system_alive, signals=(), heartbeat=None, consts=None):
    """What to do about ONE dispatched phase. Pure: no I/O, no clock, nothing is changed.

    now          epoch seconds
    pid, st      phase id and its runner state (status, dispatched_at, first_dispatched_at,
                 briefs, alive_alerted)
    est          est_minutes of the phase, as process_project clamps it (at least 10)
    system_alive result of recent_gateway_activity()
    signals      signal lines read from the file AFTER the pass consumed its signals
                 (the re-read right before posting); () when none were read
    heartbeat    value of read_heartbeat(): dict, None (missing) or "unreadable"
    consts       overrides for rebrief_constants() (tests)

    -> dict with "action", one of
       "wait"          not dispatched, or not stalled by the old rules: do nothing
       "signal"        a signal for this phase is in the file: process it, post nothing
       "done-pending"  stalled by the old rules but the heartbeat is fresh: alive, no re-brief
       "alert-alive"   as done-pending, and past the alive ceiling for the first time: one alert
       "rebrief"       stalled, not alive, first brief only so far: post the re-brief
       "block"         stalled, not alive, already briefed twice: mark blocked
       plus why, age_min (since the last brief), run_min (since the first brief),
       heartbeat (state), heartbeat_age_min, heartbeat_note, alive_ceiling_min, signal.
    """
    c = dict(rebrief_constants())
    c.update(consts or {})
    out = {"action": "wait", "why": "", "age_min": 0.0, "run_min": 0.0,
           "heartbeat": "not-checked", "heartbeat_age_min": None, "heartbeat_note": "",
           "alive_ceiling_min": None, "signal": None}
    if st.get("status") != "dispatched":
        out["why"] = "phase is not dispatched"
        return out
    age_min = (now - st.get("dispatched_at", now)) / 60.0
    first = st.get("first_dispatched_at") or st.get("dispatched_at") or now
    out["age_min"] = age_min
    out["run_min"] = (now - first) / 60.0
    why = stall_reason(age_min, est, system_alive, c)
    out["why"] = why or ""
    for sig in signals or ():
        if (isinstance(sig, dict) and str(sig.get("phase", "")) == str(pid)
                and sig.get("status") in SIGNAL_STATUSES):
            out["action"] = "signal"
            out["signal"] = sig.get("status")      # the last one wins, as when signals are applied
    if out["action"] == "signal":
        return out
    if not why:
        return out
    hb_state, hb_age, hb_note = heartbeat_state(now, pid, st, heartbeat, c)
    out.update({"heartbeat": hb_state, "heartbeat_age_min": hb_age, "heartbeat_note": hb_note})
    if hb_state == "fresh":
        ceiling = max(c["ALIVE_CEILING_FACTOR"] * est, c["ALIVE_CEILING_MIN_MINUTES"])
        out["alive_ceiling_min"] = ceiling
        if out["run_min"] > ceiling and not st.get("alive_alerted"):
            out["action"] = "alert-alive"
        else:
            out["action"] = "done-pending"
        return out
    out["action"] = "rebrief" if st.get("briefs", 1) < 2 else "block"
    return out


def apply_signals(key, name, proj, lines):
    """Apply signal lines (already read from the file) to the phase states.
    -> True when a blocked / awaiting_decision phase was re-queued with 'pending'."""
    requeued = False
    for sig in lines:
        pid = str(sig.get("phase", ""))
        status = sig.get("status", "")
        if pid not in proj["phases"]:
            continue
        note = sig.get("note", "")
        if status in ("done", "blocked", "awaiting_decision", "pending"):
            was = proj["phases"][pid]["status"]
            proj["phases"][pid].update({"status": status, "note": note,
                                        "at": sig.get("at", "")})
            proj["phases"][pid].pop("watch", None)
            if status in ("done", "blocked", "awaiting_decision"):
                # when the phase signalled: the end of the window for the token telemetry
                proj["phases"][pid]["signal_epoch"] = _iso_epoch(sig.get("at")) or time.time()
                proj["phases"][pid].pop("usage", None)
            log(f"{name}: signal {pid} {was} -> {status} {('(' + note + ')') if note else ''}")
            if status == "blocked":
                portal_post(key, ALERT_CHANNEL,
                            f"🚫 Blueprint runner: {name} phase {pid} BLOCKED — {note}",
                            wake=True)
            if status == "pending" and was in ("blocked", "awaiting_decision"):
                requeued = True
    return requeued


def order_stop(name, wo):
    """Is the work order in this folder stopped by its owner?
    projects/<name>/ORDER_STOPPED.json is written by automation/order_stop.py in the workspace, on a
    person's word. It names the order it stops ("order_key", same value as order_key(wo)).
    -> None                      no marker, or a marker for ANOTHER order (a later order in the folder runs)
    -> {"key", "why", "other"}   "other" True = marker for another order (not a stop, the caller logs it once)
    A marker that cannot be read, is not JSON or names no order stops whatever is in the folder: fail closed.
    Never raises."""
    path = f"{PROJECTS_DIR}/{name}/{ORDER_STOP_FILE}"
    try:
        raw = docker_read(path)
    except Exception as e:
        return {"key": "unreadable", "why": f"the stop marker could not be read ({type(e).__name__})", "other": False}
    if not raw or not raw.strip():
        return None
    try:
        mk = json.loads(raw)
        if not isinstance(mk, dict):
            raise ValueError("not an object")
    except Exception:
        return {"key": "invalid", "why": "the stop marker is not valid JSON; treated as a stop", "other": False}
    want = str(mk.get("order_key") or "").strip()
    who = str(mk.get("stopped_by") or "owner")[:80]
    at = str(mk.get("at") or "")[:40]
    if not want:
        return {"key": "any", "why": f"stopped by {who} {at} (the marker names no order: it stops any order here)".strip(), "other": False}
    if want != order_key(wo):
        return {"key": want, "why": f"a stop marker for another order ({want[:60]}) is in the folder", "other": True}
    return {"key": want, "why": f"stopped by {who} {at}".strip(), "other": False}


def process_project(key, state, name, wo):
    # token telemetry first: it must also run for a folder that is already finished,
    # and before a new order resets the phase states
    if name in state["projects"]:
        try:
            fill_usage(name, state["projects"][name])
        except Exception as e:
            log(f"{name}: usage fill failed (ignored): {e}")
    proj = phase_states(state, name, wo)

    # Gate: never dispatch without explicit Mitch approval recorded in the file
    if not wo.get("approved"):
        return

    # Gate: an order its owner stopped is never dispatched or re-briefed, whatever the state says.
    # Removing the marker (a person's go, automation/order_stop.py clear) is what lets it run again.
    stop = order_stop(name, wo)
    if stop and not stop["other"]:
        if proj.get("stopped_key") != stop["key"]:
            proj["stopped_key"] = stop["key"]
            proj["stopped"] = stop["why"]
            log(f"{name}: work order STOPPED BY OWNER ({stop['why']}) - no dispatch and no re-brief "
                f"while {ORDER_STOP_FILE} is in the folder")
        return
    if stop and stop["other"] and proj.get("stop_marker_other") != stop["key"]:
        proj["stop_marker_other"] = stop["key"]
        log(f"{name}: {stop['why']}; it does not stop this order")
    if proj.pop("stopped_key", None) is not None:
        proj.pop("stopped", None)
        log(f"{name}: the stop marker for this order is gone - dispatch is open again")

    # Mark completed-and-summarized orders as finished — but a re-queue
    # signal ("pending") must re-engage, so this check happens AFTER signals.
    # 1) Consume new signals
    lines, new_off = read_signals(name, proj.get("offset", 0))
    proj["offset"] = new_off
    requeued = apply_signals(key, name, proj, lines)

    # 2) Finished check (after signals so re-queues re-engage)
    if proj.get("finished"):
        if requeued:
            proj["finished"] = False
            log(f"{name}: re-engaged (phase re-queued after summary)")
        else:
            return

    # 3) Dispatch next eligible pending phase — STRICTLY one active at a time
    #    (concurrent sessions saving/backing up the same doc = v2 problem)
    now = time.time()
    if any(s["status"] == "dispatched" for s in proj["phases"].values()):
        pass  # a phase is in flight — wait for its signal
    else:
        for ph in wo["phases"]:
            pid = ph["id"]
            st = proj["phases"][pid]
            if st["status"] != "pending":
                continue
            if not deps_done(wo, proj, ph):
                continue
            # pack + class right before the dispatch; a failed pack = the old brief text
            prep = prepare_dispatch(name, ph)
            portal_post(key, CHANNEL, dispatch_text(name, wo, ph, prep), wake=True)
            st.update({"status": "dispatched", "dispatched_at": now, "briefs": 1,
                       "first_dispatched_at": now})
            st.pop("signal_epoch", None)
            st.pop("usage", None)
            for k in ("watch", "alive_alerted", "heartbeat_at"):
                st.pop(k, None)
            record_dispatch(st, prep)
            log(f"{name}: dispatched {pid} ({ph['title']}) — {dispatch_note(prep)}")
            break

    # 4) Activity-aware stall detection on dispatched phases.
    #    - dead system (no gateway activity): re-brief after IDLE_MIN
    #    - alive but phase orphaned (activity, no signal): re-brief after ORPHAN_MIN
    #    - hard ceiling stays at the old 2x-est window
    #    - max 2 briefs, then blocked + alert
    #    Re-brief guard (2026-11-15), only for a phase the rules above call stalled:
    #    - fresh heartbeat for the phase: alive, watched as "done-pending", no re-brief;
    #      past the alive ceiling: ONE alert, still no re-brief
    #    - the signal file is read AGAIN right before a re-brief or a stall-block is
    #      posted; a signal for the phase is processed and nothing is posted
    system_alive = recent_gateway_activity()
    for ph in wo["phases"]:
        pid = ph["id"]
        st = proj["phases"][pid]
        if st["status"] != "dispatched":
            continue
        est = max(int(ph.get("est_minutes", 30)), 10)
        age_min = (now - st.get("dispatched_at", now)) / 60.0
        if not stall_reason(age_min, est, system_alive):
            continue
        hb = read_heartbeat(name)
        # A re-brief gets a pack too. It is built BEFORE the signal re-read (decided on
        # what is known so far), so that the re-read stays the last thing before the post.
        prep = None
        if rebrief_decision(now, pid, st, est, system_alive, (), hb)["action"] == "rebrief":
            prep = prepare_dispatch(name, ph)
        fresh, new_off = read_signals(name, proj.get("offset", 0))
        proj["offset"] = new_off
        d = rebrief_decision(now, pid, st, est, system_alive, fresh, hb)
        if fresh:
            apply_signals(key, name, proj, fresh)
        why = d["why"]
        hb_note = d["heartbeat_note"]
        step = str(hb.get("step", ""))[:80] if isinstance(hb, dict) else ""
        if d["action"] == "signal":
            log(f"{name}: {pid} looked stalled at {age_min:.0f}min ({why}) but a "
                f"'{d['signal']}' signal was in the file on the re-read — processed, "
                f"nothing posted")
        elif d["action"] in ("done-pending", "alert-alive"):
            if st.get("watch") != "done-pending":
                log(f"{name}: {pid} no signal after {age_min:.0f}min ({why}) but "
                    f"{hb_note} (step: {step or 'not given'}) — alive, done-pending, "
                    f"no re-brief")
            st["watch"] = "done-pending"
            st["heartbeat_at"] = str(hb.get("at", ""))[:25]
            if d["action"] == "alert-alive":
                portal_post(key, ALERT_CHANNEL,
                            f"⏳ Blueprint runner: {name} {pid} has run "
                            f"{d['run_min']:.0f} min since its first brief, past the "
                            f"ceiling of {d['alive_ceiling_min']:.0f} min (est {est} min). "
                            f"Its {hb_note} (step: {step or 'not given'}), so the phase "
                            f"is treated as alive and is NOT re-briefed. This alert is "
                            f"sent once for this dispatch. Someone should look.",
                            wake=True)
                st["alive_alerted"] = True
                log(f"{name}: {pid} alive past the ceiling ({d['run_min']:.0f} > "
                    f"{d['alive_ceiling_min']:.0f} min) — alerted once, no re-brief")
        elif d["action"] == "rebrief":
            briefs = st.get("briefs", 1)
            if prep is None:              # not expected: same inputs as the decision above
                prep = prepare_dispatch(name, ph)
            portal_post(key, CHANNEL, rebrief(name, wo, ph, st, d, prep), wake=True)
            st["briefs"] = briefs + 1
            st["dispatched_at"] = now
            st.pop("watch", None)
            record_dispatch(st, prep)
            log(f"{name}: {pid} stalled {age_min:.0f}min ({why}; {hb_note}) — re-briefed "
                f"(attempt {briefs + 1}) — {dispatch_note(prep)}")
            portal_post(key, ALERT_CHANNEL,
                        f"⚠️ Blueprint runner: {name} {pid} stalled at "
                        f"{age_min:.0f} min — {why} — {hb_note} — re-briefing", wake=False)
        elif d["action"] == "block":
            st.update({"status": "blocked",
                       "note": f"stalled ({why}), no signal after 2 briefs "
                               f"({age_min:.0f} min)"})
            st.pop("watch", None)
            log(f"{name}: {pid} marked blocked (stalled twice, {why}; {hb_note})")
            portal_post(key, ALERT_CHANNEL,
                        f"🚫 Blueprint runner: {name} {pid} BLOCKED — stalled "
                        f"({why}), no signal after 2 briefs", wake=True)

    # 5) Terminal check — all phases done/blocked/awaiting_decision
    terminal = all(s["status"] in ("done", "blocked", "awaiting_decision")
                   for s in proj["phases"].values())
    if terminal and proj["phases"]:
        summarize(key, name, wo, proj)
        proj["finished"] = True
        log(f"{name}: work order complete")


def main():
    # single-instance lock via flock is handled by the cron wrapper
    key = load_env()
    state = load_state()
    orders = find_work_orders()
    if not orders:
        return  # nothing to do — no work orders exist
    for name, wo in orders.items():
        try:
            process_project(key, state, name, wo)
        except Exception as e:
            log(f"ERROR processing {name}: {e}")
            try:
                portal_post(key, ALERT_CHANNEL,
                            f"⚠️ Blueprint runner error on {name}: {e}", wake=False)
            except Exception:
                pass
    save_state(state)


if __name__ == "__main__":
    main()
