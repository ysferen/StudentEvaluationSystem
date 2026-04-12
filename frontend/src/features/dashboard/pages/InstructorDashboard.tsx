import { useMemo, useState } from 'react'
import { useQuery, useQueries } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import FileUploadModal from '../../courses/components/FileUploadModal'
import { ChartWidget } from '../../../shared/components/ui/ChartWidget'
import { ChevronLeft, ChevronRight, Upload } from 'lucide-react'
import { useAuth } from '../../auth/hooks/useAuth'
import {
  coreCoursesList
} from '../../../shared/api/generated/core/core'

import {
  coreStudentLoScoresLoAveragesRetrieve
} from '../../../shared/api/generated/core/core'
import { evaluationGradesCourseAveragesRetrieve } from '../../../shared/api/generated/evaluation/evaluation'
import type { Course } from '../../../shared/api/model/course'

interface LoAverageItem {
  lo_code: string
  avg_score: number
}

interface UploadResultPayload {
  message?: string
  results?: {
    created?: Record<string, number>
    updated?: Record<string, number>
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

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
}

const toUploadResultPayload = (value: unknown): UploadResultPayload => {
  if (!isRecord(value)) {
    return {}
  }

  const created = isRecord(value.results) && isRecord(value.results.created)
    ? Object.fromEntries(Object.entries(value.results.created)
      .filter((entry): entry is [string, number] => typeof entry[1] === 'number'))
    : undefined

  const updated = isRecord(value.results) && isRecord(value.results.updated)
    ? Object.fromEntries(Object.entries(value.results.updated)
      .filter((entry): entry is [string, number] => typeof entry[1] === 'number'))
    : undefined

  return {
    message: typeof value.message === 'string' ? value.message : undefined,
    results: created || updated ? { created, updated } : undefined,
  }
}

interface CourseWithAnalytics extends Course {
  students?: number
  avgScore?: number
  studentsAtRisk?: number
  weight?: number
  loScores?: Array<{ lo: string; score: number }>
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
  const [uploadResult, setUploadResult] = useState<UploadResultPayload | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

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
      queryFn: async () => {
        try {
          // Use orval's raw functions (not hooks) inside queryFn
          const [loAveragesRes, gradeAveragesRes] = await Promise.all([
            coreStudentLoScoresLoAveragesRetrieve(),
            evaluationGradesCourseAveragesRetrieve({ course: course.id, per_student: true })
          ])

          const loAverages = toLoAverages(loAveragesRes)
          const gradeAverages = Array.isArray(gradeAveragesRes) ? gradeAveragesRes : []

          return {
            courseId: course.id,
            loAverages,
            gradeAverages
          }
        } catch (error) {
          console.error(`Error fetching analytics for course ${course.id}:`, error)
          return {
            courseId: course.id,
            loAverages: [],
            gradeAverages: []
          }
        }
      },
      enabled: !!courses.length
    }))
  })

  // Helper functions to process API data
  const calculateGradeDistribution = (gradeAverages: Array<{ weighted_average: number | null }>) => {
    // Filter out null values and get valid averages
    const validAverages = gradeAverages
      .map(g => g.weighted_average)
      .filter((avg): avg is number => avg !== null)

    if (validAverages.length === 0) {
      return []
    }

    // Grade distribution based on grade averages
    const distribution = {
      A: validAverages.filter(s => s >= 90).length,
      B: validAverages.filter(s => s >= 80 && s < 90).length,
      C: validAverages.filter(s => s >= 70 && s < 80).length,
      D: validAverages.filter(s => s >= 60 && s < 70).length,
      F: validAverages.filter(s => s < 60).length
    }

    return [
      { grade: 'A', count: distribution.A, color: '#10b981' },
      { grade: 'B', count: distribution.B, color: '#22c55e' },
      { grade: 'C', count: distribution.C, color: '#eab308' },
      { grade: 'D', count: distribution.D, color: '#f97316' },
      { grade: 'F', count: distribution.F, color: '#ef4444' },
    ].filter(item => item.count > 0)
  }

  const calculateAverageScore = (gradeAverages: Array<{ weighted_average: number | null }>) => {
    const validAverages = gradeAverages
      .map(g => g.weighted_average)
      .filter((avg): avg is number => avg !== null)

    if (validAverages.length === 0) return 0
    const total = validAverages.reduce((sum, score) => sum + score, 0)
    return Math.round(total / validAverages.length)
  }

  const identifyStudentsAtRisk = (gradeAverages: Array<{ weighted_average: number | null }>) => {
    const validAverages = gradeAverages
      .map(g => g.weighted_average)
      .filter((avg): avg is number => avg !== null)

    return validAverages.filter(average => average < 60).length
  }

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

  const nextCourse = () => setCurrentIndex((prev) => (prev + 1) % coursesWithAnalytics.length)
  const prevCourse = () => setCurrentIndex((prev) => (prev - 1 + coursesWithAnalytics.length) % coursesWithAnalytics.length)

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
  const riskCount = course.studentsAtRisk ?? 0
  const riskColorClass = riskCount > 10
    ? 'text-red-500'
    : riskCount > 5
      ? 'text-amber-500'
      : 'text-emerald-500'

  // Get loading state for current course analytics
  const currentCourseAnalyticsLoading = courses.length > 0 && currentIndex < analyticsQueries.length
    ? analyticsQueries[currentIndex]?.isLoading
    : false

  return (
    <>
      {/* Main Content */}
      <main className="p-6 max-w-7xl mx-auto">
        {/* Course Selector */}
        {coursesLoading ? (
          <div className="flex items-center justify-center mb-6">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-primary-600 mx-auto"></div>
              <p className="mt-3 text-secondary-600 font-medium">Loading courses...</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-6 mb-6">
          <button
            onClick={prevCourse}
            disabled={coursesWithAnalytics.length <= 1}
            className="p-2 hover:bg-secondary-100 rounded-full transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-6 h-6 text-secondary-600" />
          </button>
          <div className="text-center">
            <h1 className="text-3xl font-bold text-secondary-900">{course.code}</h1>
            <p className="text-secondary-600 text-lg">{course.name}</p>
          </div>
          <button
            onClick={nextCourse}
            disabled={coursesWithAnalytics.length <= 1}
            className="p-2 hover:bg-secondary-100 rounded-full transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-6 h-6 text-secondary-600" />
          </button>
        </div>
        )}

        {/* Course Overview Card */}
        <Card className="overflow-hidden mb-6">
          <div className="flex flex-col lg:flex-row">
            {/* Left: Charts */}
            <div className="flex-1 p-6 border-b lg:border-b-0 lg:border-r border-secondary-200">
              {/* Chart and Import Controls */}
              <div className="flex items-center justify-between mb-4">
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

              {/* Chart Display */}
              <div className="h-80">
                {currentCourseAnalyticsLoading ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-primary-600 mx-auto"></div>
                      <p className="mt-3 text-secondary-600 font-medium">Loading chart data...</p>
                    </div>
                  </div>
                ) : activeChart === 'radar' ? (
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
                        opacity: 0.4
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
                      }
                    }}
                    height={320}
                    className="shadow-none border-0 p-0"
                  />
                ) : activeChart === 'bar' || activeChart === 'pie' ? (
                  <ChartWidget
                    key={`bar-chart-${course.id}`}
                    title=""
                    type="bar"
                    series={[{
                      name: 'Students',
                      data: (course.gradeDistribution || []).map(item => item.count)
                    }]}
                    options={{
                      chart: {
                        toolbar: { show: false }
                      },
                      plotOptions: {
                        bar: {
                          borderRadius: 6,
                          horizontal: true,
                          columnWidth: '50%',
                          distributed: true,
                        }
                      },
                      grid: {
                        yaxis: {
                          lines: { show: false }
                        }
                      },
                      xaxis: {
                        categories: (course.gradeDistribution || []).map(item => item.grade),
                        labels: {
                          style: {
                            fontSize: '14px',
                            fontWeight: 600
                          }
                        }
                      },
                      yaxis: {
                        labels: {
                          style: {
                            fontSize: '13px'
                          }
                        }
                      },
                      colors: (course.gradeDistribution || []).map(item => item.color),
                      legend: { show: false },
                      dataLabels: {
                        enabled: true,
                        style: {
                          fontSize: '12px',
                          fontWeight: 'bold'
                        }
                      },
                      tooltip: {
                        y: {
                          formatter: (val: number) => `${val} student${val !== 1 ? 's' : ''}`
                        }
                      }
                    }}
                    height={320}
                    className="shadow-none border-0 p-0"
                  />
                ) : null}
              </div>
            </div>

            {/* Right: Stats */}
            <div className="w-full lg:w-64 p-6">
              {currentCourseAnalyticsLoading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-10 w-10 border-b-4 border-primary-600 mx-auto"></div>
                    <p className="mt-3 text-secondary-600 text-sm">Loading stats...</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                <div>
                  <p className="text-secondary-500 text-sm mb-1">Students</p>
                  <p className="text-3xl font-bold text-secondary-900">{course.students}</p>
                </div>
                <div>
                  <p className="text-secondary-500 text-sm mb-1">Avg Score</p>
                  <p className="text-3xl font-bold text-secondary-900">
                    {course.avgScore}<span className="text-lg text-secondary-400">/100</span>
                  </p>
                </div>
                <div>
                  <p className="text-secondary-500 text-sm mb-1">Students at Risk</p>
                  <p className={`text-3xl font-bold ${
                    riskColorClass
                  }`}>
                    {riskCount}
                  </p>
                </div>
                <div>
                  <p className="text-secondary-500 text-sm mb-1">Credits</p>
                  <p className="text-3xl font-bold text-secondary-900">{course.credits}</p>
                </div>
              </div>
              )}
            </div>
          </div>
        </Card>

        {/* Course indicator dots */}
        {coursesWithAnalytics.length > 1 && (
          <div className="flex justify-center gap-2 mb-8">
            {coursesWithAnalytics.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentIndex(i)}
                className={`w-2 h-2 rounded-full transition ${
                  i === currentIndex ? 'bg-primary-500' : 'bg-secondary-300 hover:bg-secondary-400'
                }`}
              />
            ))}
          </div>
        )}

        {/* Upload Results */}
        {uploadResult && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 mb-6">
            <h3 className="text-lg font-semibold text-emerald-800 mb-3">Import Completed Successfully!</h3>
            <div className="space-y-2">
              <div>
                <span className="font-medium text-emerald-700">Message:</span>
                <span className="ml-2 text-emerald-600">{uploadResult.message}</span>
              </div>
              {uploadResult.results && (
                <div>
                  <span className="font-medium text-emerald-700">Results:</span>
                  <div className="mt-2 space-y-1">
                    {Object.entries(uploadResult.results?.created || {}).map(([entity, count]) => (
                      <div key={entity} className="text-sm text-emerald-600">
                        • Created {count} {entity}
                      </div>
                    ))}
                    {Object.entries(uploadResult.results?.updated || {}).map(([entity, count]) => (
                      <div key={entity} className="text-sm text-emerald-600">
                        • Updated {count} {entity}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <button
              onClick={() => setUploadResult(null)}
              className="mt-4 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Upload Errors */}
        {uploadError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
            <h3 className="text-lg font-semibold text-red-800 mb-3">Import Failed</h3>
            <div className="text-red-600">{uploadError}</div>
            <button
              onClick={() => setUploadError(null)}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* FileUploadModal */}
        {course.id && (
          <FileUploadModal
            course={course.name}
            courseCode={course.code}
            termId={course.term?.id ?? 1}
            isOpen={isFileUploadModalOpen}
            type="assignment_scores"
            onClose={() => setIsFileUploadModalOpen(false)}
            onUploadComplete={(result: unknown) => {
              setUploadResult(toUploadResultPayload(result))
              setIsFileUploadModalOpen(false)
              // Refetch data to update the dashboard
              window.location.reload()
            }}
            onError={(error: string) => {
              setUploadError(error)
              setIsFileUploadModalOpen(false)
            }}
          />
        )}
    </main>
    </>
  )
}

export default InstructorDashboard
