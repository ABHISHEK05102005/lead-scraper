"""
AI Lead Generation Agent — PRODUCTION VERSION
==============================================
DISCOVERY   → SerpAPI only (finds LinkedIn profiles)
ENRICHMENT  → Enrich Layer API (gets verified emails from LinkedIn URLs)

NO ScrapeGraphAI. It's replaced by Enrich Layer which also extracts company data.
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
# STEP 1 — DISCOVERY: SerpAPI Only (NO fallbacks, NO googlesearch)
# ══════════════════════════════════════════════════════════════════════════════

def discover_profiles(niche: str, location: str, count: int) -> list:
    """
    Uses SerpAPI to search Google for LinkedIn profiles.
    Returns list of tuples: (url, name_from_title, company_from_snippet)
    """
    if not SERPAPI_KEY:
        log.error("[SerpAPI] CRITICAL: SERPAPI_KEY is missing from environment.")
        return []

    query = f'site:linkedin.com/in/ "{niche}" "{location}"'
    log.info(f"[SerpAPI] Searching: {query}")

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
            profiles = []
            
            # Extract LinkedIn URLs + basic info from search results
            if "organic_results" in data:
                for result in data["organic_results"]:
                    link = result.get("link", "")
                    if "linkedin.com/in/" in link:
                        title = result.get("title", "")  # e.g., "John Doe | Senior Engineer | LinkedIn"
                        snippet = result.get("snippet", "")  # e.g., "Acme Corp • 5 years"
                        
                        profiles.append({
                            "url": link,
                            "title": title,
                            "snippet": snippet
                        })
                        
                        if len(profiles) >= count:
                            break
            
            log.info(f"[SerpAPI] Found {len(profiles)} profiles.")
            return profiles
        else:
            log.error(f"[SerpAPI] Failed: {resp.status_code} - {resp.text[:200]}")
            return []

    except Exception as e:
        log.error(f"[SerpAPI] Exception: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — ENRICHMENT: Enrich Layer API (Email + Company Data)
# ══════════════════════════════════════════════════════════════════════════════

def enrich_profile(linkedin_url: str, title: str = "", snippet: str = "") -> dict:
    """
    Calls Enrich Layer API with LinkedIn URL.
    Returns: {name, title, company, email, linkedin_url, credits_exhausted}
    
    Enrich Layer returns:
    - email (verified work email)
    - full_name
    - current_company
    - job_title
    """
    log.info(f"[EnrichLayer] Enriching: {linkedin_url}")

    try:
        resp = requests.post(
            "https://api.enrichlayer.com/v1/work-email",
            headers={
                "Authorization": f"Bearer {ENRICHLAYER_KEY}",
                "Content-Type": "application/json",
            },
            json={"linkedin_url": linkedin_url},
            timeout=20
        )
    except Exception as e:
        log.error(f"[EnrichLayer] Network error: {e}")
        return None

    # 402 / 429 = Credits exhausted
    if resp.status_code in (402, 429):
        log.warning("[EnrichLayer] Credits exhausted.")
        return {"credits_exhausted": True}

    if resp.status_code == 200:
        data = resp.json()
        
        # Extract data from Enrich Layer response
        name     = data.get("full_name") or ""
        email    = data.get("email") or data.get("work_email") or ""
        company  = data.get("current_company") or ""
        job_title = data.get("job_title") or ""
        
        # Fallback to parse title/snippet if Enrich Layer didn't return data
        if not name and title:
            # Try to extract name from title: "John Doe | Senior Engineer"
            name = title.split("|")[0].strip() if "|" in title else title.split("•")[0].strip()
        
        if not job_title and title:
            # Extract job title from title
            parts = title.split("|")
            if len(parts) > 1:
                job_title = parts[1].strip().split("•")[0].strip()
        
        if not company and snippet:
            # Extract company from snippet: "Acme Corp • 5 years"
            company = snippet.split("•")[0].strip()
        
        log.info(f"[EnrichLayer] Result: {name} | {job_title} | {company} | Email: {email or 'N/A'}")
        
        return {
            "name": name,
            "title": job_title,
            "company": company,
            "email": email,
            "linkedin_url": linkedin_url,
            "credits_exhausted": False
        }
    
    log.warning(f"[EnrichLayer] {resp.status_code}: {resp.text[:150]}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — WRITE TO GOOGLE SHEET
# ══════════════════════════════════════════════════════════════════════════════

def extract_sheet_id(url: str):
    match = re.search(r"/d/([a-zA-Z0-9\-_]+)", url)
    return match.group(1) if match else None


def write_to_sheet(sheet_url: str, rows: list) -> int:
    gc = get_gsheet_client()
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("Invalid Google Sheet URL.")

    ws = gc.open_by_key(sheet_id).sheet1

    # Add header if empty
    if not ws.get_all_values():
        ws.append_row(
            ["Name", "Job Title", "Company", "Work Email", "LinkedIn URL", "Email Status"],
            value_input_option="USER_ENTERED"
        )

    written = 0
    for lead in rows:
        email = lead.get("email", "")
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
        time.sleep(0.2)

    return written


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK — Main endpoint
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json(force=True) or {}
    niche = body.get("niche", "").strip()
    location = body.get("location", "").strip()
    count = max(1, min(int(body.get("count", 10)), 50))
    sheet_url = body.get("sheet_url", "").strip()

    if not all([niche, location, sheet_url]):
        return jsonify({
            "status": "error",
            "message": "niche, location, and sheet_url are required."
        }), 400

    if not SERPAPI_KEY:
        return jsonify({
            "status": "error",
            "message": "SERPAPI_KEY not set. Check Render environment variables."
        }), 500

    # ── 1. Discover profiles via SerpAPI ──
    profiles = discover_profiles(niche, location, count)
    if not profiles:
        return jsonify({
            "status": "error",
            "message": f"No profiles found for '{niche}' in '{location}'. Try different keywords."
        }), 404

    # ── 2. Enrich each profile via Enrich Layer ──
    leads = []
    credits_exhausted = False

    for profile in profiles:
        enriched = enrich_profile(
            profile["url"],
            profile.get("title", ""),
            profile.get("snippet", "")
        )
        
        if not enriched:
            time.sleep(3)
            continue
        
        if enriched.get("credits_exhausted"):
            log.warning("[Webhook] Enrich Layer credits exhausted. Stopping enrichment.")
            credits_exhausted = True
            break
        
        leads.append(enriched)
        log.info(f"  ✓ Added: {enriched.get('name')} | {enriched.get('title')} | {enriched.get('company')}")
        time.sleep(3)  # Rate limit

    if not leads:
        return jsonify({
            "status": "error",
            "message": "Profiles found but enrichment returned no data. Check Enrich Layer key and credits."
        }), 502

    # ── 3. Write to Google Sheet ──
    try:
        written = write_to_sheet(sheet_url, leads)
    except Exception as e:
        log.error(f"[Sheets] {e}")
        return jsonify({
            "status": "error",
            "message": f"Sheet write failed: {str(e)}"
        }), 500

    return jsonify({
        "status": "success",
        "leads_found": written,
        "credits_exhausted": credits_exhausted,
        "message": f"✅ {written} leads found via SerpAPI + Enrich Layer and written to your sheet."
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AI Lead Agent (SerpAPI + EnrichLayer)"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
