# Dashboard Charts Refactor — Head Dashboard

**Date:** 2026-04-27
**Status:** Approved

## Summary

Simplify the Head Dashboard by removing the broken Enrollment Trends chart, changing Year-Level Breakdown from bar to pie chart, and adding a new Score Averages by Year bar chart. Remove enrollment trends calculation from the backend.

## Motivation

- Enrollment trends chart is unused and adds noise
- Pie chart better communicates proportional year-level distribution
- Score averages by year (already available in the API but unused) gives program heads actionable insight into academic performance trends

## Changes

### Backend — `core/views/analytics.py`

1. **Remove** `EnrollmentTrendSerializer` (lines 13-15)
2. **Remove** `enrollment_trends` from `ProgramStatsResponseSerializer` (line 37)
3. **Remove** enrollment trends calculation block (lines 160-177, the `terms = ...` loop)
4. **Remove** `enrollment_trends` from the `Response()` dict (line 182)

Result: endpoint returns `{ programs, year_level_breakdown }` only.

### Schema & Generated Types

5. Regenerate `schema.yml` (backend) and `schema.yml` (frontend copy)
6. Run Orval to regenerate TypeScript models — removes `EnrollmentTrend` type and `enrollment_trends` field from `ProgramStatsResponse`

### Frontend — `HeadDashboard.tsx`

7. **Remove** enrollment trends chart configuration and JSX block
8. **Remove** Reports section JSX
9. **Change** year-level chart from `type: 'bar'` to `type: 'pie'` with labels showing student counts
10. **Add** score averages bar chart alongside the pie chart, using `year_level_breakdown[].avg_score`
11. Layout: KPI cards → `[Pie (student count) | Bar (avg score)]` stacked side-by-side

## Data Flow

```
GET /api/core/analytics/program-stats/
  → { programs: [...], year_level_breakdown: [{year, student_count, avg_score}] }
     ├── programs[].total_students, total_courses, avg_score → KPI cards
     ├── year_level_breakdown[].student_count → Pie chart (students per year)
     └── year_level_breakdown[].avg_score → Bar chart (score averages by year)
```

## Out of Scope

- No changes to KPI cards
- No changes to Instructor Dashboard, Student Dashboard, or other pages
- No new API endpoint — reuses existing data
