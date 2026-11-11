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

    # Mark completed-and-summarized orders as finished — but a re-queue
    # signal ("pending") must re-engage, so this check happens AFTER signals.
    # 1) Consume new signals
    lines, new_off = read_signals(name, proj.get("offset", 0))
    proj["offset"] = new_off
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
            portal_post(key, CHANNEL, brief(name, wo, ph), wake=True)
            st.update({"status": "dispatched", "dispatched_at": now, "briefs": 1,
                       "first_dispatched_at": now})
            st.pop("signal_epoch", None)
            st.pop("usage", None)
            log(f"{name}: dispatched {pid} ({ph['title']})")
            break

    # 4) Activity-aware stall detection on dispatched phases.
    #    - dead system (no gateway activity): re-brief after IDLE_MIN
    #    - alive but phase orphaned (activity, no signal): re-brief after ORPHAN_MIN
    #    - hard ceiling stays at the old 2x-est window
    #    - max 2 briefs, then blocked + alert
    system_alive = recent_gateway_activity()
    for ph in wo["phases"]:
        pid = ph["id"]
        st = proj["phases"][pid]
        if st["status"] != "dispatched":
            continue
        est = max(int(ph.get("est_minutes", 30)), 10)
        age_min = (now - st.get("dispatched_at", now)) / 60.0
        idle_dead = (not system_alive) and age_min > IDLE_MIN_MINUTES
        orphaned = system_alive and age_min > ORPHAN_MIN_MINUTES
        hard_ceiling = age_min > max(2 * est, STALL_MIN_MINUTES)
        if idle_dead or orphaned or hard_ceiling:
            why = ("no-gateway-activity" if idle_dead else
                   "orphaned (activity but no signal)" if orphaned else "hard ceiling")
            briefs = st.get("briefs", 1)
            if briefs < 2:
                portal_post(key, CHANNEL, brief(name, wo, ph), wake=True)
                st["briefs"] = briefs + 1
                st["dispatched_at"] = now
                log(f"{name}: {pid} stalled {age_min:.0f}min ({why}) — re-briefed "
                    f"(attempt {briefs + 1})")
                portal_post(key, ALERT_CHANNEL,
                            f"⚠️ Blueprint runner: {name} {pid} stalled at "
                            f"{age_min:.0f} min — {why} — re-briefing", wake=False)
            else:
                st.update({"status": "blocked",
                           "note": f"stalled ({why}), no signal after 2 briefs "
                                   f"({age_min:.0f} min)"})
                log(f"{name}: {pid} marked blocked (stalled twice, {why})")
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
