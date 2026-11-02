from __future__ import annotations

from pathlib import Path

from core_data import data_manager
from jobflow_app import create_app, extract_year, is_terminal, normalize_status


ROOT_DIR = Path(__file__).resolve().parent
DATA_FILE = ROOT_DIR / "data" / "jobs.json"
FOLLOWUPS_FILE = ROOT_DIR / "data" / "followups.json"
JOURNAL_FILE = ROOT_DIR / "data" / "journal.json"
LEADS_FILE = ROOT_DIR / "data" / "leads.json"

app = create_app()


__all__ = [
    "DATA_FILE",
    "FOLLOWUPS_FILE",
    "JOURNAL_FILE",
    "LEADS_FILE",
    "app",
    "create_app",
    "data_manager",
    "extract_year",
    "is_terminal",
    "normalize_status",
]


if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False, port=5001)