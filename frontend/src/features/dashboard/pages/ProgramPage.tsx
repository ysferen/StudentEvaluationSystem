import { useEffect, useMemo, useState, useCallback } from 'react'
import type { FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AcademicCapIcon,
  BookOpenIcon,
  ChartBarIcon,
  DocumentChartBarIcon,
  UsersIcon,
} from '@heroicons/react/24/outline'
import { Card } from '@/components/ui/custom/Card'
import ConfirmDeleteModal from '@/components/ui/custom/ConfirmDeleteModal'
import { LazyChartWidget as ChartWidget } from '@/components/ui/custom/LazyChartWidget'
import Modal from '@/components/ui/custom/Modal'
import { LearningOutcomesPanel } from '@/features/courses/components/LearningOutcomesPanel'
import type { BoxPlotData } from '@/features/courses/components/BoxPlotChart'
import type { HeatmapData } from '@/features/courses/components/StudentHeatmap'
import { coreCoursesList, useCoreTermsActiveRetrieve } from '@/shared/api/generated/core/core'
import { useCoreAnalyticsProgramStatsRetrieve } from '@/shared/api/generated/analytics/analytics'
import {
  coreProgramOutcomesList,
  useCoreProgramOutcomesCreate,
  useCoreProgramOutcomesDestroy,
  useCoreProgramOutcomesPartialUpdate,
} from '@/shared/api/generated/outcomes/outcomes'
import { coreStudentPoScoresList } from '@/shared/api/generated/scores/scores'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { downloadReportPdf } from '@/shared/api/reportDownloads'
import type { CoreStudentPoScoresListParams, ProgramOutcome, StudentProgramOutcomeScore } from '@/shared/api/model'

const fetchAllStudentPoScores = async (params: Omit<CoreStudentPoScoresListParams, 'page'>) => {
  const results: StudentProgramOutcomeScore[] = []
  let page = 1
  let hasNextPage = true

  while (hasNextPage) {
    const response = await coreStudentPoScoresList({ ...params, page })
    results.push(...(response.results || []))
    hasNextPage = Boolean(response.next)
    page += 1
  }

  return results
}

