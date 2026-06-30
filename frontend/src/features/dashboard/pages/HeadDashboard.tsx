import { useMemo, useState, useCallback } from 'react'
import { Card } from '@/components/ui/custom/Card'
import { LazyChartWidget as ChartWidget } from '@/components/ui/custom/LazyChartWidget'
import {
  UserGroupIcon,
  BookOpenIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { useCoreAnalyticsProgramStatsRetrieve } from '../../../shared/api/generated/analytics/analytics'
import { useAuth } from '../../auth/hooks/useAuth'

const HeadDashboard = () => {
  const { user } = useAuth()
  const { data: statsData, isLoading, error, refetch } = useCoreAnalyticsProgramStatsRetrieve()

  const [activeChart, setActiveChart] = useState<'gpa' | 'po'>('gpa')

  const handleSetGpaChart = useCallback(() => setActiveChart('gpa'), [])
  const handleSetPoChart = useCallback(() => setActiveChart('po'), [])

  const programs = useMemo(() => statsData?.programs || [], [statsData])

  const totalStudents = useMemo(() => programs.reduce((sum, p) => sum + p.total_students, 0), [programs])
  const totalCourses = useMemo(() => programs.reduce((sum, p) => sum + p.total_courses, 0), [programs])
  const overallAveragePoScore = useMemo(() => {
    const scored = programs.filter(p => p.avg_score !== null)
    if (scored.length === 0) return null
    return scored.reduce((sum, p) => sum + (p.avg_score ?? 0), 0) / scored.length
  }, [programs])

  const yearLevelBreakdown = useMemo(() => statsData?.year_level_breakdown || [], [statsData])
  const gpaByYear = useMemo(() => statsData?.gpa_by_year || [], [statsData])
  const weakestYearLevelPoScore = useMemo(() => {
    return [...yearLevelBreakdown]
      .filter(item => item.avg_score !== null)
      .sort((a, b) => (a.avg_score ?? 0) - (b.avg_score ?? 0))[0] ?? null
  }, [yearLevelBreakdown])

  if (isLoading) {
    return <div className="flex justify-center items-center h-96">Loading...</div>
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="text-red-800">An error occurred while loading the dashboard. Please try again.</div>
        <button
          onClick={() => refetch()}
          className="mt-3 px-4 py-2 bg-danger-600 text-white text-sm font-semibold rounded-lg hover:bg-danger-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    )
  }

  const categories = ['1st Year', '2nd Year', '3rd Year', '4th Year'].slice(0, yearLevelBreakdown.length)
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'there'

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-sky-600 to-indigo-600 p-8 text-white shadow-lg">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Welcome, {displayName}</h1>
          <p className="text-sky-100 text-lg">Program Dashboard</p>
        </div>
        <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform origin-bottom-right" />
        <div className="absolute right-20 top-0 h-full w-1/3 bg-white/5 skew-x-12 transform origin-bottom-right" />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
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
              <p className="text-sm text-secondary-600 font-medium">Average PO score</p>
              <p className="text-3xl font-bold text-secondary-900">
                {overallAveragePoScore !== null ? overallAveragePoScore.toFixed(2) : 'N/A'}
              </p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-amber-50 border-amber-200">
          <p className="text-sm text-amber-700 font-medium">Weakest year-level PO score</p>
          <p className="text-3xl font-bold text-amber-900">
            {weakestYearLevelPoScore ? `Year ${weakestYearLevelPoScore.year}` : 'N/A'}
          </p>
          <p className="text-sm text-amber-700 mt-1">
            Average PO score: {weakestYearLevelPoScore?.avg_score ?? 'N/A'}
          </p>
        </Card>
      </div>

      {/* Year-Level Context */}
      <Card variant="flat" className="bg-white border-secondary-200">
        <h2 className="text-lg font-semibold text-secondary-900 mb-4">Year-Level Context</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {yearLevelBreakdown.map(item => (
            <div key={item.year} className="rounded-xl bg-secondary-50 p-3">
              <p className="text-xs text-secondary-500">Year {item.year}</p>
              <p className="text-xl font-bold text-secondary-900">{item.student_count}</p>
              <p className="text-xs text-secondary-500">students</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Chart Toggle */}
      <Card className="overflow-hidden">
        <div className="p-6 border-b border-secondary-200">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 className="text-lg font-semibold text-gray-900">GPA and PO Scores by Year</h2>
            <div className="flex gap-2">
              <button
                onClick={handleSetGpaChart}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  activeChart === 'gpa'
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                }`}
              >
                Average GPA
              </button>
              <button
                onClick={handleSetPoChart}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  activeChart === 'po'
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                }`}
              >
                Average PO score
              </button>
            </div>
          </div>
        </div>

        <div className="p-6">
          {activeChart === 'gpa' ? (
            <ChartWidget
              title="Average GPA by year level"
              subtitle="Credit-weighted average GPA on the 4.0 scale"
              type="bar"
              series={[{
                name: 'Average GPA',
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
              title="Average PO score by year level"
              subtitle="Average program outcome score by enrolled student year level"
              type="bar"
              series={[{
                name: 'Average PO score',
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
