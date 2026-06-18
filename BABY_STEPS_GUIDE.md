# 🔥 FLEXIBLE VERSION — Google Sheet Optional

**What's new:**
- ✅ **Google Sheet URL is now OPTIONAL**
- ✅ If you don't provide a sheet URL → leads display in a table on the website
- ✅ **Download leads as CSV** directly from the table
- ✅ If you DO provide a sheet URL → leads auto-write to Google Sheet (old behavior)

**Best of both worlds!**

---

## 3-Step Setup (5 minutes)

### STEP 1: Update GitHub (2 minutes)

**A) Replace app.py:**
1. Go to: `https://github.com/ABHISHEK05102005/lead-scraper`
2. Click **`app.py`** → Click **pencil icon**
3. Delete ALL content
4. Copy ALL from **`app_FLEXIBLE.py`** (from this chat)
5. Paste it
6. Click **"Commit changes"**

**B) Replace GHL frontend HTML:**
1. Go back to your GHL website
2. Find the **Custom HTML/JS element** with your agent form
3. Click **"Edit Code"** / **`<>` icon**
4. Delete all the old HTML/CSS/JS
5. Copy ALL from **`ghl_frontend_FLEXIBLE.html`** (from this chat)
6. Paste it
7. Click **"Save"** or **"Apply"**
8. Click **"Publish"** (top right of GHL)

**Note:** Keep `requirements.txt` the same (no changes needed)

---

### STEP 2: Redeploy on Render (2 minutes)

1. Go to: `https://dashboard.render.com`
2. Click **"lead-scraper-1"** service
3. Click **"Manual Deploy"** (top right)
4. Click **"Deploy latest commit"**
5. Wait for green ✅ **"Your service is live"**

---

### STEP 3: Test It (1 minute)

**Test WITHOUT Google Sheet (display on website):**
1. Go to your GHL page
2. Fill in:
   - Niche: `AI Startup Founder`
   - Location: `USA`
   - Leads: `5`
   - **Leave Google Sheet URL BLANK** ← Important!
3. Click **"Launch AI Agent"**
4. Wait 30 seconds
5. You'll see a **table with 5 leads** appear on the website ✅
6. Click **"Download CSV"** to save as Excel/CSV file

**Test WITH Google Sheet (auto-write):**
1. Same as above, but **paste a Google Sheet URL** in the last field
2. Make sure the sheet is **shared with your service account email**
3. Click **"Launch AI Agent"**
4. Leads will be written to your sheet (old behavior) ✅

---

## How It Works

```
User clicks "Launch AI Agent"
  ↓
Backend discovers leads via SerpAPI
  ↓
Is Google Sheet URL provided?
  ├─ YES → Write to Google Sheet (returns success message)
  └─ NO  → Return leads as JSON to frontend (displays table + CSV download)
```

**No Google Sheet needed anymore!** Just use the table on the website.

---

## Features

| Feature | Status |
|---------|--------|
| **View leads in table** | ✅ Works (no sheet needed) |
| **Download as CSV** | ✅ Works (one click) |
| **Auto-write to Google Sheet** | ✅ Works (if URL provided) |
| **LinkedIn profile links** | ✅ Clickable links to each profile |
| **No external enrichment** | ✅ SerpAPI only (fast & reliable) |

---

## Troubleshooting

**Seeing error "Cannot reach backend"?**
→ Wait 2 more minutes. Render deploy still in progress.

**Table not showing?**
→ Make sure you left the Google Sheet URL blank.

**Leads not showing in table?**
→ Check backend logs on Render. Make sure SerpAPI key is set.

**Want to write to Google Sheet later?**
→ Just fill in the sheet URL and run again. Same leads will be saved to the sheet.

---

## Done! 🚀

Now you can:
1. **See results immediately** on the website (no setup required)
2. **Download as CSV** with one click
3. **Optionally save to Google Sheet** if you want

That's it! Start scraping leads now! 🎉
