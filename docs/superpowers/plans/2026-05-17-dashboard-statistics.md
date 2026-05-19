# Dashboard Statistics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve existing SES dashboard and course detail pages so instructors and program heads get clearer analytical insight without creating new analytics pages.

**Architecture:** Keep analytics inside existing page responsibilities: instructor dashboard for cross-course triage, course detail for single-course deep analysis, and head dashboard for program-level monitoring. Prefer frontend-derived statistics from already fetched data in the first iteration; add backend aggregation only if the frontend would require excessive per-course request fan-out. Use explicit score labels in UI and code, such as `Average GPA`, `Average LO score`, `Average PO score`, `Average course grade`, and `Assessment average score`.

**Tech Stack:** React, TypeScript, Vite, TanStack Query, generated Orval API clients, Tailwind CSS, existing custom chart/card components, Django/DRF only if backend aggregation becomes necessary.

---

## Files And Responsibilities

- Modify `frontend/src/features/dashboard/utils/analytics.ts`: add reusable frontend analytics helpers for at-risk ratio, weakest LO, variance, threshold counts, and explicitly named aggregate score calculations.
- Modify `frontend/src/features/dashboard/pages/InstructorDashboard.tsx`: change the dashboard from single-course-first carousel to cross-course-first insight summary while keeping selected-course drill-down.
- Modify `frontend/src/features/dashboard/components/CourseAnalyticsCard.tsx`: replace ambiguous labels like `Avg Score` with explicit score labels and support instructor summary cards.
- Create `frontend/src/features/dashboard/components/CourseHealthMatrix.tsx`: render course average grade versus at-risk ratio, with student count as visual weight.
- Create `frontend/src/features/dashboard/components/CourseAttentionList.tsx`: render courses needing attention with explicit reasons such as low average course grade, high at-risk ratio, and weakest LO score.
- Modify `frontend/src/features/courses/pages/CourseDetail.tsx`: add insight cards and make sorted assessment/LO bars the default where radar charts are less informative.
- Create `frontend/src/features/courses/components/CourseInsightCards.tsx`: show weakest LO, most difficult assessment, highest variance assessment, and students below the at-risk threshold.
- Modify `frontend/src/features/dashboard/pages/HeadDashboard.tsx`: demote year-level student counts and promote Average PO score and course-risk insights.
- Optional modify `backend/student_evaluation_system/core/views/analytics.py`: only if head dashboard course-risk aggregation cannot be done safely from existing frontend queries.

## Task 1: Shared Analytics Helpers And Explicit Score Naming

**Files:**
- Modify: `frontend/src/features/dashboard/utils/analytics.ts`
- Optional Test: `frontend/src/features/dashboard/utils/analytics.test.ts`

- [ ] **Step 1: Add explicit analytics types**

Add these exported interfaces to `frontend/src/features/dashboard/utils/analytics.ts` below `GradeItem`:

```ts
export interface GradeAverageItem {
  weighted_average: number | null
}

export interface LoAverageItem {
  lo_code: string
  lo_description?: string
  avg_score: number
}

export interface CourseInsightSummary {
  courseId: number
  courseCode: string
  courseName: string
  studentCount: number
  averageCourseGrade: number | null
  atRiskStudentCount: number
  atRiskStudentRatio: number
  weakestLoCode: string | null
  weakestLoDescription: string
  weakestLoAverageScore: number | null
}
```

- [ ] **Step 2: Rename ambiguous helper parameters**

Update existing helper signatures so score type is explicit:

