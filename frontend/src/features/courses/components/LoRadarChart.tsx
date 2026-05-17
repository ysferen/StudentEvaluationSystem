import React from 'react'
import { ChartWidget } from '@/components/ui/custom/ChartWidget'
import type { CoreLearningOutcome } from '../../../shared/api/model'

interface LoRadarChartProps {
  learningOutcomes: CoreLearningOutcome[]
  loScores?: Array<{ learning_outcome: { code: string }; score?: number }>
}

const getLOPerformance = (
  loCode: string,
  loScores?: Array<{ learning_outcome: { code: string }; score?: number }>
): number => {
  if (!loScores) return 0
  const loScoresFiltered = loScores.filter((score) =>
    score.learning_outcome.code === loCode
  )
  if (loScoresFiltered.length === 0) return 0
  const total = loScoresFiltered.reduce((sum, score) => sum + (score.score ?? 0), 0)
  return Math.round((total / loScoresFiltered.length) * 100) / 100
}

export const LoRadarChart: React.FC<LoRadarChartProps> = ({
  learningOutcomes,
  loScores,
}) => {
  if (learningOutcomes.length === 0) {
    return <p className="text-secondary-500 text-center py-4">No learning outcomes defined for this course</p>
  }

  return (
    <ChartWidget
      title=""
      type="radar"
      series={[{
        name: 'Average LO score',
        data: learningOutcomes.map(lo => Math.round(getLOPerformance(lo.code, loScores) * 10) / 10)
      }]}
      options={{
        xaxis: {
          categories: learningOutcomes.map(lo => lo.code)
        },
        yaxis: {
          show: false,
          min: 0,
          max: 100
        },
        fill: {
          opacity: 0.3,
          colors: ['#6366f1']
        },
        stroke: {
          colors: ['#6366f1']
        },
        colors: ['#6366f1'],
        markers: {
          size: 4
        },
        dataLabels: {
          enabled: true,
          background: {
            enabled: true,
            borderRadius: 2,
          }
        },
        plotOptions: {
          radar: {
            polygons: {
              strokeColors: '#e5e7eb',
              connectorColors: '#e5e7eb',
            }
          }
        }
      }}
      height={320}
      className="shadow-none border-0 p-0 [&>div]:p-0"
    />
  )
}
