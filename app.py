"""
AI Lead Generation Agent — Backend (DUAL-SOURCE DISCOVERY)
=============================================================
DISCOVERY   → SerpAPI (primary, reliable) + Google Dorking (fills gaps / backup)
              - If SerpAPI credits are exhausted          -> Google Dorking takes over
              - If SerpAPI returns 0 results               -> Google Dorking takes over
              - If SerpAPI returns PARTIAL results          -> Google Dorking tops up the rest
              - If SerpAPI key is missing entirely          -> Google Dorking is the only source
EXTRACTION  → ScrapeGraphAI  (name, title, company from LinkedIn page)
ENRICHMENT  → Enrich Layer API (verified work email from LinkedIn URL)
              If credits exhausted → leads still saved without email
"""

import os
import re
import time
import json
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from googlesearch import search   # Free fallback / supplement

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ── API Keys (set as environment variables on Render) ─────────────────────────
ENRICHLAYER_KEY = os.environ.get("ENRICHLAYER_KEY", "")
SCRAPEGRAPH_KEY = os.environ.get("SCRAPEGRAPH_KEY", "")
SERPAPI_KEY     = os.environ.get("SERPAPI_KEY", "")

# ── Google Sheets ──────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_gsheet_client():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is missing.")
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    return gspread.authorize(creds)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — DISCOVERY: SerpAPI (primary) + Google Dorking (gap-filler / backup)
# ══════════════════════════════════════════════════════════════════════════════

def discover_profiles_serpapi(niche: str, location: str, count: int):
    """
    Uses SerpAPI to search Google for LinkedIn profiles.
    Returns (urls: list, status: str)
    status is one of: 'ok', 'no_key', 'credits_exhausted', 'no_results', 'error'
    """
    if not SERPAPI_KEY:
        log.warning("[SerpAPI] No API key set.")
        return [], "no_key"

    query = f'site:linkedin.com/in/ "{niche}" "{location}"'
    log.info(f"[SerpAPI] Query: {query}")

    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": count * 2,
                "engine": "google"
            },
            timeout=30
        )

        # Credit / quota / auth problems — these status codes mean "stop using SerpAPI"
        if resp.status_code in (401, 402, 429):
            log.warning(f"[SerpAPI] Credits exhausted or rate-limited (HTTP {resp.status_code}).")
            return [], "credits_exhausted"

        if resp.status_code != 200:
            log.error(f"[SerpAPI] Status {resp.status_code}: {resp.text[:200]}")
            return [], "error"

        data = resp.json()

        # SerpAPI sometimes returns HTTP 200 but with an "error" field
        # (e.g. "Your account has run out of searches for this month.")
        if "error" in data:
            err_msg = str(data.get("error", "")).lower()
            log.warning(f"[SerpAPI] API returned error field: {err_msg}")
            if any(p in err_msg for p in ["run out", "out of searches", "exceed", "quota", "credit"]):
                return [], "credits_exhausted"
            return [], "error"

        urls = []
        for result in data.get("organic_results", []):
            link = result.get("link", "")
            if "linkedin.com/in/" in link and link not in urls:
                urls.append(link)
                if len(urls) >= count:
                    break

        log.info(f"[SerpAPI] Discovered {len(urls)} LinkedIn URLs.")
        return urls, ("ok" if urls else "no_results")

    except Exception as e:
        log.error(f"[SerpAPI] Error: {e}")
        return [], "error"


def discover_profiles_dorking(niche: str, location: str, count: int):
    """
    Free fallback / supplement: direct Google search via googlesearch-python.
    Returns (urls: list, status: str)
    status is one of: 'ok', 'no_results', 'blocked', 'error'
    """
    if count <= 0:
        return [], "ok"

    query = f'site:linkedin.com/in/ "{niche}" "{location}"'
    log.info(f"[Google Dork] Query: {query}")

    urls = []
    status = "no_results"
    try:
        for url in search(query, num_results=count * 2, sleep_interval=4):
            if "linkedin.com/in/" in url and url not in urls:
                urls.append(url)
                if len(urls) >= count:
                    break
        status = "ok" if urls else "no_results"
    except Exception as e:
        err = str(e)
        log.error(f"[Google Dork] Error: {err}")
        status = "blocked" if ("429" in err or "Too Many Requests" in err) else "error"

    log.info(f"[Google Dork] Discovered {len(urls)} LinkedIn URLs. Status: {status}")
    return urls, status


