import React, { useMemo, useState } from 'react'
import { Card } from '@/components/ui/custom/Card'
import { ChartWidget } from '@/components/ui/custom/ChartWidget'
import { BoxPlotChart, BoxPlotLegend, type BoxPlotData } from './BoxPlotChart'
import { StudentHeatmap, type HeatmapData } from './StudentHeatmap'

export type LearningOutcomeView = 'radar' | 'ranking' | 'boxplot' | 'heatmap'

export interface LearningOutcomePanelItem {
  id: number
  code: string
  description: string
}

export interface LearningOutcomeScore {
  learning_outcome: { code: string }
  score?: number | null
}

interface LearningOutcomesPanelProps {
  title?: string
  subtitle?: string
  outcomeShortLabel?: string
  outcomeLongLabel?: string
  learningOutcomes: LearningOutcomePanelItem[]
  loScores?: LearningOutcomeScore[]
  averageScoresByCode?: Record<string, number>
  boxPlotData?: BoxPlotData[]
  heatmapData?: { loCodes: string[]; students: HeatmapData[] }
  courseId?: number
  isLoading?: boolean
  errorMessage?: string | null
  canCreate?: boolean
  canEdit?: boolean
  canDelete?: boolean
  onCreate?: () => void
  onEdit?: (lo: LearningOutcomePanelItem) => void
  onDelete?: (lo: LearningOutcomePanelItem) => void
  onStudentClick?: (studentName: string) => void
  headerAction?: React.ReactNode
  emptyMessage?: string
}

const viewButtons: Array<{ value: LearningOutcomeView; label: string }> = [
  { value: 'radar', label: 'Radar' },
  { value: 'ranking', label: 'Ranking' },
  { value: 'boxplot', label: 'Boxplot' },
  { value: 'heatmap', label: 'Heatmap' },
]

const getScoreTone = (score: number): string => {
  if (score >= 80) return 'bg-emerald-100 text-emerald-700'
  if (score >= 60) return 'bg-amber-100 text-amber-700'
  return 'bg-rose-100 text-rose-700'
}

const getLoAverage = (
  loCode: string,
  loScores?: LearningOutcomeScore[],
  averageScoresByCode?: Record<string, number>,
): number => {
  const explicitAverage = averageScoresByCode?.[loCode]
  if (typeof explicitAverage === 'number') {
    return Math.round(explicitAverage * 100) / 100
  }

  const scores = (loScores ?? [])
    .filter(score => score.learning_outcome.code === loCode)
    .map(score => score.score ?? 0)

  if (scores.length === 0) return 0
  const total = scores.reduce((sum, score) => sum + score, 0)
  return Math.round((total / scores.length) * 100) / 100
}

