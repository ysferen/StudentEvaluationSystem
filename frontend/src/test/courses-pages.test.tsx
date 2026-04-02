import { describe, it } from 'vitest';

// Test activation guide:
// 1. Replace `it.skip` with `it` when implementing.
// 2. Use Arrange / Act / Assert structure in each test.
// 3. Prefer MSW handlers for API behavior instead of mocking internals.
// 4. Keep one user-visible behavior per test case.

describe('Courses pages', () => {
  it.skip('StudentCourses should render enrolled courses and support empty state', () => {
    // TODO(TEST): Implement scenario - courses/student/list-and-empty-state
    // This test will render the student courses page.
    // It will verify that a list of enrolled courses is visible when data exists.
    // It will also verify that a clear empty-state message is shown when no courses exist.
    // It will verify that loading and error UI states are handled correctly.
  });

  it.skip('StudentCourseDetail should show course sections and learning outcomes', () => {
    // TODO(TEST): Implement scenario - courses/student/detail-sections-and-fallback
    // This test will render a specific student course detail page by route id.
    // It will verify that course metadata, assessments, and learning outcomes are shown.
    // It will verify that missing or invalid course id shows a graceful fallback.
  });

  it.skip('InstructorCourses should show instructor-owned courses and navigation actions', () => {
    // TODO(TEST): Implement scenario - courses/instructor/owned-list-and-navigation
    // This test will render instructor courses.
    // It will verify only instructor-relevant courses are displayed.
    // It will verify navigation actions open the selected course detail page.
  });

  it.skip('HeadCourses should show department-wide course oversight data', () => {
    // TODO(TEST): Implement scenario - courses/head/department-oversight-and-filters
    // This test will render head courses page.
    // It will verify department-level course list appears with summary metrics.
    // It will verify filters or sorting update the visible list correctly.
  });

  it.skip('CourseDetail should show assessment mapping editor and update feedback', () => {
    // TODO(TEST): Implement scenario - courses/shared/detail-editor-and-save-feedback
    // This test will render the shared course detail page used by instructor or head.
    // It will verify key sections (assessments, mappings, scores) are visible.
    // It will verify submit/save actions display success and error feedback.
  });
});