const getQuantile = (arr: number[], q: number): number => {
  const pos = (arr.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  if (arr[base + 1] !== undefined) {
    return arr[base] + rest * (arr[base + 1] - arr[base])
  }
  return arr[base]
}

const roundScore = (value: number): number => Math.round(value * 100) / 100

const inputClass = 'block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition'

interface ProgramOutcomeModalProps {
  isOpen: boolean
  mode: 'create' | 'edit'
  programId: number | undefined
  termId: number | undefined
  existingPo?: ProgramOutcome | null
  onClose: () => void
  onSuccess: () => void
}

const ProgramOutcomeModal = ({
  isOpen,
  mode,
  programId,
  termId,
  existingPo,
  onClose,
  onSuccess,
}: ProgramOutcomeModalProps) => {
  const [code, setCode] = useState('')
  const [description, setDescription] = useState('')
  const [weight, setWeight] = useState('0')
  const [error, setError] = useState<string | null>(null)
  const createMutation = useCoreProgramOutcomesCreate()
  const updateMutation = useCoreProgramOutcomesPartialUpdate()

  useEffect(() => {
    if (mode === 'edit' && existingPo) {
      setCode(existingPo.code)
      setDescription(existingPo.description)
      setWeight(String(existingPo.weight ?? 0))
    } else if (mode === 'create') {
      setCode('')
      setDescription('')
      setWeight('0')
    }
    setError(null)
  }, [existingPo, isOpen, mode])

  const handleClose = () => {
    setCode('')
    setDescription('')
    setWeight('0')
    setError(null)
    onClose()
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    if (!code.trim()) {
      setError('PO code is required')
      return
    }
    if (!description.trim()) {
      setError('Description is required')
      return
    }

    const parsedWeight = Number(weight)
    if (Number.isNaN(parsedWeight) || parsedWeight < 0 || parsedWeight > 1) {
      setError('Weight must be between 0 and 1')
      return
    }

    try {
      if (mode === 'create') {
        if (!programId || !termId) {
          setError('Program and active term are required to create a PO')
          return
        }
        await createMutation.mutateAsync({
          data: {
            code: code.trim(),
            description: description.trim(),
            weight: parsedWeight,
            program_id: programId,
            term_id: termId,
          },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any)
      } else if (existingPo) {
        await updateMutation.mutateAsync({
          id: existingPo.id,
          data: {
            code: code.trim(),
            description: description.trim(),
            weight: parsedWeight,
          },
        })
      }
      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save program outcome')
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={mode === 'create' ? 'Create Program Outcome' : 'Edit Program Outcome'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
            <p className="text-sm text-danger-600">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Code *</label>
          <input
            type="text"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            className={inputClass}
            placeholder="e.g., PO1"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Description *</label>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className={inputClass}
            placeholder="Describe the program outcome..."
            rows={4}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Weight</label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={weight}
            onChange={(event) => setWeight(event.target.value)}
            className={inputClass}
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={handleClose} className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors">
            Cancel
          </button>
          <button type="submit" disabled={createMutation.isPending || updateMutation.isPending} className="px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50">
            {createMutation.isPending || updateMutation.isPending ? 'Saving...' : mode === 'create' ? 'Create' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

const ProgramPage = () => {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { data: statsData, isLoading: statsLoading, error: statsError, refetch } =
    useCoreAnalyticsProgramStatsRetrieve()
  const { data: activeTerm } = useCoreTermsActiveRetrieve()
  const [activeChart, setActiveChart] = useState<'gpa' | 'po'>('gpa')
  const [poCreateModalOpen, setPoCreateModalOpen] = useState(false)
  const [poEditTarget, setPoEditTarget] = useState<ProgramOutcome | null>(null)
  const [poDeleteTarget, setPoDeleteTarget] = useState<ProgramOutcome | null>(null)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const deletePoMutation = useCoreProgramOutcomesDestroy()

  const handleSetGpaChart = useCallback(() => setActiveChart('gpa'), [])
  const handleSetPoChart = useCallback(() => setActiveChart('po'), [])

  const programs = useMemo(() => statsData?.programs || [], [statsData])
  const primaryProgramId = programs[0]?.id
  const programName = programs.length === 1 ? programs[0].name : 'Program'
  const programSubtitle = programs.length === 1 ? programs[0].code : 'All assigned programs'
  const canGenerateProgramReport = programs.length === 1 && typeof primaryProgramId === 'number'
  const canCreatePO = user?.role === 'admin' || user?.role === 'program_head' || (user?.permissions?.includes('program_outcomes.add_programoutcome') ?? false)
  const canEditPO = user?.role === 'admin' || user?.role === 'program_head' || (user?.permissions?.includes('program_outcomes.change_programoutcome') ?? false)
  const canDeletePO = user?.role === 'admin' || user?.role === 'program_head' || (user?.permissions?.includes('program_outcomes.delete_programoutcome') ?? false)

  const { data: coursesData = [], isLoading: coursesLoading } = useQuery({
    queryKey: ['program-page-courses', primaryProgramId, programs.length],
    queryFn: async () => {
      const response = await coreCoursesList(programs.length === 1 ? { program: primaryProgramId } : undefined)
      return response.results || []
    },
    enabled: programs.length !== 1 || !!primaryProgramId,
  })

  const { data: programOutcomesData = [], isLoading: outcomesLoading } = useQuery({
    queryKey: ['program-page-program-outcomes', primaryProgramId, activeTerm?.id],
    queryFn: async () => {
      const response = await coreProgramOutcomesList({
        term: activeTerm?.id,
        program: primaryProgramId,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any)
      return response.results || []
    },
    enabled: !!primaryProgramId && !!activeTerm?.id,
  })

  const { data: poScoresData = [], isLoading: poScoresLoading } = useQuery({
    queryKey: ['program-page-po-scores', primaryProgramId, activeTerm?.id],
    queryFn: async () => {
      return fetchAllStudentPoScores({
        program: primaryProgramId,
        term: activeTerm?.id,
      })
    },
    enabled: !!primaryProgramId && !!activeTerm?.id,
  })

  const totalCredits = useMemo(
    () => coursesData.reduce((sum, course) => sum + (course.credits || 0), 0),
    [coursesData],
  )

  const totalInstructors = useMemo(() => {
    const instructorIds = new Set<number>()
    coursesData.forEach(course => {
      course.instructors?.forEach(instructor => {
        if (typeof instructor.id === 'number') instructorIds.add(instructor.id)
      })
    })
    return instructorIds.size
  }, [coursesData])

  const poCount = useMemo(
    () => programs.reduce((sum, program) => sum + program.po_count, 0),
    [programs],
  )

  const averagePoScore = useMemo(() => {
    const scoredPrograms = programs.filter(program => program.avg_score !== null)
    if (scoredPrograms.length === 0) return null
    const total = scoredPrograms.reduce((sum, program) => sum + (program.avg_score ?? 0), 0)
    return total / scoredPrograms.length
  }, [programs])

  const programOutcomes = useMemo(() => {
    const byCode = new Map<string, ProgramOutcome>()
    programOutcomesData.forEach(outcome => byCode.set(outcome.code, outcome))
    poScoresData
      .filter(score => !primaryProgramId || score.program_outcome.program === primaryProgramId)
      .forEach(score => byCode.set(score.program_outcome.code, score.program_outcome))
    return Array.from(byCode.values()).sort((a, b) => a.code.localeCompare(b.code))
  }, [poScoresData, primaryProgramId, programOutcomesData])

  const poScoresByCode = useMemo(() => {
    const grouped = new Map<string, number[]>()
    poScoresData
      .filter(score => !primaryProgramId || score.program_outcome.program === primaryProgramId)
      .forEach(score => {
        const code = score.program_outcome.code
        const values = grouped.get(code) ?? []
        values.push(score.score ?? 0)
        grouped.set(code, values)
      })
    return grouped
  }, [poScoresData, primaryProgramId])

  const averageScoresByCode = useMemo(() => {
    const averages: Record<string, number> = {}
    poScoresByCode.forEach((scores, code) => {
      averages[code] = scores.length > 0
        ? roundScore(scores.reduce((sum, score) => sum + score, 0) / scores.length)
        : 0
    })
    return averages
  }, [poScoresByCode])

  const poPanelScores = useMemo(() => (
    poScoresData
      .filter(score => !primaryProgramId || score.program_outcome.program === primaryProgramId)
      .map(score => ({
        learning_outcome: { code: score.program_outcome.code },
        score: score.score,
      }))
  ), [poScoresData, primaryProgramId])

  const poBoxPlotData = useMemo((): BoxPlotData[] => (
    programOutcomes.map(outcome => {
      const scores = [...(poScoresByCode.get(outcome.code) ?? [])].sort((a, b) => a - b)
      if (scores.length === 0) {
        return { code: outcome.code, min: 0, q1: 0, median: 0, q3: 0, max: 0, mean: 0 }
      }

      const n = scores.length
      return {
        code: outcome.code,
        min: roundScore(scores[0]),
        q1: roundScore(getQuantile(scores, 0.25)),
        median: roundScore(getQuantile(scores, 0.5)),
        q3: roundScore(getQuantile(scores, 0.75)),
        max: roundScore(scores[n - 1]),
        mean: roundScore(scores.reduce((sum, score) => sum + score, 0) / n),
      }
    })
  ), [poScoresByCode, programOutcomes])

  const poHeatmapData = useMemo((): { loCodes: string[]; students: HeatmapData[] } => {
    const poCodes = programOutcomes.map(outcome => outcome.code)
    const students = new Map<string, HeatmapData>()

    poScoresData
      .filter(score => !primaryProgramId || score.program_outcome.program === primaryProgramId)
      .forEach((score: StudentProgramOutcomeScore) => {
        const studentName = score.student.replace(/ \([^)]+\)$/, '')
        if (!students.has(studentName)) {
          students.set(studentName, {
            studentId: students.size + 1,
            studentName,
            loScores: {},
          })
        }
        const student = students.get(studentName)
        if (!student) return
        student.loScores[score.program_outcome.code] = roundScore(score.score ?? 0)
      })

    return {
      loCodes: poCodes,
      students: Array.from(students.values())
        .map(student => ({
          ...student,
          loScores: poCodes.reduce((acc, code) => ({
            ...acc,
            [code]: student.loScores[code] ?? 0,
          }), {} as Record<string, number>),
        }))
        .sort((a, b) => a.studentName.localeCompare(b.studentName)),
    }
  }, [poScoresData, primaryProgramId, programOutcomes])

  const yearLevelBreakdown = useMemo(() => statsData?.year_level_breakdown || [], [statsData])
  const gpaByYear = useMemo(() => statsData?.gpa_by_year || [], [statsData])
  const categories = yearLevelBreakdown.map(item => `Year ${item.year}`)

  const loading = statsLoading || coursesLoading || outcomesLoading || poScoresLoading

  const handleProgramOutcomeSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['program-page-program-outcomes'] })
    queryClient.invalidateQueries({ queryKey: ['/api/core/analytics/program-stats/'] })
    refetch()
  }, [queryClient, refetch])

  const handleProgramOutcomeDelete = useCallback(async () => {
    if (!poDeleteTarget) return
    await deletePoMutation.mutateAsync({ id: poDeleteTarget.id })
    setPoDeleteTarget(null)
    handleProgramOutcomeSuccess()
  }, [deletePoMutation, handleProgramOutcomeSuccess, poDeleteTarget])

  const handleGenerateReport = useCallback(async () => {
    if (!canGenerateProgramReport || !primaryProgramId) return

    setReportError(null)
    setIsGeneratingReport(true)
    try {
      await downloadReportPdf({
        kind: 'program',
        id: primaryProgramId,
        termId: activeTerm?.id,
        fallbackFilename: `${programSubtitle}-${activeTerm?.name ?? 'active-term'}-program-report.pdf`,
      })
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Failed to generate report.')
    } finally {
      setIsGeneratingReport(false)
    }
  }, [activeTerm?.id, activeTerm?.name, canGenerateProgramReport, primaryProgramId, programSubtitle])

  if (loading) {
    return <div className="flex justify-center items-center h-96">Loading program details...</div>
  }

  if (statsError) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="text-red-800">An error occurred while loading the program. Please try again.</div>
        <button
          onClick={() => refetch()}
          className="mt-3 px-4 py-2 bg-danger-600 text-white text-sm font-semibold rounded-lg hover:bg-danger-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <section id="overview" className="scroll-mt-24 space-y-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">{programName}</h1>
          <p className="text-secondary-500 mt-1">{programSubtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleGenerateReport}
            disabled={!canGenerateProgramReport || isGeneratingReport}
            className="bg-secondary-100 text-secondary-700 px-4 py-2 rounded-lg hover:bg-secondary-200 flex items-center space-x-2 transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          >
            <DocumentChartBarIcon className="h-5 w-5" />
            <span>{isGeneratingReport ? 'Generating...' : 'Generate Report'}</span>
          </button>
        </div>
      </div>

      {reportError && (
        <div className="rounded-lg border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-800">
          {reportError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card variant="flat" className="bg-primary-50 border-primary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-primary-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-primary-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Credits</p>
              <p className="text-3xl font-bold text-primary-700">{totalCredits}</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-cyan-50 border-cyan-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-cyan-100 rounded-xl">
              <UsersIcon className="h-8 w-8 text-cyan-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Instructors</p>
              <p className="text-3xl font-bold text-cyan-700">{totalInstructors}</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-violet-50 border-violet-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-violet-100 rounded-xl">
              <AcademicCapIcon className="h-8 w-8 text-violet-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Program Outcomes</p>
              <p className="text-3xl font-bold text-violet-700">{poCount}</p>
            </div>
          </div>
        </Card>
        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Average PO Score</p>
              <p className="text-3xl font-bold text-emerald-700">
                {averagePoScore !== null ? averagePoScore.toFixed(2) : 'N/A'}
              </p>
            </div>
          </div>
        </Card>
      </div>
      </section>

      <section id="outcomes" className="scroll-mt-24">
      <LearningOutcomesPanel
        title="Program Outcomes"
        subtitle="Average program outcome performance across students"
        outcomeShortLabel="PO"
        outcomeLongLabel="Program Outcome"
        learningOutcomes={programOutcomes}
        loScores={poPanelScores}
        averageScoresByCode={averageScoresByCode}
        boxPlotData={poBoxPlotData}
        heatmapData={poHeatmapData}
        canCreate={canCreatePO}
        canEdit={canEditPO}
        canDelete={canDeletePO}
        onCreate={() => setPoCreateModalOpen(true)}
        onEdit={(po) => setPoEditTarget(po as ProgramOutcome)}
        onDelete={(po) => setPoDeleteTarget(po as ProgramOutcome)}
        createButtonLabel="New PO"
        emptyMessage="No program outcomes defined for this program"
      />
      </section>

      <section id="year-levels" className="scroll-mt-24">
      <Card variant="flat" className="bg-white border-secondary-200">
        <h2 className="text-lg font-semibold text-secondary-900 mb-4">Year-Level Context</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {yearLevelBreakdown.map(item => (
            <div key={item.year} className="rounded-xl bg-secondary-50 p-3">
              <p className="text-xs text-secondary-500">Year {item.year}</p>
              <p className="text-xl font-bold text-secondary-900">{item.student_count}</p>
              <p className="text-xs text-secondary-500">students</p>
            </div>
          ))}
        </div>
      </Card>
      </section>

      <section id="analytics" className="scroll-mt-24">
      <Card className="overflow-hidden">
        <div className="p-6 border-b border-secondary-200">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 className="text-lg font-semibold text-gray-900">GPA and PO Scores by Year</h2>
            <div className="flex gap-2">
              <button
                onClick={handleSetGpaChart}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  activeChart === 'gpa'
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                }`}
              >
                Average GPA
              </button>
              <button
                onClick={handleSetPoChart}
                className={`px-3 py-1.5 text-sm rounded-lg transition ${
                  activeChart === 'po'
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
                }`}
              >
                Average PO score
              </button>
            </div>
          </div>
        </div>

        <div className="p-6">
          {activeChart === 'gpa' ? (
            <ChartWidget
              title="Average GPA by year level"
              subtitle="Credit-weighted average GPA on the 4.0 scale"
              type="bar"
              series={[{
                name: 'Average GPA',
                data: gpaByYear.map(y => y.gpa ?? 0),
              }]}
              options={{
                xaxis: { categories },
                colors: ['#0ea5e9'],
                yaxis: { min: 0, max: 4 },
              }}
            />
          ) : (
            <ChartWidget
              title="Average PO score by year level"
              subtitle="Average program outcome score by enrolled student year level"
              type="bar"
              series={[{
                name: 'Average PO score',
                data: yearLevelBreakdown.map(y => y.avg_score ?? 0),
              }]}
              options={{
                xaxis: { categories },
                colors: ['#8b5cf6'],
                yaxis: { min: 0, max: 100 },
              }}
            />
          )}
        </div>
      </Card>
      </section>

      <ProgramOutcomeModal
        isOpen={poCreateModalOpen}
        mode="create"
        programId={primaryProgramId}
        termId={activeTerm?.id}
        onClose={() => setPoCreateModalOpen(false)}
        onSuccess={handleProgramOutcomeSuccess}
      />
      <ProgramOutcomeModal
        isOpen={!!poEditTarget}
        mode="edit"
        programId={primaryProgramId}
        termId={activeTerm?.id}
        existingPo={poEditTarget}
        onClose={() => setPoEditTarget(null)}
        onSuccess={handleProgramOutcomeSuccess}
      />
      <ConfirmDeleteModal
        isOpen={!!poDeleteTarget}
        onClose={() => setPoDeleteTarget(null)}
        onConfirm={handleProgramOutcomeDelete}
        title="Delete Program Outcome"
        itemName={poDeleteTarget?.code ?? ''}
        confirmText={poDeleteTarget?.code ?? ''}
        inputLabel="PO code"
        isConfirming={deletePoMutation.isPending}
      />
    </div>
  )
}

export default ProgramPage
