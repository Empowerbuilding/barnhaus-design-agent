"""
vision_checks.py — Atomic parallel vision checklist runner (z.ai GLM models).

WHY THIS EXISTS (2026-11-01 audit):
  Multi-point "verify 1,2,3,4... report findings" prompts sent through the
  OpenClaw image tool (glm-5.3-flash) trigger 4,000-16,000 chars of model
  thinking per call: 65-91s per QA round, and sometimes the ENTIRE output
  budget burns on thinking -> zero-character answer -> silent failure or
  hidden retry/fallback. z.ai ignores `thinking` budget_tokens (tested).
  Atomic single-question calls keep thinking small (0.5-3K chars) and
  parallelize cleanly.

MEASURED (2-sheet permit QA, 4 checks, 2026-11-01):
  mega-prompt via image tool:    65-91s, answers sometimes empty
  atomic parallel (this file):   ~20s wall, all checks answered, real issues
                                caught (text collision, footprint mismatch)
  glm-5.3-flash per atomic check: 9-20s — sharpest, the default here
  glm-4.6v per atomic check:     4-13s — fast but misses fine detail

MODEL ROUTING (check `kind`) — quality-first, measured 2026-11-01:
  EVERYTHING defaults to glm-5.3-flash (sharpest: caught text collisions,
  footprint mismatch, doubled notes that glm-4.6v missed or returned UNCLEAR
  on). glm-4.6v compresses images ~65x harder — fast and cheap but blind to
  fine detail.
  kind "fast" or "coarse" (blank-sheet checks, rough counts) -> glm-4.6v
  --model glm-4.6v forces it for everything (use when speed > edge detail)

  Why this is still 3-4.5x faster than the image tool: checks are atomic
  (small thinking) and run in parallel — a 4-check round is ~20s wall vs
  65-91s for one mega-prompt.

KEY DISCOVERY (same pattern as qa/gemini_vision.py):
  1. ZAI_API_KEY env var
  2. OpenClaw models.json (agent container)

USAGE:
  python3 qa/vision_checks.py exports/permit_A111.png exports/permit_A112.png \
      --check "title:Do the title blocks show the correct project name and sheet numbers?" \
      --check "geometry:Does the roof plan footprint match the floor plan patio outline?" \
      --check "text:Any colliding or overlapping annotation/dimension text?" \
      --check "presence:Any orphaned tags or leaders pointing at nothing?" \
      [--workers 4] [--model glm-4.6v] [--out qa_reports/vc_<name>.json]

  Or via checklist file (JSON):
  python3 qa/vision_checks.py qa_reports/checklist.json
    {"images": ["exports/a.png", "exports/b.png"],
     "checks": [{"id": "titles", "kind": "title", "q": "Do the title blocks ...?"}]}

OUTPUT: one console line per check -> `id | VERDICT | note`, plus a JSON
report (pass --out to persist). Verdicts come from the model's own [PASS]/
[FAIL]/[UNCLEAR] tag, so phrase questions naturally — the runner does not
guess polarity from yes/no words.
"""

import base64
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ZAI_URL = "https://api.z.ai/api/anthropic/v1/messages"
MODELS_JSON = "/home/node/.openclaw/agents/main/agent/models.json"

MODEL_46V = "glm-4.6v"
MODEL_FLASH = "glm-5.3-flash"
KIND_46V = {"fast", "coarse"}   # opt-in only — 4.6v misses fine detail

MAX_WORKERS = 4
MAX_TOKENS_FIRST = 700      # small on purpose: forces short thinking
MAX_TOKENS_RETRY = 1500     # bumped only when the first try came back empty


def _find_key() -> str:
    key = os.environ.get("ZAI_API_KEY")
    if key:
        return key
    try:
        raw = open(MODELS_JSON).read()
        m = re.search(r"[a-f0-9]{32}\.[A-Za-z0-9]+", raw)
        if m:
            return m.group(0)
    except OSError:
        pass
    raise RuntimeError("No z.ai key found (env ZAI_API_KEY or models.json)")


def _fit(path: str) -> str:
    """Best-effort vision-size guard (core/fit_image.py). Returns path."""
    try:
        from core.fit_image import fit
        fit(path)
    except Exception:
        pass
    return path


