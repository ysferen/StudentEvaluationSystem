# Dashboard Charts Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove enrollment trends (backend + frontend), change year-level breakdown from bar to pie chart, add score averages bar chart, remove broken reports section.

**Architecture:** Backend drops `EnrollmentTrendSerializer` and the enrollment trends calculation loop from `analytics.py`. Frontend updates `HeadDashboard.tsx` to swap one chart type and add one new chart using the same `year_level_breakdown` data already available in the API response. Schema and Orval types regenerated to match.

**Tech Stack:** Django 5.2 + DRF + drf-spectacular, React + TypeScript + ApexCharts (react-apexcharts), Orval codegen

---

### Task 1: Backend — Remove enrollment trends from analytics.py

**Files:**
- Modify: `backend/student_evaluation_system/core/views/analytics.py`

- [ ] **Step 1: Remove `EnrollmentTrendSerializer` class**

Delete lines 13-15:
```python
class EnrollmentTrendSerializer(drf_serializers.Serializer):
    term = drf_serializers.CharField()
    student_count = drf_serializers.IntegerField()
```

- [ ] **Step 2: Remove `enrollment_trends` from `ProgramStatsResponseSerializer`**

Change line 37 from:
```python
    enrollment_trends = EnrollmentTrendSerializer(many=True)
```
to just remove that line, leaving:
```python
class ProgramStatsResponseSerializer(drf_serializers.Serializer):
    programs = ProgramStatSerializer(many=True)
    year_level_breakdown = YearLevelBreakdownSerializer(many=True)
```

- [ ] **Step 3: Remove enrollment trends calculation loop**

Delete lines 160-177 (the `terms = ...` block through the `enrollment_trends.append(...)` block). After deletion, the `year_level_breakdown = ...` line (currently line 179) should immediately follow the closing of the `for program in programs:` loop body.

- [ ] **Step 4: Remove `enrollment_trends` from the Response dict**

Change lines 181-186 from:
```python
        return Response(
            {
                "programs": program_stats,
                "enrollment_trends": enrollment_trends,
                "year_level_breakdown": year_level_breakdown,
            }
        )
```
to:
```python
        return Response(
            {
                "programs": program_stats,
                "year_level_breakdown": year_level_breakdown,
            }
        )
```

- [ ] **Step 5: Verify syntax**

Run: `python -m py_compile backend/student_evaluation_system/core/views/analytics.py`
Expected: no output (success)

- [ ] **Step 6: Commit**

```bash
git add backend/student_evaluation_system/core/views/analytics.py
git commit -m "refactor: remove enrollment trends from program-stats endpoint"
```

---

### Task 2: Regenerate OpenAPI schema

**Files:**
- Modify: `backend/student_evaluation_system/schema.yml`

- [ ] **Step 1: Regenerate backend schema**

```bash
cd backend && uv run --no-sync python student_evaluation_system/manage.py spectacular --file student_evaluation_system/schema.yml --validate
```
Expected: exit code 0, schema updated

- [ ] **Step 2: Verify `enrollment_trends` is gone from schema**

Run: `grep -c "enrollment_trends\|EnrollmentTrend" backend/student_evaluation_system/schema.yml`
Expected: `0` (no matches)

- [ ] **Step 3: Commit**

```bash
git add backend/student_evaluation_system/schema.yml
git commit -m "chore: regenerate backend schema without enrollment trends"
```

---

### Task 3: Regenerate frontend API types

**Files:**
- Modify: `frontend/schema.yml` (copy from backend)
- Modify: `frontend/src/shared/api/generated/analytics/analytics.ts` (Orval output)
- Modify: `frontend/src/shared/api/model/programStatsResponse.ts` (Orval output)
- Delete: `frontend/src/shared/api/model/enrollmentTrend.ts` (Orval will remove references)
- Modify: `frontend/src/shared/api/model/index.ts` (Orval output)

- [ ] **Step 1: Copy backend schema to frontend**

```bash
cp backend/student_evaluation_system/schema.yml frontend/schema.yml
```

- [ ] **Step 2: Run Orval to regenerate types**

```bash
cd frontend && npx orval --config orval.config.cjs
```
Expected: exit code 0, types regenerated

- [ ] **Step 3: Verify `enrollment_trends` is gone from generated types**

Run: `grep -r "enrollment_trends\|EnrollmentTrend" frontend/src/shared/api/`
Expected: no matches (all references removed automatically by Orval)

- [ ] **Step 4: Update HeadDashboard import if needed**

If the generated `analytics.ts` hook `useCoreAnalyticsProgramStatsRetrieve` changed return type, verify the import path is still valid. The hook itself should still exist — only the response shape changed.

- [ ] **Step 5: Commit**