```ts
export const calculateGradeDistribution = (
  courseGradeAverages: GradeAverageItem[]
): GradeItem[] => {
  const validAverages = courseGradeAverages
    .map(g => g.weighted_average)
    .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)

  if (validAverages.length === 0) {
    return []
  }

  const distribution = {
    A: validAverages.filter(score => score >= 90).length,
    B: validAverages.filter(score => score >= 80 && score < 90).length,
    C: validAverages.filter(score => score >= 70 && score < 80).length,
    D: validAverages.filter(score => score >= 60 && score < 70).length,
    F: validAverages.filter(score => score < 60).length,
  }

  return [
    { grade: 'A', count: distribution.A, color: '#10b981' },
    { grade: 'B', count: distribution.B, color: '#22c55e' },
    { grade: 'C', count: distribution.C, color: '#eab308' },
    { grade: 'D', count: distribution.D, color: '#f97316' },
    { grade: 'F', count: distribution.F, color: '#ef4444' },
  ].filter(item => item.count > 0)
}

export const calculateAverageCourseGrade = (
  courseGradeAverages: GradeAverageItem[]
): number | null => {
  const validAverages = courseGradeAverages
    .map(g => g.weighted_average)
    .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)

  if (validAverages.length === 0) return null
  const total = validAverages.reduce((sum, score) => sum + score, 0)
  return Math.round(total / validAverages.length)
}
```

- [ ] **Step 3: Add at-risk and weakest LO helpers**

Add these helpers to the same file:

```ts
export const countAtRiskStudentsByCourseGrade = (
  courseGradeAverages: GradeAverageItem[],
  threshold = 60,
): number => courseGradeAverages
  .map(g => g.weighted_average)
  .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)
  .filter(averageCourseGrade => averageCourseGrade < threshold).length

export const calculateAtRiskRatioByCourseGrade = (
  courseGradeAverages: GradeAverageItem[],
  threshold = 60,
): number => {
  const validAverages = courseGradeAverages
    .map(g => g.weighted_average)
    .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)

  if (validAverages.length === 0) return 0
  const atRiskCount = validAverages.filter(averageCourseGrade => averageCourseGrade < threshold).length
  return Math.round((atRiskCount / validAverages.length) * 1000) / 10
}

export const findWeakestLoAverageScore = (
  loAverages: LoAverageItem[],
): Pick<CourseInsightSummary, 'weakestLoCode' | 'weakestLoDescription' | 'weakestLoAverageScore'> => {
  if (loAverages.length === 0) {
    return {
      weakestLoCode: null,
      weakestLoDescription: '',
      weakestLoAverageScore: null,
    }
  }

  const weakestLo = [...loAverages].sort((a, b) => a.avg_score - b.avg_score)[0]
  return {
    weakestLoCode: weakestLo.lo_code,
    weakestLoDescription: weakestLo.lo_description ?? '',
    weakestLoAverageScore: Math.round(weakestLo.avg_score),
  }
}
```

- [ ] **Step 4: Preserve backward compatibility locally**

Keep the old helper names as aliases only if other files still import them:

```ts
export const calculateAverageScore = calculateAverageCourseGrade
export const identifyStudentsAtRisk = countAtRiskStudentsByCourseGrade
```

- [ ] **Step 5: Run focused lint**

Run: `npm run lint -- --file frontend/src/features/dashboard/utils/analytics.ts` from the repository root if supported by the project scripts. If that command is not supported, run the existing frontend lint command from `frontend/package.json` and record any pre-existing failures separately.

## Task 2: Instructor Dashboard Cross-Course Insight View

**Files:**
- Modify: `frontend/src/features/dashboard/pages/InstructorDashboard.tsx`
- Modify: `frontend/src/features/dashboard/components/CourseAnalyticsCard.tsx`
- Create: `frontend/src/features/dashboard/components/CourseHealthMatrix.tsx`
- Create: `frontend/src/features/dashboard/components/CourseAttentionList.tsx`

- [ ] **Step 1: Update imports to explicit helper names**

In `InstructorDashboard.tsx`, replace imports from `../utils/analytics` with:

```ts
import {
  calculateGradeDistribution,
  calculateAverageCourseGrade,
  countAtRiskStudentsByCourseGrade,
  calculateAtRiskRatioByCourseGrade,
  findWeakestLoAverageScore,
  type CourseInsightSummary,
} from '../utils/analytics'
```

