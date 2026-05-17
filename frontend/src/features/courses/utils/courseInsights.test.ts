import { describe, expect, it } from 'vitest'

import {
  calculateCourseGradeFromAssessmentGrades,
  findWeakestLoAverageScore,
} from './courseInsights'

describe('course detail insight calculations', () => {
  it('uses positive assessment weights for course grade and includes 0% as below-threshold data', () => {
    const courseGrade = calculateCourseGradeFromAssessmentGrades([
      { score: 0, assessment: { total_score: 100, weight: 40 } },
      { score: 90, assessment: { total_score: 100, weight: 60 } },
    ])

    expect(courseGrade).toBe(54)
  })

  it('falls back to simple assessment percentage mean when no positive weights exist', () => {
    const courseGrade = calculateCourseGradeFromAssessmentGrades([
      { score: 0, assessment: { total_score: 100, weight: 0 } },
      { score: 80, assessment: { total_score: 100, weight: null } },
    ])

    expect(courseGrade).toBe(40)
  })

  it('selects a 0% LO average as the weakest valid LO', () => {
    const weakestLo = findWeakestLoAverageScore(
      [
        { code: 'LO1' },
        { code: 'LO2' },
      ],
      [
        { learning_outcome: { code: 'LO1' }, score: 88 },
        { learning_outcome: { code: 'LO2' }, score: 0 },
      ],
    )

    expect(weakestLo).toEqual({ code: 'LO2', averageLoScore: 0 })
  })
})
