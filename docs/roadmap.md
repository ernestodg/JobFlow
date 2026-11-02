# JobFlow - Development Roadmap

**Project**: JobFlow - Job Application Tracker Dashboard  
**Version**: 0.1.0 (MVP)  
**Started**: October 27, 2025  
**Target Completion**: TBD

---

## Setup Phase

### Environment Setup
- [x] Create project directory structure
- [x] Initialize Git repository
- [x] Create virtual environment
- [x] Create `requirements.txt`
- [x] Install Flask + dependencies
- [ ] Configure Python environment
- [ ] Test basic Flask server

### Documentation
- [x] Create `README.md`
- [x] Create `docs/spec.md`
- [x] Create `docs/blueprint.md`
- [x] Create `docs/roadmap.md` (this file)

---

## Core Development

### Data Layer
- [x] Define JSON schema
- [x] Create sample `jobs.json` with 15+ entries
- [x] Implement `load_jobs()` function
- [x] Implement `extract_year()` utility
- [x] Implement `normalize_status()` utility
- [ ] Add JSON validation on load
- [ ] Write unit tests for utilities

### API Endpoints

#### `/api/years`
- [x] Create route handler
- [x] Extract unique years from data
- [x] Sort years descending
- [x] Add verbose logging
- [ ] Write pytest tests
- [ ] Test with curl

#### `/api/sankey`
- [x] Create route handler
- [x] Implement year query parameter
- [x] Build flow dictionary (Source → Stage → Status)
- [x] Generate nodes list
- [x] Generate links with indices
- [x] Add verbose logging
- [ ] Write pytest tests
- [ ] Test with multiple years

#### `/api/status_counts`
- [x] Create route handler
- [x] Implement year filtering
- [x] Count jobs by status
- [x] Sort by count descending
- [x] Add verbose logging
- [ ] Write pytest tests
- [ ] Validate response format

#### `/api/health`
- [x] Create health check endpoint
- [ ] Add system metrics (optional)

### Frontend Development

#### Base HTML
- [x] Create `templates/index.html`
- [x] Add Plotly.js CDN
- [x] Create responsive layout
- [x] Add header with branding
- [x] Add footer

#### Year Filter UI
- [x] Create year filter container
- [x] Implement `loadYears()` function
- [x] Render year buttons dynamically
- [x] Add click handlers
- [x] Implement active state CSS
- [x] Add loading state

#### Sankey Diagram
- [x] Create chart container
- [x] Implement `loadSankey()` function
- [x] Parse API response
- [x] Configure Plotly Sankey
- [x] Add color palette generator
- [x] Handle empty data gracefully
- [ ] Add tooltip customization
- [ ] Test with edge cases

#### Status Bar Chart
- [x] Create chart container
- [x] Implement `loadStatusChart()` function
- [x] Configure Plotly bar chart
- [x] Add colors and labels
- [ ] Add click-to-filter functionality
- [ ] Test responsiveness

#### Interactivity
- [x] Implement `selectYear()` function
- [x] Update button states on click
- [x] Reload charts on year change
- [ ] Add smooth transitions
- [ ] Add keyboard navigation
- [ ] Test on multiple browsers

---

## CLI Tools

### tracker.py
- [x] Create CLI entry point
- [x] Implement `add` command (interactive)
- [x] Implement `list` command
- [x] Implement `stats` command
- [x] Add help message
- [ ] Add `edit` command
- [ ] Add `delete` command
- [ ] Add input validation

### chart.py
- [x] Create batch chart generator
- [x] Implement `generate_sankey()` function
- [x] Save to static HTML file
- [ ] Add year parameter support
- [ ] Add command-line arguments
- [ ] Generate multiple chart types

---

## Testing

### Unit Tests
- [x] Create `tests/test_api.py`
- [x] Test health endpoint
- [x] Test years endpoint structure
- [x] Test sankey endpoint structure
- [x] Test status counts endpoint
- [x] Test utility functions
- [ ] Test error handling
- [ ] Test edge cases (empty data, invalid dates)
- [ ] Achieve 80%+ coverage

