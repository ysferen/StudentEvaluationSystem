import { evaluationEnrollmentsList } from './generated/evaluation/evaluation'
import type {
  CourseEnrollment,
  EvaluationEnrollmentsListParams,
  PaginatedCourseEnrollmentList,
} from './model'

export type CourseEnrollmentsData = Omit<PaginatedCourseEnrollmentList, 'results'> & {
  results: CourseEnrollment[]
}

export const fetchAllEvaluationEnrollments = async (
  params: Omit<EvaluationEnrollmentsListParams, 'page'>
): Promise<CourseEnrollmentsData> => {
  const results: CourseEnrollment[] = []
  let page = 1
  let firstPage: PaginatedCourseEnrollmentList | null = null
  let hasNextPage = true

  while (hasNextPage) {
    const response = await evaluationEnrollmentsList({ ...params, page })
    if (!firstPage) {
      firstPage = response
    }
    results.push(...(response.results || []))
    hasNextPage = Boolean(response.next)
    page += 1
  }

  return {
    count: firstPage?.count ?? results.length,
    next: null,
    previous: null,
    results,
  }
}
