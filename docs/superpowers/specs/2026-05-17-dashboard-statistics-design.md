# Dashboard Statistics Design

## Goal

Improve existing SES dashboard and course detail pages so instructors and program heads get stronger analytical insight from assessment, LO, and PO score data. Do not create a new term progress page. Keep responsibilities separated across existing pages.

All UI labels and plan/code names must avoid ambiguous score wording. Use explicit labels such as Average GPA, Average LO score, Average PO score, Average course grade, and Assessment average score instead of generic labels like Avg score or Average score.

## Page Responsibilities

### Instructor Dashboard

The instructor dashboard is the instructor's cross-course insight and triage page. It should answer: "Which of my courses need attention, and why?"

It should compare all courses first, then allow the instructor to inspect one selected course. The current single-course carousel can remain as a secondary detail preview, but it should not be the only analytical structure.

Recommended statistics:

- Total active courses.
- Total enrolled students across the instructor's courses.
- Overall average across instructor courses. Use a simple mean in the first iteration because existing dashboard calculations already use unweighted course averages; introduce credit weighting later only if the UI explicitly labels it.
- Total and percentage of at-risk students.
- Course health matrix: average score versus at-risk ratio, with student count as visual weight.
- Weakest LO per course.
- Grade distribution per course or across all courses.
- Courses needing attention, sorted by weak LO score, low average, or high at-risk ratio.
- Grading/completion coverage where derivable from current assessment and grade data: completed grade entries divided by expected grade entries for enrolled students and published assessments.

Low-value statistics should be demoted. Credits alone are not a primary insight unless used as a weighting factor.

### Course Detail Page

The course detail page is the deep analysis workspace for one course. It should answer: "Inside this course, what exactly is happening across assessments, LOs, and students?"

The current implementation is directionally good. It already includes LO and assessment radar charts, box plots, heatmaps, student tables, and per-student drill-down. The main improvement is to make charts more insight-driven and less decorative.

Recommended statistics:

- Insight cards: weakest LO, most difficult assessment, highest variance assessment, and students below threshold.
- LO analysis: keep heatmap and box plot; add or prefer a sorted LO bar chart for clearer ranking.
- Assessment analysis: replace assessment radar as the default with sorted assessment difficulty bars.
- Assessment heatmap and assessment box plot remain useful because they expose student-level performance and score spread.
- Student drill-down remains useful and should stay.
- Threshold-based filtering can be added later for students below 50, 60, or 70. The first iteration should use 60 as the default at-risk threshold to match current dashboard logic.

Radar charts may remain as an optional view, but should not be the default for assessments because sorted bars communicate difficulty and ranking more clearly.

### Head Dashboard

The head dashboard is the program-level outcome monitoring page. It should answer: "Across the program, where is performance improving or weakening?"

Recommended statistics:

- Program average.
- Total students and active courses as compact summary context.
- At-risk course count or at-risk student ratio across the program.
- Weakest POs across the program.
- PO attainment by year level.
- Course health list or matrix across the program.
- GPA or score by year level if it helps explain progression.
- Mapping and coverage completeness where derivable from existing LO, PO, assessment, and mapping data.

Student count by year is useful context, but it should be a side widget rather than a primary chart. Raw counts should support the main analysis, not dominate the page.

## Statistics Priority

High-value statistics:

- At-risk ratio per course.
- Weakest LO per course.
- Weakest PO per program or year level.
- Assessment average and pass rate.
- Score variance and score spread.
- Grade completion rate.
- Assessment-to-LO and LO-to-PO coverage completeness.
- Threshold counts for students below 50, 60, or 70.

Medium-value statistics:

- Median score.
- Pass/fail ratio.
- Best and worst performing LO.
- Course weighted average by credits.
- Student count by year or course.

Low-value as primary graphs:

- Raw counts without interpretation.
- Pie charts for simple counts.
- Credits alone.
- Instructor count alone.

## Recommended Implementation Sequence

1. Improve instructor dashboard first because instructor insight is the main goal.
2. Improve course detail second by adding insight cards and making sorted bars the default where radar charts are weak.
3. Improve head dashboard third by promoting PO/course-risk analysis and demoting count-based charts.

## Non-Goals

- Do not create a new term progress page in this iteration.
- Do not split analytics into many new pages unless the existing pages become too dense after targeted improvements.
- Do not remove existing useful course detail views such as heatmaps, box plots, or student drill-down.
- Do not manually edit generated API client files.

## Implementation Decisions

- Use 60 as the initial at-risk threshold because current instructor analytics already classifies students below 60 as at risk.
- Use simple course averages first unless a chart explicitly communicates credit weighting.
- Derive grading completion from existing data if feasible; if it requires excessive client-side requests, defer it behind a backend endpoint rather than adding a slow frontend query fan-out.
- Reuse existing analytics calculations for instructor views first. Add dedicated backend aggregation endpoints only when the frontend would otherwise need many per-course requests or duplicated business logic.
