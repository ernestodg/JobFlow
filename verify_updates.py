import json

data = json.load(open('data/jobs.json'))
rejected = [j for j in data['jobs'] if j['status'] == 'Rejected' and j['source'] == 'LinkedIn']
print(f'LinkedIn jobs with Rejected status: {len(rejected)}')
print(f'Total jobs in file: {len(data["jobs"])}')

status_counts = {}
for j in data['jobs']:
    status = j['status']
    status_counts[status] = status_counts.get(status, 0) + 1

print(f'\nStatus breakdown:')
for k in sorted(status_counts.keys()):
    print(f'  {k}: {status_counts[k]}')

print(f'\nLinkedIn jobs by status:')
source_status = {}
for j in data['jobs']:
    if j['source'] == 'LinkedIn':
        key = f"LinkedIn - {j['status']}"
        source_status[key] = source_status.get(key, 0) + 1
        
for k in sorted(source_status.keys()):
    print(f'  {k}: {source_status[k]}')
