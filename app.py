"""
AI Lead Generation Agent — Backend (Strict SerpAPI Version)
===========================================================
DISCOVERY   → SerpAPI Only (Legitimate Google search from data centers)
EXTRACTION  → ScrapeGraphAI (name, title, company from LinkedIn page)
ENRICHMENT  → Enrich Layer API (verified work email from LinkedIn URL)
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ── API Keys (set as environment variables on Render) ─────────────────────────
ENRICHLAYER_KEY = os.environ.get("ENRICHLAYER_KEY", "")
SCRAPEGRAPH_KEY = os.environ.get("SCRAPEGRAPH_KEY", "")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

# ── Google Sheets ──────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_gsheet_client():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is missing.")
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    return gspread.authorize(creds)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — DISCOVERY: SerpAPI Only
# ══════════════════════════════════════════════════════════════════════════════

def discover_profiles_serpapi(niche: str, location: str, count: int) -> list:
    """
    Uses SerpAPI to search Google for LinkedIn profiles.
    Works reliably from data centers.
    """
    if not SERPAPI_KEY:
        log.warning("[SerpAPI] No API key set.")
        return []

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

        if resp.status_code == 200:
            data = resp.json()
            urls = []
            
            # Extract LinkedIn URLs from organic results
            if "organic_results" in data:
                for result in data["organic_results"]:
                    link = result.get("link", "")
                    if "linkedin.com/in/" in link and link not in urls:
                        urls.append(link)
                        if len(urls) >= count:
                            break
            
            log.info(f"[SerpAPI] Discovered {len(urls)} LinkedIn URLs.")
            return urls
        else:
            log.error(f"[SerpAPI] Status {resp.status_code}: {resp.text[:200]}")
            return []

    except Exception as e:
        log.error(f"[SerpAPI] Error: {e}")
        return []


def discover_profiles(niche: str, location: str, count: int) -> tuple:
    """
    Main discovery function. Strictly processes requests via SerpAPI.
    Returns (urls: list, method_used: str)
    """
    if not SERPAPI_KEY:
        log.error("[Discovery] CRITICAL: SERPAPI_KEY env var is missing.")
        return [], "none"

    urls = discover_profiles_serpapi(niche, location, count)
    if urls:
        return urls, "serpapi"
    
    # Return empty if SerpAPI failed or found nothing
    return [], "none"


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
        return "", False

    if resp.status_code in (402, 429):
        log.warning("[EnrichLayer] Credits exhausted — disabling enrichment for this run.")
        return "", True

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

    # ── 1. Discover LinkedIn URLs via SerpAPI ──
    profile_urls, discovery_method = discover_profiles(niche, location, count)
    if not profile_urls:
        return jsonify({
            "status": "error",
            "message": "No LinkedIn profiles found. Ensure your SerpAPI key is correctly set up in Render and has remaining search credits."
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
            "message": "Profiles discovered via SerpAPI, but ScrapeGraphAI data extraction failed. Please check your ScrapeGraphAI key."
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
        "credits_exhausted": credits_exhausted,
        "method":            f"{discovery_method} + scrapegraph + enrich_layer",
        "message":           f"{written} leads successfully processed and written via SerpAPI configuration.",
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AI Lead Agent v2 (Strict SerpAPI)"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
