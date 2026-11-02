import json
from datetime import datetime

# Load current jobs.json
with open('d:\\PROJECTS\\JOB_HUNT_TRACKER\\data\\jobs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

jobs = data['jobs']
updated_count = 0

# Update all "Applied" to "Rejected"
for job in jobs:
    if job.get('status') == 'Applied':
        job['status'] = 'Rejected'
        updated_count += 1
        print(f"Updated: {job.get('company')} - {job.get('title')}")

# Update last_modified
data['last_modified'] = datetime.now().isoformat() + '+00:00'

# Save
with open('d:\\PROJECTS\\JOB_HUNT_TRACKER\\data\\jobs.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✓ Updated {updated_count} jobs from 'Applied' to 'Rejected'")
print(f"✓ File saved successfully")

# Show final status breakdown
status_counts = {}
for job in jobs:
    status = job.get('status', 'Unknown')
    status_counts[status] = status_counts.get(status, 0) + 1

print(f"\nFinal status breakdown:")
for status in sorted(status_counts.keys()):
    print(f"  {status}: {status_counts[status]}")