- [ ] **Step 2: Build course insight summaries**

Inside `InstructorDashboard.tsx`, after `coursesWithAnalytics`, add a memoized summary array:

```ts
const courseInsightSummaries = useMemo<CourseInsightSummary[]>(() => {
  return courses.map((course: Course) => {
    const analytics = analyticsMap.get(course.id)
    const gradeAverages = analytics?.gradeAverages ?? []
    const weakestLo = findWeakestLoAverageScore(analytics?.loAverages ?? [])

    return {
      courseId: course.id,
      courseCode: course.code,
      courseName: course.name,
      studentCount: gradeAverages.length,
      averageCourseGrade: calculateAverageCourseGrade(gradeAverages),
      atRiskStudentCount: countAtRiskStudentsByCourseGrade(gradeAverages),
      atRiskStudentRatio: calculateAtRiskRatioByCourseGrade(gradeAverages),
      ...weakestLo,
    }
  })
}, [analyticsMap, courses])
```

If `analyticsMap` is recreated on every render, wrap its construction in `useMemo` before using it in this memo.

- [ ] **Step 3: Create CourseHealthMatrix component**

Create `frontend/src/features/dashboard/components/CourseHealthMatrix.tsx`:

```tsx
import type { CourseInsightSummary } from '../utils/analytics'
import { Card } from '@/components/ui/custom/Card'

interface CourseHealthMatrixProps {
  courses: CourseInsightSummary[]
  onSelectCourse: (courseId: number) => void
}

export const CourseHealthMatrix = ({ courses, onSelectCourse }: CourseHealthMatrixProps) => {
  return (
    <Card className="overflow-hidden">
      <div className="p-6 border-b border-secondary-200">
        <h2 className="text-lg font-semibold text-secondary-900">Course Health Matrix</h2>
        <p className="text-sm text-secondary-500 mt-1">Average course grade versus at-risk student ratio</p>
      </div>
      <div className="p-6 space-y-3">
        {courses.map(course => {
          const averageCourseGrade = course.averageCourseGrade ?? 0
          return (
            <button
              key={course.courseId}
              type="button"
              onClick={() => onSelectCourse(course.courseId)}
              className="w-full grid grid-cols-[7rem_1fr_5rem] items-center gap-3 text-left rounded-xl border border-secondary-200 p-3 hover:bg-secondary-50 transition-colors"
            >
              <span className="font-semibold text-primary-700">{course.courseCode}</span>
              <span className="relative h-8 rounded-full bg-secondary-100 overflow-hidden">
                <span
                  className="absolute left-0 top-0 h-full bg-primary-500/70"
                  style={{ width: `${Math.min(100, averageCourseGrade)}%` }}
                />
                <span
                  className="absolute top-1/2 -translate-y-1/2 h-5 w-5 rounded-full bg-danger-500 border-2 border-white shadow"
                  style={{ left: `${Math.min(95, course.atRiskStudentRatio)}%` }}
                  title={`${course.atRiskStudentRatio}% at-risk students`}
                />
              </span>
              <span className="text-sm text-secondary-700 text-right">
                {course.averageCourseGrade ?? 'N/A'} avg
              </span>
            </button>
          )
        })}
      </div>
    </Card>
  )
}
```

- [ ] **Step 4: Create CourseAttentionList component**

Create `frontend/src/features/dashboard/components/CourseAttentionList.tsx`:

