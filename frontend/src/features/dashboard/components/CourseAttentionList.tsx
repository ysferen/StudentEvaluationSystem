import type { CourseInsightSummary } from '../utils/analytics'
import { Card } from '@/components/ui/custom/Card'

interface CourseAttentionListProps {
  courses: CourseInsightSummary[]
  selectedCourseId?: number
  onSelectCourse: (courseId: number) => void
}

const getAttentionReason = (course: CourseInsightSummary): string => {
  if (course.atRiskStudentRatio >= 30) return `${course.atRiskStudentRatio}% at-risk by average course grade`
  if ((course.averageCourseGrade ?? 100) < 65) return `Low average course grade: ${course.averageCourseGrade}`
  if ((course.weakestLoAverageScore ?? 100) < 65 && course.weakestLoCode) {
    return `Weakest LO average score: ${course.weakestLoCode} at ${course.weakestLoAverageScore}%`
  }
  return 'Monitor current course progress'
}

export const CourseAttentionList = ({ courses, selectedCourseId, onSelectCourse }: CourseAttentionListProps) => {
  const sortedCourses = [...courses].sort((a, b) => {
    const aRisk = a.atRiskStudentRatio
    const bRisk = b.atRiskStudentRatio
    if (bRisk !== aRisk) return bRisk - aRisk
    return (a.averageCourseGrade ?? 100) - (b.averageCourseGrade ?? 100)
  })

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-6 border-b border-secondary-200">
        <h2 className="text-lg font-semibold text-secondary-900">Courses Needing Attention</h2>
        <p className="text-sm text-secondary-500 mt-1">Sorted by at-risk ratio and average course grade</p>
      </div>
      <div className="divide-y divide-secondary-100">
        {sortedCourses.length === 0 ? (
          <p className="p-6 text-sm text-secondary-500">No course analytics available yet.</p>
        ) : sortedCourses.map(course => {
          const isSelected = course.courseId === selectedCourseId

          return (
            <button
              key={course.courseId}
              type="button"
              onClick={() => onSelectCourse(course.courseId)}
              className={`w-full p-4 text-left transition-colors ${isSelected ? 'bg-primary-50' : 'hover:bg-secondary-50'}`}
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-secondary-900">{course.courseCode} - {course.courseName}</p>
                  <p className="text-sm text-secondary-600 mt-1">{getAttentionReason(course)}</p>
                </div>
                <div className="text-right text-sm text-secondary-600">
                  <p>{course.atRiskStudentCount}/{course.studentCount} at risk</p>
                  <p>Average course grade: {course.averageCourseGrade ?? 'N/A'}</p>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </Card>
  )
}