export const LearningOutcomesPanel: React.FC<LearningOutcomesPanelProps> = ({
  title = 'Learning Outcomes',
  subtitle,
  outcomeShortLabel = 'LO',
  outcomeLongLabel = 'Learning Outcome',
  learningOutcomes,
  loScores,
  averageScoresByCode,
  boxPlotData = [],
  heatmapData = { loCodes: [], students: [] },
  courseId,
  isLoading = false,
  errorMessage = null,
  canCreate = false,
  canEdit = false,
  canDelete = false,
  onCreate,
  onEdit,
  onDelete,
  onStudentClick,
  headerAction,
  emptyMessage = 'No learning outcomes defined for this course',
}) => {
  const [activeView, setActiveView] = useState<LearningOutcomeView>('radar')

  const outcomesWithScores = useMemo(() => (
    learningOutcomes.map(lo => ({
      ...lo,
      score: getLoAverage(lo.code, loScores, averageScoresByCode),
    }))
  ), [averageScoresByCode, learningOutcomes, loScores])

  const rankedOutcomes = useMemo(() => (
    [...outcomesWithScores].sort((a, b) => a.score - b.score)
  ), [outcomesWithScores])

  const hasOutcomes = learningOutcomes.length > 0

  const emptyState = (
    <div className="rounded-xl border border-secondary-200 bg-secondary-50 px-5 py-8 text-center">
      <h3 className="text-base font-semibold text-secondary-900">No {outcomeLongLabel} data available</h3>
      <p className="mt-2 text-sm text-secondary-500">{emptyMessage}</p>
    </div>
  )

  return (
    <Card>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-secondary-900">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-secondary-500">{subtitle}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {canCreate && (
            <button
              onClick={onCreate}
              className="flex items-center space-x-1.5 rounded-lg bg-primary-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-primary-700"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>New LO</span>
            </button>
          )}
          {headerAction}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {viewButtons.map(button => (
          <button
            key={button.value}
            onClick={() => setActiveView(button.value)}
            className={`rounded-lg px-3 py-1.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 ${
              activeView === button.value
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            {button.label}
          </button>
        ))}
      </div>

      {errorMessage && (
        <div className="mb-4 rounded-xl border border-danger-200 bg-danger-50 px-4 py-3 text-sm font-medium text-danger-800">
          {errorMessage}
        </div>
      )}

      {isLoading ? (
        <div className="flex min-h-56 items-center justify-center rounded-xl border border-dashed border-secondary-200 bg-secondary-50/60 px-4 py-8">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-4 border-primary-600" />
            <p className="mt-3 text-sm font-medium text-secondary-600">Loading chart data...</p>
          </div>
        </div>
      ) : hasOutcomes ? (
        <>
          {activeView === 'radar' && (
            <ChartWidget
              key={`lo-radar-${courseId ?? 'course'}`}
              title=""
              type="radar"
              series={[{
                name: `Average ${outcomeShortLabel} score`,
                data: outcomesWithScores.map(lo => Math.round(lo.score * 10) / 10),
              }]}
              options={{
                xaxis: { categories: outcomesWithScores.map(lo => lo.code) },
                yaxis: { show: false, min: 0, max: 100 },
                fill: { opacity: 0.3, colors: ['#6366f1'] },
                stroke: { colors: ['#6366f1'] },
                colors: ['#6366f1'],
                markers: { size: 4 },
                dataLabels: { enabled: true, background: { enabled: true, borderRadius: 2 } },
                plotOptions: {
                  radar: {
                    polygons: {
                      strokeColors: '#e5e7eb',
                      connectorColors: '#e5e7eb',
                    },
                  },
                },
              }}
              height={320}
              className="border-0 p-0 shadow-none [&>div]:p-0"
            />
          )}

          {activeView === 'ranking' && (
            <div className="space-y-2.5">
              {rankedOutcomes.map((lo, idx) => (
                <div key={lo.id} className="rounded-xl border border-secondary-200 bg-white p-3.5 shadow-sm">
                  <div className="flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-indigo-50 px-2 py-0.5 font-mono text-xs font-bold text-indigo-600">{lo.code}</span>
                        <span className="text-xs font-medium text-secondary-500">Rank {idx + 1}</span>
                      </div>
                    </div>
                    <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-bold ${getScoreTone(lo.score)}`}>
                      Average {outcomeShortLabel} score: {lo.score}%
                    </span>
                  </div>
                  <div className="mt-2.5 h-2.5 overflow-hidden rounded-full bg-secondary-100" aria-label={`${lo.code} average ${outcomeShortLabel} score ${lo.score}%`}>
                    <div className="h-full rounded-full bg-primary-500" style={{ width: `${Math.min(100, Math.max(0, lo.score))}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeView === 'boxplot' && (
            boxPlotData.length > 0 ? (
              <>
                <BoxPlotChart data={boxPlotData} />
                <div className="mt-5 border-t border-secondary-100 pt-4">
                  <BoxPlotLegend />
                </div>
              </>
            ) : emptyState
          )}

          {activeView === 'heatmap' && (
            heatmapData.students.length > 0 ? (
              <StudentHeatmap
                loCodes={heatmapData.loCodes}
                students={heatmapData.students}
                onStudentClick={onStudentClick}
              />
            ) : emptyState
          )}

          <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2">
            {rankedOutcomes.map(lo => (
              <div key={lo.id} className="group relative flex flex-col rounded-xl border border-secondary-200 bg-white p-3 shadow-sm">
                <div className="mb-2 flex items-center justify-between">
                  <span className="rounded bg-indigo-50 px-2 py-0.5 font-mono text-xs font-bold text-indigo-600">{lo.code}</span>
                  <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-bold ${getScoreTone(lo.score)}`}>
                    {lo.score}%
                  </span>
                </div>
                <span className="text-sm leading-snug text-secondary-700">{lo.description || 'No description available'}</span>
                {(canEdit || canDelete) && (
                  <div className="absolute bottom-2 right-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    {canEdit && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onEdit?.(lo) }}
                        className="rounded-md bg-secondary-100 p-1 text-secondary-600 transition-colors hover:bg-primary-100 hover:text-primary-700"
                        title="Edit"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                        </svg>
                      </button>
                    )}
                    {canDelete && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onDelete?.(lo) }}
                        className="rounded-md bg-secondary-100 p-1 text-secondary-600 transition-colors hover:bg-danger-100 hover:text-danger-700"
                        title="Delete"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="py-4 text-center text-secondary-500">{emptyMessage}</p>
      )}
    </Card>
  )
}