```tsx
import type { CourseInsightSummary } from '../utils/analytics'
import { Card } from '@/components/ui/custom/Card'

interface CourseAttentionListProps {
  courses: CourseInsightSummary[]
  onSelectCourse: (courseId: number) => void
}

const getAttentionReason = (course: CourseInsightSummary): string => {
  if (course.atRiskStudentRatio >= 30) return `${course.atRiskStudentRatio}% at-risk by average course grade`
  if ((course.averageCourseGrade ?? 100) < 65) return `Low average course grade: ${course.averageCourseGrade}`
  if ((course.weakestLoAverageScore ?? 100) < 65 && course.weakestLoCode) return `Weakest LO: ${course.weakestLoCode} at ${course.weakestLoAverageScore}%`
  return 'Monitor current course progress'
}

export const CourseAttentionList = ({ courses, onSelectCourse }: CourseAttentionListProps) => {
  const sortedCourses = [...courses].sort((a, b) => {
    const aRisk = a.atRiskStudentRatio
    const bRisk = b.atRiskStudentRatio
    if (bRisk !== aRisk) return bRisk - aRisk
    return (a.averageCourseGrade ?? 100) - (b.averageCourseGrade ?? 100)
  })

  return (
    <Card className="overflow-hidden">
      <div className="p-6 border-b border-secondary-200">
        <h2 className="text-lg font-semibold text-secondary-900">Courses Needing Attention</h2>
        <p className="text-sm text-secondary-500 mt-1">Sorted by at-risk ratio and average course grade</p>
      </div>
      <div className="divide-y divide-secondary-100">
        {sortedCourses.map(course => (
          <button
            key={course.courseId}
            type="button"
            onClick={() => onSelectCourse(course.courseId)}
            className="w-full p-4 text-left hover:bg-secondary-50 transition-colors"
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-secondary-900">{course.courseCode} - {course.courseName}</p>
                <p className="text-sm text-secondary-600 mt-1">{getAttentionReason(course)}</p>
              </div>
              <div className="text-right text-sm text-secondary-600">
                <p>{course.atRiskStudentCount}/{course.studentCount} at risk</p>
                <p>Average course grade: {course.averageCourseGrade ?? 'N/A'}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </Card>
  )
}
```

- [ ] **Step 5: Recompose InstructorDashboard**

Place the summary cards, `CourseHealthMatrix`, and `CourseAttentionList` above the selected-course chart card. Update labels to avoid ambiguous `Avg Score`:

```tsx
<CourseAnalyticsCard
  studentCount={totalInstructorStudents}
  averageCourseGrade={overallAverageCourseGrade}
  studentsAtRisk={totalAtRiskStudents}
  atRiskStudentRatio={overallAtRiskStudentRatio}
  courseCount={courseInsightSummaries.length}
/>

<div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
  <CourseHealthMatrix
    courses={courseInsightSummaries}
    onSelectCourse={(courseId) => {
      const nextIndex = coursesWithAnalytics.findIndex(item => item.id === courseId)
      if (nextIndex >= 0) setCurrentIndex(nextIndex)
    }}
  />
  <CourseAttentionList
    courses={courseInsightSummaries}
    onSelectCourse={(courseId) => {
      const nextIndex = coursesWithAnalytics.findIndex(item => item.id === courseId)
      if (nextIndex >= 0) setCurrentIndex(nextIndex)
    }}
  />
</div>
```

Run frontend lint after this task if practical. Do not run full build unless needed for diagnosing type errors.

## Task 3: Course Detail Insight Cards And Clearer Default Charts

**Files:**
- Modify: `frontend/src/features/courses/pages/CourseDetail.tsx`
- Create: `frontend/src/features/courses/components/CourseInsightCards.tsx`

- [ ] **Step 1: Create CourseInsightCards component**

Create `frontend/src/features/courses/components/CourseInsightCards.tsx`:

