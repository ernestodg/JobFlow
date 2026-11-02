# JobFlow

JobFlow is a local-first job search tracker with a Flask dashboard, analytics views, PostgreSQL-backed storage, and an optional desktop app wrapper.

It is built for people who want more than a spreadsheet: pipeline visibility, follow-up tracking, journal context, career timeline history, and richer analytics in a multi-user setup.

![Version](https://img.shields.io/badge/version-0.2.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Why JobFlow

Most job trackers are either too thin to be useful or too heavy for a solo workflow. JobFlow stays local and simple while still giving you:

- A visual application pipeline instead of a flat list
- Follow-up and journal context tied to your search activity
- Analytics views for timing, outcomes, and patterns
- A desktop option for people who want an app instead of a browser tab

## What's Included Now

Compared with the original dashboard-first version, the repository now includes:

- richer analytics endpoints and the `/stats2` experience
- PostgreSQL + SQLAlchemy persistence for core entities
- account-based multi-user access with login and registration
- follow-up tracking and follow-up analytics
- journal storage and related API support
- a complete leads workflow (capture, track, convert-to-job)
- calendar aggregation for jobs, follow-ups, and leads in one view
- metrics caching and admin maintenance endpoints
- desktop packaging support for local native use
- broader automated test coverage across unit, integration, property, contract, and performance suites

## What JobFlow Does

- Tracks job applications in PostgreSQL with per-user data isolation
- Visualizes pipeline flow with a Sankey chart
- Breaks down outcomes by status and year
- Shows a career timeline for hired roles and prior experience
- Tracks networking leads with contact status and next actions
- Manages follow-ups and SLA-style follow-up views
- Converts qualified leads into job applications with linkage
- Stores journal entries alongside application activity
- Exposes API endpoints for jobs, follow-ups, journal, metrics, and analytics
- Supports an optional desktop build using PyWebView and PyInstaller

## Current Features

### Dashboard

- Year-based filtering
- Sankey flow from source -> stage -> status
- Status distribution views
- Career timeline view for hired or employed roles
- Advanced analytics page at `/stats2`

### Analytics

- Scatter plot data endpoints
- Heatmap data endpoints
- Application timing and trend analysis
- Metrics cache endpoints for faster analytics reuse

### Data Management

- PostgreSQL persistence via SQLAlchemy models
- Per-user records across jobs, follow-ups, leads, and journal entries
- Session-based auth for protected pages and APIs
- JSON import/migration support for legacy data
- Synthetic demo seed data for migration and maintenance scripts

### Workflow Support

- Follow-up tracking
- Enhanced follow-up analytics
- Journal entry storage
- Leads CRUD workflow (Active/Replied/No Response/Converted/Closed)
- Lead next-action reminders and calendar integration
- Lead-to-job conversion with linked `job_id`
- Bulk update endpoints
- Admin cache rebuild and health endpoints

### Delivery Options

- Flask web app for browser-based use
- Desktop launcher with native window shell
- Windows and macOS packaging scripts

### Quality

- Unit, integration, property, contract, and performance tests
- Snapshot fixtures and schema fixtures
- Ruff, mypy, bandit, safety, and coverage tooling in dev dependencies

## Typical Workflow

1. Register an account and add leads or job records through the dashboard.
2. Track lead status and next actions from the leads workspace.
3. Convert qualified leads into job applications when opportunities become concrete.
4. Review pipeline flow, follow-ups, journal context, and outcomes on the dashboard.
5. Open `/stats2` to inspect timing and pattern-level analytics.
6. Package the app as a desktop build if you want a native local experience.

## Run Modes

### 1. Web App

Run the Flask server directly from source.

Default runtime uses PostgreSQL via `jobflow_app.create_app()`.

### 2. Desktop App

Run a local desktop wrapper that starts the Flask app on a free local port and opens it in a native window.

The desktop build stores user data in the operating system's application data directory instead of the repository's `data/` folder.

## Quick Start

### Prerequisites

- Python 3.11 or newer
- `pip`

### Installation

```bash
python -m venv .venv
```

#### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### macOS / Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure Database

Set one of these environment variables to your PostgreSQL connection URL:

- `JOBFLOW_DATABASE_URL`
- `DATABASE_URL`

Startup fails if neither is set. Also set `JOBFLOW_SECRET_KEY` to a long random value; there is no default secret. Keep real values outside Git.

For PowerShell local development:

```powershell
$env:JOBFLOW_DATABASE_URL = "sqlite:///jobflow-local.sqlite"
$env:JOBFLOW_SECRET_KEY = "<your-long-random-secret>"
python app.py
```

SQLite is suitable for isolated development; PostgreSQL is the normal deployment backend.

For Docker, copy `.env.example` to `.env`, replace every placeholder, and run `docker compose up --build`. The database URL must use the same URL-encoded password as `JOBFLOW_POSTGRES_PASSWORD` and host `db`. Compose requires all three variables. Both exposed ports bind to loopback. No production secrets are supplied.

### Start the Web App

```bash
python app.py
```

Then open:

```text
http://localhost:5001
```

### Start the Desktop App

```bash
python app_desktop.py
```

## API Surface

The repository currently includes endpoints covering:

- `/api/health`
- `/api/auth/register`
- `/api/auth/login`
- `/api/auth/pin-login`
- `/api/auth/logout`
- `/api/auth/me`
- `/api/years`
- `/api/sankey`
- `/api/status_counts`
- `/api/timeline`
- `/api/jobs`
- `/api/jobs/<job_id>`
- `/api/jobs/bulk-update`
- `/api/jobs/statistics`
- `/api/jobs/sla-violations`
- `/api/followups`
- `/api/followups/enhanced`
- `/api/followups/sla`
- `/api/followups/analytics`
- `/api/followups/search`
- `/api/leads`
- `/api/leads/<lead_id>`
- `/api/leads/convert_to_job`
- `/api/journal`
- `/api/calendar`
- `/api/metrics/cache`
- `/api/admin/rebuild_cache`
- `/api/admin/health`
- `/api/stats2/scatter`
- `/api/stats2/heatmap`

The UI entry points are:

- `/` for the main dashboard
- `/leads` for lead management and conversion workflows
- `/stats2` for advanced analytics

## Data Files

Primary runtime data is stored in PostgreSQL.

Repository JSON files in `data/` are kept for legacy compatibility, migration, fixtures, and maintenance scripts:

- `data/jobs.json`
- `data/followups.json`
- `data/journal.json`
- `data/leads.json`
- `data/metrics.cache.json`

### Follow-up Cadence Regeneration

To re-apply follow-up cadence rules at any time:

```bash
python scripts/update_followup_cadence.py
```

What it does:

- Updates first reminder due dates for auto-generated applied follow-ups.
- Uses 5 days for `source: Email` and 7 days for `source: LazyApply` (or other non-email sources).
- Adds one second reminder 14 days after the first reminder when missing.
- Creates a backup at `data/followups.json.bak_cadence` before writing changes.

Optional preview mode:

```bash
python scripts/update_followup_cadence.py --dry-run
```

Desktop mode uses an OS-specific user data directory.

### Desktop Data Locations

- Windows: `%LOCALAPPDATA%\JobFlow Tracker`
- macOS: `~/Library/Application Support/JobFlow Tracker`
- Linux: `~/.local/share/JobFlow Tracker`

## Repository Layout

```text
JOB_HUNT_TRACKER/
├── app.py                   # Main Flask server entry point
├── app_desktop.py           # Desktop launcher
├── app/                     # App package for packaged desktop mode
│   ├── __init__.py          # App factory
│   ├── api/                 # Blueprint routes
│   ├── static/              # Static assets
│   └── templates/           # HTML templates
├── data/                    # Active local data files
├── seed_data/               # Seed data for desktop first run
├── tests/                   # Automated test suites
├── docs/                    # Specs, blueprint, roadmap
├── scripts/                 # Build, lint, coverage, test helpers
├── assets/                  # App icons and packaging assets
└── JobFlowTracker.spec      # PyInstaller spec
```

## Testing

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the provided scripts:

```bash
./scripts/test.sh
./scripts/coverage.sh
./scripts/lint.sh
```

Available test areas include:

- `tests/unit`
- `tests/integration`
- `tests/property`
- `tests/contracts`
- `tests/performance`
- `tests/ui_smoke`

## Desktop Packaging

### Windows

```cmd
scripts\build_win.bat
```

### macOS

```bash
./scripts/build_mac.sh
```

The desktop build uses:

- `pywebview` for the native shell
- `waitress` for the embedded local server
- `platformdirs` for OS-correct data locations
- `PyInstaller` for packaging

## Tech Stack

- Backend: Flask
- Frontend: server-rendered templates plus client-side JavaScript
- Charts and analytics visuals: Plotly
- Storage: PostgreSQL via SQLAlchemy; SQLite for isolated development
- Desktop shell: PyWebView
- Packaging: PyInstaller
- Testing: pytest, Hypothesis, syrupy, coverage

## Documentation

- `docs/spec.md`
- `docs/blueprint.md`
- `docs/roadmap.md`
- `ANALYTICS_API.md`
- `DESKTOP_README.md`
- `QUICKSTART.md`
- `LEADS_QUICKSTART.md`
- `LEADS_IMPLEMENTATION.md`
- `LEADS_COMPLETE.md`

## Notes

- Configure a database URL and a secret before startup. Legacy JSON utilities remain available.
- Some utility and migration scripts in the repository are intended for data cleanup, status updates, and one-off maintenance tasks.
- The codebase currently contains both the original single-file Flask server path and the packaged app-factory path used by the desktop wrapper.

## License

MIT

## Validation limitations

The SQLAlchemy multi-user tests are the current application checks. Some legacy JSON-era tests expect removed module-level loaders and metrics helpers; those failures and historical performance collection failures remain unresolved. This repository does not claim a fully passing test suite. Use isolated SQLite databases for tests and never production data.

Demo fixtures are synthetic. Do not commit application records, exports, database dumps, backups, or real environment files. The development server disables debug mode and binds to loopback. Internet-facing deployment requires additional hardening, including TLS, CSRF protection, and login rate limiting.
