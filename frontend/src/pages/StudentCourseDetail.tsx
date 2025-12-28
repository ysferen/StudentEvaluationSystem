import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import { Card } from '../components/ui/Card'
import { LazyChartWidget as ChartWidget } from '../components/ui/LazyChartWidget'
import {
  ChartBarIcon,
  AcademicCapIcon,
  ChartPieIcon,
} from '@heroicons/react/24/outline'
import { coreCoursesRetrieve, coreCoursesLearningOutcomesRetrieve } from '../api/generated/core/core'
import { coreStudentLoScoresList } from '../api/generated/scores/scores'
import { evaluationGradesList, evaluationGradesCourseAveragesRetrieve } from '../api/generated/evaluation/evaluation'


const StudentCourseDetail = () => {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()

  const results = useQueries({
    queries: [
      {
        queryKey: ['course', id],
        queryFn: () => coreCoursesRetrieve(parseInt(id!)),
        enabled: !!id,
      },
      {
        queryKey: ['loScores', user?.id, id],
        queryFn: () => coreStudentLoScoresList({ student: user!.id, course: parseInt(id!) }),
        enabled: !!user && !!id,
      },
      {
        queryKey: ['studentGrades', user?.id, id],
        queryFn: () => evaluationGradesList({ student: user!.id, course: parseInt(id!) }),
        enabled: !!user && !!id,
      },
      {
        queryKey: ['learningOutcomes', id],
        queryFn: () => coreCoursesLearningOutcomesRetrieve(parseInt(id!)),
        enabled: !!id,
      },
      {
        queryKey: ['courseAverages', user?.id, id],
        queryFn: () => evaluationGradesCourseAveragesRetrieve({ student: user!.id, course: parseInt(id!) }),
        enabled: !!user && !!id,
      },
    ],
  })

  const [courseQuery, loScoresQuery, gradesQuery, learningOutcomesQuery, courseAvgQuery] = results
  const loading = results.some(q => q.isLoading)

  const course = useMemo(() => courseQuery.data || null, [courseQuery.data])
  const loScores = useMemo(() => loScoresQuery.data?.results || [], [loScoresQuery.data])
  const studentGrades = useMemo(() => gradesQuery.data?.results || [], [gradesQuery.data])
  const learningOutcomes = useMemo(() => {
    const data = learningOutcomesQuery.data
    return Array.isArray(data) ? data : []
  }, [learningOutcomesQuery.data])
  const weightedAverage = useMemo(() => {
    const avgData = courseAvgQuery.data
    return avgData && Array.isArray(avgData) && avgData.length > 0 ? avgData[0].weighted_average : null
  }, [courseAvgQuery.data])

  // Check if scores are already in percentage (0-100) or decimal (0-1) format
  const scoreMultiplier =
    loScores.length > 0 && loScores[0]?.score && loScores[0].score <= 1 ? 100 : 1

  // Bar Chart Data for Assessment Scores
  const barChartData = {
    series: [
      {
        name: 'Score',
        data: loScores.map((s) => Math.round((s.score || 0) * scoreMultiplier)),
      },
    ],
    options: {
      chart: {
        toolbar: { show: false },
      },
      plotOptions: {
        bar: {
          borderRadius: 6,
          horizontal: false,
          columnWidth: '60%',
          distributed: true,
        },
      },
      dataLabels: {
        enabled: true,
        style: {
          fontSize: '11px',
          fontWeight: 'bold',
        },
      },
      xaxis: {
        categories: loScores.map((s) => s.learning_outcome.code),
        labels: {
          style: {
            fontSize: '12px',
          },
        },
      },
      yaxis: {
        max: 100,
        labels: {
        },
      },
      colors: [
        '#0d9488',
        '#14b8a6',
        '#2dd4bf',
        '#5eead4',
        '#06b6d4',
        '#22d3ee',
        '#0ea5e9',
        '#38bdf8',
      ],
      legend: { show: false },
      tooltip: {
        y: {
        },
      },
    },
  }

  // Radar Chart Data for Learning Outcomes
  const radarChartData = {
    series: [
      {
        name: 'Achievement',
        data: loScores.map((s) => Math.round((s.score || 0) * scoreMultiplier)),
      },
    ],
    options: {
      chart: {
        toolbar: { show: false },
        dropShadow: {
          enabled: true,
          blur: 8,
          opacity: 0.1,
        },
      },
      stroke: { width: 2 },
      fill: { opacity: 0.3 },
      markers: { size: 4 },
      xaxis: {
        categories: loScores.map((s) => s.learning_outcome?.code || ''),
        labels: {
          style: {
            fontSize: '12px',
            fontWeight: 600,
          },
        },
      },
      yaxis: {
        show: true,
        min: 0,
        max: 100,
        tickAmount: 5,
      },
      colors: ['#0d9488'],
      tooltip: {
        enabled: true,
        y: {
        },
      },
      plotOptions: {
        radar: {
          polygons: {
            strokeColors: '#e5e7eb',
            connectorColors: '#e5e7eb',
            fill: {
              colors: ['#f9fafb', '#fff'],
            },
          },
        },
      },
    },
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 font-medium">Loading course details...</p>
        </div>
      </div>
    )
  }

  if (!course) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <ChartBarIcon className="h-16 w-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Course not found</h3>
          <p className="text-gray-500">The requested course could not be found.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Course Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{course.code}</h1>
          <p className="text-lg text-gray-600 mt-1">{course.name}</p>
        </div>
      </div>

      {/* Tab Content */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Assessment Scores</h2>
          {studentGrades.length > 0 ? (
            <>
              {/* Charts - Now at top */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Bar Chart */}
                <Card>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Score Distribution
                  </h3>
                  <ChartWidget
                    title=""
                    type="bar"
                    series={[{
                      name: 'Score',
                      data: studentGrades.map((g) => Math.round((g.score / (g.assessment?.total_score || 1)) * 100)),
                    }]}
                    options={{
                      ...barChartData.options,
                      xaxis: {
                        categories: studentGrades.map((g) => g.assessment?.name || ''),
                        labels: { style: { fontSize: '12px' } },
                      },
                    }}
                    height={300}
                    className="border-0 shadow-none p-0"
                  />
                </Card>

                {/* Learning Outcome Radar Chart */}
                <Card className="flex flex-col">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Learning Outcome Overview
                  </h3>
                  <div className="flex-1 flex items-center justify-center min-h-[280px]">
                    {learningOutcomes.length > 0 ? (
                      <ChartWidget
                        title=""
                        type="radar"
                        series={[{
                          name: 'Score',
                          data: learningOutcomes.map((lo: any) => {
                            const scoreData = loScores.find((s) => s.learning_outcome?.id === lo.id)
                            return scoreData ? Math.round((scoreData.score || 0) * scoreMultiplier) : 0
                          }),
                        }]}
                        options={{
                          ...radarChartData.options,
                          chart: {
                            ...radarChartData.options.chart,
                            height: '100%',
                            parentHeightOffset: 0,
                          },
                          plotOptions: {
                            radar: {
                              size: 120,
                              polygons: {
                                strokeColors: '#e5e7eb',
                                connectorColors: '#e5e7eb',
                                fill: {
                                  colors: ['#f9fafb', '#fff'],
                                },
                              },
                            },
                          },
                          xaxis: {
                            categories: learningOutcomes.map((lo: any) => lo.code),
                            labels: {
                              style: { fontSize: '11px', fontWeight: 600 },
                              offsetY: 0,
                            },
                          },
                        }}
                        height={280}
                        className="border-0 shadow-none p-0 w-full"
                      />
                    ) : (
                      <p className="text-gray-500 text-sm">No learning outcomes defined</p>
                    )}
                  </div>
                </Card>
              </div>

              {/* Score Card */}
              {weightedAverage !== null && (
                <Card className="bg-primary-50 border-primary-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Average Score</h3>
                    </div>
                    <p className="text-3xl font-bold text-primary-600">
                      {Math.round(weightedAverage)}
                    </p>
                  </div>
                </Card>
              )}

              {/* Assessment List */}
              <div className="space-y-4">
                {studentGrades.map((grade) => {
                  return (
                    <Card key={grade.id} className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-lg text-sm font-semibold capitalize">
                            {(grade.assessment as any)?.assessment_type || 'Assessment'}
                          </span>
                          <div>
                            <p className="font-medium text-gray-900">{grade.assessment?.name}</p>
                            <p className="text-sm text-gray-500">
                              Weight: {((grade.assessment?.weight || 0) * 100).toFixed(0)}%
                            </p>
                          </div>
                        </div>
                      </div>
                      <div className="ml-4 text-right">
                        <p className="text-2xl font-bold text-primary-600">
                          {grade.score}
                        </p>
                      </div>
                    </Card>
                  )
                })}
              </div>
            </>
          ) : (
            <Card className="text-center py-12">
              <ChartBarIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No assessment data
              </h3>
              <p className="text-gray-500">
                Assessment scores will appear here once available.
              </p>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Learning Outcomes</h2>
          {learningOutcomes.length > 0 ? (
            <div className="space-y-4">
              {learningOutcomes.map((lo: any) => {
                // Find matching score if available
                const scoreData = loScores.find(
                  (s) => s.learning_outcome?.id === lo.id
                )
                return (
                  <Card key={lo.id} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-lg text-sm font-semibold">
                          {lo.code}
                        </span>
                        <p className="text-gray-700">{lo.description}</p>
                      </div>
                    </div>
                    {scoreData && (
                      <div className="ml-4">
                        <span className="text-2xl font-bold text-primary-600">
                          {Math.round((scoreData.score || 0) * scoreMultiplier)}%
                        </span>
                      </div>
                    )}
                  </Card>
                )
              })}
            </div>
          ) : (
            <Card className="text-center py-12">
              <AcademicCapIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No learning outcomes
              </h3>
              <p className="text-gray-500">
                Learning outcomes for this course will appear here once defined.
              </p>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-gray-900">Course Analytics</h2>
          {studentGrades.length > 0 ? (
            (() => {
              // Find highest and lowest scoring assessments
              const gradesWithPercentage = studentGrades.map((g) => ({
                ...g,
                percentage: (g.score / (g.assessment?.total_score || 1)) * 100
              }))
              const highestGrade = gradesWithPercentage.reduce((max, g) =>
                g.percentage > max.percentage ? g : max
              )
              const lowestGrade = gradesWithPercentage.reduce((min, g) =>
                g.percentage < min.percentage ? g : min
              )

              return (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card className="text-center">
                    <p className="text-sm text-gray-500 mb-2">Weighted Average</p>
                    <p className="text-4xl font-bold text-primary-600">
                      {weightedAverage !== null ? `${weightedAverage.toFixed(1)}%` : '-'}
                    </p>
                  </Card>
                  <Card className="text-center">
                    <p className="text-sm text-gray-500 mb-2">Highest Score</p>
                    <p className="text-4xl font-bold text-green-600">
                      {Math.round(highestGrade.percentage)}%
                    </p>
                    <p className="text-sm text-gray-500 mt-1 capitalize">
                      {highestGrade.assessment.name}
                    </p>
                  </Card>
                  <Card className="text-center">
                    <p className="text-sm text-gray-500 mb-2">Lowest Score</p>
                    <p className="text-4xl font-bold text-amber-600">
                      {Math.round(lowestGrade.percentage)}%
                    </p>
                    <p className="text-sm text-gray-500 mt-1 capitalize">
                      {lowestGrade.assessment.name}
                    </p>
                  </Card>
                </div>
              )
            })()
          ) : (
            <Card className="text-center py-12">
              <ChartPieIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No analytics data
              </h3>
              <p className="text-gray-500">
                Analytics will appear here once you have assessment scores.
              </p>
            </Card>
          )}
        </div>
    </div>
  )
}

export default StudentCourseDetail
