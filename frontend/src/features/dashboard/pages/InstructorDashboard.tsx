import { useMemo, useState, useCallback } from 'react'
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query'
import ConfirmDeleteModal from '@/components/ui/custom/ConfirmDeleteModal'
import CreateEditLOModal from '../../courses/components/CreateEditLOModal'
import { LearningOutcomesPanel } from '../../courses/components/LearningOutcomesPanel'
import { useAuth } from '../../auth/hooks/useAuth'
import {
  coreCoursesList,
  coreStudentLoScoresLoAveragesRetrieve
} from '../../../shared/api/generated/core/core'
import { evaluationGradesCourseAveragesRetrieve } from '../../../shared/api/generated/evaluation/evaluation'
import { coreLearningOutcomesDestroy, coreLearningOutcomesList } from '../../../shared/api/generated/outcomes/outcomes'
import { isRecord } from '@/shared/utils/guards'
import { CourseAnalyticsCard } from '../components/CourseAnalyticsCard'
import { CourseHealthMatrix } from '../components/CourseHealthMatrix'
import { CourseAttentionList } from '../components/CourseAttentionList'
import {
  calculateGradeDistribution,
  calculateAverageCourseGrade,
  countAtRiskStudentsByCourseGrade,
  calculateAtRiskRatioByCourseGrade,
  findWeakestLoAverageScore,
  normalizeCourseGradeAverages,
  normalizeLoAverages,
  type CourseInsightSummary,
} from '../utils/analytics'
import type { Course } from '../../../shared/api/model/course'
import type { CoreLearningOutcome } from '../../../shared/api/model/coreLearningOutcome'

interface LoAverageItem {
  lo_code: string
  lo_description?: string
  avg_score: number
}

const toLoAverages = (value: unknown): LoAverageItem[] => {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .filter((item): item is LoAverageItem => (
      isRecord(item)
      && typeof item.lo_code === 'string'
      && typeof item.avg_score === 'number'
    ))
    .map(item => ({
      lo_code: item.lo_code,
      lo_description: typeof item.lo_description === 'string' ? item.lo_description : '',
      avg_score: item.avg_score
    }))
}

interface CourseWithAnalytics extends Course {
  students?: number
  averageCourseGrade?: number | null
  studentsAtRisk?: number
  weight?: number
  loScores?: Array<{ lo: string; description: string; score: number }>
  gradeDistribution?: Array<{ grade: string; count: number; color: string }>
  learningOutcomes?: CoreLearningOutcome[]
}

interface CourseAnalytics {
  courseId: number
  loAverages: LoAverageItem[]
  gradeAverages: Array<{ weighted_average: number | null }>
  learningOutcomes: CoreLearningOutcome[]
}

const countValidCourseGradeAverages = (
  courseGradeAverages: Array<{ averageCourseGrade: number | null }>
): number => courseGradeAverages.filter(({ averageCourseGrade }) => averageCourseGrade !== null).length