def _ask(model: str, prompt: str, image_paths: list, max_tokens: int) -> tuple:
    """One atomic call. Returns (answer_text, think_chars, usage)."""
    key = _find_key()
    content = []
    for p in image_paths:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({"type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}})
    content.append({"type": "text", "text": prompt})

    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}]}
    headers = {"Authorization": ("Bear" + "er ") + key, "Content-Type": "application/json"}

    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(ZAI_URL, json=body, headers=headers, timeout=120)
            if r.status_code in (429, 500, 502, 503):
                last_err = f"HTTP {r.status_code}"
                time.sleep(3 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            txt = "".join(c.get("text", "") for c in data.get("content", [])
                          if c.get("type") == "text")
            think = sum(len(c.get("thinking", "")) for c in data.get("content", [])
                        if c.get("type") == "thinking")
            return txt.strip(), think, data.get("usage", {})
        except Exception as e:
            last_err = str(e)
            time.sleep(3)
    raise RuntimeError(f"z.ai call failed after 3 tries: {last_err}")


def run_check(check: dict, image_paths: list, model_override: str = None) -> dict:
    """Run one atomic check. Retries once with a bigger budget on empty answers."""
    q = check["q"]
    kind = (check.get("kind") or "").lower()
    model = model_override or (MODEL_46V if kind in KIND_46V else MODEL_FLASH)
    prompt = (f"{q}\n\nAnswer in ONE sentence, ending with the verdict tag "
              f"[PASS], [FAIL], or [UNCLEAR]. PASS = check satisfied / no problem "
              f"found. FAIL = problem found (say exactly where). UNCLEAR = cannot "
              f"determine from these images. Decide from direct visual inspection "
              f"only — do NOT deliberate step by step; if unsure, answer UNCLEAR "
              f"immediately.")

    t0 = time.time()
    try:
        txt, think, usage = _ask(model, prompt, image_paths, MAX_TOKENS_FIRST)
        if not txt:  # thinking ate the budget — retry once with room
            txt, think2, usage = _ask(model, prompt, image_paths, MAX_TOKENS_RETRY)
            think += think2
        m = re.search(r"\[(PASS|FAIL|UNCLEAR)\]", txt, re.IGNORECASE)
        verdict = m.group(1).upper() if m else "UNCLEAR"
        note = re.sub(r"\[(PASS|FAIL|UNCLEAR)\]", "", txt, flags=re.IGNORECASE).strip()
        return {"id": check.get("id") or q[:40], "kind": kind, "model": model,
                "verdict": verdict, "note": note[:400], "seconds": round(time.time() - t0, 1),
                "think_chars": think, "ok": True}
    except Exception as e:
        return {"id": check.get("id") or q[:40], "kind": kind, "model": model,
                "verdict": "ERROR", "note": str(e)[:300], "seconds": round(time.time() - t0, 1),
                "ok": False}


def run_checklist(checks: list, image_paths: list, workers: int = MAX_WORKERS,
                  model_override: str = None) -> list:
    image_paths = [_fit(p) for p in image_paths]
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_check, c, image_paths, model_override): c for c in checks}
        for f in as_completed(futs):
            results.append(f.result())
    results.sort(key=lambda r: r["id"])
    return results


def _print(results: list) -> None:
    for r in results:
        flag = {"PASS": "OK ", "FAIL": "!! ", "UNCLEAR": "?  ", "ERROR": "XX "}[r["verdict"]]
        print(f"{flag} {r['id']:<28} {r['verdict']:<7} {r['seconds']:>5.1f}s  {r['note'][:110]}")
    fails = sum(1 for r in results if r["verdict"] == "FAIL")
    errs = sum(1 for r in results if not r["ok"])
    print(f"\n{len(results)} checks: {fails} FAIL, {errs} error"
          f"{'s' if errs != 1 else ''}, wall-parallel via vision_checks.py")


def main() -> None:
    args = sys.argv[1:]
    out_path = None
    workers = MAX_WORKERS
    model_override = None

    if args and args[0].endswith(".json") and not args[0].startswith("--"):
        spec = json.load(open(args[0]))
        images = spec.get("images", [])
        checks = spec.get("checks", [])
        rest = args[1:]
    else:
        images, checks, rest = [], [], []
        i = 0
        while i < len(args):
            a = args[i]
            if a == "--check" and i + 1 < len(args):
                spec_str = args[i + 1]
                kind, _, q = spec_str.partition(":")
                if not q.strip():          # no colon — the whole string is the question
                    kind, q = "", spec_str
                checks.append({"id": kind or q[:30], "kind": kind, "q": q.strip()})
                i += 2
                continue
            if a in ("--workers", "--model", "--out") and i + 1 < len(args):
                rest.extend([a, args[i + 1]])
                i += 2
                continue
            if a.startswith("--"):
                rest.append(a)
                i += 1
                continue
            images.append(a)
            i += 1

    i = 0
    while i < len(rest):
        if rest[i] == "--workers" and i + 1 < len(rest):
            workers = int(rest[i + 1]); i += 2; continue
        if rest[i] == "--model" and i + 1 < len(rest):
            model_override = rest[i + 1]; i += 2; continue
        if rest[i] == "--out" and i + 1 < len(rest):
            out_path = rest[i + 1]; i += 2; continue
        i += 1

    if not images or not checks:
        print(__doc__)
        sys.exit(1)

    results = run_checklist(checks, images, workers, model_override)
    _print(results)
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump({"images": images, "results": results}, f, indent=1)
        print(f"report: {out_path}")


if __name__ == "__main__":
    main()