def discover_profiles(niche: str, location: str, count: int):
    """
    Combines both discovery sources so neither one running dry stops the agent:

      • SerpAPI credits exhausted   → Google Dorking covers the full count
      • SerpAPI returns 0 results   → Google Dorking covers the full count
      • SerpAPI returns PARTIAL     → Google Dorking tops up the remainder
      • SerpAPI key missing         → Google Dorking is used alone
      • SerpAPI fully satisfies it  → Google Dorking is skipped entirely (saves free credits)

    Returns (urls: list, method_used: str) — method_used is e.g.
    "serpapi", "google_dorking", or "serpapi+google_dorking"
    """
    urls = []
    methods_used = []

    serp_urls, serp_status = discover_profiles_serpapi(niche, location, count)
    if serp_urls:
        urls.extend(serp_urls)
        methods_used.append("serpapi")
    log.info(f"[Discovery] SerpAPI status='{serp_status}', found={len(serp_urls)}")

    remaining = count - len(urls)
    if remaining > 0:
        log.info(f"[Discovery] Need {remaining} more lead(s) — trying Google Dorking...")
        dork_urls, dork_status = discover_profiles_dorking(niche, location, remaining)
        for u in dork_urls:
            if u not in urls:
                urls.append(u)
        if dork_urls:
            methods_used.append("google_dorking")
        log.info(f"[Discovery] Google Dorking status='{dork_status}', found={len(dork_urls)}")

    method = "+".join(methods_used) if methods_used else "none"
    return urls[:count], method


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — EXTRACTION: ScrapeGraphAI (Name, Title, Company)
# ══════════════════════════════════════════════════════════════════════════════

