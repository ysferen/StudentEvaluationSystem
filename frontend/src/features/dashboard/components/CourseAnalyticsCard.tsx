import React from 'react'
import {
  UserGroupIcon,
  AcademicCapIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/custom/Card'
import { AtRiskPanel } from './AtRiskPanel'

interface CourseAnalyticsCardProps {
  studentCount: number
  averageCourseGrade: number | null
  studentsAtRisk: number
  atRiskStudentRatio?: number
  credits?: number
  courseCount?: number
}

export const CourseAnalyticsCard: React.FC<CourseAnalyticsCardProps> = ({
  studentCount,
  averageCourseGrade,
  studentsAtRisk,
  atRiskStudentRatio,
  credits,
  courseCount,
}) => {
  const hasAverageCourseGrade = averageCourseGrade !== null

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card variant="flat" className="bg-white border-secondary-200">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-primary-100 rounded-xl">
            <UserGroupIcon className="h-8 w-8 text-primary-600" />
          </div>
          <div>
            <p className="text-sm text-secondary-600 font-medium">Students</p>
            <p className="text-3xl font-bold text-secondary-900">{studentCount}</p>
          </div>
        </div>
      </Card>
      <Card variant="flat" className="bg-white border-secondary-200">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-violet-100 rounded-xl">
            <AcademicCapIcon className="h-8 w-8 text-violet-600" />
          </div>
          <div>
            <p className="text-sm text-secondary-600 font-medium">Average course grade</p>
            <p className="text-3xl font-bold text-secondary-900">
              {hasAverageCourseGrade ? averageCourseGrade : 'N/A'}
              {hasAverageCourseGrade && <span className="text-lg text-secondary-400">/100</span>}
            </p>
          </div>
        </div>
      </Card>
      <AtRiskPanel riskCount={studentsAtRisk} />
      <Card variant="flat" className="bg-white border-secondary-200">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-violet-100 rounded-xl">
            <BookOpenIcon className="h-8 w-8 text-violet-600" />
          </div>
          <div>
            <p className="text-sm text-secondary-600 font-medium">{courseCount === undefined ? 'Credits' : 'Courses'}</p>
            <p className="text-3xl font-bold text-secondary-900">{courseCount ?? credits ?? 0}</p>
            {atRiskStudentRatio !== undefined && (
              <p className="text-xs text-secondary-500 mt-1">{atRiskStudentRatio}% at-risk by average course grade</p>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}
