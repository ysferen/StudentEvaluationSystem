import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import {
  BookOpenIcon,
  AcademicCapIcon,
  ChartBarIcon,
  CalendarIcon,
  UserIcon,
} from '@heroicons/react/24/outline'
import { evaluationEnrollmentsList } from '../api/generated/evaluation/evaluation'

const StudentCourses = () => {
  const { user } = useAuth()

  const { data, isLoading } = useQuery({
    queryKey: ['studentEnrollments', user?.id],
    queryFn: () => evaluationEnrollmentsList({ student: user!.id }),
    enabled: !!user,
  })

  const enrollments = useMemo(() => data?.results || [], [data])
  const totalCredits = useMemo(
    () => enrollments.reduce((sum, e: any) => sum + (e.course.credits || 0), 0),
    [enrollments]
  )

  if (isLoading) {
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
      <div>
        <h1 className="text-3xl font-bold text-secondary-900">My Courses</h1>
        <p className="text-secondary-500 mt-1">Courses you are currently enrolled in</p>
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
              <p className="text-3xl font-bold text-primary-700">{enrollments.length}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-cyan-50 border-cyan-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-cyan-100 rounded-xl">
              <AcademicCapIcon className="h-8 w-8 text-cyan-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Credits</p>
              <p className="text-3xl font-bold text-cyan-700">{totalCredits}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Completed</p>
              <p className="text-3xl font-bold text-emerald-700">
                {enrollments.filter(e => e.id).length}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Courses Grid */}
      {enrollments.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {enrollments.map(enrollment => (
            <Link
              key={enrollment.id}
              to={`/student/courses/${enrollment.course.id}`}
              className="block"
            >
              <Card variant="hover" className="group cursor-pointer h-full transition-all duration-200 hover:shadow-lg hover:border-primary-300">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="h-12 w-12 rounded-xl bg-primary-600 flex items-center justify-center text-white font-bold shadow-lg">
                      {enrollment.course.code?.slice(0, 2)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-secondary-900 group-hover:text-primary-600 transition-colors">
                        {enrollment.course.code}
                      </h3>
                      <p className="text-xs text-secondary-500 flex items-center gap-1">
                        <CalendarIcon className="h-3 w-3" />
                        {enrollment.course.term?.name || 'Current Term'}
                      </p>
                    </div>
                  </div>
                  <Badge variant="primary" className="text-xs">
                    {enrollment.course.credits} CR
                  </Badge>
                </div>
                
                <h4 className="font-medium text-secondary-900 mb-3 line-clamp-2">
                  {enrollment.course.name}
                </h4>
                
                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-sm text-secondary-600">
                    <UserIcon className="h-4 w-4 mr-2" />
                    {enrollment.course.instructors.length > 0
                      ? `${enrollment.course.instructors[0].first_name} ${enrollment.course.instructors[0].last_name}`
                      : 'Not assigned'
                    }
                  </div>
                  <div className="flex items-center text-sm text-secondary-600">
                    <AcademicCapIcon className="h-4 w-4 mr-2" />
                    {enrollment.course.credits} credits
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-secondary-100">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-secondary-600">Status</span>
                    <Badge variant="info">In Progress</Badge>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card className="text-center py-16">
          <BookOpenIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
          <h3 className="text-lg font-semibold text-secondary-900 mb-2">No courses enrolled</h3>
          <p className="text-secondary-500">You haven't enrolled in any courses yet.</p>
        </Card>
      )}
    </div>
  )
}

export default StudentCourses
