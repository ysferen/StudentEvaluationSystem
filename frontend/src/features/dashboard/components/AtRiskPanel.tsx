import React from 'react'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/custom/Card'

interface AtRiskPanelProps {
  riskCount: number
}

export const AtRiskPanel: React.FC<AtRiskPanelProps> = ({ riskCount }) => {
  const riskColorClass = riskCount > 10
    ? 'text-danger-600'
    : riskCount > 5
      ? 'text-warning-600'
      : 'text-success-600'

  return (
    <Card variant="flat" className="bg-white border-secondary-200">
      <div className="flex items-center space-x-4">
        <div className="p-3 bg-danger-100 rounded-xl">
          <ExclamationTriangleIcon className="h-8 w-8 text-danger-600" />
        </div>
        <div>
          <p className="text-sm text-secondary-600 font-medium">Students at Risk</p>
          <p className={`text-3xl font-bold ${riskColorClass}`}>{riskCount}</p>
        </div>
      </div>
    </Card>
  )
}
