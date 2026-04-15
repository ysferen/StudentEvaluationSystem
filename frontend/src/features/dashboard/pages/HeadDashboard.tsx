import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import { LazyChartWidget as ChartWidget } from '../../../shared/components/ui/LazyChartWidget'
import {
  BuildingOfficeIcon,
  UserGroupIcon,
  BookOpenIcon,
  ChartBarIcon,
  ArrowDownTrayIcon,
  DocumentIcon
} from '@heroicons/react/24/outline'
import { coreProgramsList } from '../../../shared/api/generated/core/core'
import type { Program } from '../../../shared/api/model'

const HeadDashboard = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['programs'],
    queryFn: () => coreProgramsList({}),
  })

  const programs = useMemo(() => data?.results || [], [data])
  const loading = isLoading

  // Mock data for Program Performance (replace with real API call later)
  const programPerformance = {
    series: [{
      name: 'Average GPA',
      data: [3.2, 2.9, 3.4, 3.1]
    }],
    options: {
      xaxis: {
        categories: programs.map((p: Program) => p.code) // Use real program codes
      },
      colors: ['#0ea5e9']
    }
  }

  // Mock data for Enrollment Trends (replace with real API call later)
  const enrollmentTrends = {
    series: [{
      name: 'Students',
      data: [320, 342, 355, 380, 410]
    }],
    options: {
      xaxis: {
        categories: ['2021', '2022', '2023', '2024', '2025']
      },
      stroke: { curve: 'smooth' as const },
      colors: ['#8b5cf6']
    }
  }

  if (loading) {
    return <div className="flex justify-center items-center h-96">Loading...</div>
  }

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-sky-600 to-indigo-600 p-8 text-white shadow-lg">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2">Department Overview</h1>
          <p className="text-sky-100 text-lg">Computer Science & Engineering Department</p>
        </div>
        <div className="absolute right-0 top-0 h-full w-1/3 bg-white/10 skew-x-12 transform origin-bottom-right" />
        <div className="absolute right-20 top-0 h-full w-1/3 bg-white/5 skew-x-12 transform origin-bottom-right" />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card variant="flat" className="bg-white border-secondary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-sky-100 rounded-xl">
              <UserGroupIcon className="h-8 w-8 text-sky-600" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Students</p>
              <p className="text-3xl font-bold text-secondary-900">410</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-white border-secondary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-indigo-100 rounded-xl">
              <BuildingOfficeIcon className="h-8 w-8 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Faculty Members</p>
              <p className="text-3xl font-bold text-secondary-900">24</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-white border-secondary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-fuchsia-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-fuchsia-600" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Active Programs</p>
              <p className="text-3xl font-bold text-secondary-900">{programs.length}</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-white border-secondary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Dept. Avg GPA</p>
              <p className="text-3xl font-bold text-secondary-900">3.15</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ChartWidget
          title="Program Performance"
          subtitle="Average GPA by Program"
          type="bar"
          series={programPerformance.series}
          options={programPerformance.options}
        />
        <ChartWidget
          title="Enrollment Trends"
          subtitle="Year-over-year student enrollment"
          type="line"
          series={enrollmentTrends.series}
          options={enrollmentTrends.options}
        />
      </div>

      {/* Reports Section */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-secondary-900">Department Reports</h2>
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