### Integration Tests
- [ ] Test full dashboard load
- [ ] Test year filtering workflow
- [ ] Test data refresh
- [ ] Test with large dataset (500+ jobs)
- [ ] Performance benchmarks

### Manual Testing
- [ ] Test on Chrome
- [ ] Test on Firefox
- [ ] Test on Safari
- [ ] Test on Edge
- [ ] Test responsive design (mobile)
- [ ] Test with screen reader (a11y)

---

## Polish & Documentation

### CSS & Styling
- [x] Add gradient header
- [x] Style year buttons
- [x] Add hover effects
- [x] Style charts
- [ ] Add dark mode toggle
- [ ] Improve mobile layout
- [ ] Add animations
- [ ] Create custom color themes

### Logging
- [x] Configure Python logging
- [x] Add route-level logs
- [x] Log API requests
- [x] Log API responses
- [ ] Add performance metrics
- [ ] Add error tracking

### Documentation
- [x] Complete README with setup
- [x] Add usage examples
- [x] Document API endpoints
- [ ] Add screenshots
- [ ] Create video demo
- [ ] Write contributing guide

---

## CI/CD (Optional)

### GitHub Actions
- [x] Create `.github/workflows/ci.yml`
- [ ] Configure pytest runner
- [ ] Add linting (flake8)
- [ ] Add type checking (mypy)
- [ ] Add code coverage reporting
- [ ] Add PR checks

---

## Known Issues & Bugs

### High Priority
- [ ] None currently

### Medium Priority
- [ ] Date parsing fails silently on invalid formats
- [ ] No validation for required fields in JSON

### Low Priority
- [ ] Console logs could be more structured
- [ ] No graceful handling of empty jobs.json on first run

---

## Future Enhancements (Post-MVP)

### v0.2 Features
- [ ] CSV export functionality
- [ ] Dark mode toggle
- [ ] Data upload UI (drag & drop)
- [ ] Mobile-responsive design
- [ ] Search/filter by company or title

### v0.3 Features
- [ ] Timeline view (applications over time)
- [ ] Success rate analytics
- [ ] Email integration (parse application emails)
- [ ] Browser extension for quick adds

### v1.0 Features
- [ ] Multi-user support (optional authentication)
- [ ] Cloud sync (optional)
- [ ] Mobile app
- [ ] AI-powered insights

---

## Metrics & KPIs

### Development Metrics
- **Lines of Code**: ~1,200
- **Test Coverage**: Target 80%+
- **Documentation**: 100% of public APIs

### Performance Metrics
- **Initial Load**: < 2s (target)
- **Chart Render**: < 500ms (target)
- **API Response**: < 100ms (target)

### Quality Metrics
- **Bugs**: 0 critical, < 5 minor
- **Accessibility**: WCAG 2.1 Level A
- **Browser Support**: Chrome, Firefox, Safari, Edge (latest 2 versions)

---

## Notes & Decisions

### Architecture Decisions
- **Why Flask?**: Lightweight, no database needed, easy local setup
- **Why Plotly?**: Interactive, well-documented, no additional frontend framework
- **Why JSON file?**: Simple, human-readable, easy to edit manually
- **Why no database?**: Overkill for single-user local app, adds complexity

### Design Decisions
- **Year as primary filter**: Most users care about current/recent year
- **Sankey diagram**: Shows flow better than pie charts or tables
- **CLI tool**: Faster than web form for power users

---

## Changelog

### [0.1.0] - 2025-10-27 (Initial Release)
- ✅ Core Flask app with API endpoints
- ✅ Interactive Sankey diagram
- ✅ Status bar chart
- ✅ Year filtering
- ✅ CLI tool for data entry
- ✅ Sample data (15 jobs)
- ✅ Documentation (spec, blueprint, roadmap)
- ✅ Basic tests

---

**Last Updated**: October 27, 2025  
**Status**: 🚧 In Development → 🎯 Ready for Testing
