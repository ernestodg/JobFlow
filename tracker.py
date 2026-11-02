"""
JobFlow CLI - Command-line interface for job tracking
Simple tool to add, edit, and manage job applications.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "jobs.json"


def load_jobs():
    """Load jobs from JSON file."""
    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️  Error: {DATA_FILE} is not valid JSON")
        return []


def save_jobs(jobs):
    """Save jobs to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(jobs)} jobs to {DATA_FILE}")


def add_job():
    """Interactive CLI to add a new job application."""
    print("\n📝 Add New Job Application\n")

    # Collect data
    company = input("Company name: ").strip()
    if not company:
        print("❌ Company name is required")
        return

    title = input("Job title: ").strip()
    if not title:
        print("❌ Job title is required")
        return

    date_applied = input("Date applied (YYYY-MM-DD) [today]: ").strip()
    if not date_applied:
        date_applied = datetime.now().strftime("%Y-%m-%d")

    # Validate date format
    try:
        datetime.strptime(date_applied, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        return

    status = (
        input(
            "Status (applied/interviewing/phone_screen/take_home/offer/accepted/rejected/ghosted/withdrawn/negotiating) [applied]: "
        )
        .strip()
        .lower()
    )
    if not status:
        status = "applied"

    stage = input("Stage (applied/phone/technical/take_home/final/offer/background_check) [applied]: ").strip().lower()
    if not stage:
        stage = "applied"

    source = input("Source (LinkedIn/Indeed/Referral/Company Site) [LinkedIn]: ").strip()
    if not source:
        source = "LinkedIn"

    # Additional fields
    location = input("Location (Remote/City/Hybrid) [Remote]: ").strip()
    if not location:
        location = "Remote"

    job_type = input("Job Type (Full-time/Contract/Part-time) [Full-time]: ").strip()
    if not job_type:
        job_type = "Full-time"

    salary_range = input("Salary Range (e.g., $120k-$150k) (optional): ").strip()

    url = input("Job URL (optional): ").strip()

    notes = input("Notes (optional): ").strip()

    # Create job object
    job = {
        "company": company,
        "title": title,
        "date_applied": date_applied,
        "status": status,
        "stage": stage,
        "source": source,
        "location": location,
        "job_type": job_type,
        "salary_range": salary_range,
        "url": url,
        "notes": notes,
    }

    # Load existing jobs and append
    jobs = load_jobs()
    jobs.append(job)
    save_jobs(jobs)

    print(f"\n✅ Added: {company} - {title}")


def list_jobs():
    """List all job applications."""
    jobs = load_jobs()

    if not jobs:
        print("📭 No jobs found")
        return

    print(f"\n📊 Total Jobs: {len(jobs)}\n")

    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['company']} - {job['title']}")
        print(f"   Applied: {job['date_applied']} | Status: {job['status']} | Source: {job.get('source', 'N/A')}")
        if job.get("notes"):
            print(f"   Notes: {job['notes']}")
        print()


def stats():
    """Show job application statistics."""
    jobs = load_jobs()

    if not jobs:
        print("📭 No jobs found")
        return

    # Count by status
    from collections import Counter

    status_counts = Counter(job["status"] for job in jobs)

    print("\n📈 Job Application Statistics\n")
    print(f"Total Applications: {len(jobs)}")
    print("\nBy Status:")
    for status, count in status_counts.most_common():
        print(f"  {status.title()}: {count}")

    # Count by year
    year_counts = Counter()
    for job in jobs:
        try:
            year = datetime.strptime(job["date_applied"], "%Y-%m-%d").year
            year_counts[year] += 1
        except (ValueError, KeyError):
            pass

    print("\nBy Year:")
    for year, count in sorted(year_counts.items(), reverse=True):
        print(f"  {year}: {count}")


def show_help():
    """Show help message."""
    print(
        """
🚀 JobFlow CLI - Job Application Tracker

Usage:
    python tracker.py <command>

Commands:
    add         Add a new job application (interactive)
    list        List all job applications
    stats       Show statistics
    help        Show this help message

Examples:
    python tracker.py add
    python tracker.py list
    python tracker.py stats
    """
    )


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == "add":
        add_job()
    elif command == "list":
        list_jobs()
    elif command == "stats":
        stats()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
