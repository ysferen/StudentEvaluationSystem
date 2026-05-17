import type { CourseInsightSummary } from '../utils/analytics'
import { Card } from '@/components/ui/custom/Card'

interface CourseHealthMatrixProps {
  courses: CourseInsightSummary[]
  selectedCourseId?: number
  onSelectCourse: (courseId: number) => void
}

export const CourseHealthMatrix = ({ courses, selectedCourseId, onSelectCourse }: CourseHealthMatrixProps) => {
  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-6 border-b border-secondary-200">
        <h2 className="text-lg font-semibold text-secondary-900">Course Health Matrix</h2>
        <p className="text-sm text-secondary-500 mt-1">Average course grade versus at-risk student ratio</p>
      </div>
      <div className="p-6 space-y-3">
        {courses.length === 0 ? (
          <p className="text-sm text-secondary-500">No course analytics available yet.</p>
        ) : courses.map(course => {
          const averageCourseGrade = course.averageCourseGrade ?? 0
          const isSelected = course.courseId === selectedCourseId

          return (
            <button
              key={course.courseId}
              type="button"
              onClick={() => onSelectCourse(course.courseId)}
              className={`w-full grid grid-cols-[7rem_1fr_5rem] items-center gap-3 text-left rounded-xl border p-3 transition-colors ${
                isSelected ? 'border-primary-300 bg-primary-50' : 'border-secondary-200 hover:bg-secondary-50'
              }`}
            >
              <span className="font-semibold text-primary-700">{course.courseCode}</span>
              <span className="relative h-8 rounded-full bg-secondary-100 overflow-hidden">
                <span
                  className="absolute left-0 top-0 h-full bg-primary-500/70"
                  style={{ width: `${Math.min(100, averageCourseGrade)}%` }}
                />
                <span
                  className="absolute top-1/2 -translate-y-1/2 h-5 w-5 rounded-full bg-danger-500 border-2 border-white shadow"
                  style={{ left: `${Math.min(95, course.atRiskStudentRatio)}%` }}
                  title={`${course.atRiskStudentRatio}% at-risk students`}
                />
              </span>
              <span className="text-sm text-secondary-700 text-right leading-tight">
                Average course grade: {course.averageCourseGrade ?? 'N/A'}
              </span>
            </button>
          )
        })}
      </div>
    </Card>
  )
}
