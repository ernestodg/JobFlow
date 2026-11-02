# JobFlow - Product Specification

## 1. One-Liner

**JobFlow is a Flask + Plotly dashboard for job seekers to visualize all job applications over time and track outcomes interactively.**

## 2. Problem & Objective

### Problem
Tracking job applications manually in spreadsheets is messy, unvisual, and provides no insight into application patterns or outcomes. Job seekers need a simple way to:
- See their application pipeline at a glance
- Understand which sources yield the best results
- Track progress through interview stages
- Identify bottlenecks in their job search

### Objective
Simplify the view of job search progress using interactive Sankey diagrams and bar charts that provide actionable insights.

### Key Performance Indicators (KPIs)
- ⚡ **Time to input data**: < 5 minutes for initial setup
- 🚀 **Sankey render time**: < 2 seconds
- 📝 **Data editability**: JSON file editable without schema breakage
- 🎯 **Accuracy**: 100% data integrity across filters and views

## 3. Users & Use Cases

### Primary User
Job seeker actively managing 100+ applications across multiple platforms (LinkedIn, Indeed, Torre.ai, company websites, referrals).

### User Personas
- **Active Job Seeker**: Applying to 10-20 jobs per week, needs quick data entry and visual feedback
- **Strategic Job Hunter**: Wants to analyze which sources and strategies work best
- **Passive Candidate**: Tracks occasional applications and interview progress

### Use Cases

#### UC1: Add New Job Application
**Actor**: Job Seeker  
**Goal**: Record a new job application  
**Flow**:
1. User runs `python tracker.py add`
2. CLI prompts for company, title, date, status, stage, source, notes
3. Data is saved to `jobs.json`
4. Dashboard auto-updates on refresh

#### UC2: Visualize Yearly Pipeline
**Actor**: Job Seeker  
**Goal**: View application flow for a specific year  
**Flow**:
1. User opens dashboard at `http://localhost:5000`
2. Year buttons auto-generate from data
3. User clicks year (default: current year)
4. Sankey diagram renders showing: Source → Stage → Status

#### UC3: Filter by Year
**Actor**: Job Seeker  
**Goal**: Compare application outcomes across years  
**Flow**:
1. User clicks different year buttons
2. Both Sankey and status charts update instantly
3. Can compare 2024 vs 2025 strategies

#### UC4: Analyze Status Distribution
**Actor**: Job Seeker  
**Goal**: Understand application outcomes  
**Flow**:
1. View bar chart showing status counts
2. Identify percentage of applications in each stage
3. Spot patterns (e.g., high rejection rate at technical stage)

## 4. MVP Scope

### Must Have (v0.1)
- ✅ Flask app reading from `jobs.json`
- ✅ Sankey chart showing application flow
- ✅ Status bar chart showing distribution
- ✅ Year filter buttons (auto-generated)
- ✅ Responsive design for desktop browsers
- ✅ CLI tool for adding jobs
- ✅ Verbose console logging for debugging

### Nice to Have (v0.2+)
- 📊 Export filtered data to CSV
- 🌙 Dark mode toggle
- 📤 Data upload UI (drag & drop JSON)
- 📱 Mobile-responsive design
- 🔍 Search/filter by company or title
- 📧 Weekly email summary
- 🎨 Customizable color schemes

### Out of Scope
- User authentication/multi-user support
- Cloud hosting/deployment
- Database integration
- Email integration for application tracking
- Browser extension
- Mobile app

## 5. Integrations & Data

### Data Source
- **Primary**: Local JSON file (`jobs.json`)
- **Format**: Array of job objects with standardized fields
- **Schema**:
  ```json
  {
    "company": "string (required)",
    "title": "string (required)",
    "date_applied": "YYYY-MM-DD (required)",
    "status": "string (required)",
    "stage": "string (required)",
    "source": "string (optional)",
    "notes": "string (optional)"
  }
  ```

### Standard Status Values
- `applied`: Initial application submitted
- `interviewing`: In interview process
- `offer`: Offer received
- `accepted`: Offer accepted
- `rejected`: Application/interview rejected
- `ghosted`: No response from company
- `withdrawn`: Candidate withdrew

### Standard Stage Values
- `applied`: Application submitted
- `phone`: Phone screening
- `technical`: Technical interview/assessment
- `final`: Final round/on-site
- `offer`: Offer stage

### Privacy & Security
- ✅ No external tracking or telemetry
- ✅ All data stored locally
- ✅ No network calls except to localhost
- ✅ Open-source and auditable

## 6. Constraints

### Technical Constraints
- **Language**: Python 3.11+
- **Framework**: Flask (lightweight, no database)
- **Visualization**: Plotly.js (via CDN)
- **Deployment**: Local only (no cloud requirement)
- **Browser**: Modern browsers with ES6 support

### Business Constraints
- **Cost**: Zero-cost runtime (no paid services)
- **License**: MIT (open-source)
- **Maintenance**: Solo developer friendly

### Design Constraints
- **UX**: Single-page dashboard
- **Performance**: < 2s load time for 500 jobs
- **Accessibility**: Keyboard navigable

## 7. Definition of Done

### Functional Acceptance Criteria
- ✅ Sankey diagram renders correctly by year
- ✅ Year filter buttons work without page reload
- ✅ Status bar chart updates with year filter
- ✅ JSON editing does not crash app
- ✅ All API endpoints return valid JSON
- ✅ CLI tool successfully adds jobs

### Technical Acceptance Criteria
- ✅ Verbose console logs for each request
- ✅ Unit tests pass for all API endpoints
- ✅ No errors in browser console
- ✅ Code follows PEP 8 style guide
- ✅ README with clear setup instructions

### Quality Acceptance Criteria
- ✅ Sankey renders with correct node labels
- ✅ Link values match actual job counts
- ✅ No duplicate nodes in Sankey
- ✅ Year buttons sorted newest first
- ✅ Charts responsive to window resize

### Documentation Acceptance Criteria
- ✅ `spec.md` complete
- ✅ `blueprint.md` complete
- ✅ `roadmap.md` complete
- ✅ README with usage examples
- ✅ Code comments for complex logic

---

**Document Version**: 1.0  
**Last Updated**: October 27, 2025  
**Status**: Draft → Ready for Implementation
