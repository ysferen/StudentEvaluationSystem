import React from 'react'
import { ChartWidget } from '../../../shared/components/ui/ChartWidget'

interface GradeDistributionItem {
  grade: string
  count: number
  color: string
}

interface GradeDistributionChartProps {
  data: GradeDistributionItem[]
  courseId?: number
}

export const GradeDistributionChart: React.FC<GradeDistributionChartProps> = ({
  data,
  courseId,
}) => {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-secondary-500">
        No grade data available
      </div>
    )
  }

  return (
    <ChartWidget
      key={`bar-chart-${courseId}`}
      title=""
      type="bar"
      series={[{
        name: 'Students',
        data: data.map(item => item.count)
      }]}
      options={{
        chart: {
          toolbar: { show: false }
        },
        plotOptions: {
          bar: {
            borderRadius: 6,
            horizontal: true,
            columnWidth: '50%',
            distributed: true,
          }
        },
        grid: {
          yaxis: {
            lines: { show: false }
          }
        },
        xaxis: {
          categories: data.map(item => item.grade),
          labels: {
            style: {
              fontSize: '14px',
              fontWeight: 600
            }
          }
        },
        yaxis: {
          labels: {
            style: {
              fontSize: '13px'
            }
          }
        },
        colors: data.map(item => item.color),
        legend: { show: false },
        dataLabels: {
          enabled: true,
          style: {
            fontSize: '12px',
            fontWeight: 'bold'
          }
        },
        tooltip: {
          y: {
            formatter: (val: number) => `${val} student${val !== 1 ? 's' : ''}`
          }
        }
      }}
      height={320}
      className="shadow-none border-0 p-0"
    />
  )
}
