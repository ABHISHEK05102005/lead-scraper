# 🍼 BABY STEP DEPLOYMENT GUIDE
## AI Lead Agent — From Zero to Live

**Your API key:** `NNlLhg06FnpEaqSlUtqP4g` (Enrich Layer)
**Google Dorking:** FREE — no key needed, uses Google search directly

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART A — Get ScrapeGraphAI Key
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Step 1.**  Open a new browser tab → go to:
```
https://scrapegraphai.com
```

**Step 2.** Click the **"Get Started"** or **"Sign Up"** button (top right of the page)

**Step 3.** Enter your email and create a password → Click **"Create Account"**

**Step 4.** Check your email inbox → click the verification link they send you

**Step 5.** After login, you'll land on a dashboard. Look for **"API Key"** or **"API Token"** in the left sidebar

**Step 6.** Click it → you'll see a long string like `sg-xxxxxxxxxxxxxxxx`

**Step 7.** Click the **Copy** button next to the key

**Step 8.** Open Notepad on your computer and paste it like this:
```
SCRAPEGRAPH_KEY = sg-xxxxxxxxxxxxxxxx
```
Save the Notepad file as `mykeys.txt` on your Desktop so you don't lose it.

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART B — Create Google Service Account
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This lets the agent write to ANY Google Sheet.

**Step 1.** Go to:
```
https://console.cloud.google.com
```

**Step 2.** Sign in with your Google/Gmail account

**Step 3.** At the very top of the page, you'll see a blue dropdown that says **"Select a project"** → Click it

**Step 4.** A popup opens → Click **"NEW PROJECT"** button (top right of that popup)

**Step 5.** In the **"Project name"** box type: `lead-agent`  
→ Leave everything else as-is → Click **"CREATE"**

**Step 6.** Wait 10 seconds → click the **"Select a project"** dropdown again → click **"lead-agent"**

**Step 7.** At the top of the page, you'll see a search bar. Type:
```
Google Sheets API
```
→ Press Enter → Click the result that says **"Google Sheets API"**

**Step 8.** Click the big blue **"ENABLE"** button

**Step 9.** Now in the left sidebar, click **"IAM & Admin"** → then click **"Service Accounts"**

**Step 10.** Click **"+ CREATE SERVICE ACCOUNT"** button at the top

**Step 11.** In the **"Service account name"** box type: `lead-agent-bot`  
→ Click **"CREATE AND CONTINUE"**

**Step 12.** On the next screen (Grant access) → click **"CONTINUE"** (skip this step)

**Step 13.** On the next screen → click **"DONE"**

**Step 14.** You'll now see `lead-agent-bot@lead-agent-xxxxx.iam.gserviceaccount.com` in a list  
→ Click on that email address

**Step 15.** Click the **"KEYS"** tab at the top

**Step 16.** Click **"ADD KEY"** → Click **"Create new key"**

**Step 17.** Select **"JSON"** → Click **"CREATE"**

**Step 18.** A file downloads automatically to your computer (something like `lead-agent-xxxxx.json`)

**Step 19.** Find that file on your computer → Right-click it → Open with **Notepad**

**Step 20.** Press `Ctrl + A` to select ALL the text → Press `Ctrl + C` to copy it

**Step 21.** Open your `mykeys.txt` file on Desktop → paste it like:
```
GOOGLE_SERVICE_ACCOUNT_JSON = { "type": "service_account", ...entire thing... }
```

**Step 22.** Also find the line that says `"client_email":` in that JSON  
→ Copy just that email address (looks like `lead-agent-bot@lead-agent-xxxxx.iam.gserviceaccount.com`)  
→ Paste it in `mykeys.txt` too:
```
SERVICE_ACCOUNT_EMAIL = lead-agent-bot@lead-agent-xxxxx.iam.gserviceaccount.com
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART C — Upload Code to GitHub
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Step 1.** Go to:
```
https://github.com
```

**Step 2.** Click **"Sign up"** (top right) → create a free account with your email

**Step 3.** After logging in, click the **"+"** icon in the top right corner → Click **"New repository"**

**Step 4.** In the **"Repository name"** box type: `lead-agent-backend`

**Step 5.** Make sure **"Public"** is selected

**Step 6.** Tick the checkbox that says **"Add a README file"**

**Step 7.** Click the green **"Create repository"** button

**Step 8.** You'll see your new repo page. Click **"uploading an existing file"** link  
(it's a small link in the middle of the page, in the sentence "...or uploading an existing file")

**Step 9.** A file upload area appears. Drag and drop these 2 files from your computer:
- `app.py`
- `requirements.txt`

(These are the files you downloaded from this chat)

**Step 10.** Scroll down → click the green **"Commit changes"** button

**Step 11.** Wait 5 seconds → you'll see both files listed in your repo ✅

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART D — Deploy Backend on Render
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Step 1.** Go to:
```
https://render.com
```

**Step 2.** Click **"Get Started for Free"** → Sign up using your **GitHub account** (click "Continue with GitHub")

**Step 3.** It will ask permission to access GitHub → Click **"Authorize Render"**

**Step 4.** On the Render dashboard, click the **"New +"** button (top right)  
→ Click **"Web Service"**

**Step 5.** Under "Connect a repository", you'll see your GitHub repos  
→ Find **"lead-agent-backend"** and click **"Connect"**

**Step 6.** Fill in these settings on the next screen:

| Field | What to type |
|-------|-------------|
| Name | `ai-lead-agent` |
| Region | Choose the closest to you |
| Branch | `main` |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --workers 2 --timeout 120` |

**Step 7.** Scroll down to the **"Environment Variables"** section  
→ Click **"Add Environment Variable"** for each of these 3 items:

