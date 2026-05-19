import React from 'react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/custom/Card'

interface AtRiskPanelProps {
  riskCount: number
  riskRatio?: number
  studentCount?: number
}

const getRiskStatus = (riskCount: number, riskRatio?: number, studentCount?: number) => {
  if (studentCount === 0) {
    return { label: 'No grade data', className: 'bg-secondary-50 text-secondary-700 border-secondary-200' }
  }

  if (riskRatio !== undefined) {
    if (riskRatio >= 30) return { label: 'High risk', className: 'bg-danger-50 text-danger-700 border-danger-200' }
    if (riskRatio > 0) return { label: 'Some risk', className: 'bg-warning-50 text-warning-700 border-warning-200' }
    return { label: 'Low risk', className: 'bg-success-50 text-success-700 border-success-200' }
  }

  if (riskCount > 10) return { label: 'High risk', className: 'bg-danger-50 text-danger-700 border-danger-200' }
  if (riskCount > 5) return { label: 'Some risk', className: 'bg-warning-50 text-warning-700 border-warning-200' }
  return { label: 'Low risk', className: 'bg-success-50 text-success-700 border-success-200' }
}

export const AtRiskPanel: React.FC<AtRiskPanelProps> = ({ riskCount, riskRatio, studentCount }) => {
  const riskStatus = getRiskStatus(riskCount, riskRatio, studentCount)
  const riskColorClass = riskStatus.className.includes('danger')
    ? 'text-danger-600'
    : riskStatus.className.includes('warning')
      ? 'text-warning-600'
      : riskStatus.className.includes('success')
        ? 'text-success-600'
        : 'text-secondary-900'
  const riskContext = riskRatio === undefined
    ? 'Based on course grades'
    : studentCount === 0
      ? 'No student grade data'
      : `${riskRatio}% of students`

  return (
    <Card variant="flat" className="bg-white border-secondary-200">
      <div className="flex items-center space-x-4">
        <div className="p-3 bg-danger-100 rounded-xl">
          <ExclamationTriangleIcon className="h-8 w-8 text-danger-600" />
        </div>
        <div>
          <p className="text-sm text-secondary-600 font-medium">Students at Risk</p>
          <p className={`text-3xl font-bold ${riskColorClass}`}>{riskCount}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${riskStatus.className}`}>
              {riskStatus.label}
            </span>
            <span className="text-xs text-secondary-500">
              {riskContext}
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}
