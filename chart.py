"""
JobFlow Chart Generator - Batch Sankey diagram generation
Creates a static HTML Sankey chart from jobs.json
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import plotly.graph_objects as go
except ImportError:
    print("⚠️  Plotly not installed. Run: pip install plotly")
    exit(1)

DATA_FILE = Path(__file__).parent / "jobs.json"
OUTPUT_FILE = Path(__file__).parent / "sankey_chart.html"


def load_jobs():
    """Load jobs from JSON file."""
    if not DATA_FILE.exists():
        print(f"❌ Data file not found: {DATA_FILE}")
        return []

    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def extract_year(date_str):
    """Extract year from date string."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").year
    except (ValueError, TypeError):
        return None


def normalize_status(status):
    """Normalize status values."""
    status_map = {
        "applied": "Applied",
        "interviewing": "Interviewing",
        "phone_screen": "Phone Screen",
        "take_home": "Take Home Assignment",
        "technical": "Technical Round",
        "offer": "Offer",
        "accepted": "Accepted",
        "rejected": "Rejected",
        "ghosted": "Ghosted",
        "withdrawn": "Withdrawn",
        "negotiating": "Negotiating",
        "background_check": "Background Check",
    }
    return status_map.get(status.lower(), status.title())


def generate_sankey(jobs, year=None):
    """
    Generate Sankey diagram from jobs data.

    Args:
        jobs: List of job dictionaries
        year: Optional year filter

    Returns:
        Plotly Figure object
    """
    # Filter by year if specified
    if year:
        jobs = [j for j in jobs if extract_year(j.get("date_applied")) == year]
        print(f"📊 Generating chart for {year} ({len(jobs)} jobs)")
    else:
        print(f"📊 Generating chart for all jobs ({len(jobs)} jobs)")

    if not jobs:
        print("❌ No jobs to visualize")
        return None

    # Build flow: Source -> Stage -> Status
    flows = defaultdict(int)

    for job in jobs:
        source = job.get("source", "Unknown").title()
        stage = job.get("stage", "applied").title()
        status = normalize_status(job.get("status", "applied"))

        flows[(source, stage)] += 1
        flows[(stage, status)] += 1

    # Build nodes
    nodes = []
    node_indices = {}

    for (src, tgt), count in flows.items():
        if src not in node_indices:
            node_indices[src] = len(nodes)
            nodes.append(src)
        if tgt not in node_indices:
            node_indices[tgt] = len(nodes)
            nodes.append(tgt)

    # Build links
    source_indices = []
    target_indices = []
    values = []

    for (src, tgt), count in flows.items():
        source_indices.append(node_indices[src])
        target_indices.append(node_indices[tgt])
        values.append(count)

    # Create Sankey diagram
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=nodes, color="lightblue"),
                link=dict(source=source_indices, target=target_indices, value=values),
            )
        ]
    )

    title = f"Job Application Flow - {year}" if year else "Job Application Flow - All Years"
    fig.update_layout(title_text=title, font_size=12, height=600)

    return fig


def main():
    """Generate and save Sankey chart."""
    print("🚀 JobFlow Chart Generator\n")

    jobs = load_jobs()

    if not jobs:
        return

    # TODO: Add command-line argument for year filtering
    # For now, generate chart for all jobs
    fig = generate_sankey(jobs)

    if fig:
        fig.write_html(OUTPUT_FILE)
        print(f"✅ Chart saved to: {OUTPUT_FILE}")
        print("   Open in browser to view")


if __name__ == "__main__":
    main()
