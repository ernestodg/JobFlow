# Follow-ups Analytics Dashboard API

## Overview

The Enhanced Follow-ups Analytics Dashboard provides comprehensive metrics and insights for job application follow-up activity, SLA compliance, conversion tracking, and actionable recommendations.

## Endpoint

```
GET /api/followups/analytics
```

## Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days_back` | integer | 90 | Number of days to look back for analysis |
| `start_date` | ISO date | - | Specific start date for analysis period |
| `end_date` | ISO date | - | Specific end date for analysis period |

## Response Structure

```json
{
  "period": {
    "start_date": "2025-08-12T16:07:15.728031+00:00",
    "end_date": "2025-11-10T16:07:15.728031+00:00", 
    "days": 90
  },
  "activity_metrics": {
    "total_followups": 13,
    "total_jobs": 32,
    "jobs_with_followups": 9,
    "avg_followups_per_job": 0.4,
    "followup_frequency": {},
    "followup_types": {},
    "author_activity": {}
  },
  "sla_metrics": {
    "total_violations": 0,
    "violation_breakdown": {
      "no_followup": 0,
      "interview_stale": 0,
      "screening_stale": 0,
      "offer_overdue": 0
    },
    "compliance_rate": 100.0,
    "avg_violation_days": 0,
    "worst_violations": []
  },
  "outcome_metrics": {
    "conversion_rates": {
      "no_followup": {
        "total_jobs": 120,
        "positive_outcomes": 9,
        "conversion_rate": 7.5
      },
      "low_activity": {
        "total_jobs": 8,
        "positive_outcomes": 0,
        "conversion_rate": 0.0
      }
    },
    "next_action_completion": {
      "total_actions": 3,
      "completed_actions": 0,
      "completion_rate": 0.0,
      "overdue_actions": 3,
      "overdue_rate": 100.0
    }
  },
  "time_series": {
    "daily_activity": {},
    "weekly_trends": {},
    "monthly_summary": {}
  },
  "insights": [
    {
      "type": "info",
      "category": "activity",
      "message": "Low follow-up activity: 0.4 follow-ups per job on average",
      "recommendation": "Consider increasing follow-up frequency to improve engagement and outcomes."
    }
  ],
  "recommendations": {
    "immediate_actions": [],
    "optimization_opportunities": []
  },
  "generated_at": "2025-11-10T16:07:15.728070+00:00"
}
```

## Key Features

### 1. Activity Metrics
- **Follow-up Volume**: Track total follow-ups, jobs, and average activity per job
- **Frequency Analysis**: Daily/weekly/monthly follow-up patterns
- **Type Distribution**: Breakdown by follow-up types (call, email, interview, etc.)
- **Author Activity**: Track follow-up activity by team member

### 2. SLA Compliance Tracking
- **Violation Detection**: Automated detection of SLA violations
- **Compliance Rate**: Percentage of jobs meeting SLA requirements
- **Violation Categories**:
  - `no_followup`: Jobs without follow-up activity beyond threshold
  - `interview_stale`: Interview stage jobs without recent updates
  - `screening_stale`: Screening stage jobs without recent updates
  - `offer_overdue`: Job offers requiring response
- **Worst Violations**: Top violations by days overdue

### 3. Conversion Analysis
- **Activity-Based Segmentation**: Jobs grouped by follow-up activity level
  - No follow-up
  - Low activity (1-2 follow-ups)
  - Medium activity (3-5 follow-ups)
  - High activity (6+ follow-ups)
- **Conversion Rates**: Success rates by activity level
- **Impact Analysis**: Correlation between follow-up frequency and outcomes

### 4. Task Management Metrics
- **Next Action Tracking**: Monitor pending and completed next actions
- **Completion Rates**: Percentage of actions completed on time
- **Overdue Analysis**: Identify and track overdue action items

### 5. Time Series Analysis
- **Daily Activity**: Follow-up and application activity by day
- **Trend Analysis**: Weekly and monthly patterns
- **Type Breakdown**: Activity segmented by follow-up types

### 6. Actionable Insights
- **Automated Analysis**: AI-generated insights based on data patterns
- **Categorized Recommendations**:
  - Immediate actions (warnings/errors)
  - Optimization opportunities (improvements)
- **Context-Aware Suggestions**: Recommendations based on current performance

## Usage Examples

### Basic Analytics (90-day window)
```bash
curl "http://127.0.0.1:5001/api/followups/analytics"
```

### Custom Date Range
```bash
curl "http://127.0.0.1:5001/api/followups/analytics?start_date=2025-10-01&end_date=2025-11-01"
```

### Recent Activity (30 days)
```bash
curl "http://127.0.0.1:5001/api/followups/analytics?days_back=30"
```

## Integration with Other APIs

The analytics endpoint integrates with the enhanced follow-ups API ecosystem:

- **Enhanced Follow-ups**: `/api/followups/enhanced` - Detailed follow-up data with SLA info
- **SLA Violations**: `/api/followups/sla` - Real-time SLA violation monitoring
- **Advanced Search**: `/api/followups/search` - Query-based follow-up analysis
- **Bulk Operations**: `/api/followups/bulk` - Mass follow-up management

## Performance Considerations

- **Caching**: Large datasets are processed efficiently with optimized algorithms
- **Filtering**: Time-based filtering reduces processing overhead for recent analysis
- **Pagination**: Time series data is segmented to prevent large response payloads
- **Error Handling**: Graceful handling of data inconsistencies and missing values

## Data Sources

The analytics dashboard processes data from:
- **Jobs**: Primary job application data
- **Follow-ups**: All follow-up activity and notes
- **Settings**: SLA thresholds and configuration
- **Historical Data**: Complete activity timeline for trend analysis

## Business Value

### For Job Seekers
- **Performance Optimization**: Identify most effective follow-up strategies
- **Time Management**: Track and improve action item completion
- **Success Patterns**: Understand which activities lead to better outcomes

### For Teams/Organizations
- **Process Improvement**: Optimize follow-up workflows and procedures
- **Compliance Monitoring**: Ensure timely follow-up on opportunities
- **Resource Allocation**: Focus efforts on highest-impact activities

## Implementation Status

✅ **Complete**: Full analytics dashboard with all planned features
- Activity metrics and frequency analysis
- SLA compliance monitoring and violation tracking
- Conversion rate analysis by follow-up activity level
- Next action completion and overdue tracking
- Time series analysis with daily/weekly/monthly breakdowns
- Automated insight generation with actionable recommendations
- Integration with enhanced follow-ups API ecosystem

The Follow-ups Analytics Dashboard is production-ready and provides comprehensive insights for optimizing job search follow-up strategies.