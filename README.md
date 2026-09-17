# AI Client Intelligence Platform

AI-augmented client intelligence and workflow layer for financial advisory practices.
Single-engine, multi-vertical architecture — Phase 1.

---

## Quick Start

### 1. Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Docker Desktop | Latest | [docker.com/get-started](https://www.docker.com/get-started/) |
| Git | Any | Optional |

### 2. Clone / open the project

```powershell
cd "d:\Tharun\Python\Client intelligence"
```

### 3. Configure environment

Edit `.env` — the file was created automatically. Fill in at minimum:

```
ANTHROPIC_API_KEY=sk-ant-...      # Required for AI classification
```

Google Sheets sync is **optional for Phase 1** — leave `GOOGLE_SERVICE_ACCOUNT_JSON` and
`SHEETS_SPREADSHEET_ID` blank and the app runs fine without it.

See `docs/google_cloud_setup.md` for the full Sheets setup walkthrough.

### 4. Start PostgreSQL (Docker)

```powershell
docker compose up -d
```

Wait ~10 seconds for Postgres to be ready (check: `docker compose logs db`).

### 5. Activate virtual environment

```powershell
venv\Scripts\Activate.ps1
```

### 6. Initialise the database

```powershell
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

### 7. Seed the practitioner account

```powershell
python scripts/seed.py
```

### 8. Run the development server

```powershell
python run.py
```

Open **http://localhost:5000**

---

## Testing the pipeline

1. Go to **http://localhost:5000/intake/form**
2. Fill in the client intake form and submit
3. Claude classifies the client in ~2–3 seconds
4. You land on the success page with segment, risk level, and confidence
5. The dashboard at **http://localhost:5000** shows the new client

---

## Key URLs

| URL | Purpose |
|-----|---------|
| `GET /` | Redirects to dashboard |
| `GET /dashboard` | Main practitioner view |
| `GET /intake/form` | Native intake form (dev/test) |
| `POST /intake/webhook` | Apps Script / external webhook endpoint |
| `GET /intake/responses` | All raw submissions + classification results |
| `GET /audit` | Audit log — every AI decision |
| `GET /clients/<id>` | Per-client detail view |
| `GET /api/clients` | JSON REST — all clients |
| `GET /api/segments` | JSON REST — all segments |

---

## Project Structure

```
app/
├── __init__.py          Flask app factory
├── config.py            Dev / production config
├── extensions.py        db, migrate instances
├── models/              SQLAlchemy models (all entities)
├── services/
│   ├── llm_client.py    Anthropic wrapper (provider-swappable)
│   ├── classification_service.py   Core AI pipeline
│   ├── audit_service.py            Immutable audit log
│   └── sheets_sync.py              Google Sheets sync
├── intake/routes.py     Webhook + native form
├── api/routes.py        Dashboard + REST endpoints
├── vertical/loader.py   YAML config loader (LRU-cached)
└── templates/           Jinja2 dark-mode UI

vertical_configs/
└── financial_advisory.yaml   Intake questions, classification prompt, escalation thresholds

docs/
├── google_cloud_setup.md       Step-by-step GCP setup
└── google_apps_script_webhook.js   Paste into Google Sheet's Apps Script editor

scripts/
└── seed.py    Seeds practitioner + default segments
```

---

## Running Tests

```powershell
# Requires a running Postgres instance (can use the same Docker one, or a separate ci_test DB)
pytest tests/ -v
```

---

## Phase Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ **Done** | Core pipeline — intake → classify → DB → Sheets |
| 2 | ✅ **Done** | Note intelligence — typed notes → Gemini extraction (sentiment, actions, key facts, reminders) |
| 3 | ✅ **Done** | Dynamic schema — AI proposed fields confirm/reject API (`/api/schema`) |
| 4 | ✅ **Done** | Voice input — Browser MediaRecorder → Gemini Files API transcription → note pipeline |
| 5 | ✅ **Done** | Triage & lead ranking — `/triage` view with Gemini priority scores + lead→client conversion |
| 6 | ✅ **Done** | Reminders — auto-created from notes, `/reminders` page with resolve UI |
| 7 | ✅ **Done** | Client query escalation — Gemini drafts response, flags for practitioner review |
| 8 | ✅ **Done** | Auth — User model, login/logout, session guard (`login_required`) |
| 9 | ✅ **Done** | Multi-vertical — `therapy.yaml` + `hr_advisory.yaml` vertical configs |
| 10 | ✅ **Done** | Semantic search — Gemini embeddings + pgvector, command-palette (⌘K), CSV export, inline profile edit |
| 11 | ✅ **Done** | Analytics & Insights — `/analytics` page with Chart.js (segment, risk, sentiment, triage, 30-day timeseries) |
| 12 | ✅ **Done** | Production Polish — 404/500 pages, Procfile, gunicorn |
| 13 | ✅ **Done** | Appointments — full CRUD, monthly calendar view, upcoming list, mark-complete |
| 14 | ✅ **Done** | Watchlists — create named groups, add/remove clients, manage from sidebar |
| 15 | ✅ **Done** | Client Timeline — unified chronological event stream (intake/notes/reminders/queries/appointments) with filter bar |