```tsx
import { Card } from '@/components/ui/custom/Card'

interface CourseInsightCardsProps {
  weakestLoCode: string | null
  weakestLoAverageScore: number | null
  mostDifficultAssessmentName: string | null
  mostDifficultAssessmentAverageScore: number | null
  highestVarianceAssessmentName: string | null
  highestVarianceAssessmentSpread: number | null
  studentsBelowThresholdCount: number
  atRiskThreshold: number
}

export const CourseInsightCards = ({
  weakestLoCode,
  weakestLoAverageScore,
  mostDifficultAssessmentName,
  mostDifficultAssessmentAverageScore,
  highestVarianceAssessmentName,
  highestVarianceAssessmentSpread,
  studentsBelowThresholdCount,
  atRiskThreshold,
}: CourseInsightCardsProps) => {
  const cards = [
    {
      label: 'Weakest LO average score',
      value: weakestLoCode ? `${weakestLoCode}: ${weakestLoAverageScore ?? 'N/A'}%` : 'N/A',
      tone: 'text-indigo-700 bg-indigo-50 border-indigo-200',
    },
    {
      label: 'Lowest assessment average score',
      value: mostDifficultAssessmentName ? `${mostDifficultAssessmentName}: ${mostDifficultAssessmentAverageScore ?? 'N/A'}%` : 'N/A',
      tone: 'text-rose-700 bg-rose-50 border-rose-200',
    },
    {
      label: 'Highest assessment score spread',
      value: highestVarianceAssessmentName ? `${highestVarianceAssessmentName}: ${highestVarianceAssessmentSpread ?? 'N/A'} pts` : 'N/A',
      tone: 'text-amber-700 bg-amber-50 border-amber-200',
    },
    {
      label: `Students below ${atRiskThreshold}% course grade`,
      value: String(studentsBelowThresholdCount),
      tone: 'text-violet-700 bg-violet-50 border-violet-200',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map(card => (
        <Card key={card.label} variant="flat" className={`border ${card.tone}`}>
          <p className="text-xs font-semibold uppercase tracking-wide opacity-80">{card.label}</p>
          <p className="mt-2 text-2xl font-bold">{card.value}</p>
        </Card>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Compute explicit course detail insights**

In `CourseDetail.tsx`, import `CourseInsightCards`, then add memoized calculations before render:

```ts
const atRiskCourseGradeThreshold = 60

const weakestLoInsight = useMemo(() => {
  if (!data?.learningOutcomes) return { code: null, averageLoScore: null }
  const ranked = data.learningOutcomes
    .map(lo => ({ code: lo.code, averageLoScore: getLOPerformance(lo.code) }))
    .filter(item => item.averageLoScore > 0)
    .sort((a, b) => a.averageLoScore - b.averageLoScore)
  return ranked[0] ?? { code: null, averageLoScore: null }
}, [data?.learningOutcomes, data?.loScores])

const assessmentDifficultyInsights = useMemo(() => {
  const rankedByAverage = [...assessmentRadarData].sort((a, b) => a.avg - b.avg)
  const rankedBySpread = [...assessmentBoxPlotData]
    .map(item => ({ name: item.code, spread: Math.round((item.max - item.min) * 10) / 10 }))
    .sort((a, b) => b.spread - a.spread)

  return {
    mostDifficultAssessment: rankedByAverage[0] ?? null,
    highestSpreadAssessment: rankedBySpread[0] ?? null,
  }
}, [assessmentRadarData, assessmentBoxPlotData])

const studentsBelowCourseGradeThreshold = useMemo(() => {
  return Array.from(studentDataMap.values())
    .filter(student => student.overallScore > 0 && student.overallScore < atRiskCourseGradeThreshold)
    .length
}, [studentDataMap])
```

- [ ] **Step 3: Render insight cards below CourseHeader**

Insert after `CourseHeader`:

```tsx
<CourseInsightCards
  weakestLoCode={weakestLoInsight.code}
  weakestLoAverageScore={weakestLoInsight.averageLoScore}
  mostDifficultAssessmentName={assessmentDifficultyInsights.mostDifficultAssessment?.name ?? null}
  mostDifficultAssessmentAverageScore={assessmentDifficultyInsights.mostDifficultAssessment?.avg ?? null}
  highestVarianceAssessmentName={assessmentDifficultyInsights.highestSpreadAssessment?.name ?? null}
  highestVarianceAssessmentSpread={assessmentDifficultyInsights.highestSpreadAssessment?.spread ?? null}
  studentsBelowThresholdCount={studentsBelowCourseGradeThreshold}
  atRiskThreshold={atRiskCourseGradeThreshold}
