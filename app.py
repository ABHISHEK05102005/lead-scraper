"""
AI Lead Generation Agent — FLEXIBLE VERSION
============================================
DISCOVERY ONLY → SerpAPI (finds LinkedIn profiles + basic data)

If Google Sheet URL provided → writes to sheet
If NO Google Sheet URL → returns data as JSON for frontend display (CSV/table format)
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

def discover_profiles(niche: str, location: str, count: int) -> list:
    """
    Uses SerpAPI to search Google for LinkedIn profiles.
    Extracts name, title, company from search results.
    Returns list of leads with data extracted from SerpAPI results.
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
            leads = []
            
            # Extract LinkedIn URLs + data from search results
            if "organic_results" in data:
                for result in data["organic_results"]:
                    link = result.get("link", "")
                    if "linkedin.com/in/" not in link:
                        continue
                    
                    title = result.get("title", "")  # "John Doe | Senior Engineer | LinkedIn"
                    snippet = result.get("snippet", "")  # "Acme Corp • 5 years"
                    
                    # Parse name from title
                    name = ""
                    job_title = ""
                    if title:
                        parts = title.split("|")
                        name = parts[0].strip() if len(parts) > 0 else ""
                        job_title = parts[1].strip() if len(parts) > 1 else ""
                        job_title = job_title.split("LinkedIn")[0].strip()  # Remove "LinkedIn" suffix
                    
                    # Parse company from snippet
                    company = ""
                    if snippet:
                        company = snippet.split("•")[0].strip()
                    
                    if name:  # Only add if we got a name
                        leads.append({
                            "name": name,
                            "title": job_title,
                            "company": company,
                            "linkedin_url": link,
                        })
                        log.info(f"  ✓ Found: {name} | {job_title} | {company}")
                    
                    if len(leads) >= count:
                        break
            
            log.info(f"[SerpAPI] Extracted {len(leads)} leads from search results.")
            return leads
        else:
            log.error(f"[SerpAPI] Failed: {resp.status_code} - {resp.text[:200]}")
            return []

    except Exception as e:
        log.error(f"[SerpAPI] Exception: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — OPTIONAL: WRITE TO GOOGLE SHEET (if URL provided)
# ══════════════════════════════════════════════════════════════════════════════

def extract_sheet_id(url: str):
    match = re.search(r"/d/([a-zA-Z0-9\-_]+)", url)
    return match.group(1) if match else None


def write_to_sheet(sheet_url: str, rows: list) -> int:
    """Returns number of rows written to sheet. Raises exception if fails."""
    gc = get_gsheet_client()
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("Invalid Google Sheet URL.")

    ws = gc.open_by_key(sheet_id).sheet1

    # Add header if empty
    if not ws.get_all_values():
        ws.append_row(
            ["Name", "Job Title", "Company", "LinkedIn URL"],
            value_input_option="USER_ENTERED"
        )

    written = 0
    for lead in rows:
        ws.append_row([
            lead.get("name", ""),
            lead.get("title", ""),
            lead.get("company", ""),
            lead.get("linkedin_url", ""),
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
    sheet_url = body.get("sheet_url", "").strip()  # NOW OPTIONAL

    if not niche or not location:
        return jsonify({
            "status": "error",
            "message": "niche and location are required."
        }), 400

    if not SERPAPI_KEY:
        return jsonify({
            "status": "error",
            "message": "SERPAPI_KEY not set. Check Render environment variables."
        }), 500

    # ── 1. Discover profiles via SerpAPI ──
    leads = discover_profiles(niche, location, count)
    if not leads:
        return jsonify({
            "status": "error",
            "message": f"No profiles found for '{niche}' in '{location}'. Try different keywords or check your SerpAPI credits."
        }), 404

    # ── 2. If Google Sheet URL provided → write to sheet ──
    if sheet_url:
        try:
            written = write_to_sheet(sheet_url, leads)
            return jsonify({
                "status": "success",
                "leads_found": written,
                "destination": "google_sheet",
                "message": f"✅ {written} leads written to your Google Sheet."
            })
        except Exception as e:
            log.error(f"[Sheets] {e}")
            return jsonify({
                "status": "error",
                "message": f"Sheet write failed: {str(e)}. Make sure sheet is shared with service account."
            }), 500
    
    # ── 3. If NO Google Sheet URL → return data for frontend display ──
    else:
        log.info(f"[Webhook] No sheet URL provided. Returning {len(leads)} leads as JSON for frontend.")
        return jsonify({
            "status": "success",
            "leads_found": len(leads),
            "destination": "frontend_display",
            "leads": leads,  # ← Return the actual lead data
            "message": f"✅ {len(leads)} leads found! View below or download as CSV."
        })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AI Lead Agent (SerpAPI Only)"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
