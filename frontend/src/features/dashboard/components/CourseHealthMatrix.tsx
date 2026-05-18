import type { CourseInsightSummary } from '../utils/analytics'
import { Card } from '@/components/ui/custom/Card'

interface CourseHealthMatrixProps {
  courses: CourseInsightSummary[]
  selectedCourseId?: number
  onSelectCourse: (courseId: number) => void
}

export const CourseHealthMatrix = ({ courses, selectedCourseId, onSelectCourse }: CourseHealthMatrixProps) => {
  const maxStudentCount = Math.max(...courses.map(course => course.studentCount), 0)

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-6 border-b border-secondary-200">
        <h2 className="text-lg font-semibold text-secondary-900">Course Health Matrix</h2>
        <p className="text-sm text-secondary-500 mt-1">Average course grade versus at-risk student ratio</p>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-secondary-600">
          <span className="inline-flex items-center gap-2">
            <span className="h-2.5 w-8 rounded-full bg-primary-500/70" aria-hidden="true" />
            Teal bar = average course grade
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-3.5 w-3.5 rounded-full bg-danger-500 border-2 border-white shadow" aria-hidden="true" />
            Red marker = at-risk student ratio
          </span>
          <span>Marker size and row label show students with grade data.</span>
        </div>
      </div>
      <div className="p-6 space-y-3">
        {courses.length === 0 ? (
          <p className="text-sm text-secondary-500">No course analytics available yet.</p>
        ) : courses.map(course => {
          const hasAverageCourseGrade = course.averageCourseGrade !== null
          const isEmptyCourse = !hasAverageCourseGrade && course.studentCount === 0
          const atRiskLabel = hasAverageCourseGrade ? `${course.atRiskStudentRatio}% at risk` : 'At-risk ratio: N/A'
          const averageCourseGrade = course.averageCourseGrade ?? 0
          const isSelected = course.courseId === selectedCourseId
          const markerSize = maxStudentCount > 0
            ? 14 + Math.round((course.studentCount / maxStudentCount) * 12)
            : 14

          return (
            <button
              key={course.courseId}
              type="button"
              onClick={() => onSelectCourse(course.courseId)}
              className={`w-full grid grid-cols-1 gap-3 text-left rounded-xl border p-3 transition-colors sm:grid-cols-[7rem_1fr_8rem] sm:items-center ${
                isSelected ? 'border-primary-300 bg-primary-50' : 'border-secondary-200 hover:bg-secondary-50'
              }`}
              aria-label={`${course.courseCode}: ${hasAverageCourseGrade ? `average course grade ${course.averageCourseGrade}` : 'no grade data'}, ${hasAverageCourseGrade ? `${course.atRiskStudentRatio}% at-risk students` : 'at-risk ratio N/A'}, ${course.studentCount} students with grade data`}
            >
              <span className="font-semibold text-primary-700">{course.courseCode}</span>
              <span className={`relative h-8 rounded-full ${hasAverageCourseGrade ? 'bg-secondary-100' : 'bg-secondary-50 border border-dashed border-secondary-200'} overflow-hidden`}>
                {hasAverageCourseGrade ? (
                  <span
                    className="absolute left-0 top-0 h-full bg-primary-500/70"
                    style={{ width: `${Math.min(100, averageCourseGrade)}%` }}
                  />
                ) : (
                  <span className="absolute inset-0 flex items-center px-3 text-xs font-medium text-secondary-400">
                    {isEmptyCourse ? 'No grade data' : 'Average course grade N/A'}
                  </span>
                )}
                {hasAverageCourseGrade ? (
                  <span
                    className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-danger-500 border-2 border-white shadow"
                    style={{
                      height: `${markerSize}px`,
                      left: `${Math.min(100, Math.max(0, course.atRiskStudentRatio))}%`,
                      width: `${markerSize}px`,
                    }}
                    title={`${course.atRiskStudentRatio}% at-risk students; ${course.studentCount} students with grade data`}
                    aria-hidden="true"
                  />
                ) : null}
              </span>
              <span className="text-sm text-secondary-700 text-right leading-tight">
                <span className="block font-medium text-secondary-900">
                  {isEmptyCourse ? 'No grade data' : `${course.averageCourseGrade ?? 'N/A'} avg`}
                </span>
                <span className="block text-xs text-secondary-500">
                  {course.studentCount} grade-data students · {atRiskLabel}
                </span>
              </span>
            </button>
          )
        })}
      </div>
    </Card>
  )
}
