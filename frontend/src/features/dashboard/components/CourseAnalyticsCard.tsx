import React from 'react'
import { Users, GraduationCap, BookOpen } from 'lucide-react'
import { Card } from '@/components/ui/custom/Card'
import { AtRiskPanel } from './AtRiskPanel'

interface CourseAnalyticsCardProps {
  studentCount: number
  averageCourseGrade: number | null
  studentsAtRisk: number
  atRiskStudentRatio?: number
  credits?: number
  courseCount?: number
  attentionCourseCount?: number
}

const getAverageGradeStatus = (averageCourseGrade: number | null) => {
  if (averageCourseGrade === null) {
    return { label: 'No grade data', className: 'bg-secondary-50 text-secondary-700 border-secondary-200' }
  }

  if (averageCourseGrade < 65) return { label: 'Low', className: 'bg-danger-50 text-danger-700 border-danger-200' }
  if (averageCourseGrade < 80) return { label: 'Moderate', className: 'bg-warning-50 text-warning-700 border-warning-200' }
  return { label: 'Good', className: 'bg-success-50 text-success-700 border-success-200' }
}

const getCourseStatus = (
  courseCount?: number,
  attentionCourseCount?: number,
  credits?: number,
  studentCount?: number,
  averageCourseGrade?: number | null,
) => {
  if (courseCount === undefined) {
    return {
      label: `${credits ?? 0} credit${(credits ?? 0) === 1 ? '' : 's'} tracked`,
      className: 'bg-secondary-50 text-secondary-700 border-secondary-200',
    }
  }

  if (courseCount === 0) {
    return { label: 'No courses tracked', className: 'bg-secondary-50 text-secondary-700 border-secondary-200' }
  }

  if (attentionCourseCount !== undefined && attentionCourseCount > 0) {
    return {
      label: `${attentionCourseCount} course${attentionCourseCount === 1 ? '' : 's'} need${attentionCourseCount === 1 ? 's' : ''} attention`,
      className: 'bg-warning-50 text-warning-700 border-warning-200',
    }
  }

  if (studentCount === 0 && averageCourseGrade === null) {
    return { label: 'No grade data yet', className: 'bg-secondary-50 text-secondary-700 border-secondary-200' }
  }

  if (attentionCourseCount === 0) {
    return { label: 'No courses need attention', className: 'bg-success-50 text-success-700 border-success-200' }
  }

  return {
    label: `${courseCount} course${courseCount === 1 ? '' : 's'} tracked`,
    className: 'bg-secondary-50 text-secondary-700 border-secondary-200',
  }
}

export const CourseAnalyticsCard: React.FC<CourseAnalyticsCardProps> = ({
  studentCount,
  averageCourseGrade,
  studentsAtRisk,
  atRiskStudentRatio,
  credits,
  courseCount,
  attentionCourseCount,
}) => {
  const hasAverageCourseGrade = averageCourseGrade !== null
  const averageGradeStatus = getAverageGradeStatus(averageCourseGrade)
  const courseStatus = getCourseStatus(courseCount, attentionCourseCount, credits, studentCount, averageCourseGrade)

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card variant="flat" className="bg-white border-secondary-200">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-primary-100 rounded-xl">
            <Users className="h-8 w-8 text-primary-600" />
          </div>
          <div>
            <p className="text-sm text-secondary-600 font-medium">Students</p>
            <p className="text-3xl font-bold text-secondary-900">{studentCount}</p>
            <p className="mt-1 text-xs text-secondary-500">Students with grade data</p>
          </div>
        </div>
      </Card>
      <Card variant="flat" className="bg-white border-secondary-200">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-violet-100 rounded-xl">
            <GraduationCap className="h-8 w-8 text-violet-600" />
          </div>
          <div>
            <p className="text-sm text-secondary-600 font-medium">Average course grade</p>
            <p className="text-3xl font-bold text-secondary-900">
              {hasAverageCourseGrade ? averageCourseGrade : 'N/A'}
              {hasAverageCourseGrade && <span className="text-lg text-secondary-400">/100</span>}
            </p>
            <span className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${averageGradeStatus.className}`}>
              {averageGradeStatus.label}
            </span>
          </div>
        </div>
      </Card>
      <AtRiskPanel riskCount={studentsAtRisk} riskRatio={atRiskStudentRatio} studentCount={studentCount} />
      <Card variant="flat" className="bg-white border-secondary-200">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-violet-100 rounded-xl">
            <BookOpen className="h-8 w-8 text-violet-600" />
          </div>
          <div>
            <p className="text-sm text-secondary-600 font-medium">{courseCount === undefined ? 'Credits' : 'Courses'}</p>
            <p className="text-3xl font-bold text-secondary-900">{courseCount ?? credits ?? 0}</p>
            <span className={`mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${courseStatus.className}`}>
              {courseStatus.label}
            </span>
          </div>
        </div>
      </Card>
    </div>
  )
}
