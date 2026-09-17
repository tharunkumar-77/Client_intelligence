# Google Cloud Setup — One-Time Walkthrough

This covers the exact steps to create a Google Cloud project, service account, and enable the APIs needed for Phase 1 (Sheets sync) and Phase 5+ (Calendar, Meet).

---

## Step 1 — Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown (top-left) → **New Project**
3. Name it `client-intelligence` → **Create**
4. Wait ~30 seconds, then select the new project from the dropdown

---

## Step 2 — Enable the Required APIs

In your new project, go to **APIs & Services → Library** and enable these one by one:

| API | When needed |
|-----|-------------|
| **Google Sheets API** | Phase 1 — client sync |
| **Google Drive API** | Phase 1 — required alongside Sheets |
| **Google Calendar API** | Phase 5 — appointment scheduling |
| **Google Meet API** | Phase 5 — meet link generation |

Search for each by name → click it → **Enable**.

---

## Step 3 — Create a Service Account

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → Service Account**
3. Name: `ci-service-account` → **Create and Continue**
4. Skip role assignment for now → **Done**
5. Click the service account email that appears in the list
6. Go to **Keys** tab → **Add Key → Create New Key → JSON**
7. A JSON file downloads automatically — **keep this secure**

---

## Step 4 — Add the Service Account Key to .env

Open the downloaded JSON file in a text editor. Copy the entire content (it's one JSON object).

In your `.env` file, paste it as a single line for `GOOGLE_SERVICE_ACCOUNT_JSON`:

```bash
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...all on one line..."}
```

**Tip:** On macOS/Linux you can do:
```bash
GOOGLE_SERVICE_ACCOUNT_JSON=$(cat ~/Downloads/ci-service-account-xxxx.json | tr -d '\n')
```

On Windows PowerShell:
```powershell
$env:GOOGLE_SERVICE_ACCOUNT_JSON = (Get-Content "~\Downloads\ci-service-account-xxxx.json" -Raw).Replace("`n","")
```

---

## Step 5 — Create and Share the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) → create a new spreadsheet
2. Name it `Client Intelligence — [Your Name]`
3. Create a sheet (tab) named exactly: **`Clients`**
4. Copy the spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
   ```
5. Add it to `.env`:
   ```
   SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
   ```
6. Click **Share** in the spreadsheet → enter the service account email (from Step 3) → give it **Editor** access

---

## Step 6 — Verify the Connection

Start Flask and submit a test intake form:

```bash
python run.py
```

Open `http://localhost:5000/intake/form`, fill it in, and submit. Check:
- Your Postgres `clients` table has a new row
- The Google Sheet `Clients` tab has the same client as a new row

If the sheet doesn't update, check the Flask logs — sheets sync failures are non-fatal and logged as warnings.

---

## Phase 5 Addition — Calendar & Meet (when ready)

When you reach Phase 5, you'll need to:
1. Enable **Google Calendar API** in the same project (Step 2)
2. Go back to the service account → **Details** tab → note the service account email
3. Share your Google Calendar with the service account email (same as sharing a file)
4. Add `https://www.googleapis.com/auth/calendar` to the service account scopes in `sheets_sync.py` (or a new `calendar_service.py`)

---

## Security Notes

- The service account JSON is equivalent to a password. Never commit it to git.
- `.gitignore` already excludes `.env`.
- For a team/production deployment, use a secrets manager (GCP Secret Manager, AWS Secrets Manager, or Doppler) instead of a `.env` file.
