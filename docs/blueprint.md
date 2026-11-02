# JobFlow - Technical Blueprint

## 0. Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Client)                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │           index.html (Dashboard UI)              │  │
│  │  - Plotly.js (Sankey + Bar Charts)              │  │
│  │  - Vanilla JavaScript (API calls, state)        │  │
│  │  - CSS (Responsive layout)                       │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/JSON
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Flask Backend (Python 3.11+)                │
│  ┌──────────────────────────────────────────────────┐  │
│  │                  app.py                          │  │
│  │  Routes:                                         │  │
│  │  - GET /                → index.html            │  │
│  │  - GET /api/years       → [2025, 2024, ...]    │  │
│  │  - GET /api/sankey      → {nodes, links}       │  │
│  │  - GET /api/status_counts → {labels, counts}   │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ File I/O
                        ↓
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                            │
│  ┌──────────────────────────────────────────────────┐  │
│  │              jobs.json (Local File)              │  │
│  │  [                                               │  │
│  │    {company, title, date_applied, status, ...}  │  │
│  │  ]                                               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

Additional Tools:
- tracker.py: CLI for data entry
- chart.py: Batch Sankey generation (static HTML)
```

### Technology Stack

**Frontend**
- HTML5 + CSS3 (no framework)
- Vanilla JavaScript (ES6+)
- Plotly.js 2.27.0 (via CDN)

**Backend**
- Python 3.11+
- Flask 3.0+
- Standard library only (json, logging, datetime)

**Data**
- JSON file storage (no database)
- Schema validation on read

**Testing**
- pytest for API tests
- Manual testing for UI

### Design Principles

1. **Simplicity First**: No unnecessary dependencies
2. **Local & Private**: All data stays on user's machine
3. **Fast Loading**: < 2s render time
4. **Verbose Logging**: Console logs for debugging
5. **Fail Gracefully**: Handle missing/malformed data

---

## 1. Development Chunks

### Chunk 1: Setup & Boilerplate (2h)
**Goal**: Get basic Flask app running

**Tasks**:
- [ ] Create project structure
- [ ] Set up virtual environment
- [ ] Install Flask + dependencies
- [ ] Create basic `app.py` with health check route
- [ ] Create `templates/index.html` skeleton
- [ ] Test local server runs

**Deliverable**: Flask app responds at `localhost:5000`

---

### Chunk 2: Data Schema & Loader (2h)
**Goal**: Define and implement data loading

**Tasks**:
- [ ] Define JSON schema in `docs/schema.json`
- [ ] Implement `load_jobs()` function with error handling
- [ ] Create `sample_jobs.json` with 15+ entries
- [ ] Write `extract_year()` utility function
- [ ] Write `normalize_status()` utility function
- [ ] Add unit tests for utilities

**Deliverable**: Reliable data loading with validation

---

### Chunk 3: Years API Endpoint (2h)
**Goal**: Implement `/api/years`

**Tasks**:
- [ ] Create route handler
- [ ] Extract unique years from `date_applied`
- [ ] Sort years descending (newest first)
- [ ] Add verbose logging
- [ ] Write pytest test cases
- [ ] Test with curl/Postman

**Deliverable**: `/api/years` returns `[2025, 2024, ...]`

**Test Cases**:
```python
def test_years_returns_array()
def test_years_sorted_descending()
def test_years_handles_empty_data()
```

---

### Chunk 4: Sankey API Endpoint (3h)
**Goal**: Implement `/api/sankey?year=YYYY`

**Tasks**:
- [ ] Create route handler with year query param
- [ ] Build flow dictionary: Source → Stage → Status
- [ ] Generate unique nodes list
- [ ] Generate links with source/target indices
- [ ] Add verbose logging for flow counts
- [ ] Write pytest test cases
- [ ] Test with sample data

**Deliverable**: `/api/sankey?year=2025` returns Plotly-compatible JSON

**Data Structure**:
```json
{
  "nodes": ["LinkedIn", "Applied", "Interviewing", "Rejected"],
  "links": {
    "source": [0, 1, 1],
    "target": [1, 2, 3],
    "value": [10, 5, 5]
  }
}
```

**Test Cases**:
```python
def test_sankey_without_year_filter()
def test_sankey_with_year_filter()
def test_sankey_links_structure()
def test_sankey_handles_invalid_year()
```

---

### Chunk 5: Frontend Sankey Rendering (3h)
**Goal**: Display interactive Sankey diagram

**Tasks**:
- [ ] Add Plotly.js CDN to `index.html`
- [ ] Create `loadYears()` JavaScript function
- [ ] Render year buttons dynamically
- [ ] Create `loadSankey()` function
- [ ] Parse API response and build Plotly config
- [ ] Add loading states
- [ ] Style chart container

**Deliverable**: Sankey renders on page load

**JavaScript Functions**:
- `loadYears()`: Fetch and render year buttons
- `selectYear(year)`: Handle button clicks
- `loadSankey()`: Fetch and render Sankey
- `generateColors(count)`: Color palette generator

---

### Chunk 6: Active Year State Logic (2h)
**Goal**: Make year filtering interactive

**Tasks**:
- [ ] Add click handlers to year buttons
- [ ] Implement active button CSS state
- [ ] Update `currentYear` global variable
- [ ] Trigger chart reload on year change
- [ ] Add smooth transitions
- [ ] Test with multiple years

**Deliverable**: Clicking year button redraws Sankey

**State Management**:
```javascript
let currentYear = null;

