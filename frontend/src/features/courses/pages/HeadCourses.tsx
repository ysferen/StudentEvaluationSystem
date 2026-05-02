import { useState, useEffect, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import {
  BookOpenIcon,
  AcademicCapIcon,
  UsersIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import {
  coreCoursesList,
  coreTermsList,
} from '../../../shared/api/generated/core/core'
import {
  useCoreAnalyticsProgramStatsRetrieve
} from '../../../shared/api/generated/analytics/analytics'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

function formatInstructorNames(
  instructors: readonly Record<string, unknown>[] | undefined,
): string {
  if (!instructors || instructors.length === 0) return 'Not assigned'
  return instructors
    .map((inst) => {
      const first = inst.first_name ?? ''
      const last = inst.last_name ?? ''
      return `${first} ${last}`.trim()
    })
    .filter(Boolean)
    .join(', ')
}

const HeadCourses = () => {
  const navigate = useNavigate()

  const [selectedTermId, setSelectedTermId] = useState<string>('')

  const { data: statsData, isLoading: statsLoading } =
    useCoreAnalyticsProgramStatsRetrieve()
  const userProgramId = statsData?.programs?.[0]?.id

  const { data: termsData } = useQuery({
    queryKey: ['head-terms'],
    queryFn: async () => {
      const response = await coreTermsList()
      return response.results || []
    }
  })

  useEffect(() => {
    if (termsData && !selectedTermId) {
      const active = termsData.find(t => t.is_active)
      if (active) setSelectedTermId(String(active.id))
    }
  }, [termsData, selectedTermId])

  const { data: coursesData, isLoading: coursesLoading } = useQuery({
    queryKey: ['head-courses', userProgramId, selectedTermId],
    queryFn: async () => {
      const response = await coreCoursesList({
        program: userProgramId ?? undefined,
        ...(selectedTermId ? { term: Number(selectedTermId) } : {}),
      })
      return response.results || []
    },
    enabled: !!userProgramId
  })

  const totalStudents = useMemo(() => statsData?.programs?.[0]?.total_students ?? 0, [statsData])

  const totalCredits = coursesData?.reduce((sum, course) => sum + (course.credits || 0), 0) || 0

  const uniqueInstructors = useMemo(() => {
    if (!coursesData) return 0
    const instructorIds = new Set<number>()
    coursesData.forEach(course => {
      course.instructors?.forEach((inst: Record<string, unknown>) => {
        if (inst.id) instructorIds.add(inst.id as number)
      })
    })
    return instructorIds.size
  }, [coursesData])

  const loading = statsLoading || coursesLoading

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto" />
          <p className="mt-4 text-secondary-600 font-medium">Loading program courses...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">Program Courses</h1>
          <p className="text-secondary-500 mt-1">
            {termsData?.find((t) => String(t.id) === selectedTermId)?.name || '—'}
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <Select
            value={selectedTermId}
            onValueChange={(value) => setSelectedTermId(value || '')}
            items={termsData?.reduce<Record<string, React.ReactNode>>((acc, term) => {
              acc[String(term.id)] = term.name
              return acc
            }, {}) ?? {}}
          >
            <SelectTrigger className="w-52">
              <SelectValue placeholder="Select term..." />
            </SelectTrigger>
            <SelectContent alignItemWithTrigger={false}>
              {termsData?.map((term) => (
                <SelectItem key={term.id} value={String(term.id)}>
                  {term.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card variant="flat" className="bg-primary-50 border-primary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-primary-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-primary-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Courses</p>
              <p className="text-3xl font-bold text-primary-700">{coursesData?.length || 0}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-cyan-50 border-cyan-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-cyan-100 rounded-xl">
              <UsersIcon className="h-8 w-8 text-cyan-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Students</p>
              <p className="text-3xl font-bold text-cyan-700">{totalStudents}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-violet-50 border-violet-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-violet-100 rounded-xl">
              <AcademicCapIcon className="h-8 w-8 text-violet-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Instructors</p>
              <p className="text-3xl font-bold text-violet-700">{uniqueInstructors}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Credits</p>
              <p className="text-3xl font-bold text-emerald-700">{totalCredits}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Courses Table */}
      {coursesData && coursesData.length > 0 ? (
        <div className="bg-white rounded-xl border border-secondary-200 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-secondary-200">
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Code</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Course</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Instructors</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Credits</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {coursesData.map((course) => (
                <tr
                  key={course.id}
                  className="border-b border-secondary-100 last:border-0 hover:bg-secondary-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/head/course/${course.id}`)}
                >
                  <td className="px-6 py-4">
                    <span className="font-bold text-primary-600">{course.code}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-medium text-secondary-900">{course.name}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-secondary-700">
                      {formatInstructorNames(course.instructors as readonly Record<string, unknown>[] | undefined)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-secondary-900">{course.credits}</span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      to={`/head/course/${course.id}`}
                      className="text-primary-600 hover:text-primary-700"
                      onClick={(e) => e.stopPropagation()}
                    >
                      →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-secondary-200">
          <BookOpenIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
          <h3 className="text-lg font-semibold text-secondary-900 mb-2">No courses found</h3>
          <p className="text-secondary-500 mb-6">No courses are available in your program for this term.</p>
        </div>
      )}
    </div>
  )
}

export default HeadCourses