/>
```

- [ ] **Step 4: Make sorted bars the default for assessment analysis**

Change `assessmentChartView` state to include `bar` and default to `bar`:

```ts
const [assessmentChartView, setAssessmentChartView] = useState<'bar' | 'radar' | 'boxplot' | 'heatmap'>('bar')
```

Add a button labeled `Difficulty Bars`, and render a horizontal sorted bar list for `assessmentChartView === 'bar'`:

```tsx
{assessmentChartView === 'bar' && (
  <div className="space-y-3">
    {[...assessmentRadarData].sort((a, b) => a.avg - b.avg).map(assessment => (
      <div key={assessment.id} className="grid grid-cols-[12rem_1fr_4rem] items-center gap-3">
        <span className="text-sm font-medium text-secondary-700 truncate">{assessment.name}</span>
        <div className="h-3 rounded-full bg-secondary-100 overflow-hidden">
          <div className="h-full rounded-full bg-primary-500" style={{ width: `${Math.min(100, assessment.avg)}%` }} />
        </div>
        <span className="text-sm font-semibold text-secondary-900 text-right">{assessment.avg}%</span>
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 5: Rename visible ambiguous labels**

In `CourseDetail.tsx`, replace visible generic labels:

- `Overall Course Score` -> `Overall course grade`
- `Score` in assessment score table -> `Assessment score (%)`
- `Score` in LO score table -> `LO score (%)`
- Any chart label `Average Score` -> `Assessment average score` or `Average LO score` depending on chart data.

Run frontend lint after this task if practical.

## Task 4: Head Dashboard Outcome Monitoring Refinement

**Files:**
- Modify: `frontend/src/features/dashboard/pages/HeadDashboard.tsx`

- [ ] **Step 1: Rename ambiguous program score variables and labels**

In `HeadDashboard.tsx`, rename `overallAvg` to `overallAveragePoScore` because it is derived from `ProgramStat.avg_score`, which the backend calculates from `StudentProgramOutcomeScore`.

Update visible card text:

```tsx
<p className="text-sm text-secondary-600 font-medium">Average PO Score</p>
<p className="text-3xl font-bold text-secondary-900">
  {overallAveragePoScore !== null ? overallAveragePoScore.toFixed(2) : 'N/A'}
</p>
```

- [ ] **Step 2: Demote year-level student count pie chart**

Replace the large `Year-Level Breakdown` pie chart with a compact card list:

```tsx
<Card variant="flat" className="bg-white border-secondary-200">
  <h2 className="text-lg font-semibold text-secondary-900 mb-4">Year-Level Context</h2>
  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
    {yearLevelBreakdown.map(item => (
      <div key={item.year} className="rounded-xl bg-secondary-50 p-3">
        <p className="text-xs text-secondary-500">Year {item.year}</p>
        <p className="text-xl font-bold text-secondary-900">{item.student_count}</p>
        <p className="text-xs text-secondary-500">students</p>
      </div>
    ))}
  </div>
</Card>
```

- [ ] **Step 3: Make PO progression explicit**

Rename chart titles and series labels:

```tsx
title="Average GPA by Year Level"
subtitle="Credit-weighted average GPA on the 4.0 scale"
name="Average GPA"
```

For PO:

```tsx
title="Average PO Score by Year Level"
subtitle="Average program outcome score by enrolled student year level"
name="Average PO Score"
```

- [ ] **Step 4: Add weakest year-level PO context card**

Compute the lowest year-level Average PO score:

```ts
const weakestYearLevelPoScore = useMemo(() => {
  return yearLevelBreakdown
    .filter(item => item.avg_score !== null)
    .sort((a, b) => (a.avg_score ?? 0) - (b.avg_score ?? 0))[0] ?? null
}, [yearLevelBreakdown])
```

Render a summary card near the top metrics:

```tsx
<Card variant="flat" className="bg-amber-50 border-amber-200">
  <p className="text-sm text-amber-700 font-medium">Weakest Year-Level PO Score</p>
  <p className="text-3xl font-bold text-amber-900">
    {weakestYearLevelPoScore ? `Year ${weakestYearLevelPoScore.year}` : 'N/A'}
  </p>
  <p className="text-sm text-amber-700 mt-1">
    Average PO score: {weakestYearLevelPoScore?.avg_score ?? 'N/A'}
  </p>
</Card>
```

- [ ] **Step 5: Run focused lint**

Run frontend lint after this task if practical. Do not run full build unless lint/type errors indicate it is needed.

## Task 5: Final Consistency Pass And Documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-05-17-dashboard-statistics-design.md` if implementation decisions changed.
- Modify: `docs/superpowers/plans/2026-05-17-dashboard-statistics.md` if task execution finds necessary corrections.
- Inspect: `frontend/src/features/dashboard/pages/InstructorDashboard.tsx`
- Inspect: `frontend/src/features/courses/pages/CourseDetail.tsx`
- Inspect: `frontend/src/features/dashboard/pages/HeadDashboard.tsx`

- [ ] **Step 1: Search for ambiguous frontend labels**

Search frontend files touched in this plan for ambiguous labels:

```bash
rg "Avg Score|Average Score|avgScore|overallAvg|Score Averages" frontend/src/features/dashboard frontend/src/features/courses
```

Rename matches according to the data source:

- GPA data -> `Average GPA`.
- `StudentLearningOutcomeScore` data -> `Average LO score` or `LO score (%)`.
- `StudentProgramOutcomeScore` data -> `Average PO score` or `PO score (%)`.
- `StudentGrade` weighted averages -> `Average course grade`.
- Assessment percentage data -> `Assessment average score` or `Assessment score (%)`.

- [ ] **Step 2: Check chart defaults against responsibilities**

Verify these page defaults manually in code:

- Instructor dashboard first shows cross-course insight, not only a selected-course carousel.
- Course detail first shows insight cards and assessment difficulty bars before optional radar.
- Head dashboard uses student count by year only as context, not the main visual.

- [ ] **Step 3: Run lint once for the touched frontend area**

Run the repository's frontend lint command. If the exact command is unclear, inspect `frontend/package.json` and use its lint script. Record pre-existing unrelated failures separately.

- [ ] **Step 4: Update design documentation if implementation differed**

If implementation chose a different threshold, chart default, or derivation method, update `docs/superpowers/specs/2026-05-17-dashboard-statistics-design.md` with the actual decision. Keep the task count unchanged.

- [ ] **Step 5: Prepare final summary**

Summarize changed pages and explicitly name score types in the final message:

- Instructor dashboard: average course grade, at-risk ratio by average course grade, weakest LO average score.
- Course detail: weakest LO average score, lowest assessment average score, highest assessment score spread, students below course-grade threshold.
- Head dashboard: Average PO score and Average GPA labels.

Do not commit unless the user explicitly asks for a commit.

## Self-Review Notes

- Spec coverage: This plan covers instructor dashboard improvements first, course detail insight cards/chart defaults second, and head dashboard outcome monitoring third. It preserves existing pages and avoids creating a new term progress page.
- Placeholder scan: The plan contains concrete files, code snippets, labels, and commands. No placeholder implementation tasks remain.
- Type consistency: Shared helper names use explicit score types. UI labels distinguish Average GPA, Average PO score, Average LO score, Average course grade, and Assessment average score.
