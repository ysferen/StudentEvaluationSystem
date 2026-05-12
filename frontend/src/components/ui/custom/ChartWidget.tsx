import ReactApexChart from 'react-apexcharts'
import type { ApexOptions } from 'apexcharts'
import { Card } from './Card'

// Safely unwrap the CJS export. If it's wrapped in an object, we extract .default.
// If it's already the component, we just use it directly.
const Chart = (ReactApexChart as any).default || ReactApexChart

export interface ChartWidgetProps {
    title: string
    subtitle?: string
    type: 'line' | 'area' | 'bar' | 'radar' | 'donut' | 'pie'
    series: any[] // Note: Add your ApexAxisChartSeries type imports back if needed!
    options?: ApexOptions
    height?: number
    className?: string
}

export const ChartWidget = ({
    title,
    subtitle,
    type,
    series,
    options = {},
    height = 350,
    className
}: ChartWidgetProps) => {
    const defaultOptions = {
        chart: {
            toolbar: {
                show: false
            },
            fontFamily: 'Inter, sans-serif',
        },
        dataLabels: {
            enabled: false
        },
        stroke: {
            curve: 'smooth' as const
        },
        ...options
    }

    return (
        <Card className={className}>
            <div className="mb-4">
                <h3 className="text-lg font-bold text-secondary-900">{title}</h3>
                {subtitle && <p className="text-sm text-secondary-500">{subtitle}</p>}
            </div>
            <div className="w-full">
                <Chart
                    options={defaultOptions}
                    series={series}
                    type={type}
                    height={height}
                    width="100%"
                />
            </div>
        </Card>
    )
}
