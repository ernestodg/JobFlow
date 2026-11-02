from __future__ import annotations

from core_data import data_manager
from jobflow_app import create_app, extract_year, is_terminal, normalize_status


app = create_app()


__all__ = [
	"app",
	"create_app",
	"data_manager",
	"extract_year",
	"is_terminal",
	"normalize_status",
]