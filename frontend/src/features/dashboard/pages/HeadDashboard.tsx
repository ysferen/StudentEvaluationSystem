import { useMemo, useState, useCallback } from 'react'
import { Card } from '../../../shared/components/ui/Card'
import { LazyChartWidget as ChartWidget } from '../../../shared/components/ui/LazyChartWidget'
import {
  UserGroupIcon,
  BookOpenIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { useCoreAnalyticsProgramStatsRetrieve } from '../../../shared/api/generated/analytics/analytics'

const HeadDashboard = () => {
  const { data: statsData, isLoading } = useCoreAnalyticsProgramStatsRetrieve()

  const [activeChart, setActiveChart] = useState<'gpa' | 'po'>('gpa')

  const handleSetGpaChart = useCallback(() => setActiveChart('gpa'), [])
  const handleSetPoChart = useCallback(() => setActiveChart('po'), [])

  const programs = useMemo(() => statsData?.programs || [], [statsData])

  const totalStudents = useMemo(() => programs.reduce((sum, p) => sum + p.total_students, 0), [programs])
  const totalCourses = useMemo(() => programs.reduce((sum, p) => sum + p.total_courses, 0), [programs])
  const overallAvg = useMemo(() => {
    const scored = programs.filter(p => p.avg_score !== null)
    if (scored.length === 0) return null
    return scored.reduce((sum, p) => sum + (p.avg_score ?? 0), 0) / scored.length
  }, [programs])

  const yearLevelBreakdown = useMemo(() => statsData?.year_level_breakdown || [], [statsData])
  const gpaByYear = useMemo(() => statsData?.gpa_by_year || [], [statsData])

  if (isLoading) {
    return <div className="flex justify-center items-center h-96">Loading...</div>
  }

  const categories = ['1st Year', '2nd Year', '3rd Year', '4th Year'].slice(0, yearLevelBreakdown.length)

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-sky-600 to-indigo-600 p-8 text-white shadow-lg">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Program Overview</h1>
          <p className="text-sky-100 text-lg">Program Dashboard</p>
        </div>
        <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform origin-bottom-right" />
        <div className="absolute right-20 top-0 h-full w-1/3 bg-white/5 skew-x-12 transform origin-bottom-right" />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card variant="flat" className="bg-white border-secondary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-sky-100 rounded-xl">
              <UserGroupIcon className="h-8 w-8 text-sky-600" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Students</p>
              <p className="text-3xl font-bold text-secondary-900">{totalStudents}</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-white border-secondary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-indigo-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Courses</p>
              <p className="text-3xl font-bold text-secondary-900">{totalCourses}</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-white border-secondary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Program Average</p>
              <p className="text-3xl font-bold text-secondary-900">
                {overallAvg !== null ? overallAvg.toFixed(2) : 'N/A'}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Year-Level Breakdown */}
      <ChartWidget
        title="Year-Level Breakdown"
        subtitle="Student distribution by year"
        type="pie"
        series={yearLevelBreakdown.map(y => y.student_count)}
        options={{
          labels: categories,
          colors: ['#0ea5e9', '#8b5cf6', '#f59e0b', '#10b981'],
        }}
      />

      {/* Chart Toggle */}
      <Card className="overflow-hidden">
        <div className="p-6 border-b border-secondary-200">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 className="text-lg font-semibold text-gray-900">Score Averages by Year</h2>
            <div className="flex gap-2">
              <button
                onClick={handleSetGpaChart}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  activeChart === 'gpa'
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                }`}
              >
                GPA Averages
              </button>
              <button
                onClick={handleSetPoChart}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  activeChart === 'po'
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                }`}
              >
                PO Scores
              </button>
            </div>
          </div>
        </div>

        <div className="p-6">
          {activeChart === 'gpa' ? (
            <ChartWidget
              title="GPA Averages by Year"
              subtitle="Weighted grade point average per year level"
              type="bar"
              series={[{
                name: 'Avg GPA',
                data: gpaByYear.map(y => y.gpa ?? 0),
              }]}
              options={{
                xaxis: {
                  categories,
                },
                colors: ['#0ea5e9'],
                yaxis: {
                  min: 0,
                  max: 4,
                },
              }}
            />
          ) : (
            <ChartWidget
              title="PO Score Averages by Year"
              subtitle="Average program outcome score per year level"
              type="bar"
              series={[{
                name: 'Avg PO Score',
                data: yearLevelBreakdown.map(y => y.avg_score ?? 0),
              }]}
              options={{
                xaxis: {
                  categories,
                },
                colors: ['#8b5cf6'],
                yaxis: {
                  min: 0,
                  max: 100,
                },
              }}
            />
          )}
        </div>
      </Card>

    </div>
  )
}

export default HeadDashboard
