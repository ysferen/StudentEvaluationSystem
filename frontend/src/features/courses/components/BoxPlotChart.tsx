import React from 'react'

export interface BoxPlotData {
  code: string
  min: number
  q1: number
  median: number
  q3: number
  max: number
  mean: number
}

interface BoxPlotChartProps {
  data: BoxPlotData[]
  width?: number
  height?: number
}

const getBoxColor = (median: number) => {
  if (median >= 80) return { stroke: '#15803d', fill: '#bbf7d0', whisker: '#4ade80' }
  if (median >= 60) return { stroke: '#a16207', fill: '#fef08a', whisker: '#facc15' }
  return { stroke: '#b91c1c', fill: '#fecaca', whisker: '#f87171' }
}

export const BoxPlotChart: React.FC<BoxPlotChartProps> = ({
  data,
  width = 500,
  height = 44,
}) => {
  const PAD = 12
  const scale = width / 100
  const x = (v: number) => PAD + v * scale

  if (data.length === 0) {
    return <p className="text-secondary-500 text-center py-4">No data available</p>
  }

  return (
    <div className="space-y-6">
      {data.map((box) => {
        const c = getBoxColor(box.median)

        return (
          <div key={box.code}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-semibold text-secondary-800">{box.code}</span>
              <div className="flex items-center gap-3 text-xs text-secondary-500 tabular-nums">
                <span>Min <span className="font-semibold text-secondary-700">{box.min}</span></span>
                <span>Q1 <span className="font-semibold text-secondary-700">{box.q1}</span></span>
                <span>Med <span className="font-semibold text-secondary-700">{box.median}</span></span>
                <span>Q3 <span className="font-semibold text-secondary-700">{box.q3}</span></span>
                <span>Max <span className="font-semibold text-secondary-700">{box.max}</span></span>
              </div>
            </div>
            <svg width="100%" viewBox={`0 0 ${width + PAD * 2} ${height}`} preserveAspectRatio="none" className="overflow-visible">
              <rect x={PAD} y={19} width={width} height={2} rx={1} fill="#f3f4f6" />
              <line x1={x(box.min)} y1={20} x2={x(box.q1)} y2={20} stroke="#9ca3af" strokeWidth={1.5} />
              <line x1={x(box.q3)} y1={20} x2={x(box.max)} y2={20} stroke="#9ca3af" strokeWidth={1.5} />
              <line x1={x(box.min)} y1={12} x2={x(box.min)} y2={28} stroke="#6b7280" strokeWidth={2} strokeLinecap="round" />
              <line x1={x(box.max)} y1={12} x2={x(box.max)} y2={28} stroke="#6b7280" strokeWidth={2} strokeLinecap="round" />
              <rect
                x={x(box.q1)} y={8} width={x(box.q3) - x(box.q1)} height={24}
                fill={c.fill}
                stroke={c.stroke}
                strokeWidth={2}
                rx={4}
              />
              <line
                x1={x(box.median)} y1={6} x2={x(box.median)} y2={34}
                stroke={c.stroke} strokeWidth={3} strokeLinecap="round"
              />
              <polygon
                points={`${x(box.mean)},${14} ${x(box.mean) + 5},${20} ${x(box.mean)},${26} ${x(box.mean) - 5},${20}`}
                fill="#4f46e5"
                stroke="#fff"
                strokeWidth={1.5}
              />
              {[0, 25, 50, 75, 100].map((tick) => (
                <text key={tick} x={x(tick)} y={42} fontSize={10} textAnchor="middle" fill="#9ca3af" fontFamily="ui-monospace, monospace">
                  {tick}
                </text>
              ))}
            </svg>
          </div>
        )
      })}
    </div>
  )
}

export const BoxPlotLegend: React.FC = () => (
  <div className="flex items-center justify-center gap-5 text-xs text-secondary-500">
    <div className="flex items-center gap-1.5">
      <div className="w-5 h-3 rounded border-2 border-emerald-700 bg-emerald-200" />
      <span>IQR (Q1–Q3)</span>
    </div>
    <div className="flex items-center gap-1.5">
      <div className="w-0.5 h-4 bg-secondary-800 rounded-full" />
      <span>Median</span>
    </div>
    <div className="flex items-center gap-1.5">
      <div className="w-2.5 h-2.5 bg-indigo-600 rotate-45 rounded-[1px]" />
      <span>Mean</span>
    </div>
    <div className="flex items-center gap-1.5">
      <div className="w-0.5 h-3 bg-gray-400 rounded-full mx-1" />
      <span>Whiskers (Min–Max)</span>
    </div>
  </div>
)
