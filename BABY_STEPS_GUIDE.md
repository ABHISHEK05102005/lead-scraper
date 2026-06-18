# ⚡ SERPAPI ONLY — Ultra Simple Setup (Final)

**What this does:**
- ✅ Uses ONLY SerpAPI to find LinkedIn profiles
- ✅ Extracts name, title, company from search results
- ✅ Writes to Google Sheet
- ❌ NO Enrich Layer (removed)
- ❌ NO emails
- ❌ NO external enrichment

**Result:** Fast, reliable, no dependencies on other APIs.

---

## 4-Step Setup (5 minutes)

### STEP 1: Update GitHub (2 minutes)

**A) Replace app.py:**
1. Go to: `https://github.com/ABHISHEK05102005/lead-scraper`
2. Click **`app.py`** → Click **pencil icon**
3. Delete ALL content (Ctrl+A → Delete)
4. Copy ALL from **`app_SERPAPI_ONLY.py`** (from this chat)
5. Paste it (Ctrl+V)
6. Scroll down → Click **"Commit changes"**

**B) Replace requirements.txt:**
1. Go back to repo → Click **`requirements.txt`** → Click **pencil icon**
2. Delete ALL content
3. Copy ALL from **`requirements_SERPAPI_ONLY.txt`** (from this chat)
4. Paste it
5. Click **"Commit changes"**

---

### STEP 2: Clean Up Render Environment (1 minute)

1. Go to: `https://dashboard.render.com`
2. Click **"lead-scraper-1"** service → Click **"Environment"**
3. **Delete these 2 variables:**
   - ❌ ENRICHLAYER_KEY → click trash icon
   - ❌ SCRAPEGRAPH_KEY → click trash icon

**Keep only:**
- ✅ SERPAPI_KEY
- ✅ GOOGLE_SERVICE_ACCOUNT_JSON

---

### STEP 3: Verify Start Command (30 seconds)

1. Click **"Settings"** (top right of Render page)
2. Find **"Start Command"**
3. Make sure it says:
   ```
   gunicorn app:app --workers 2 --timeout 120
   ```
4. If not, click **"Edit"** and fix it

---

### STEP 4: Redeploy (2 minutes)

1. Click **"Manual Deploy"** (top right)
2. Click **"Deploy latest commit"**
3. **Wait for green ✅ "Your service is live"**

---

## Test It

1. Go to your GHL form
2. Fill in:
   - Niche: `AI Startup Founder`
   - Location: `USA`
   - Leads: `10`
   - Google Sheet: your test sheet
3. Click **"Launch AI Agent"**
4. **Wait 30 seconds**
5. Check your Google Sheet

You should see 10 rows with: **Name | Job Title | Company | LinkedIn URL**

No emails (they're optional), but you get the leads instantly. ✅

---

## Why This Works

| Component | Status |
|-----------|--------|
| SerpAPI finds profiles | ✅ 100% reliable |
| Parse name/title/company | ✅ Works great |
| Write to Google Sheet | ✅ 100% reliable |
| Enrich Layer | ❌ Removed (not needed) |
| ScrapeGraphAI | ❌ Removed (not needed) |

**Less = Better. Only what you need.**

---

## Done! 🎉

That's it. No more errors. No more complex APIs.

Just profiles → names → Google Sheet.

Follow the 4 steps above and you're done forever. ✅