```bash
git add frontend/schema.yml frontend/src/shared/api/
git commit -m "chore: regenerate frontend API types without enrollment trends"
```

---

### Task 4: Frontend — Update HeadDashboard.tsx

**Files:**
- Modify: `frontend/src/features/dashboard/pages/HeadDashboard.tsx`

- [ ] **Step 1: Remove unused imports**

Remove `ArrowDownTrayIcon` and `DocumentIcon` from the `@heroicons/react` import (lines 8-9) since the Reports section is being deleted. Resulting import:
```typescript
import {
  UserGroupIcon,
  BookOpenIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
```

- [ ] **Step 2: Remove enrollment trends `useMemo` block**

Delete lines 43-58 (the `const enrollmentTrends = useMemo(...)` block).

The `statsData` dependency was only used by `enrollmentTrends` and `yearLevelBreakdown`. Since `yearLevelBreakdown` uses it through `yearLevelBreakdown` memos, `statsData` is still referenced by the `yearLevelBreakdown` memo — but that memo already reads from `statsData?.year_level_breakdown` on line 26. Keep line 26 as-is.

Also remove `programStatsResponse` import reference — let's check: the hook still returns `ProgramStatsResponse` (now without `enrollment_trends`). The `year_level_breakdown` and `programs` fields are still there, so the existing destructuring `statsData?.programs` and `statsData?.year_level_breakdown` still work. No import changes needed.

- [ ] **Step 3: Change year-level chart from bar to pie**

Replace the year-level chart JSX (lines 117-123) with a pie chart that shows student counts per year:

```tsx
          <ChartWidget
            title="Year-Level Breakdown"
            subtitle="Student distribution by year"
            type="pie"
            series={yearLevelBreakdown.map(y => y.student_count)}
            options={{
              labels: ['1st Year', '2nd Year', '3rd Year', '4th Year'].slice(0, yearLevelBreakdown.length),
              colors: ['#0ea5e9', '#8b5cf6', '#f59e0b', '#10b981'],
            }}
          />
```

Note: `.slice(0, yearLevelBreakdown.length)` ensures labels match the actual number of years returned by the API. Also remove the old `yearLevelData` `useMemo` block (lines 28-41) since the pie chart doesn't need it.

- [ ] **Step 4: Add score averages bar chart**

Add alongside the pie chart in the same `grid grid-cols-1 lg:grid-cols-2` div:

```tsx
          <ChartWidget
            title="Score Averages by Year"
            subtitle="Average program outcome score per year level"
            type="bar"
            series={[{
              name: 'Avg Score',
              data: yearLevelBreakdown.map(y => y.avg_score ?? 0),
            }]}
            options={{
              xaxis: {
                categories: ['1st Year', '2nd Year', '3rd Year', '4th Year'].slice(0, yearLevelBreakdown.length),
              },
              colors: ['#8b5cf6'],
              yaxis: {
                min: 0,
                max: 100,
              },
            }}
          />
```

- [ ] **Step 5: Remove Reports section**

Delete lines 133-164 (the `{/* Reports Section */}` comment and the entire `<Card>` block that follows it, through the closing `</Card>`).

- [ ] **Step 6: Remove unused `useMemo` import if no longer needed**

Check if `useMemo` is still used after removing `yearLevelData` and `enrollmentTrends`. It is still used for `programs`, `totalStudents`, `totalCourses`, `overallAvg`, and `yearLevelBreakdown`. Keep it.

- [ ] **Step 7: Verify TypeScript compilation**

```bash
cd frontend && npx tsc --noEmit --pretty
```
Expected: no errors related to HeadDashboard.tsx

- [ ] **Step 8: Commit**

```bash
git add frontend/src/features/dashboard/pages/HeadDashboard.tsx
git commit -m "feat: replace enrollment trends with score averages bar chart, change year-level to pie chart, remove reports"
```

---

### Final Verification

- [ ] **Step 1: Restart backend and hit the endpoint**

```bash
# In Docker: docker compose restart backend
# Then:
curl -s http://localhost:8000/api/core/analytics/program-stats/ | python -m json.tool | head -20
```
Expected: response has `programs` and `year_level_breakdown` but NO `enrollment_trends`

- [ ] **Step 2: Check year_level_breakdown data shape**

```bash
curl -s http://localhost:8000/api/core/analytics/program-stats/ | python -c "import sys,json; d=json.load(sys.stdin); [print(f'Year {y[\"year\"]}: {y[\"student_count\"]} students, avg {y[\"avg_score\"]}') for y in d['year_level_breakdown']]"
```
Expected: actual student counts and score values (not all zeros)

- [ ] **Step 3: Open frontend and verify visually**

Dashboard should show: 3 KPI cards → Pie chart + Bar chart side by side. No enrollment trends, no reports section.
