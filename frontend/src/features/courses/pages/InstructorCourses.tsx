import { useMemo, useState, useEffect } from 'react'
import { useQuery, useQueries } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/hooks/useAuth'
import { Card } from '../../../shared/components/ui/Card'
import { Badge } from '../../../shared/components/ui/Badge'
import {
  BookOpenIcon,
  AcademicCapIcon,
  UsersIcon,
  ChartBarIcon,
  CalendarIcon,
  PlusIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import {
  coreCoursesList,
  coreTermsList,
} from '../../../shared/api/generated/core/core'
import {
  corePermissionsMyPermissionsRetrieve
} from '../../../shared/api/generated/core/core'
import { PermissionTierEnum } from '../../../shared/api/model'
import {
  evaluationGradesCourseAveragesRetrieve
} from '../../../shared/api/generated/evaluation/evaluation'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface CourseStatsData {
  courseId: number
  studentCount: number
  studentIds: number[]
  average: number | null
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const getStudentId = (value: unknown): number | null => {
  if (!isRecord(value)) {
    return null
  }

  const maybeId = value.student_id
  return typeof maybeId === 'number' ? maybeId : null
}

const InstructorCourses = () => {
  const { user } = useAuth()

  const [selectedTermId, setSelectedTermId] = useState<string>('')

  const { data: termsData } = useQuery({
    queryKey: ['terms'],
    queryFn: async () => {
      const response = await coreTermsList()
      return response.results || []
    }
  })

  // Default to active term when terms load
  useEffect(() => {
    if (termsData && !selectedTermId) {
      const active = termsData.find(t => t.is_active)
      if (active) setSelectedTermId(String(active.id))
    }
  }, [termsData, selectedTermId])

  const { data: coursesData, isLoading: coursesLoading } = useQuery({
    queryKey: ['instructor-courses', user?.id, selectedTermId],
    queryFn: async () => {
      const response = await coreCoursesList({
        instructor: user?.id,
        ...(selectedTermId ? { term: Number(selectedTermId) } : {}),
      })
      return response.results || []
    },
    enabled: !!user?.id
  })

  const { data: permissionsData } = useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => corePermissionsMyPermissionsRetrieve(),
    enabled: !!user?.id
  })

  const canCreateCourse = useMemo(() => {
    if (!Array.isArray(permissionsData)) return false
    return permissionsData.some(
      (p: { resource_area?: string; permission_tier?: string }) =>
        p.resource_area === 'courses' && p.permission_tier === PermissionTierEnum.full
    )
  }, [permissionsData])

  // Combined query for both student counts and average scores using grade averages API
  const courseStatsQueries = useQueries({
    queries: (coursesData || []).map((course) => ({
      queryKey: ['course-stats', course.id],
      queryFn: async () => {
        const response = await evaluationGradesCourseAveragesRetrieve({ course: course.id, per_student: true })
        // response is an array of student grade averages with student_id
        if (Array.isArray(response) && response.length > 0) {
          const validAverages = response
            .map(r => r.weighted_average)
            .filter((avg): avg is number => avg !== null)
          const courseAvg = validAverages.length > 0
            ? validAverages.reduce((sum, avg) => sum + avg, 0) / validAverages.length
            : null
          // Extract student IDs from the response (each entry has student_id)
          const studentIds = response
            .map((r) => getStudentId(r))
            .filter((id): id is number => id != null)

          return {
            courseId: course.id,
            studentCount: studentIds.length,
            studentIds,
            average: courseAvg
          } as CourseStatsData
        }
        return {
          courseId: course.id,
          studentCount: 0,
          studentIds: [],
          average: null
        } as CourseStatsData
      },
      enabled: !!coursesData?.length
    }))
  })

  // Calculate total UNIQUE students from all course stats
  const totalStudents = useMemo(() => {
    const allStudentIds = new Set<number>()
    courseStatsQueries.forEach(query => {
      if (query.data?.studentIds) {
        query.data.studentIds.forEach((id: number) => allStudentIds.add(id))
      }
    })
    return allStudentIds.size
  }, [courseStatsQueries])

    const totalCredits = coursesData?.reduce((sum, course) => sum + (course.credits || 0), 0) || 0

  const isLoadingData = coursesLoading || courseStatsQueries.some(q => q.isLoading)

if (isLoadingData) {
  return (
    <div className="flex justify-center items-center min-h-96">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto"></div>
        <p className="mt-4 text-secondary-600 font-medium">Loading your courses...</p>
      </div>
    </div>
  )
}

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">My Courses</h1>
          <p className="text-secondary-500 mt-1">
            {termsData?.find((t) => String(t.id) === selectedTermId)?.name || 'Loading...'}
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
          {canCreateCourse && (
            <button className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors shadow-lg shadow-primary-500/30">
              <PlusIcon className="h-5 w-5" />
              <span>New Course</span>
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card variant="flat" className="bg-primary-50 border-primary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-primary-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-primary-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Active Courses</p>
              <p className="text-3xl font-bold text-primary-700">{  coursesData?.length || 0}</p>
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

        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <AcademicCapIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Credits</p>
              <p className="text-3xl font-bold text-emerald-700">{totalCredits}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Courses Grid */}
      {coursesData && coursesData.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {coursesData.map((course, index) => {
            // Get real data from combined query
            const statsData = courseStatsQueries[index]?.data
            const studentCount = statsData?.studentCount ?? 0
            const avgScore = statsData?.average ? Math.round(statsData.average) : null

            return (
              <Card key={course.id} variant="hover" className="group relative">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="h-12 w-12 rounded-xl bg-primary-600 flex items-center justify-center text-white font-bold shadow-lg">
                      {course.code?.slice(0, 2)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-secondary-900 group-hover:text-primary-600 transition-colors">
                        {course.code}
                      </h3>
                      <p className="text-xs text-secondary-500 flex items-center gap-1">
                        <CalendarIcon className="h-3 w-3" />
                        {course.term?.name || 'Current Term'}
                      </p>
                    </div>
                  </div>
                  <Badge variant="primary" className="text-xs">
                    {course.credits} CR
                  </Badge>
                </div>

                <h4 className="font-medium text-secondary-900 mb-3 line-clamp-2">
                  {course.name}
                </h4>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-secondary-600">Students</span>
                    {courseStatsQueries[index]?.isLoading ? (
                      <span className="text-secondary-400 animate-pulse">Loading...</span>
                    ) : (
                      <span className="font-medium text-secondary-900">{studentCount}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-secondary-600">Avg Score</span>
                    {courseStatsQueries[index]?.isLoading ? (
                      <span className="text-secondary-400 animate-pulse">Loading...</span>
                    ) : avgScore !== null ? (
                      <span className="font-medium text-secondary-900">{avgScore}</span>
                    ) : (
                      <span className="text-secondary-400">No data</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-secondary-600">Credits</span>
                    <span className="font-medium text-secondary-900">{course.credits}</span>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-secondary-100">
                  <div className="flex items-center justify-between">
                    <Link
                      to={`/instructor/course/${course.id}`}
                      className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center gap-1"
                    >
                      <ChartBarIcon className="h-4 w-4" />
                      View Details
                    </Link>
                    <button className="text-secondary-400 hover:text-secondary-600 transition-colors">
                      <Cog6ToothIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      ) : (
        <Card className="text-center py-16">
          <BookOpenIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
          <h3 className="text-lg font-semibold text-secondary-900 mb-2">No courses assigned</h3>
          <p className="text-secondary-500 mb-6">You haven't been assigned to any courses yet.</p>
          {canCreateCourse && (
            <button className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors">
              <PlusIcon className="h-5 w-5" />
              <span>Create Course</span>
            </button>
          )}
        </Card>
      )}
    </div>
  )
}

export default InstructorCourses
