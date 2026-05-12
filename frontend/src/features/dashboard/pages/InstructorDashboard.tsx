import { useMemo, useState, useCallback } from 'react'
import { useQuery, useQueries } from '@tanstack/react-query'
import FileUploadModal from '../../courses/components/FileUploadModal'
import { Card } from '@/components/ui/custom/Card'
import { ChartWidget } from '@/components/ui/custom/ChartWidget'
import { ChevronLeft, ChevronRight, Upload } from 'lucide-react'
import { useAuth } from '../../auth/hooks/useAuth'
import {
  coreCoursesList,
  coreStudentLoScoresLoAveragesRetrieve
} from '../../../shared/api/generated/core/core'
import { evaluationGradesCourseAveragesRetrieve } from '../../../shared/api/generated/evaluation/evaluation'
import { isRecord } from '@/shared/utils/guards'
import { CourseAnalyticsCard } from '../components/CourseAnalyticsCard'
import { GradeDistributionChart } from '../components/GradeDistributionChart'
import {
  calculateGradeDistribution,
  calculateAverageScore,
  identifyStudentsAtRisk,
} from '../utils/analytics'
import type { Course } from '../../../shared/api/model/course'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

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
  avgScore?: number
  studentsAtRisk?: number
  weight?: number
  loScores?: Array<{ lo: string; description: string; score: number }>
  gradeDistribution?: Array<{ grade: string; count: number; color: string }>
}

interface CourseAnalytics {
  courseId: number
  loAverages: LoAverageItem[]
  gradeAverages: Array<{ weighted_average: number | null }>
}