**Variable 1:**
- Key box: `ENRICHLAYER_KEY`
- Value box: `NNlLhg06FnpEaqSlUtqP4g`

**Variable 2:**
- Key box: `SCRAPEGRAPH_KEY`  
- Value box: *(paste your ScrapeGraphAI key from mykeys.txt)*

**Variable 3:**
- Key box: `GOOGLE_SERVICE_ACCOUNT_JSON`
- Value box: *(paste the ENTIRE JSON content from your service account file — the whole thing from `{` to `}`)*

**Step 8.** Scroll down → select **"Free"** plan

**Step 9.** Click the big **"Create Web Service"** button

**Step 10.** Render will now build and deploy (takes 2-4 minutes). You'll see logs scrolling.  
Wait until you see: **"Your service is live"** ✅

**Step 11.** At the top of the Render page, copy your live URL — it looks like:
```
https://ai-lead-agent-xxxx.onrender.com
```
→ Paste this URL into your `mykeys.txt` file:
```
BACKEND_URL = https://ai-lead-agent-xxxx.onrender.com
```

**Step 12.** Test it: Open a new browser tab → type your URL + `/health`:
```
https://ai-lead-agent-xxxx.onrender.com/health
```
You should see: `{"service": "AI Lead Agent v2", "status": "ok"}` ✅  
If you see this, your backend is working perfectly!

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART E — Add Form to GoHighLevel (GHL)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Step 1.** Log in to your GHL account at:
```
https://app.gohighlevel.com
```

**Step 2.** In the left sidebar, click **"Sites"**

**Step 3.** Click **"Funnels"** OR **"Websites"** — whichever one you want to add the agent to

**Step 4.** Click on your funnel/website to open it

**Step 5.** Click **"Edit"** button to open the page builder

**Step 6.** In the builder, look at the left panel for elements  
→ Scroll down until you find an element called **"Custom JS/HTML"** or **"HTML"**

**Step 7.** Drag that element and drop it onto your page where you want the agent form to appear

**Step 8.** Click on the element you just dropped → look for a button that says **"Edit Code"** or shows `< >` icon → Click it

**Step 9.** A code editor box opens. Select all existing text inside it and delete it.

**Step 10.** Open the `ghl_frontend.html` file you downloaded from this chat  
→ Select all (Ctrl+A) → Copy (Ctrl+C)

**Step 11.** Go back to GHL → Click inside the code editor → Paste (Ctrl+V)

**Step 12.** Now find this line in the pasted code (it's near the bottom, inside the `<script>` tag):
```javascript
const BACKEND_URL = "https://YOUR-APP.onrender.com";
```
→ Delete `https://YOUR-APP.onrender.com`  
→ Type your actual Render URL from `mykeys.txt` (e.g., `https://ai-lead-agent-xxxx.onrender.com`)

**Step 13.** Click **"Save"** or **"Apply"** button in the code editor

**Step 14.** Click the **"Save"** button for the whole page (usually top right of builder)

**Step 15.** Click **"Publish"** to make the page live

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART F — Set Up Your Google Sheet
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do this EVERY TIME a user wants to use a new Google Sheet.

**Step 1.** Open the Google Sheet the user wants to fill (or create a new one at sheets.google.com)

**Step 2.** Click the **"Share"** button (green button, top right corner)

**Step 3.** In the box that says "Add people and groups", paste your service account email:
```
lead-agent-bot@lead-agent-xxxxx.iam.gserviceaccount.com
```
*(This is what you saved in mykeys.txt as SERVICE_ACCOUNT_EMAIL)*

**Step 4.** Make sure the dropdown next to it says **"Editor"** (not Viewer)

**Step 5.** Click **"Send"**  
→ You may see a warning: "This person may not have a Google account" → click **"Share anyway"** — that's fine!

**Step 6.** Copy the URL of the Google Sheet from your browser address bar:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit
```

**Step 7.** Paste this URL into the **Google Sheet URL** field in your GHL page form

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART G — Run Your First Test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Step 1.** Open your published GHL page

**Step 2.** Fill in the form:
- **Target Niche:** `Digital Marketing Agency Owner`
- **Target Location:** `Miami, Florida`
- **Number of Leads:** `5`
- **Google Sheet URL:** *(paste the sheet URL from Part F)*

**Step 3.** Click **"Launch AI Agent"**

**Step 4.** Wait 60–90 seconds (it takes time to search Google + scrape 5 profiles)

**Step 5.** You'll see a green success message showing how many leads were written

**Step 6.** Open your Google Sheet — you should see rows like this:

| Name | Job Title | Company | Work Email | LinkedIn URL | Email Status |
|------|-----------|---------|-----------|--------------|-------------|
| John Smith | Founder | Growth Co | john@growth.co | linkedin.com/in/... | ✅ Found |
| Jane Doe | CEO | Miami Digital | | linkedin.com/in/... | ❌ Not found |

---

# ⚠️ IMPORTANT NOTES

**About Enrich Layer credits:**
- You have 100 credits (13 days left on trial)
- Each credit = 1 email lookup
- If credits run out mid-batch, remaining leads are saved WITHOUT email (but name/title/company still saved)
- Buy more credits at: https://enrichlayer.com → Billing → Buy Credits

**About Google Dorking:**
- Completely FREE — uses Google search results directly
- Has a built-in 3-5 second delay between searches to avoid blocks
- If Google temporarily blocks (rare), wait 1-2 hours and try again

**About Render free tier:**
- Server "sleeps" after 15 minutes of no use
- First request after sleeping takes ~30 seconds to wake up — that's normal
- The GHL form will show "Agent Running..." while it wakes up — just wait

**Sheet not updating?**
→ Make sure you shared the sheet with the service account email (Part F)  
→ The email must be set to "Editor" not "Viewer"
