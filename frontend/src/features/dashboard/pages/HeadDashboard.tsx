import { useMemo } from 'react'
import { Card } from '../../../shared/components/ui/Card'
import { LazyChartWidget as ChartWidget } from '../../../shared/components/ui/LazyChartWidget'
import {
  UserGroupIcon,
  BookOpenIcon,
  ChartBarIcon,
  ArrowDownTrayIcon,
  DocumentIcon
} from '@heroicons/react/24/outline'
import { useCoreAnalyticsProgramStatsRetrieve } from '../../../shared/api/generated/analytics/analytics'

const HeadDashboard = () => {
  const { data: statsData, isLoading } = useCoreAnalyticsProgramStatsRetrieve()

  const programs = useMemo(() => statsData?.programs || [], [statsData])

  const totalStudents = useMemo(() => programs.reduce((sum, p) => sum + p.total_students, 0), [programs])
  const totalCourses = useMemo(() => programs.reduce((sum, p) => sum + p.total_courses, 0), [programs])
  const overallAvg = useMemo(() => {
    const scored = programs.filter(p => p.avg_score !== null)
    if (scored.length === 0) return null
    return scored.reduce((sum, p) => sum + (p.avg_score ?? 0), 0) / scored.length
  }, [programs])

  const yearLevelBreakdown = useMemo(() => statsData?.year_level_breakdown || [], [statsData])

  const yearLevelData = useMemo(() => {
    return {
      series: [{
        name: 'Students',
        data: yearLevelBreakdown.map(y => y.student_count)
      }],
      options: {
        xaxis: {
          categories: ['1st Year', '2nd Year', '3rd Year', '4th Year']
        },
        colors: ['#0ea5e9']
      }
    }
  }, [yearLevelBreakdown])

  const enrollmentTrends = useMemo(() => {
    const trends = statsData?.enrollment_trends || []
    return {
      series: [{
        name: 'Students',
        data: trends.map(t => t.student_count)
      }],
      options: {
        xaxis: {
          categories: trends.map(t => t.term)
        },
        stroke: { curve: 'smooth' as const },
        colors: ['#8b5cf6']
      }
    }
  }, [statsData])

  if (isLoading) {
    return <div className="flex justify-center items-center h-96">Loading...</div>
  }

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
              <p className="text-sm text-secondary-600 font-medium">Program Avg GPA</p>
              <p className="text-3xl font-bold text-secondary-900">
                {overallAvg !== null ? overallAvg.toFixed(2) : 'N/A'}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ChartWidget
          title="Year-Level Breakdown"
          subtitle="Student count by year level"
          type="bar"
          series={yearLevelData.series}
          options={yearLevelData.options}
        />
        <ChartWidget
          title="Enrollment Trends"
          subtitle="Student enrollment over terms"
          type="line"
          series={enrollmentTrends.series}
          options={enrollmentTrends.options}
        />
      </div>

      {/* Reports Section */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-secondary-900">Program Reports</h2>
          <button className="text-sky-600 hover:text-sky-700 font-medium text-sm">View All Reports</button>
        </div>
        <div className="space-y-4">
          {[
            { name: 'Fall 2025 Accreditation Report', type: 'PDF', size: '2.4 MB', date: 'Nov 20, 2025' },
            { name: 'Faculty Evaluation Summary', type: 'Excel', size: '1.1 MB', date: 'Nov 15, 2025' },
            { name: 'Student Outcome Assessment', type: 'PDF', size: '3.8 MB', date: 'Nov 10, 2025' },
          ].map((report, index) => (
            <div key={index} className="flex items-center justify-between p-4 bg-secondary-50 rounded-xl hover:bg-secondary-100 transition-colors group cursor-pointer">
              <div className="flex items-center space-x-4">
                <div className="h-10 w-10 rounded-lg bg-white flex items-center justify-center shadow-sm">
                  <DocumentIcon className="h-6 w-6 text-secondary-500 group-hover:text-sky-600 transition-colors" />
                </div>
                <div>
                  <h4 className="font-semibold text-secondary-900">{report.name}</h4>
                  <p className="text-sm text-secondary-500">{report.type} • {report.size}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-secondary-500">{report.date}</span>
                <button className="p-2 text-secondary-400 hover:text-sky-600 transition-colors">
                  <ArrowDownTrayIcon className="h-5 w-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default HeadDashboard
