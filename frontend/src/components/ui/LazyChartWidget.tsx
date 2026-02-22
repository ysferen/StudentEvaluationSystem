import { lazy, Suspense } from 'react'

// Lazy load the actual ChartWidget component (and ApexCharts with it)
const ChartWidget = lazy(() => import('./ChartWidget').then(module => ({
  default: module.ChartWidget
})))

// Skeleton/placeholder while chart loads
function ChartLoadingSkeleton({ height = 350 }: { height?: number }) {
  return (
    <div
      className="animate-pulse bg-gray-200 rounded-lg flex items-center justify-center"
      style={{ height: `${height}px` }}
    >
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p className="mt-2 text-sm text-gray-500">Loading chart...</p>
      </div>
    </div>
  )
}

// Export wrapper that adds Suspense
export function LazyChartWidget(props: any) {
  return (
    <Suspense fallback={<ChartLoadingSkeleton height={props.height} />}>
      <ChartWidget {...props} />
    </Suspense>
  )
}
