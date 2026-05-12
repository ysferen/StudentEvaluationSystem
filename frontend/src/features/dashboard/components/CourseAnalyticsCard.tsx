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
  avgScore: number
  studentsAtRisk: number
  credits?: number
}

export const CourseAnalyticsCard: React.FC<CourseAnalyticsCardProps> = ({
  studentCount,
  avgScore,
  studentsAtRisk,
  credits,
}) => {
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
            <p className="text-sm text-secondary-600 font-medium">Avg Score</p>
            <p className="text-3xl font-bold text-secondary-900">{avgScore}<span className="text-lg text-secondary-400">/100</span></p>
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
            <p className="text-sm text-secondary-600 font-medium">Credits</p>
            <p className="text-3xl font-bold text-secondary-900">{credits ?? 0}</p>
          </div>
        </div>
      </Card>
    </div>
  )
}
