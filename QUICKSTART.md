# JobFlow - Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Start the Dashboard
```bash
cd /path/to/JobFlow
source venv/bin/activate
python app.py
```
Then open: **http://localhost:5001**

### 2. Add Your First Job
```bash
python tracker.py add
```
Follow the prompts to enter job details.

### 3. View Statistics
```bash
python tracker.py stats
```

---

## 📊 Dashboard Features

- **Year Filter Buttons**: Click to filter applications by year (defaults to 2025)
- **Sankey Diagram**: Shows flow from Source → Stage → Status
- **Status Chart**: Donut chart showing distribution of application statuses
- **Career Timeline**: Right side lists confirmed hires with Start, End and Duration (X years Y days)

---

## 📝 Data Schema Reference

### Required Fields
- `company`: Company name
- `title`: Job title
- `date_applied`: Date in YYYY-MM-DD format
- `status`: Current status (see options below)
- `stage`: Interview stage (see options below)

### Optional Fields
- `source`: Where you found the job (LinkedIn, Indeed, Referral, etc.)
- `location`: Remote/City/Hybrid
- `country`: Country of the role or employer (e.g., US, CA, UK)
- `job_type`: Full-time/Contract/Part-time
- `salary_range`: e.g., "$120k-$150k"
- `url`: Link to job posting
- `notes`: Any additional notes
- `date_end`: End date (YYYY-MM-DD) for hired roles
- `duration_days`: Auto-computed when `date_end` is set for hired roles (otherwise 0)

### Status Options
- `applied` - Initial application submitted
- `interviewing` - In interview process
- `phone_screen` - Phone screening scheduled/completed
- `take_home` - Working on take-home assignment
- `offer` - Offer received
- `accepted` - Offer accepted
- `rejected` - Application/interview rejected
- `ghosted` - No response from company
- `withdrawn` - You withdrew
- `negotiating` - In salary negotiation

### Stage Options
- `applied` - Application submitted
- `phone` - Phone screening
- `technical` - Technical interview/assessment
- `take_home` - Take-home assignment
- `final` - Final round/on-site
- `offer` - Offer stage
- `background_check` - Background check in progress

---

## 🛠️ CLI Commands

### Add a Job
```bash
python tracker.py add
```
Interactive prompts guide you through adding a new application.

### List All Jobs
```bash
python tracker.py list
```
Shows all jobs with key details.

### View Statistics
```bash
python tracker.py stats
```
Shows breakdown by status and year.

### Generate Static Chart
```bash
python chart.py
```
Creates `sankey_chart.html` file you can open in any browser.

---

## 💡 Pro Tips

### Direct JSON Editing
You can edit `jobs.json` directly for bulk updates:
```bash
open jobs.json  # Opens in default editor
```

### Backup Your Data
```bash
cp jobs.json jobs_backup_$(date +%Y%m%d).json
```

### Quick Stats Check
```bash
python tracker.py stats | grep "Total"
```

### Filter by Status
```bash
python tracker.py list | grep -i "interviewing"
```

---

## 🎯 Recommended Workflow

1. **Daily**: Add new applications via CLI
   ```bash
   python tracker.py add
   ```

2. **Weekly**: Review dashboard for patterns
   - Open http://localhost:5001
   - Check conversion rates
   - Identify bottlenecks

3. **Monthly**: Backup your data
   ```bash
   cp jobs.json backups/jobs_$(date +%Y_%m).json
   ```

---

## 🔧 Troubleshooting

### Port Already in Use
If you see "Address already in use", the app is configured for port 5001. If that's taken:
```python
# In app.py, change the last line:
app.run(debug=False, host='127.0.0.1', port=5002)
```

### Virtual Environment Not Activated
Always activate before running:
```bash
source venv/bin/activate
```

### Tests Failing
Run tests to verify everything works:
```bash
pytest tests/test_api.py -v
pytest tests/test_utils.py -v
```

### Dashboard Not Loading
1. Check Flask is running (you should see logs)
2. Verify URL is http://localhost:5001
3. Check browser console for errors (F12)

---

## 📈 Next Steps

Now that everything is set up:

1. **Replace sample data** with your real job applications
2. **Customize statuses** if you use different terminology
3. **Track consistently** - add jobs as you apply
4. **Review weekly** to spot trends and optimize your strategy

---

**Happy Job Hunting! 🚀**

For questions or issues, refer to the full documentation in `/docs/`