function selectYear(year) {
  currentYear = year;
  updateButtonStates();
  loadCharts();
}
```

---

### Chunk 7: Status Bar Chart (2h)
**Goal**: Add status distribution chart

**Tasks**:
- [ ] Create `/api/status_counts?year=YYYY` route
- [ ] Count jobs by normalized status
- [ ] Sort by count descending
- [ ] Create `loadStatusChart()` JavaScript function
- [ ] Render Plotly bar chart
- [ ] Style chart container
- [ ] Write pytest tests

**Deliverable**: Bar chart shows status breakdown by year

**Test Cases**:
```python
def test_status_counts_without_filter()
def test_status_counts_arrays_same_length()
def test_status_counts_sorted_descending()
```

---

### Chunk 8: Logging & Testing (2h)
**Goal**: Add comprehensive logging and tests

**Tasks**:
- [ ] Configure Python logging (DEBUG level)
- [ ] Add log statements to all routes
- [ ] Log request parameters
- [ ] Log response data (truncated)
- [ ] Create `tests/test_api.py`
- [ ] Run full test suite
- [ ] Fix any failing tests

**Deliverable**: Console shows request → response flow

**Logging Format**:
```
2025-10-27 10:15:30 - app - INFO - GET /api/sankey - Year filter: 2025
2025-10-27 10:15:30 - app - INFO - Filtered to 10 jobs for year 2025
2025-10-27 10:15:30 - app - INFO - Generated Sankey with 8 nodes and 12 links
```

---

### Chunk 9: CSS & UI Polish (2h)
**Goal**: Make dashboard production-ready

**Tasks**:
- [ ] Add gradient header background
- [ ] Style year buttons with hover effects
- [ ] Add active button highlight
- [ ] Make charts responsive
- [ ] Add loading spinners
- [ ] Add error message styling
- [ ] Test on different screen sizes

**Deliverable**: Polished, professional-looking dashboard

---

## 2. Per-Chunk Development Process

For each chunk:

1. **Write Tests First** (TDD approach)
   - Define expected behavior in pytest
   - Run tests (should fail initially)

2. **Implement Minimal Code**
   - Write simplest code to pass tests
   - Add verbose logging
   - Handle edge cases

3. **Console Log Validation**
   - Run app and check console output
   - Verify request → response flow
   - Ensure no errors

4. **Update Roadmap**
   - Check off completed tasks
   - Document any blockers

---

## 3. Testing Strategy

### Unit Tests (pytest)

**Test Files**:
- `tests/test_api.py`: API endpoint tests
- `tests/test_utils.py`: Utility function tests

**Coverage Goals**:
- All API routes: 100%
- Utility functions: 100%
- Error handling: 80%+

**Test Scenarios**:
- ✅ Happy path (valid data)
- ✅ Empty data file
- ✅ Malformed JSON
- ✅ Invalid date formats
- ✅ Missing required fields
- ✅ Year filter edge cases

### Integration Tests

**Manual Testing Checklist**:
- [ ] Dashboard loads without errors
- [ ] Year buttons render correctly
- [ ] Clicking year updates charts
- [ ] Sankey displays all data
- [ ] Bar chart shows correct counts
- [ ] Console logs are verbose
- [ ] No JavaScript errors

### Log Validation

**Requirements**:
- Every API request logged with parameters
- Response data logged (summary)
- Errors logged with stack traces
- Performance metrics (optional)

---

## 4. Deliverables

### Code Files

```
JOB_HUNT_TRACKER/
├── app.py                  # Flask server (200 lines)
├── tracker.py              # CLI tool (150 lines)
├── chart.py                # Batch generator (100 lines)
├── jobs.json               # Sample data (15+ entries)
├── templates/
│   └── index.html          # Dashboard (400 lines)
├── tests/
│   ├── test_api.py         # API tests (150 lines)
│   └── test_utils.py       # Utility tests (50 lines)
├── docs/
│   ├── spec.md             # This document
│   ├── blueprint.md        # Technical design
│   └── roadmap.md          # Progress tracking
├── requirements.txt        # Python dependencies
├── README.md               # Setup & usage guide
└── .github/
    └── workflows/
        └── ci.yml          # GitHub Actions (optional)
