import React from 'react'
import {
  BookOpenIcon,
  UsersIcon,
  AcademicCapIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/custom/Card'
import type { Course } from '../../../shared/api/model'

interface CourseHeaderProps {
  course: Course
  avgScore: number
  loCount: number
  canEdit: boolean
  canDelete: boolean
  onEdit: () => void
  onDelete: () => void
  onImport: () => void
  getInstructorNames: () => string
}

const getScoreTextColor = (avgScore: number): string => {
  if (avgScore >= 70) return 'text-emerald-700'
  if (avgScore >= 50) return 'text-amber-700'
  if (avgScore === 0) return 'text-secondary-400'
  return 'text-red-700'
}

export const CourseHeader: React.FC<CourseHeaderProps> = ({
  course,
  avgScore,
  loCount,
  canEdit,
  canDelete,
  onEdit,
  onDelete,
  onImport,
  getInstructorNames,
}) => {
  const scoreTextColor = getScoreTextColor(avgScore)

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">
            {course.code} - {course.name}
          </h1>
          <div className="flex items-center gap-2 mt-2">
            {canEdit && (
              <button
                onClick={onEdit}
                className="bg-secondary-100 text-secondary-700 px-3 py-1.5 rounded-lg hover:bg-secondary-200 flex items-center space-x-1.5 transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                </svg>
                <span>Edit</span>
              </button>
            )}
            {canDelete && (
              <button
                onClick={onDelete}
                className="bg-danger-50 text-danger-700 px-3 py-1.5 rounded-lg hover:bg-danger-100 flex items-center space-x-1.5 transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
                <span>Delete</span>
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onImport}
            className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 flex items-center space-x-2 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <span>Import File</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card variant="flat" className="bg-primary-50 border-primary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-primary-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-primary-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Credits</p>
              <p className="text-3xl font-bold text-primary-700">{course.credits}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-cyan-50 border-cyan-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-cyan-100 rounded-xl">
              <UsersIcon className="h-8 w-8 text-cyan-700" />
            </div>
            <div className="min-w-0">
              <p className="text-sm text-secondary-600 font-medium">Instructors</p>
              <p className="text-lg font-bold text-cyan-700 truncate">{getInstructorNames()}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <AcademicCapIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Avg Score</p>
              <p className={`text-3xl font-bold ${scoreTextColor}`}>{avgScore}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-violet-50 border-violet-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-violet-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-violet-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Learning Outcomes</p>
              <p className="text-3xl font-bold text-violet-700">{loCount}</p>
            </div>
          </div>
        </Card>
      </div>
    </>
  )
}
