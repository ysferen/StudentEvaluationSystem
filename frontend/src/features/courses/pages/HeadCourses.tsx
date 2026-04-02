import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import { Badge } from '../../../shared/components/ui/Badge'
import {
  BookOpenIcon,
  AcademicCapIcon,
  UsersIcon,
  ChartBarIcon,
  EyeIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline'
import { coreCoursesList, coreProgramsList } from '../../../shared/api/generated/core/core'

const HeadCourses = () => {
  const [selectedProgram, setSelectedProgram] = React.useState<string>('all')

  const results = useQueries({
    queries: [
      {
        queryKey: ['courses'],
        queryFn: () => coreCoursesList({}),
      },
      {
        queryKey: ['programs'],
        queryFn: () => coreProgramsList({}),
      },
    ],
  })

  const [coursesQuery, programsQuery] = results
  const loading = results.some(q => q.isLoading)

  const courses = useMemo(() => coursesQuery.data?.results || [], [coursesQuery.data])
  const programs = useMemo(() => programsQuery.data?.results || [], [programsQuery.data])

  const filteredCourses = useMemo(() => {
    if (selectedProgram === 'all') return courses
    return courses.filter(course => course.program?.id === parseInt(selectedProgram))
  }, [courses, selectedProgram])

  const totalStudents = useMemo(() => {
    return courses.reduce((sum) => sum + Math.floor(Math.random() * 60) + 15, 0)
  }, [courses])

  const totalInstructors = useMemo(() => {
    const instructorIds = new Set<number>()
    courses.forEach(course => {
      course.instructors?.forEach(instructor => {
        if (typeof instructor.id === 'number') instructorIds.add(instructor.id)
      })
    })
    return instructorIds.size
  }, [courses])

  const totalCredits = courses.reduce((sum, course) => sum + (course.credits || 0), 0)

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-secondary-600 font-medium">Loading courses...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">Department Courses</h1>
          <p className="text-secondary-500 mt-1">Overview of all courses in the department</p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={selectedProgram}
            onChange={(e) => setSelectedProgram(e.target.value)}
            className="px-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white text-secondary-900"
          >
            <option value="all">All Programs</option>
            {programs.map((program) => (
              <option key={program.id} value={program.id.toString()}>
                {program.code} - {program.name}
              </option>
            ))}
          </select>
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
              <p className="text-3xl font-bold text-primary-700">{filteredCourses.length}</p>
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
              <p className="text-sm text-secondary-600 font-medium">Instructors</p>
              <p className="text-3xl font-bold text-emerald-700">{totalInstructors}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-amber-50 border-amber-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-amber-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-amber-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Credits</p>
              <p className="text-3xl font-bold text-amber-700">{totalCredits}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Courses Table */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-secondary-900">Course List</h2>
          <div className="flex items-center space-x-2">
            <button className="flex items-center space-x-2 px-3 py-2 text-secondary-600 hover:text-secondary-900 transition-colors">
              <FunnelIcon className="h-4 w-4" />
              <span className="text-sm">Filter</span>
            </button>
          </div>
        </div>

        {filteredCourses.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-secondary-200">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">Course</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">Program</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">Instructor</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">Students</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">Credits</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">Term</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCourses.map((course) => {
                  const program = programs.find(p => p.id === course.program?.id)
                  const studentCount = Math.floor(Math.random() * 60) + 15 // Mock data

                  return (
                    <tr key={course.id} className="border-b border-secondary-100 hover:bg-secondary-50 transition-colors">
                      <td className="py-3 px-4">
                        <div>
                          <div className="font-medium text-secondary-900">{course.code}</div>
                          <div className="text-sm text-secondary-600 line-clamp-1">{course.name}</div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="secondary" className="text-xs">
                          {program?.code || 'N/A'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm text-secondary-900">
                          {course.instructors && course.instructors.length > 0
                            ? `${course.instructors[0].first_name} ${course.instructors[0].last_name}`
                            : 'Not assigned'
                          }
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <UsersIcon className="h-4 w-4 text-secondary-400" />
                          <span className="text-sm text-secondary-900">{studentCount}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-secondary-900">{course.credits}</span>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="secondary" className="text-xs">
                          {course.term?.name || 'Current'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-2">
                          <Link
                            to={`/head/course/${course.id}`}
                            className="text-primary-600 hover:text-primary-700 transition-colors"
                          >
                            <EyeIcon className="h-4 w-4" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-16">
            <BookOpenIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
            <h3 className="text-lg font-semibold text-secondary-900 mb-2">No courses found</h3>
            <p className="text-secondary-500">
              {selectedProgram === 'all'
                ? 'No courses are available in the department.'
                : 'No courses found for the selected program.'
              }
            </p>
          </div>
        )}
      </Card>
    </div>
  )
}

export default HeadCourses
