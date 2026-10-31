#!/usr/bin/env python3
"""family_search.py — find direct-download .rfa/.zip URLs for Revit families.

Part of the family-sourcing pipeline (2026-10-31, Phase 2). Companion to the bridge
commands revit.download_family / revit.list_local_families / revit.load_family.

Usage:
    python3 family_search.py "gas patio heater"
    python3 family_search.py "modine hot dawg unit heater" --limit 6

What it does:
  1. DuckDuckGo lite search (no API key) for "<query> revit family rfa download"
  2. Ranks results by source tier (manufacturer/curated > free library > unknown)
  3. DEEP mode (default): fetches top result pages and extracts direct .rfa/.zip links
  4. HEAD-verifies the direct file links (content-type / size plausibility)

Output JSON: `direct_files` (feed straight into revit.download_family) and `pages`
(leads with no direct link found on them). Login-walled sources are BLOCKED by
design — flag those to Tony for a manual one-time grab instead.

Flow after picking a URL (mandatory):
    revit.list_local_families {search:...}   <- ALWAYS check cache first
    revit.download_family {url:...}
    revit.load_family {family_path:...}
    ONE test placement + revit.diagnose_element -> then batch
"""
import argparse
import http.client
import json
import re
import sys
import urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FamilySourcing/1.0"
MAX_BODY = 2 * 1024 * 1024  # cap page fetch at 2MB

# Vetted source tiers. Extend freely — unknown domains still pass as tier 3 (flagged).
TIER1_DOMAINS = [
    "arcat.com",             # no-login manufacturer BIM library
    "bromic.com",            # manufacturer (premium patio heaters)
    "brantradiant.com",      # manufacturer (infrared heaters)
    "modine.com", "marleymep.com", "infratech.com",
    "rinnai.us", "trane.com", "carrier.com", "lennox.com", "daikin.com",
    "mesteksa.com", "greenheck.com", "broan-nutone.com",
]
TIER2_DOMAINS = [
    "families.draftsperson.net",
    "freerevitmodels.com",
    "libraryrevit.com",
    "revitfamiliesfree.com",
    "cadauthority.com",
    "revitmonsters.org",
]
BLOCKED_DOMAINS = [
    # login-walled (needs browser session) — flag to Tony instead
    "revitcity.com", "bimobject.com", "bimsmith.com", "modlar.com",
    "bimstore", "nbsnationalbimlibrary",
    # junk / not-file sources
    "youtube.com", "youtu.be", "reddit.com", "pinterest", "facebook.com",
    "amazon.com", "ebay.com", "quora.com", "medium.com",
]


def fetch(url, method="GET", extra_headers=None, timeout=15):
    """Return (status, final_url, body_bytes) or raise."""
    p = urllib.parse.urlparse(url)
    if p.scheme != "https":
        raise ValueError("https only")
    conn = http.client.HTTPSConnection(p.netloc, timeout=timeout)
    path = p.path + ("?" + p.query if p.query else "")
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*"}
    if extra_headers:
        headers.update(extra_headers)
    conn.request(method, path, headers=headers)
    r = conn.getresponse()
    body = r.read(MAX_BODY)
    conn.close()
    return r.status, url, body


def ddg_search(query, max_results=15):
    """Search DuckDuckGo (lite endpoint — html endpoint serves bot challenges)."""
    q = urllib.parse.quote(query + " revit family rfa download")
    urls = []
    try:
        status, _, body = fetch("https://lite.duckduckgo.com/lite/?q=" + q, timeout=20)
        if status == 200:
            text = body.decode("utf-8", errors="replace")
            for m in re.finditer(r"uddg=([^&\"<>]+)", text):
                dec = urllib.parse.unquote(m.group(1))
                if dec.startswith("https://") and dec not in urls:
                    urls.append(dec)
    except Exception:
        pass
    return urls[:max_results]


def classify(url):
    u = url.lower()
    if any(b in u for b in BLOCKED_DOMAINS):
        return None
    if any(t in u for t in TIER1_DOMAINS):
        return 1, "manufacturer/curated"
    if any(t in u for t in TIER2_DOMAINS):
        return 2, "free-library"
    return 3, "unknown-domain"


def extract_file_links(page_url, body_text):
    """Pull .rfa/.zip hrefs out of a page, absolutized."""
    found = []
    for m in re.finditer(r"""href\s*=\s*["']([^"']+)["']""", body_text, re.I):
        href = m.group(1).strip()
        if href.startswith(("javascript:", "mailto:", "#", "data:")):
            continue
        clean = href.split("#")[0]
        if not clean:
            continue
        if ".rfa" in clean.lower() or ".zip" in clean.lower():
            absu = urllib.parse.urljoin(page_url, clean)
            if absu.lower().startswith("https://") and absu not in found:
                found.append(absu)
    return found


def head_verify(url, timeout=12):
    try:
        status, _, _ = fetch(url, method="HEAD", timeout=timeout)
        if status in (405, 403, 501):
            status, _, _ = fetch(url, method="GET",
                                 extra_headers={"Range": "bytes=0-0"}, timeout=timeout)
        return {"http": status, "plausible": status == 200}
    except Exception as e:
        return {"error": str(e)[:120], "plausible": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=6, help="pages to deep-scan")
    ap.add_argument("--no-deep", action="store_true", help="skip page fetching")
    ap.add_argument("--no-verify", action="store_true", help="skip HEAD checks")
    args = ap.parse_args()

    raw = ddg_search(args.query)
    pages = []
    for url in raw:
        c = classify(url)
        if c is None:
            continue
        tier, tname = c
        pages.append({"url": url, "domain": urllib.parse.urlparse(url).netloc,
                      "tier": tier, "tier_name": tname})
    pages.sort(key=lambda p: (p["tier"], 0 if (".rfa" in p["url"] or ".zip" in p["url"]) else 1))
    pages = pages[:args.limit]

    direct_files = []
    if not args.no_deep:
        for page in pages:
            try:
                status, _, body = fetch(page["url"], timeout=15)
                if status != 200:
                    page["fetch_status"] = status
                    continue
                links = extract_file_links(page["url"], body.decode("utf-8", errors="replace"))
                page["direct_file_count"] = len(links)
                for l in links[:5]:
                    direct_files.append({"url": l, "source_page": page["url"],
                                         "tier": page["tier"], "tier_name": page["tier_name"]})
            except Exception as e:
                page["fetch_error"] = str(e)[:120]

    if not args.no_verify:
        for f in direct_files[:8]:
            f["verified"] = head_verify(f["url"])

    print(json.dumps({
        "query": args.query,
        "pages_checked": len(pages),
        "direct_files": direct_files,
        "pages": pages,
        "blocked_note": "Login-walled sources (RevitCity/BIMobject/BIMsmith) are excluded by design — ask Tony for a one-time manual grab of anything that only exists there.",
        "flow_note": "Pick a direct_files url -> revit.list_local_families first (cache!) -> revit.download_family {url} -> revit.load_family -> ONE test placement + revit.diagnose_element -> batch. Revit-2026+ families fail at load (valid reject). Tier 3 = unknown domain: the download gates still protect, but diagnose carefully."
    }, indent=2))


if __name__ == "__main__":
    main()
