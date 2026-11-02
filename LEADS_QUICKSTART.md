# Leads Module - Quick Start Guide

## Getting Started

### 1. Access the Leads Page
Navigate to `http://localhost:5000/leads` to see the Leads dashboard.

### 2. Add Your First Lead

**Via UI:**
1. Click the **+ Add Lead** button
2. Fill in required fields:
   - Name (e.g., "Jane Doe")
   - Company (e.g., "Tech Corp")
   - Contact Method (email, LinkedIn, phone, etc.)
   - Date Contacted (YYYY-MM-DD format)
   - Status (Active, Replied, No Response, Converted, Closed)
3. Optional: Add role, email, LinkedIn, source, topic, notes
4. Optional: Set next action (what and when)
5. Click **Save Lead**

**Via API:**
```bash
curl -X POST http://localhost:5000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "company": "Tech Corp",
    "contact_method": "email",
    "date_contacted": "2025-11-05",
    "status": "Active",
    "source": "Networking",
    "topic": "Software architecture roles",
    "notes": "Initial inquiry"
  }'
```

### 3. Track Lead Status

Update a lead's status as it progresses:
- **Active** - Recently contacted, awaiting response
- **Replied** - Got a response, conversation ongoing
- **No Response** - No reply after X days
- **Converted** - Has become a job application
- **Closed** - No longer pursuing

**Via UI:** Click Edit, change status, save

**Via API:**
```bash
curl -X PATCH http://localhost:5000/api/leads/lead_abc123 \
  -H "Content-Type: application/json" \
  -d '{"status": "Replied"}'
```

### 4. Set Next Actions

Each lead can have a next action reminder:
- **What:** Description of the action (e.g., "Send portfolio", "Follow up", "Schedule call")
- **When:** Date to do the action (YYYY-MM-DD format)
- **Done:** Checkbox to mark when completed

The next action date appears in calendar view.

### 5. Convert Lead to Job

When a lead identifies a specific opportunity:

**Via UI:**
1. Click **Convert** on the lead row
2. Fill in job details:
   - Job Title (required)
   - Company (pre-filled)
   - Date Applied (defaults to today)
   - Status (Applied, Viewed, Under Consideration)
3. Click **Convert to Job**

**Result:**
- New job created in jobs.json with source "Lead Conversion"
- Lead status changed to "Converted"
- Lead automatically linked to job (linked_job_id)

**Via API:**
```bash
curl -X POST http://localhost:5000/api/leads/convert_to_job \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": "lead_abc123",
    "job_payload": {
      "title": "Senior Engineer",
      "company": "Tech Corp",
      "date_applied": "2025-11-10",
      "status": "Applied"
    }
  }'
```

### 6. Filter and Search

**By Status:** Dropdown filter to show Active, Replied, No Response, Converted, or Closed leads

**By Source:** Filter by how you found the lead (Networking, LinkedIn, Referral, etc.)

**Search/Sort:** Use DataTables search and column sorting for fine-grained filtering

### 7. View in Calendar

All lead contact dates and next actions appear in the calendar:
- **Blue events** - Lead contact date
- **Green events** - Lead next action due
- Works alongside job applications and follow-ups

### 8. Delete a Lead

**Via UI:** Click Delete button (with confirmation)

**Via API:**
```bash
curl -X DELETE http://localhost:5000/api/leads/lead_abc123
```

## Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| lead_id | string | auto | Unique identifier (auto-generated) |
| name | string | ✓ | Person's name |
| company | string | ✓ | Company name |
| role | string | | Job role/title |
| email | string | | Email address |
| linkedin | string | | LinkedIn profile URL |
| contact_method | enum | ✓ | How you contacted them |
| date_contacted | date | ✓ | When you first contacted them (YYYY-MM-DD) |
| status | enum | ✓ | Current status |
| source | enum | | How you found them |
| topic | string | | What you inquired about |
| notes | string | | Additional context |
| next_action.what | string | | Description of next action |
| next_action.when | date | | When to take next action |
| linked_job_id | string | | Job ID if converted to application |

## Status Codes

