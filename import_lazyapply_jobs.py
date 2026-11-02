import json
import csv
import uuid
from datetime import datetime, UTC

# Read the CSV file
csv_file = 'job-applications.csv'
jobs_added = []


def normalize_title(raw_title: str) -> str:
    title = raw_title.strip()
    replacements = [
        "Job Application for ",
        " - Greenhouse",
        " - Lever",
    ]
    for token in replacements:
        title = title.replace(token, "")

    # Handle common platform suffix patterns
    if " @ " in title and " - Jobs" in title:
        title = title.split(" @ ")[0].strip()
    if " - Jobs" in title:
        title = title.replace(" - Jobs", "").strip()

    # Keep only job title if content includes " at Company"
    if " at " in title:
        title = title.split(" at ")[0].strip()

    return " ".join(title.split())


def normalize_company(raw_company: str) -> str:
    return " ".join(raw_company.strip().lower().split())

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Parse job title and remove common platform/application wrappers
        title = normalize_title(row['Job Title'])
        
        company = row['Company Name'].strip()
        date_applied = row['Date Applied'].strip()  # Format: M/D/YYYY
        
        # Convert date to YYYY-MM-DD format
        date_parts = date_applied.split('/')
        if len(date_parts) == 3:
            month, day, year = date_parts
            date_applied_fmt = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        else:
            date_applied_fmt = '2026-03-18'
        
        url = row['Job Link'].strip()
        platform = row['Platform'].strip()
        
        job_entry = {
            'company': company,
            'title': title,
            'date_applied': date_applied_fmt,
            'status': 'Applied',
            'stage': 'applied',
            'source': 'LazyApply',
            'location': '',  # Not provided in CSV
            'job_type': 'Full-time',  # Default assumption
            'salary_range': '',
            'url': url,
            'notes': f'Applied via {platform}',
            'country': 'US',  # Default to US for now
            'job_id': f'job_{uuid.uuid4().hex[:12]}'
        }
        
        jobs_added.append(job_entry)
        print(f"Parsed: {company} - {title}")

print(f"\n✓ Parsed {len(jobs_added)} job entries from CSV")

# Load current jobs.json
with open('d:\\PROJECTS\\JOB_HUNT_TRACKER\\data\\jobs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

jobs = data['jobs']
initial_count = len(jobs)

# Check for duplicates before adding
duplicates_skipped = 0

existing_urls = {j.get('url', '').strip().lower() for j in jobs if j.get('url')}
existing_company_title = {
    (normalize_company(j.get('company', '')), normalize_title(j.get('title', '')).lower())
    for j in jobs
}

for new_job in jobs_added:
    url_key = new_job['url'].strip().lower()
    ct_key = (normalize_company(new_job['company']), normalize_title(new_job['title']).lower())

    # De-duplicate by URL first, then normalized company+title.
    exists = (url_key and url_key in existing_urls) or (ct_key in existing_company_title)
    
    if not exists:
        jobs.append(new_job)
        if url_key:
            existing_urls.add(url_key)
        existing_company_title.add(ct_key)
    else:
        duplicates_skipped += 1
        print(f"Skipped duplicate: {new_job['company']} - {new_job['title']}")

# Update last_modified
data['last_modified'] = datetime.now(UTC).isoformat()

# Save
with open('d:\\PROJECTS\\JOB_HUNT_TRACKER\\data\\jobs.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✓ Added {len(jobs_added) - duplicates_skipped} new job entries")
if duplicates_skipped > 0:
    print(f"⚠ Skipped {duplicates_skipped} duplicate entries")
print(f"✓ File saved successfully")
print(f"\nJob count: {initial_count} → {len(jobs)}")
