import { useState, useMemo, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { coreCoursesRetrieve } from '../../../shared/api/generated/core/core'
import { coreLearningOutcomesList } from '../../../shared/api/generated/outcomes/outcomes'
import FileUploadModal from '../components/FileUploadModal'
import MappingEditor from '../components/MappingEditor'
import { coreStudentLoScoresList } from '../../../shared/api/generated/scores/scores'
import { evaluationGradesList } from '../../../shared/api/generated/evaluation/evaluation'
import { Card } from '../../../shared/components/ui/Card'
import { ChartWidget } from '../../../shared/components/ui/ChartWidget'
import {
  BookOpenIcon,
  UsersIcon,
  AcademicCapIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline'
import type {
  Course,
  CourseInstructorsItem,
  CoreLearningOutcome,
  StudentLearningOutcomeScore,
} from '../../../shared/api/model'

interface BoxPlotData {
  code: string
  min: number
  q1: number
  median: number
  q3: number
  max: number
  mean: number
}

interface HeatmapData {
  studentName: string
  studentId: number
  loScores: Record<string, number>
}

interface AssessmentHeatmapData {
  assessments: { id: number; name: string; totalScore: number }[]
  students: { name: string; scores: Record<number, number> }[]
}

interface CourseDetailQueryData {
  course: Course
  learningOutcomes: CoreLearningOutcome[]
  loScores: StudentLearningOutcomeScore[]
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const getInstructorName = (instructor: CourseInstructorsItem): string => {
  const firstName = typeof instructor.first_name === 'string' ? instructor.first_name : ''
  const lastName = typeof instructor.last_name === 'string' ? instructor.last_name : ''
  const fullName = `${firstName} ${lastName}`.trim()

  if (fullName) {
    return fullName
  }

  if (typeof instructor.username === 'string') {
    return instructor.username
  }

  return 'Unknown Instructor'
}

const CourseDetail = () => {
  const { id: courseId } = useParams<{ id: string }>()
  const [isFileUploadModalOpen, setIsFileUploadModalOpen] = useState(false)
  const [isMappingEditorOpen, setIsMappingEditorOpen] = useState(false)
  const [loChartView, setLoChartView] = useState<'radar' | 'boxplot'>('radar')

  useEffect(() => {
    if (isMappingEditorOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isMappingEditorOpen])

  const { data, isLoading, error, refetch } = useQuery<CourseDetailQueryData>({
    queryKey: ['course', courseId],
    queryFn: async () => {
      if (!courseId) throw new Error('Course ID is required')
      const courseResponse = await coreCoursesRetrieve(Number(courseId))
      const loResponse = await coreLearningOutcomesList({ course: Number(courseId) })
      const loScoresResponse = await coreStudentLoScoresList({ course: Number(courseId) })
      return {
        course: courseResponse,
        learningOutcomes: loResponse.results || [],
        loScores: loScoresResponse.results || []
      }
    }
  })

  const handleUploadComplete = () => {
    refetch()
  }

  const getInstructorNames = () => {
    if (!data?.course?.instructors || data.course.instructors.length === 0) {
      return 'Not assigned'
    }
    return data.course.instructors.map(getInstructorName).join(', ')
  }

  const getAverageScore = () => {
    if (!data?.loScores || data.loScores.length === 0) return 0
    const total = data.loScores.reduce((sum, score) => sum + (score.score ?? 0), 0)
    return Math.round((total / data.loScores.length) * 100) / 100
  }

  const getLOPerformance = (loCode: string) => {
    if (!data?.loScores) return 0
    const loScoresFiltered = data.loScores.filter((score) =>
      score.learning_outcome.code === loCode
    )
    if (loScoresFiltered.length === 0) return 0
    const total = loScoresFiltered.reduce((sum, score) => sum + (score.score ?? 0), 0)
    return Math.round((total / loScoresFiltered.length) * 100) / 100
  }

  const boxPlotData = useMemo((): BoxPlotData[] => {
    if (!data?.learningOutcomes || !data?.loScores) return []

    return data.learningOutcomes.map((lo) => {
      const loScoresFiltered = data.loScores
        .filter((score) => score.learning_outcome.code === lo.code)
        .map((score) => score.score ?? 0)
        .sort((a: number, b: number) => a - b)

      if (loScoresFiltered.length === 0) {
        return {
          code: lo.code,
          min: 0,
          q1: 0,
          median: 0,
          q3: 0,
          max: 0,
          mean: 0
        }
      }

      const n = loScoresFiltered.length
      const min = loScoresFiltered[0]
      const max = loScoresFiltered[n - 1]
      const mean = loScoresFiltered.reduce((sum, val) => sum + val, 0) / n

      const getQuantile = (arr: number[], q: number): number => {
        const pos = (arr.length - 1) * q
        const base = Math.floor(pos)
        const rest = pos - base
        if (arr[base + 1] !== undefined) {
          return arr[base] + rest * (arr[base + 1] - arr[base])
        }
        return arr[base]
      }

      const q1 = getQuantile(loScoresFiltered, 0.25)
      const median = getQuantile(loScoresFiltered, 0.5)
      const q3 = getQuantile(loScoresFiltered, 0.75)

      return {
        code: lo.code,
        min: Math.round(min * 100) / 100,
        q1: Math.round(q1 * 100) / 100,
        median: Math.round(median * 100) / 100,
        q3: Math.round(q3 * 100) / 100,
        max: Math.round(max * 100) / 100,
        mean: Math.round(mean * 100) / 100
      }
    })
  }, [data?.learningOutcomes, data?.loScores])

  const heatmapData = useMemo((): { loCodes: string[]; students: HeatmapData[] } => {
    if (!data?.learningOutcomes || !data?.loScores) return { loCodes: [], students: [] }

    const loCodes = data.learningOutcomes.map((lo) => lo.code)

    const studentMap = new Map<number, HeatmapData>()

    data.loScores.forEach((score) => {
      const studentId = score.student_id
      let studentName = `Student ${studentId}`

      if (typeof score.student === 'string') {
        studentName = score.student.replace(/ \([^)]+\)$/, '')
      }

      const maybeScore = isRecord(score) ? score as Record<string, unknown> : null
      const detail = maybeScore?.student_detail
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0]
        if (typeof first === 'string') {
          studentName = first
        } else if (isRecord(first)) {
          const firstName = typeof first.first_name === 'string' ? first.first_name : ''
          const lastName = typeof first.last_name === 'string' ? first.last_name : ''
          const fullName = `${firstName} ${lastName}`.trim()
          if (fullName) {
            studentName = fullName
          } else if (typeof first.username === 'string') {
            studentName = first.username
          }
        }
      }
      const loCode = score.learning_outcome.code

      const existing = studentMap.get(studentId)
      if (existing) {
        existing.loScores[loCode] = Math.round((score.score ?? 0) * 100) / 100
      } else {
        studentMap.set(studentId, {
          studentId,
          studentName,
          loScores: {
            [loCode]: Math.round((score.score ?? 0) * 100) / 100,
          }
        })
      }
    })

    const students = Array.from(studentMap.values()).map(student => ({
      ...student,
      loScores: loCodes.reduce((acc, code) => ({
        ...acc,
        [code]: student.loScores[code] ?? 0
      }), {} as Record<string, number>)
    }))

    students.sort((a, b) => a.studentName.localeCompare(b.studentName))

    return { loCodes, students }
  }, [data?.learningOutcomes, data?.loScores])

  const { data: gradesData } = useQuery({
    queryKey: ['grades', courseId],
    queryFn: async () => {
      if (!courseId) return { results: [] }
      const resp = await evaluationGradesList({ course: Number(courseId) })
      return resp
    },
    enabled: !!courseId
  })

  const assessmentHeatmap = useMemo((): AssessmentHeatmapData => {
    const results = gradesData?.results || []
    if (results.length === 0) return { assessments: [], students: [] }

    const assessmentMap = new Map<number, { id: number; name: string; totalScore: number }>()
    const studentMap = new Map<string, { name: string; scores: Record<number, number> }>()

    for (const grade of results) {
      const aId = grade.assessment.id
      if (!assessmentMap.has(aId)) {
        assessmentMap.set(aId, {
          id: aId,
          name: grade.assessment.name,
          totalScore: grade.assessment.total_score ?? 100
        })
      }
      const studentName = grade.student.replace(/ \([^)]+\)$/, '')
      if (!studentMap.has(studentName)) {
        studentMap.set(studentName, { name: studentName, scores: {} })
      }
      const total = assessmentMap.get(aId)!.totalScore
      const pct = total > 0 ? Math.round((grade.score / total) * 1000) / 10 : 0
      studentMap.get(studentName)!.scores[aId] = pct
    }

    const assessments = Array.from(assessmentMap.values()).sort((a, b) => a.id - b.id)
    const students = Array.from(studentMap.values()).sort((a, b) => a.name.localeCompare(b.name))

    for (const student of students) {
      for (const a of assessments) {
        if (!(a.id in student.scores)) {
          student.scores[a.id] = 0
        }
      }
    }

    return { assessments, students }
  }, [gradesData])

  const getHeatmapColor = (score: number): string => {
    if (score === 0) return 'rgb(249, 250, 251)'

    const normalized = Math.max(0, Math.min(100, score)) / 100

    if (normalized < 0.25) {
      const t = normalized / 0.25
      const r = 239 - Math.round(11 * t)
      const g = 68 + Math.round(46 * t)
      const b = 68 + Math.round(14 * t)
      return `rgb(${r}, ${g}, ${b})`
    } else if (normalized < 0.5) {
      const t = (normalized - 0.25) / 0.25
      const r = 228 + Math.round(24 * t)
      const g = 114 + Math.round(97 * t)
      const b = 82 - Math.round(27 * t)
      return `rgb(${r}, ${g}, ${b})`
    } else if (normalized < 0.75) {
      const t = (normalized - 0.5) / 0.25
      const r = 252 - Math.round(68 * t)
      const g = 211 + Math.round(33 * t)
      const b = 55 + Math.round(58 * t)
      return `rgb(${r}, ${g}, ${b})`
    } else {
      const t = (normalized - 0.75) / 0.25
      const r = 184 - Math.round(150 * t)
      const g = 244 - Math.round(42 * t)
      const b = 113 + Math.round(19 * t)
      return `rgb(${r}, ${g}, ${b})`
    }
  }

  const getTextColor = (score: number): string => {
    if (score === 0) return 'rgb(107, 114, 128)'
    if (score >= 60) return 'rgb(17, 24, 39)'
    return 'rgb(255, 255, 255)'
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-secondary-600">Loading course details...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="text-red-800">Error: {error instanceof Error ? error.message : 'An error occurred while loading course details'}</div>
      </div>
    )
  }

  if (!data?.course) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <div className="text-yellow-800">Course not found</div>
      </div>
    )
  }

  const avgScore = getAverageScore()
  const scoreTextColor = avgScore >= 70 ? 'text-emerald-700' : avgScore >= 50 ? 'text-amber-700' : avgScore === 0 ? 'text-secondary-400' : 'text-red-700'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">
            {data.course.code} - {data.course.name}
          </h1>
        </div>
        <button
          onClick={() => setIsFileUploadModalOpen(true)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 flex items-center space-x-2 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <span>Import File</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card variant="flat" className="bg-primary-50 border-primary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-primary-100 rounded-xl">
              <BookOpenIcon className="h-8 w-8 text-primary-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Credits</p>
              <p className="text-3xl font-bold text-primary-700">{data.course.credits}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-cyan-50 border-cyan-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-cyan-100 rounded-xl">
              <UsersIcon className="h-8 w-8 text-cyan-700" />
            </div>
            <div className="min-w-0">
              <p className="text-sm text-secondary-600 font-medium">Instructors</p>
              <p className="text-lg font-bold text-cyan-700 truncate">{getInstructorNames()}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <AcademicCapIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Avg Score</p>
              <p className={`text-3xl font-bold ${scoreTextColor}`}>{avgScore}%</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-violet-50 border-violet-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-violet-100 rounded-xl">
              <ChartBarIcon className="h-8 w-8 text-violet-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Learning Outcomes</p>
              <p className="text-3xl font-bold text-violet-700">{data.learningOutcomes?.length || 0}</p>
            </div>
          </div>
        </Card>
      </div>

      <Card>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-secondary-900">Learning Outcomes</h2>
          <button
            onClick={() => setIsMappingEditorOpen(true)}
            className="bg-primary-600 text-white px-3 py-1.5 rounded-lg hover:bg-primary-700 flex items-center space-x-1 text-sm transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span>Outcome Mapping</span>
          </button>
        </div>
        <div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setLoChartView('radar')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              loChartView === 'radar'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Radar
          </button>
          <button
            onClick={() => setLoChartView('boxplot')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              loChartView === 'boxplot'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Box Plot
          </button>
        </div>
        {data.learningOutcomes && data.learningOutcomes.length > 0 ? (
          <>
            {loChartView === 'radar' ? (
              <ChartWidget
                title=""
                type="radar"
                series={[{
                  name: 'Average Score',
                  data: data.learningOutcomes.map(lo => Math.round(getLOPerformance(lo.code) * 10) / 10)
                }]}
                options={{
                  xaxis: {
                    categories: data.learningOutcomes.map(lo => lo.code)
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
            ) : (
              <div className="space-y-6">
                {boxPlotData.length > 0 ? (
                  boxPlotData.map((box) => {
                    const W = 500
                    const PAD = 12
                    const scale = W / 100
                    const x = (v: number) => PAD + v * scale

                    const getBoxColor = (median: number) => {
                      if (median >= 80) return { stroke: '#15803d', fill: '#bbf7d0', whisker: '#4ade80' }
                      if (median >= 60) return { stroke: '#a16207', fill: '#fef08a', whisker: '#facc15' }
                      return { stroke: '#b91c1c', fill: '#fecaca', whisker: '#f87171' }
                    }
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
                        <svg width="100%" viewBox={`0 0 ${W + PAD * 2} 44`} preserveAspectRatio="none" className="overflow-visible">
                          <rect x={PAD} y={19} width={W} height={2} rx={1} fill="#f3f4f6" />
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
                  })
                ) : (
                  <p className="text-secondary-500 text-center py-4">No data available</p>
                )}
              </div>
            )}
            {boxPlotData.length > 0 && loChartView === 'boxplot' && (
              <div className="mt-5 pt-4 border-t border-secondary-100">
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
              </div>
            )}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.learningOutcomes.map((lo) => {
                const score = getLOPerformance(lo.code)
                return (
                  <div key={lo.id} className="flex flex-col p-3 rounded-xl border border-secondary-200 bg-white shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded text-xs">{lo.code}</span>
                      <span className={`font-bold px-2 py-0.5 rounded-full text-xs whitespace-nowrap ${
                        score >= 80 ? 'bg-emerald-100 text-emerald-700' : score >= 60 ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'
                      }`}>
                        {score}%
                      </span>
                    </div>
                    <span className="text-secondary-700 text-sm leading-snug">{lo.description}</span>
                  </div>
                )
              })}
            </div>
          </>
        ) : (
          <p className="text-secondary-500 text-center py-4">No learning outcomes defined for this course</p>
        )}
      </Card>

      <Card>
        <h2 className="text-xl font-bold text-secondary-900 mb-4">Student Performance Heatmap</h2>
        {heatmapData.students.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-secondary-100">
                  <th className="sticky left-0 bg-secondary-100 px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-r border-secondary-200 z-10 min-w-[120px] max-w-[180px]">
                    Student
                  </th>
                  {heatmapData.loCodes.map((loCode) => (
                    <th key={loCode} className="px-2 py-1.5 text-center text-xs font-semibold text-secondary-700 border-b border-secondary-200 min-w-[60px]">
                      {loCode}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapData.students.map((student, idx) => (
                  <tr key={student.studentId} className={idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}>
                    <td className="sticky left-0 px-2 py-1.5 text-sm font-medium text-secondary-900 border-b border-r border-secondary-200 truncate min-w-[120px] max-w-[180px]" style={{ backgroundColor: idx % 2 === 0 ? '#fff' : '#f9fafbfa' }}>
                      {student.studentName}
                    </td>
                    {heatmapData.loCodes.map((loCode) => {
                      const score = student.loScores[loCode] ?? 0
                      const bgColor = getHeatmapColor(score)
                      const textColor = getTextColor(score)
                      return (
                        <td
                          key={loCode}
                          className="px-2 py-1.5 text-center font-mono text-xs font-medium border-b border-secondary-200"
                          style={{ backgroundColor: bgColor, color: textColor }}
                        >
                          {score > 0 ? score.toFixed(1) : '−'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-secondary-500 text-center py-8">No student performance data available</p>
        )}
        {heatmapData.students.length > 0 && (
          <div className="mt-4 flex items-center justify-center gap-1">
            {[0, 25, 50, 75, 100].map((val) => (
              <div key={val} className="flex items-center gap-1">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: getHeatmapColor(val) }} />
                <span className="text-xs text-secondary-600 tabular-nums">{val}%</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="text-xl font-bold text-secondary-900 mb-4">Assessment Scores</h2>
        {assessmentHeatmap.students.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-secondary-100">
                  <th className="sticky left-0 bg-secondary-100 px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-r border-secondary-200 z-10 min-w-[120px] max-w-[180px]">
                    Student
                  </th>
                  {assessmentHeatmap.assessments.map((a) => (
                    <th key={a.id} className="px-2 py-1.5 text-center text-xs font-semibold text-secondary-700 border-b border-secondary-200 min-w-[60px]">
                      <div className="truncate max-w-[80px]" title={a.name}>{a.name}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {assessmentHeatmap.students.map((student, idx) => (
                  <tr key={idx} className={`hover:bg-secondary-100/50 ${idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}`}>
                    <td className="sticky left-0 px-2 py-1.5 text-sm font-medium text-secondary-900 border-b border-r border-secondary-200 truncate min-w-[120px] max-w-[180px]" style={{ backgroundColor: idx % 2 === 0 ? '#fff' : '#f9fafbfa' }}>
                      {student.name}
                    </td>
                    {assessmentHeatmap.assessments.map((a) => {
                      const pct = student.scores[a.id] ?? 0
                      const bgColor = getHeatmapColor(pct)
                      const textColor = getTextColor(pct)
                      return (
                        <td
                          key={a.id}
                          className="px-2 py-1.5 text-center font-mono text-xs font-medium border-b border-secondary-200"
                          style={{ backgroundColor: bgColor, color: textColor }}
                        >
                          {pct > 0 ? pct.toFixed(1) : '−'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-secondary-500 text-center py-8">No assessment data available</p>
        )}
        {assessmentHeatmap.students.length > 0 && (
          <div className="mt-4 flex items-center justify-center gap-1">
            {[0, 25, 50, 75, 100].map((val) => (
              <div key={val} className="flex items-center gap-1">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: getHeatmapColor(val) }} />
                <span className="text-xs text-secondary-600 tabular-nums">{val}%</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <FileUploadModal
        course={data.course.name}
        courseCode={data.course.code}
        termId={data.course.term?.id ?? 0}
        isOpen={isFileUploadModalOpen}
        onClose={() => setIsFileUploadModalOpen(false)}
        type="assignment_scores"
        onUploadComplete={handleUploadComplete}
      />

      {isMappingEditorOpen && createPortal(
        <div
          className="fixed bg-black bg-opacity-50 flex items-center justify-center p-4"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 9999
          }}
          onWheel={(e) => e.stopPropagation()}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setIsMappingEditorOpen(false)
            }
          }}
        >
          <div
            className="bg-white rounded-xl w-full max-w-7xl h-[95vh] overflow-hidden p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <MappingEditor
              courseId={Number(courseId)}
              onClose={() => setIsMappingEditorOpen(false)}
            />
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}

export default CourseDetail