### Lead Statuses
- **Active** - Waiting for response or actively in conversation
- **Replied** - Got a response, ongoing dialogue
- **No Response** - No reply after initial contact
- **Converted** - Became a formal job application
- **Closed** - Stopped pursuing this lead

### Contact Methods
- **email** - Email correspondence
- **linkedin** - LinkedIn message
- **phone** - Phone call
- **in-person** - Talked in person
- **other** - Other method

### Lead Sources
- **Networking** - From networking event/connection
- **LinkedIn** - Found on LinkedIn
- **Referral** - Referred by someone
- **Company Website** - Found via company careers page
- **Job Board** - Found on job board
- **Event** - Met at conference/event
- **Other** - Other source

## Tips & Best Practices

1. **Consistent Naming** - Use full names for easier follow-up
2. **Date Format** - Always use YYYY-MM-DD (e.g., 2025-11-05)
3. **Regular Updates** - Mark status as you get responses
4. **Set Reminders** - Use next_action dates to stay on track
5. **Keep Notes** - Add context about the conversation
6. **Convert When Ready** - Convert to job as soon as you identify a specific role
7. **Link Multiple Contacts** - Can have multiple leads from same company

## Troubleshooting

**Can't see leads page?**
- Check the URL: `http://localhost:5000/leads`
- Ensure Flask app is running

**Validation error when adding lead?**
- Check date format (must be YYYY-MM-DD)
- Ensure all required fields are filled
- Verify status/contact_method are from allowed list

**Can't convert lead to job?**
- Lead must not already be converted
- Job title is required
- Date applied must be valid YYYY-MM-DD format

**Data not saving?**
- Check write permissions on `data/` directory
- Check browser console for API errors
- See server logs for detailed error messages

## Related Features

### Jobs Module
- View converted leads as jobs
- See "Lead Conversion" as source
- Lead context preserved in notes

### Calendar
- Lead contact dates displayed
- Next action dates trigger reminders
- Color-coded (blue for contacts, green for actions)

### Follow-ups (Future)
- Can create follow-ups from leads
- Track communications per lead

## Example Workflow

```
1. Meet someone at networking event
   → Create Lead (source: Networking)
   
2. Email them about opportunities
   → Set next action: Follow up in 1 week
   
3. They reply with interesting role
   → Update status: Replied
   → Prepare application materials
   
4. Ready to apply for specific job
   → Click Convert
   → Create job record
   → Track as formal application
   
5. Continue job application process
   → Lead status: Converted
   → Job now tracked in Jobs tab
   → Next actions via follow-ups
```

## Data Format Example

```json
{
  "schema_version": 1,
  "leads": [
    {
      "lead_id": "lead_abc123",
      "name": "Jane Doe",
      "company": "Tech Corp",
      "role": "Hiring Manager",
      "email": "jane@example.com",
      "linkedin": "https://example.com/demo-profile",
      "contact_method": "linkedin",
      "date_contacted": "2025-11-05",
      "status": "Replied",
      "source": "Networking",
      "topic": "Software architect roles",
      "notes": "Met at ReactConf, discussed architecture team opening",
      "next_action": {
        "what": "Send portfolio and availability",
        "when": "2025-11-08",
        "done": false
      },
      "linked_job_id": null
    }
  ]
}
```

## API Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/leads` | View leads page |
| GET | `/api/leads` | List all leads |
| POST | `/api/leads` | Create new lead |
| PATCH | `/api/leads/<lead_id>` | Update lead |
| DELETE | `/api/leads/<lead_id>` | Delete lead |
| POST | `/api/leads/convert_to_job` | Convert lead to job |
| GET | `/api/calendar` | Get calendar events (includes leads) |

## Next Steps

1. **Explore the Dashboard** - Check out the leads grid and try filtering
2. **Add Sample Leads** - Create a few test leads to get familiar
3. **Try Conversion** - Convert a lead to a job, see it in Jobs tab
4. **Set Reminders** - Use next actions for follow-up tracking
5. **Extend** - Add more sources/statuses as needed

## Support

For issues or questions:
1. Check `LEADS_IMPLEMENTATION.md` for technical details
2. Review `tests/test_leads.py` for usage examples
3. Check server logs for detailed errors
4. Verify data format in `data/leads.json`
