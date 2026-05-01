import { useMemo, memo } from 'react'
import { Link } from 'react-router-dom'
import { Card } from '../../../shared/components/ui/Card'
import { Badge } from '../../../shared/components/ui/Badge'
import {
  BookOpenIcon,
  AcademicCapIcon,
  UsersIcon,
  ChartBarIcon,
  CalendarIcon,
  PlusIcon,
} from '@heroicons/react/24/outline'
import { useCoreCoursesList } from '../../../shared/api/generated/core/core'
import { useCoreAnalyticsProgramStatsRetrieve } from '../../../shared/api/generated/analytics/analytics'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Converts a course's instructor list into a comma-separated name string
 * (e.g. "Jane Smith, John Doe"). Returns "Not assigned" when empty.
 */
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

// ---------------------------------------------------------------------------
// Memoized course card
// ---------------------------------------------------------------------------

const CourseCard = memo(function CourseCard({
  course,
}: {
  course: {
    id: number
    code: string
    name: string
    credits?: number
    term?: { name: string }
    program?: { code: string }
    instructors?: readonly Record<string, unknown>[]
  }
}) {
  const instructorNames = useMemo(
    () => formatInstructorNames(course.instructors),
    [course.instructors],
  )

  return (
    <Card variant="hover" className="group relative">
      {/* Header: code initials, code + term, credits badge */}
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
        <Badge variant="primary" className="text-xs shrink-0">
          {course.credits} CR
        </Badge>
      </div>

      {/* Course name */}
      <h4 className="font-medium text-secondary-900 mb-3 line-clamp-2">
        {course.name}
      </h4>

      {/* Info rows */}
      <div className="space-y-2 mb-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-secondary-600">Program</span>
          <Badge variant="secondary" className="text-xs">
            {course.program?.code || 'N/A'}
          </Badge>
        </div>
        <div className="flex items-center justify-between text-sm gap-2">
          <span className="text-secondary-600 shrink-0">Instructors</span>
          <span className="font-medium text-secondary-900 text-right">
            {instructorNames}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-secondary-600">Credits</span>
          <span className="font-medium text-secondary-900">
            {course.credits}
          </span>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-secondary-100">
        <Link
          to={`/head/course/${course.id}`}
          className="text-primary-600 hover:text-primary-700 text-sm font-medium inline-flex items-center gap-1"
        >
          <ChartBarIcon className="h-4 w-4" />
          View Details
        </Link>
      </div>
    </Card>
  )
})

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

const HeadCourses = () => {
  const { data: statsData, isLoading: statsLoading } =
    useCoreAnalyticsProgramStatsRetrieve()
  const userProgramId = statsData?.programs?.[0]?.id

  const { data: coursesData, isLoading: coursesLoading } = useCoreCoursesList(
    { program: userProgramId },
    { query: { enabled: !!userProgramId } },
  )

  const loading = statsLoading || coursesLoading

  const courses = useMemo(() => coursesData?.results || [], [coursesData])

  const totalStudents = useMemo(
    () => statsData?.programs?.[0]?.total_students ?? 0,
    [statsData],
  )

  const totalInstructors = useMemo(() => {
    const uniqueIds = new Set<number>()
    for (const course of courses) {
      if (!course.instructors) continue
      for (const instructor of course.instructors) {
        if (typeof instructor.id === 'number') {
          uniqueIds.add(instructor.id as number)
        }
      }
    }
    return uniqueIds.size
  }, [courses])

  const totalCredits = courses.reduce(
    (sum, course) => sum + (course.credits || 0),
    0,
  )

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto" />
          <p className="mt-4 text-secondary-600 font-medium">
            Loading courses...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">
            Program Courses
          </h1>
          <p className="text-secondary-500 mt-1">
            Overview of courses in your program
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <Link
            to="/head/courses/new"
            className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors shadow-lg shadow-primary-500/30"
          >
            <PlusIcon className="h-5 w-5" />
            <span>New Course</span>
          </Link>
        </div>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card variant="flat" className="bg-primary-50 border-primary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-primary-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-primary-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">
                Total Courses
              </p>
              <p className="text-3xl font-bold text-primary-700">
                {courses.length}
              </p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-cyan-50 border-cyan-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-cyan-100 rounded-xl">
              <UsersIcon className="h-8 w-8 text-cyan-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">
                Total Students
              </p>
              <p className="text-3xl font-bold text-cyan-700">
                {totalStudents}
              </p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <AcademicCapIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">
                Instructors
              </p>
              <p className="text-3xl font-bold text-emerald-700">
                {totalInstructors}
              </p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-amber-50 border-amber-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-amber-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-amber-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">
                Total Credits
              </p>
              <p className="text-3xl font-bold text-amber-700">
                {totalCredits}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Course card grid */}
      {courses.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </div>
      ) : (
        <Card className="text-center py-16">
          <BookOpenIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
          <h3 className="text-lg font-semibold text-secondary-900 mb-2">
            No courses found
          </h3>
          <p className="text-secondary-500 mb-6">
            No courses are available in your program.
          </p>
          <Link
            to="/head/courses/new"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-colors"
          >
            <PlusIcon className="h-5 w-5" />
            <span>Create Course</span>
          </Link>
        </Card>
      )}
    </div>
  )
}

export default HeadCourses
