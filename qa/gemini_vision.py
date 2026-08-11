"""
gemini_vision.py — Direct Gemini API calls for scripted vision QA.

Keeps the agent loop out of tile-by-tile inspection: scripts call Gemini
directly, aggregate findings, and the agent only reads the final report.

Key discovery order:
  1. GEMINI_API_KEY / GOOGLE_API_KEY env var
  2. OpenClaw models.json (agent container)
"""

import base64
import json
import os
import re
import time

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
DEFAULT_MODEL = "gemini-3-flash-preview"   # fast + cheap for tile passes
MODELS_JSON = "/home/node/.openclaw/agents/main/agent/models.json"


def _find_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    try:
        raw = open(MODELS_JSON).read()
        m = re.search(r"AIzaSy[A-Za-z0-9_-]+", raw)
        if m:
            return m.group(0)
    except OSError:
        pass
    raise RuntimeError("No Gemini API key found (env GEMINI_API_KEY or models.json)")


def ask_image(image_path: str, prompt: str, model: str = DEFAULT_MODEL,
              retries: int = 2) -> str:
    """Send one image + prompt to Gemini, return text response."""
    key = _find_key()
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    body = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                {"text": prompt},
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }

    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(GEMINI_URL.format(model=model, key=key),
                              json=body, timeout=120)
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except Exception as e:
            last_err = e
            time.sleep(3)
    raise RuntimeError(f"Gemini call failed after {retries + 1} tries: {last_err}")


def ask_image_json(image_path: str, prompt: str, model: str = DEFAULT_MODEL) -> dict | list:
    """Like ask_image but expects/extracts a JSON payload from the reply."""
    text = ask_image(image_path, prompt, model=model)
    # Strip markdown fences if present
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    raw = m.group(1) if m else text
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {"parse_error": True, "raw": text[:2000]}