const InstructorDashboard = () => {
  const { user } = useAuth()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [activeChart, setActiveChart] = useState('radar')
  const [isFileUploadModalOpen, setIsFileUploadModalOpen] = useState(false)

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
        const [loAveragesRes, gradeAveragesRes] = await Promise.all([
          coreStudentLoScoresLoAveragesRetrieve({ params: { course: course.id } }),
          evaluationGradesCourseAveragesRetrieve({ course: course.id, per_student: true })
        ])
        return {
          courseId: course.id,
          loAverages: toLoAverages(loAveragesRes),
          gradeAverages: Array.isArray(gradeAveragesRes) ? gradeAveragesRes : []
        }
      },
      retry: 1,
      enabled: !!courses.length
    }))
  })

  const currentAnalytics = analyticsQueries[currentIndex]
  const analyticsError = currentAnalytics?.isError ?? false

  // Combine course data with analytics
  // Create a Map for O(1) lookup of analytics by course ID
  const analyticsMap = new Map<number, CourseAnalytics>()
  analyticsQueries.forEach((query, index) => {
    if (query.data && courses[index]) {
      analyticsMap.set(courses[index].id, query.data as CourseAnalytics)
    }
  })

  const coursesWithAnalytics: CourseWithAnalytics[] = courses.map((course: Course) => {
    const analytics = analyticsMap.get(course.id)

    if (!analytics) {
      return {
        ...course,
        students: 0,
        avgScore: 0,
        studentsAtRisk: 0,
        weight: course.credits || 1,
        loScores: [],
        gradeDistribution: []
      }
    }

    // Format LO averages for radar chart
    const aggregatedLOScores = analytics.loAverages.map((lo) => ({
      lo: lo.lo_code,
      description: lo.lo_description || '',
      score: Math.round(lo.avg_score)
    }))

    // Grade distribution based on grade averages
    const gradeDistribution = calculateGradeDistribution(analytics.gradeAverages)

    // Average score from grade averages
    const avgScore = calculateAverageScore(analytics.gradeAverages)

    // Students at risk from grade averages
    const studentsAtRisk = identifyStudentsAtRisk(analytics.gradeAverages)

    // Count unique students from grade averages
    const studentCount = analytics.gradeAverages.length

    return {
      ...course,
      students: studentCount,
      avgScore,
      studentsAtRisk,
      weight: course.credits || 1,
      loScores: aggregatedLOScores,
      gradeDistribution
    }
  })

  const nextCourse = useCallback(
    () => setCurrentIndex((prev) => (prev + 1) % courses.length),
    [courses.length]
  )
  const prevCourse = useCallback(
    () => setCurrentIndex((prev) => (prev - 1 + courses.length) % courses.length),
    [courses.length]
  )

  const course = coursesWithAnalytics[currentIndex] || {
    code: 'No Course',
    name: 'No courses available',
    students: 0,
    avgScore: 0,
    studentsAtRisk: 0,
    weight: 0,
    loScores: [],
    gradeDistribution: []
  }
  // Get loading state for current course analytics
  const currentCourseAnalyticsLoading = courses.length > 0 && currentIndex < analyticsQueries.length
    ? analyticsQueries[currentIndex]?.isLoading
    : false

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
        {/* Hero/Welcome Section with Course Selector */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-primary-600 to-primary-800 p-8 text-white shadow-lg">
          <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex-1">
              <h1 className="text-3xl font-bold mb-2">{course.code}</h1>
              <p className="text-primary-100 text-lg">{course.name}</p>
            </div>
            {coursesWithAnalytics.length > 1 && (
              <div className="flex items-center gap-4">
                <button
                  onClick={prevCourse}
                  className="p-2 hover:bg-white/10 rounded-full transition-colors"
                >
                  <ChevronLeft className="w-6 h-6" />
                </button>
                <button
                  onClick={nextCourse}
                  className="p-2 hover:bg-white/10 rounded-full transition-colors"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              </div>
            )}
          </div>
          <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform origin-bottom-right" />
          <div className="absolute right-20 top-0 h-full w-1/3 bg-white/5 skew-x-12 transform origin-bottom-right" />
        </div>

        {/* Course indicator dots */}
        {coursesWithAnalytics.length > 1 && (
          <div className="flex justify-center gap-2">
            {coursesWithAnalytics.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentIndex(i)}
                className={`w-3 h-3 rounded-full transition ${
                  i === currentIndex ? 'bg-primary-600' : 'bg-secondary-300 hover:bg-secondary-400'
                }`}
              />
            ))}
          </div>
        )}

        {/* Stats Row */}
        <CourseAnalyticsCard
          studentCount={course.students ?? 0}
          avgScore={course.avgScore ?? 0}
          studentsAtRisk={course.studentsAtRisk ?? 0}
          credits={course.credits}
        />

        {/* Chart Card */}
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-secondary-200">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex gap-2">
                <button
                  onClick={() => setActiveChart('radar')}
                  className={`px-3 py-1.5 text-sm rounded-lg transition ${
                    activeChart === 'radar'
                      ? 'bg-primary-600 text-white'
                      : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                  }`}
                >
                  LO Scores
                </button>
                <button
                  onClick={() => setActiveChart('bar')}
                  className={`px-3 py-1.5 text-sm rounded-lg transition ${
                    activeChart === 'bar'
                      ? 'bg-primary-600 text-white'
                      : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                  }`}
                >
                  Grade Distribution
                </button>
              </div>
              <button
                onClick={() => setIsFileUploadModalOpen(true)}
                className="flex items-center gap-2 px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Upload className="w-4 h-4" />
                <span>Import Data</span>
              </button>
            </div>
          </div>

          {/* Chart Display */}
          <div className="p-6">
            {analyticsError && (
              <Card className="bg-danger-50 border border-danger-200 rounded-xl p-4 mb-4">
                <div className="flex items-center gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-danger-600" />
                  <p className="text-danger-800 text-sm font-medium">
                    Failed to load analytics for this course
                  </p>
                </div>
              </Card>
            )}
            {currentCourseAnalyticsLoading ? (
              <div className="h-80 flex items-center justify-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-primary-600 mx-auto" />
                  <p className="mt-4 text-secondary-600 font-medium">Loading chart data...</p>
                </div>
              </div>
            ) : activeChart === 'radar' ? (
              <>
                <ChartWidget
                  key={`radar-chart-${course.id}`}
                  title=""
                  type="radar"
                  series={[{
                    name: 'Score',
                    data: (course.loScores || []).map(lo => lo.score)
                  }]}
                  options={{
                    xaxis: {
                      categories: (course.loScores || []).map(lo => lo.lo)
                    },
                    yaxis: {
                      show : false,
                      min: 0,
                      max: 100
                    },
                    fill: {
                      opacity: 0.3,
                      colors: ['#6366f1']
                    },
                    stroke: {
                      colors: ['#6366f1']
                    },
                    colors: ['#6366f1'],
                    markers: {
                      size: 4
                    },
                    dataLabels: {
                      enabled: true,
                      background: {
                        enabled: true,
                        borderRadius:2,
                      }
                    },
                    plotOptions: {
                      radar: {
                        polygons: {
                          strokeColors: '#e5e7eb',
                          connectorColors: '#e5e7eb',
                        }
                      }
                    }
                  }}
                  height={320}
                  className="shadow-none border-0 p-0 [&>div]:p-0"
                />
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(course.loScores || []).map((lo, idx) => (
                    <div key={idx} className="flex flex-col p-3 rounded-xl border border-secondary-200 bg-white shadow-sm">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded text-xs">{lo.lo}</span>
                        <span className={`font-bold px-2 py-0.5 rounded-full text-xs whitespace-nowrap ${
                          lo.score >= 80 ? 'bg-emerald-100 text-emerald-700' : lo.score >= 60 ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'
                        }`}>
                          {lo.score}%
                        </span>
                      </div>
                      <span className="text-secondary-700 text-sm leading-snug">{lo.description || 'No description available'}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : activeChart === 'bar' || activeChart === 'pie' ? (
              <GradeDistributionChart
                data={course.gradeDistribution || []}
                courseId={course.id}
              />
            ) : null}
          </div>
        </Card>

        {/* FileUploadModal */}
        {course.id && (
          <FileUploadModal
            course={course.name}
            courseCode={course.code}
            termId={course.term?.id ?? 1}
            isOpen={isFileUploadModalOpen}
            type="assignment_scores"
            onClose={() => setIsFileUploadModalOpen(false)}
            onUploadComplete={() => {
              setIsFileUploadModalOpen(false)
            }}
          />
        )}
      </main>
    </>
  )
}

export default InstructorDashboard