const InstructorDashboard = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loCreateModalOpen, setLoCreateModalOpen] = useState(false)
  const [loEditTarget, setLoEditTarget] = useState<CoreLearningOutcome | null>(null)
  const [loDeleteTarget, setLoDeleteTarget] = useState<CoreLearningOutcome | null>(null)

  const canCreateLO = user?.permissions?.includes('learning_outcomes.add_learningoutcome') ?? false
  const canEditLO = user?.permissions?.includes('learning_outcomes.change_learningoutcome') ?? false
  const canDeleteLO = user?.permissions?.includes('learning_outcomes.delete_learningoutcome') ?? false

  // Fetch courses for the instructor using orval
  const { data: coursesData, isLoading: coursesLoading } = useQuery({
    queryKey: ['instructor-courses', user?.id],
    queryFn: async () => {
      // Pass instructor filter via params in options (second parameter)
      const response = await coreCoursesList(undefined, { params: { instructor: user?.id } })
      return response.results || []
    },
    enabled: !!user?.id
  })

  const courses = useMemo(() => Array.isArray(coursesData) ? coursesData : [], [coursesData])

  // Fetch analytics for all courses in parallel using orval raw functions
  const analyticsQueries = useQueries({
    queries: courses.map((course: Course) => ({
      queryKey: ['course-analytics', course.id],
      queryFn: async (): Promise<CourseAnalytics> => {
        const [loAveragesRes, gradeAveragesRes, learningOutcomesRes] = await Promise.all([
          coreStudentLoScoresLoAveragesRetrieve({ params: { course: course.id } }),
          evaluationGradesCourseAveragesRetrieve({ course: course.id, per_student: true }),
          coreLearningOutcomesList({ course: course.id }),
        ])
        return {
          courseId: course.id,
          loAverages: toLoAverages(loAveragesRes),
          gradeAverages: Array.isArray(gradeAveragesRes) ? gradeAveragesRes : [],
          learningOutcomes: learningOutcomesRes.results || [],
        }
      },
      retry: 1,
      enabled: !!courses.length
    }))
  })

  const currentAnalytics = analyticsQueries[currentIndex]
  const analyticsError = currentAnalytics?.isError ?? false
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'there'

  const analyticsMap = useMemo(() => {
    const map = new Map<number, CourseAnalytics>()
    analyticsQueries.forEach((query, index) => {
      if (query.data && courses[index]) {
        map.set(courses[index].id, query.data as CourseAnalytics)
      }
    })
    return map
  }, [analyticsQueries, courses])

  const coursesWithAnalytics: CourseWithAnalytics[] = useMemo(() => courses.map((course: Course) => {
    const analytics = analyticsMap.get(course.id)

    if (!analytics) {
      return {
        ...course,
        students: 0,
        averageCourseGrade: null,
        studentsAtRisk: 0,
        weight: course.credits || 1,
        loScores: [],
        gradeDistribution: [],
        learningOutcomes: [],
      }
    }

    const courseGradeAverages = normalizeCourseGradeAverages(analytics.gradeAverages)
    const aggregatedLOScores = normalizeLoAverages(analytics.loAverages).map((lo) => ({
      lo: lo.loCode,
      description: lo.loDescription || '',
      score: Math.round(lo.averageLoScore)
    }))

    const studentCountWithGradeData = countValidCourseGradeAverages(courseGradeAverages)

    return {
      ...course,
      students: studentCountWithGradeData,
      averageCourseGrade: calculateAverageCourseGrade(courseGradeAverages),
      studentsAtRisk: countAtRiskStudentsByCourseGrade(courseGradeAverages),
      weight: course.credits || 1,
      loScores: aggregatedLOScores,
      gradeDistribution: calculateGradeDistribution(courseGradeAverages),
      learningOutcomes: analytics.learningOutcomes,
    }
  }), [analyticsMap, courses])

  const courseInsightSummaries = useMemo<CourseInsightSummary[]>(() => {
    return courses.map((course: Course) => {
      const analytics = analyticsMap.get(course.id)
      const gradeAverages = normalizeCourseGradeAverages(analytics?.gradeAverages ?? [])
      const weakestLo = findWeakestLoAverageScore(normalizeLoAverages(analytics?.loAverages ?? []))
      const studentCountWithGradeData = countValidCourseGradeAverages(gradeAverages)

      return {
        courseId: course.id,
        courseCode: course.code,
        courseName: course.name,
        studentCount: studentCountWithGradeData,
        averageCourseGrade: calculateAverageCourseGrade(gradeAverages),
        atRiskStudentCount: countAtRiskStudentsByCourseGrade(gradeAverages),
        atRiskStudentRatio: calculateAtRiskRatioByCourseGrade(gradeAverages),
        ...weakestLo,
      }
    })
  }, [analyticsMap, courses])

  const overallCourseGradeAverages = useMemo(() => {
    return courses.flatMap((course: Course) => (
      normalizeCourseGradeAverages(analyticsMap.get(course.id)?.gradeAverages ?? [])
    ))
  }, [analyticsMap, courses])

  const totalInstructorStudents = countValidCourseGradeAverages(overallCourseGradeAverages)
  const overallAverageCourseGrade = calculateAverageCourseGrade(overallCourseGradeAverages)
  const totalAtRiskStudents = countAtRiskStudentsByCourseGrade(overallCourseGradeAverages)
  const overallAtRiskStudentRatio = calculateAtRiskRatioByCourseGrade(overallCourseGradeAverages)
  const attentionCourseCount = courseInsightSummaries.filter(course => (
    course.atRiskStudentRatio >= 30
    || (course.averageCourseGrade ?? 100) < 65
    || ((course.weakestLoAverageScore ?? 100) < 65 && Boolean(course.weakestLoCode))
  )).length

  const selectCourseById = useCallback((courseId: number) => {
    const nextIndex = coursesWithAnalytics.findIndex(item => item.id === courseId)
    if (nextIndex >= 0) setCurrentIndex(nextIndex)
  }, [coursesWithAnalytics])

  const course = coursesWithAnalytics[currentIndex] || {
    code: 'No Course',
    name: 'No courses available',
    students: 0,
    averageCourseGrade: null,
    studentsAtRisk: 0,
    weight: 0,
    loScores: [],
    gradeDistribution: []
  }

  const selectedCourseLearningOutcomes = course.learningOutcomes || []

  const selectedCourseAverageScoresByCode = useMemo(() => (
    (course.loScores || []).reduce<Record<string, number>>((acc, lo) => {
      acc[lo.lo] = lo.score
      return acc
    }, {})
  ), [course.loScores])

  // Get loading state for current course analytics
  const currentCourseAnalyticsLoading = courses.length > 0 && currentIndex < analyticsQueries.length
    ? analyticsQueries[currentIndex]?.isLoading
    : false

  const handleLOSuccess = useCallback(() => {
    setLoCreateModalOpen(false)
    setLoEditTarget(null)
    queryClient.invalidateQueries({ queryKey: ['course-analytics', course.id] })
  }, [course.id, queryClient])

  const handleLODelete = useCallback(async () => {
    if (!loDeleteTarget) return
    await coreLearningOutcomesDestroy(loDeleteTarget.id)
    setLoDeleteTarget(null)
    queryClient.invalidateQueries({ queryKey: ['course-analytics', course.id] })
  }, [course.id, loDeleteTarget, queryClient])

  // Loading state
  if (coursesLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto" />
          <p className="mt-4 text-secondary-600 font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Main Content */}
      <main className="p-6 max-w-7xl mx-auto space-y-8">
        {/* Hero/Welcome Section */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-primary-600 to-primary-800 p-8 text-white shadow-lg">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex-1">
              <h1 className="text-3xl font-bold mb-2">Welcome, {displayName}</h1>
              <p className="text-primary-100 text-lg">Cross-course insight summary and selected-course detail</p>
            </div>
          </div>
          <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform origin-bottom-right" />
          <div className="absolute right-20 top-0 h-full w-1/3 bg-white/5 skew-x-12 transform origin-bottom-right" />
        </div>

        {/* Stats Row */}
        <CourseAnalyticsCard
          studentCount={totalInstructorStudents}
          averageCourseGrade={overallAverageCourseGrade}
          studentsAtRisk={totalAtRiskStudents}
          atRiskStudentRatio={overallAtRiskStudentRatio}
          courseCount={courseInsightSummaries.length}
          attentionCourseCount={attentionCourseCount}
        />

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <CourseHealthMatrix
            courses={courseInsightSummaries}
            selectedCourseId={course.id}
            onSelectCourse={selectCourseById}
          />
          <CourseAttentionList
            courses={courseInsightSummaries}
            selectedCourseId={course.id}
            onSelectCourse={selectCourseById}
          />
        </div>

        <LearningOutcomesPanel
          title={`Selected Course: ${course.code}`}
          subtitle={course.name}
          learningOutcomes={selectedCourseLearningOutcomes}
          averageScoresByCode={selectedCourseAverageScoresByCode}
          courseId={course.id}
          isLoading={currentCourseAnalyticsLoading}
          errorMessage={analyticsError ? 'Failed to load analytics for this course' : null}
          canCreate={canCreateLO && Boolean(course.id)}
          canEdit={canEditLO}
          canDelete={canDeleteLO}
          onCreate={() => setLoCreateModalOpen(true)}
          onEdit={(lo) => setLoEditTarget(lo as CoreLearningOutcome)}
          onDelete={(lo) => setLoDeleteTarget(lo as CoreLearningOutcome)}
          emptyMessage="Learning outcomes for this course will appear here once defined."
        />

        {course.id && (
          <>
            <CreateEditLOModal
              isOpen={loCreateModalOpen}
              onClose={() => setLoCreateModalOpen(false)}
              onSuccess={handleLOSuccess}
              mode="create"
              courseId={course.id}
              courseTemplateId={course.course_template_id ?? null}
            />
            <CreateEditLOModal
              isOpen={!!loEditTarget}
              onClose={() => setLoEditTarget(null)}
              onSuccess={handleLOSuccess}
              mode="edit"
              courseId={course.id}
              courseTemplateId={course.course_template_id ?? null}
              existingLo={loEditTarget ? { id: loEditTarget.id, code: loEditTarget.code, description: loEditTarget.description } : null}
            />
            <ConfirmDeleteModal
              isOpen={!!loDeleteTarget}
              onClose={() => setLoDeleteTarget(null)}
              onConfirm={handleLODelete}
              title="Delete Learning Outcome"
              itemName={loDeleteTarget?.code ?? ''}
              confirmText={loDeleteTarget?.code ?? ''}
              inputLabel="LO code"
            />
          </>
        )}
      </main>
    </>
  )
}

export default InstructorDashboard
