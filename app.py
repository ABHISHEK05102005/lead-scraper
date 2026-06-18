"""
AI Lead Generation Agent — WITH PAGINATION
============================================
DISCOVERY → SerpAPI with pagination (fetches multiple pages of Google results)
This is needed because Google only returns 10 results per page by default.
To get 50 leads, we need ~5 separate API calls (pages).
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

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_gsheet_client():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON env var is missing.")
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    return gspread.authorize(creds)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — DISCOVERY: SerpAPI WITH PAGINATION
# ══════════════════════════════════════════════════════════════════════════════

def parse_lead_from_result(result: dict) -> dict:
    """Extract name, title, company from a single SerpAPI organic_result."""
    link = result.get("link", "")
    title = result.get("title", "")
    snippet = result.get("snippet", "")

    name = ""
    job_title = ""
    company = ""

    if title:
        # Format usually: "Name - Title - Company | LinkedIn"
        # or "Name | Title | LinkedIn"
        clean_title = title.replace(" | LinkedIn", "").replace("| LinkedIn", "")

        if "|" in clean_title:
            parts = [p.strip() for p in clean_title.split("|")]
        else:
            parts = [p.strip() for p in clean_title.split(" - ")]

        name = parts[0] if len(parts) > 0 else ""
        job_title = parts[1] if len(parts) > 1 else ""
        company = parts[2] if len(parts) > 2 else ""

    # Try to get company from snippet if not found in title
    if not company and snippet:
        company = snippet.split("•")[0].split(".")[0].strip()[:80]

    return {
        "name": name,
        "title": job_title,
        "company": company,
        "linkedin_url": link,
    }


def discover_profiles(niche: str, location: str, count: int) -> list:
    """
    Uses SerpAPI with PAGINATION to fetch enough LinkedIn profiles.
    Google returns ~10 results per page, so we loop through multiple
    pages (using the 'start' parameter) until we have enough leads
    or run out of results.
    """
    if not SERPAPI_KEY:
        log.error("[SerpAPI] CRITICAL: SERPAPI_KEY is missing from environment.")
        return []

    query = f'site:linkedin.com/in/ "{niche}" "{location}"'
    log.info(f"[SerpAPI] Searching: {query} (target: {count} leads)")

    leads = []
    seen_urls = set()
    start = 0
    max_pages = 10  # Safety cap: max 10 pages = up to 100 results, 10 SerpAPI credits used
    page_num = 0

    while len(leads) < count and page_num < max_pages:
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": SERPAPI_KEY,
                    "engine": "google",
                    "start": start,   # <-- THIS IS THE PAGINATION KEY
                    "num": 10,
                },
                timeout=30
            )
        except Exception as e:
            log.error(f"[SerpAPI] Exception on page {page_num}: {e}")
            break

        if resp.status_code != 200:
            log.error(f"[SerpAPI] Page {page_num} failed: {resp.status_code} - {resp.text[:200]}")
            break

        data = resp.json()
        organic_results = data.get("organic_results", [])

        if not organic_results:
            log.info(f"[SerpAPI] No more results at page {page_num}. Stopping.")
            break

        new_this_page = 0
        for result in organic_results:
            link = result.get("link", "")
            if "linkedin.com/in/" not in link:
                continue
            if link in seen_urls:
                continue

            lead = parse_lead_from_result(result)
            if lead["name"]:
                leads.append(lead)
                seen_urls.add(link)
                new_this_page += 1
                log.info(f"  ✓ [{len(leads)}/{count}] {lead['name']} | {lead['title']} | {lead['company']}")

            if len(leads) >= count:
                break

        log.info(f"[SerpAPI] Page {page_num} done. +{new_this_page} new leads. Total: {len(leads)}")

        if new_this_page == 0:
            # No new LinkedIn results on this page — likely exhausted relevant results
            log.info("[SerpAPI] No new LinkedIn URLs found on this page. Stopping pagination.")
            break

        start += 10
        page_num += 1
        time.sleep(1)  # Be gentle between page requests

    log.info(f"[SerpAPI] Final: {len(leads)} leads found across {page_num + 1} page(s).")
    return leads


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — WRITE TO GOOGLE SHEET (optional)
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
# WEBHOOK
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json(force=True) or {}
    niche = body.get("niche", "").strip()
    location = body.get("location", "").strip()
    count = max(1, min(int(body.get("count", 10)), 50))
    sheet_url = body.get("sheet_url", "").strip()

    if not all([niche, location]):
        return jsonify({"status": "error", "message": "niche and location are required."}), 400

    if not SERPAPI_KEY:
        return jsonify({"status": "error", "message": "SERPAPI_KEY not set in Render environment."}), 500

    leads = discover_profiles(niche, location, count)
    if not leads:
        return jsonify({
            "status": "error",
            "message": f"No profiles found for '{niche}' in '{location}'. Try broader keywords."
        }), 404

    response_data = {
        "status": "success",
        "leads_found": len(leads),
        "leads": leads,
        "message": f"✅ {len(leads)} leads found via SerpAPI."
    }

    if sheet_url:
        try:
            written = write_to_sheet(sheet_url, leads)
            response_data["message"] = f"✅ {written} leads found and written to your sheet."
            response_data["sheet_written"] = written
        except Exception as e:
            log.error(f"[Sheets] {e}")
            response_data["sheet_error"] = str(e)

    return jsonify(response_data)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AI Lead Agent (SerpAPI + Pagination)"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