def extract_profile(url: str) -> dict:
    """Sends a LinkedIn URL to ScrapeGraphAI. Returns name, title, company."""
    log.info(f"[ScrapeGraph] Extracting: {url}")

    try:
        resp = requests.post(
            "https://api.scrapegraphai.com/v2/extract",
            headers={
                "Authorization": f"Bearer {SCRAPEGRAPH_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "url": url,
                "prompt": "Extract the person's full name, current job title, and current company name.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name":    {"type": "string"},
                        "title":   {"type": "string"},
                        "company": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json().get("result", resp.json())
            result["linkedin_url"] = url
            return result
        log.warning(f"[ScrapeGraph] {resp.status_code}")
    except Exception as e:
        log.error(f"[ScrapeGraph] {e}")
    return {}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — ENRICHMENT: Enrich Layer API (Work Email)
# ══════════════════════════════════════════════════════════════════════════════

def enrich_email(linkedin_url: str) -> tuple:
    """
    Calls Enrich Layer API to get the work email for a LinkedIn profile.
    Returns (email: str, credits_exhausted: bool).
    402 / 429 status = credits gone → flag to stop calling for rest of batch.
    """
    log.info(f"[EnrichLayer] Looking up email for: {linkedin_url}")

    try:
        resp = requests.post(
            "https://api.enrichlayer.com/v1/work-email",
            headers={
                "Authorization": f"Bearer {ENRICHLAYER_KEY}",
                "Content-Type": "application/json",
            },
            json={"linkedin_url": linkedin_url},
            timeout=15
        )
    except Exception as e:
        log.error(f"[EnrichLayer] {e}")
        return "", False   # Network error — skip this one but don't stop

    if resp.status_code in (402, 429):
        log.warning("[EnrichLayer] Credits exhausted — disabling enrichment for this run.")
        return "", True   # Signal to stop enrichment calls

    if resp.status_code == 200:
        data = resp.json()
        email = data.get("email") or data.get("work_email") or ""
        log.info(f"[EnrichLayer] Email: {email or 'not found'}")
        return email, False

    log.warning(f"[EnrichLayer] {resp.status_code}: {resp.text[:150]}")
    return "", False


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — WRITE TO GOOGLE SHEET
# ══════════════════════════════════════════════════════════════════════════════

def extract_sheet_id(url: str):
    match = re.search(r"/d/([a-zA-Z0-9\-_]+)", url)
    return match.group(1) if match else None


def write_to_sheet(sheet_url: str, rows: list) -> int:
    gc       = get_gsheet_client()
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("Invalid Google Sheet URL — could not find spreadsheet ID.")

    ws = gc.open_by_key(sheet_id).sheet1

    if not ws.get_all_values():
        ws.append_row(
            ["Name", "Job Title", "Company", "Work Email", "LinkedIn URL", "Email Status"],
            value_input_option="USER_ENTERED"
        )

    written = 0
    for lead in rows:
        email  = lead.get("email", "")
        status = "✅ Found" if email else "❌ Not found"
        ws.append_row([
            lead.get("name", ""),
            lead.get("title", ""),
            lead.get("company", ""),
            email,
            lead.get("linkedin_url", ""),
            status,
        ], value_input_option="USER_ENTERED")
        written += 1
        time.sleep(0.3)

    return written


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK — Called by GHL frontend
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/webhook", methods=["POST"])
def webhook():
    body      = request.get_json(force=True) or {}
    niche     = body.get("niche", "").strip()
    location  = body.get("location", "").strip()
    count     = max(1, min(int(body.get("count", 10)), 50))
    sheet_url = body.get("sheet_url", "").strip()

    if not all([niche, location, sheet_url]):
        return jsonify({"status": "error", "message": "niche, location, and sheet_url are all required."}), 400

    # ── 1. Discover LinkedIn URLs (SerpAPI + Google Dorking working together) ──
    profile_urls, discovery_method = discover_profiles(niche, location, count)
    if not profile_urls:
        return jsonify({
            "status": "error",
            "message": (
                "No LinkedIn profiles found from either source. This usually means: "
                "(1) no profiles really match this niche/location combo, "
                "(2) SerpAPI credits are exhausted AND Google blocked the backup search, or "
                "(3) your SerpAPI key is invalid/missing. "
                "Try a broader niche or different location, or check your SerpAPI dashboard for remaining credits."
            )
        }), 404

    # ── 2 & 3. Extract profile info + enrich email ──
    leads             = []
    credits_exhausted = False

    for url in profile_urls:
        profile = extract_profile(url)
        if not profile.get("name"):
            time.sleep(3)
            continue

        email = ""
        if not credits_exhausted:
            email, credits_exhausted = enrich_email(url)
            time.sleep(2)

        profile["email"] = email
        leads.append(profile)

        log.info(f"  ✓ {profile.get('name')} | {profile.get('title')} | Email: {email or 'N/A'}")
        time.sleep(5)   # Delay between LinkedIn scrapes to stay safe

    if not leads:
        return jsonify({
            "status": "error",
            "message": "Profiles found but data extraction failed. Check your ScrapeGraphAI key."
        }), 502

    # ── 4. Write to Google Sheet ──
    try:
        written = write_to_sheet(sheet_url, leads)
    except Exception as e:
        log.error(f"[Sheets] {e}")
        return jsonify({"status": "error", "message": f"Leads found but sheet write failed: {str(e)}"}), 500

    return jsonify({
        "status":            "success",
        "leads_found":       written,
        "discovery_method":  discovery_method,                         # "serpapi" / "google_dorking" / "serpapi+google_dorking"
        "credits_exhausted": credits_exhausted,                        # Enrich Layer credits
        "method":            f"{discovery_method} + scrapegraph + enrich_layer",  # kept for backward compatibility
        "message":           f"{written} leads written to your Google Sheet.",
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AI Lead Agent v3"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
