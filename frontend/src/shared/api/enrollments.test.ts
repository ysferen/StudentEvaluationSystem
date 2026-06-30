import { beforeEach, describe, expect, it, vi } from 'vitest'
import { evaluationEnrollmentsList } from './generated/evaluation/evaluation'
import { fetchAllEvaluationEnrollments } from './enrollments'
import type { CourseEnrollment, PaginatedCourseEnrollmentList } from './model'

vi.mock('./generated/evaluation/evaluation', () => ({
  evaluationEnrollmentsList: vi.fn(),
}))

const mockEvaluationEnrollmentsList = vi.mocked(evaluationEnrollmentsList)

const enrollment = (id: number): CourseEnrollment => ({
  id,
  student: `Student ${id}`,
  student_id: id,
  course: { id: 10 } as CourseEnrollment['course'],
  enrolled_at: '2026-05-22T00:00:00Z',
})

const page = (
  results: CourseEnrollment[],
  next: string | null
): PaginatedCourseEnrollmentList => ({
  count: 3,
  next,
  previous: null,
  results,
})

describe('fetchAllEvaluationEnrollments', () => {
  beforeEach(() => {
    mockEvaluationEnrollmentsList.mockReset()
  })

  it('fetches every enrollment page and returns one combined result set', async () => {
    mockEvaluationEnrollmentsList
      .mockResolvedValueOnce(page([enrollment(1), enrollment(2)], '/api/evaluation/enrollments/?page=2'))
      .mockResolvedValueOnce(page([enrollment(3)], null))

    const result = await fetchAllEvaluationEnrollments({ course: 10 })

    expect(mockEvaluationEnrollmentsList).toHaveBeenNthCalledWith(1, { course: 10, page: 1 })
    expect(mockEvaluationEnrollmentsList).toHaveBeenNthCalledWith(2, { course: 10, page: 2 })
    expect(result).toEqual({
      count: 3,
      next: null,
      previous: null,
      results: [enrollment(1), enrollment(2), enrollment(3)],
    })
  })
})
