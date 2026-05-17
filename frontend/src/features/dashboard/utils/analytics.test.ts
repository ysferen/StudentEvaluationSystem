import { describe, expect, it } from 'vitest'

import {
  calculateAtRiskRatioByCourseGrade,
  calculateAverageCourseGrade,
  calculateGradeDistribution,
  countAtRiskStudentsByCourseGrade,
  findWeakestLoAverageScore,
} from './analytics'

describe('dashboard analytics helpers', () => {
  it('calculates grade distribution from average course grades', () => {
    expect(
      calculateGradeDistribution([
        { averageCourseGrade: 95 },
        { averageCourseGrade: 85 },
        { averageCourseGrade: 75 },
        { averageCourseGrade: 65 },
        { averageCourseGrade: 55 },
        { averageCourseGrade: null },
      ]),
    ).toEqual([
      { grade: 'A', count: 1, color: '#10b981' },
      { grade: 'B', count: 1, color: '#22c55e' },
      { grade: 'C', count: 1, color: '#eab308' },
      { grade: 'D', count: 1, color: '#f97316' },
      { grade: 'F', count: 1, color: '#ef4444' },
    ])
  })

  it('calculates average course grade and returns null when no valid grades exist', () => {
    expect(
      calculateAverageCourseGrade([
        { averageCourseGrade: 70 },
        { averageCourseGrade: 81 },
        { averageCourseGrade: null },
      ]),
    ).toBe(76)

    expect(calculateAverageCourseGrade([{ averageCourseGrade: null }])).toBeNull()
  })

  it('counts at-risk students and calculates percentage ratio by average course grade', () => {
    const courseGradeAverages = [
      { averageCourseGrade: 59 },
      { averageCourseGrade: 60 },
      { averageCourseGrade: 40 },
      { averageCourseGrade: null },
    ]

    expect(countAtRiskStudentsByCourseGrade(courseGradeAverages)).toBe(2)
    expect(calculateAtRiskRatioByCourseGrade(courseGradeAverages)).toBe(66.7)
    expect(calculateAtRiskRatioByCourseGrade([{ averageCourseGrade: null }])).toBe(0)
  })

  it('finds the weakest LO average score with explicit fields', () => {
    expect(
      findWeakestLoAverageScore([
        { loCode: 'LO1', loDescription: 'Strong topic', averageLoScore: 82 },
        { loCode: 'LO2', averageLoScore: 54.4 },
      ]),
    ).toEqual({
      weakestLoCode: 'LO2',
      weakestLoDescription: '',
      weakestLoAverageScore: 54,
    })

    expect(findWeakestLoAverageScore([])).toEqual({
      weakestLoCode: null,
      weakestLoDescription: '',
      weakestLoAverageScore: null,
    })
  })
})
