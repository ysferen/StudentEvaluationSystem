import Chart from 'react-apexcharts'
import { Card } from './Card'

interface ChartWidgetProps {
    title: string
    subtitle?: string
    type: 'line' | 'area' | 'bar' | 'radar' | 'donut' | 'pie'
    series: any[]
    options?: any
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
            curve: 'smooth'
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