```

### Documentation

**README.md**: Quick start guide
**spec.md**: Requirements & scope
**blueprint.md**: Architecture & design
**roadmap.md**: Task tracking

### Tests

**test_api.py**: All API endpoints
**test_utils.py**: Helper functions

### CI/CD (Optional)

**GitHub Actions**:
- Run pytest on push
- Lint with flake8
- Type check with mypy (optional)

---

## 5. API Specification

### GET /

**Description**: Serve main dashboard HTML  
**Response**: HTML page

---

### GET /api/health

**Description**: Health check endpoint  
**Response**:
```json
{
  "status": "ok",
  "timestamp": "2025-10-27T10:15:30.123456"
}
```

---

### GET /api/years

**Description**: Get all unique years from applications  
**Response**:
```json
[2025, 2024, 2023]
```
**Notes**: Sorted descending (newest first)

---

### GET /api/sankey?year=YYYY

**Description**: Get Sankey diagram data for a year  
**Parameters**:
- `year` (optional): Filter by year

**Response**:
```json
{
  "nodes": ["LinkedIn", "Applied", "Interviewing", "Rejected"],
  "links": {
    "source": [0, 1, 1],
    "target": [1, 2, 3],
    "value": [10, 5, 5]
  }
}
```

---

### GET /api/status_counts?year=YYYY

**Description**: Get status distribution for a year  
**Parameters**:
- `year` (optional): Filter by year

**Response**:
```json
{
  "labels": ["Applied", "Interviewing", "Rejected"],
  "counts": [50, 30, 20]
}
```

---

## 6. Performance Considerations

### Optimization Targets

- **Initial load**: < 2s for 500 jobs
- **Year filter**: < 500ms to redraw
- **API response**: < 100ms

### Optimization Techniques

1. **Client-side caching**: Store API responses
2. **Lazy loading**: Load charts only when visible
3. **Debouncing**: Prevent rapid re-renders
4. **Efficient data structures**: Use sets for uniqueness

### Monitoring

- Console performance.now() for critical paths
- Browser DevTools Network tab
- Flask request timing logs

---

## 7. Future Enhancements (v0.2+)

### Feature Backlog

1. **CSV Export**: Download filtered data
2. **Dark Mode**: Toggle theme
3. **Data Upload UI**: Drag & drop JSON
4. **Mobile Responsive**: Touch-friendly design
5. **Search Filter**: Find by company/title
6. **Custom Colors**: User-defined palette
7. **Multi-chart Views**: Side-by-side comparison

### Technical Debt

- Add JSON schema validation library
- Implement proper error boundaries
- Add TypeScript for frontend
- Use proper state management (Redux/Zustand)

---

**Document Version**: 1.0  
**Last Updated**: October 27, 2025  
**Status**: Ready for Development
