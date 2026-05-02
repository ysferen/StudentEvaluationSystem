import { useState, useMemo, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { coreCoursesRetrieve } from '../../../shared/api/generated/core/core'
import { coreLearningOutcomesList } from '../../../shared/api/generated/outcomes/outcomes'
import FileUploadModal from '../components/FileUploadModal'
import MappingEditor from '../components/MappingEditor'
import { coreStudentLoScoresList } from '../../../shared/api/generated/scores/scores'
import { Card } from '../../../shared/components/ui/Card'
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
        <div className="space-y-3">
          {data.learningOutcomes?.map((lo) => (
            <div key={lo.id} className="border-l-4 border-indigo-500 pl-4 py-2 bg-secondary-50 rounded-r-lg">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-secondary-900">{lo.code}</h4>
                    <span className={`text-sm font-bold px-2 py-0.5 rounded ${getLOPerformance(lo.code) >= 80 ? 'bg-emerald-100 text-emerald-700' : getLOPerformance(lo.code) >= 60 ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'}`}>
                      {getLOPerformance(lo.code)}%
                    </span>
                  </div>
                  <p className="text-sm text-secondary-600 mt-1">{lo.description}</p>
                </div>
              </div>
            </div>
          ))}
          {!data.learningOutcomes || data.learningOutcomes.length === 0 && (
            <p className="text-secondary-500 text-center py-4">No learning outcomes defined for this course</p>
          )}
        </div>
      </Card>

      <Card>
        <h2 className="text-xl font-bold text-secondary-900 mb-4">Performance Overview</h2>
        <div className="space-y-4">
          {boxPlotData.length > 0 ? (
            boxPlotData.map((box) => {
              const boxWidth = 300
              const scale = boxWidth / 100
              const xMin = box.min * scale
              const xQ1 = box.q1 * scale
              const xMedian = box.median * scale
              const xQ3 = box.q3 * scale
              const xMax = box.max * scale

              const getBoxColor = (median: number) => {
                if (median >= 80) return { main: '#22c55e', bg: 'rgba(34, 197, 94, 0.15)' }
                if (median >= 60) return { main: '#eab308', bg: 'rgba(234, 179, 8, 0.15)' }
                return { main: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' }
              }
              const boxColor = getBoxColor(box.median)

              return (
                <div key={box.code} className="flex items-center space-x-4">
                  <span className="text-sm font-semibold w-14 text-secondary-700">{box.code}</span>
                  <div className="flex-1 flex items-center h-10">
                    <svg width={boxWidth + 40} height={45} className="overflow-visible">
                      <defs>
                        <linearGradient id="gradientScale" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#ef4444" stopOpacity="0.12" />
                          <stop offset="25%" stopColor="#f97316" stopOpacity="0.12" />
                          <stop offset="50%" stopColor="#eab308" stopOpacity="0.12" />
                          <stop offset="75%" stopColor="#84cc16" stopOpacity="0.12" />
                          <stop offset="100%" stopColor="#22c55e" stopOpacity="0.12" />
                        </linearGradient>
                      </defs>
                      <rect x="0" y={5} width={boxWidth} height={30} fill="url(#gradientScale)" rx={4} />

                      <line
                        x1="0" y1={20} x2={boxWidth} y2={20}
                        stroke="#e5e7eb" strokeWidth={1}
                      />
                      {[0, 25, 50, 75, 100].map((tick) => (
                        <g key={tick}>
                          <line
                            x1={tick * scale} y1={14} x2={tick * scale} y2={26}
                            stroke="#d1d5db" strokeWidth={1}
                          />
                          <text
                            x={tick * scale} y={41}
                            fontSize={9} textAnchor="middle" fill="#6b7280"
                          >
                            {tick}
                          </text>
                        </g>
                      ))}
                      <line
                        x1={xMin} y1={20} x2={xMax} y2={20}
                        stroke="#374151" strokeWidth={2}
                      />
                      <line
                        x1={xMin} y1={10} x2={xMin} y2={30}
                        stroke="#374151" strokeWidth={2}
                      />
                      <line
                        x1={xMax} y1={10} x2={xMax} y2={30}
                        stroke="#374151" strokeWidth={2}
                      />
                      <rect
                        x={xQ1} y={6} width={xQ3 - xQ1} height={28}
                        fill={boxColor.bg}
                        stroke={boxColor.main}
                        strokeWidth={2.5}
                        rx={3}
                      />
                      <line
                        x1={xMedian} y1={6} x2={xMedian} y2={34}
                        stroke="#1f2937" strokeWidth={3}
                      />
                      <polygon
                        points={`${box.mean * scale},${20} ${box.mean * scale + 4},${14} ${box.mean * scale + 8},${20} ${box.mean * scale + 4},${26}`}
                        fill="#4f46e5"
                        stroke="#fff"
                        strokeWidth={1}
                      />
                    </svg>
                  </div>
                  <div className="text-xs text-secondary-600 flex space-x-2 min-w-[140px]">
                    <span className="font-semibold text-secondary-700">Med: {box.median}</span>
                    <span>Q1: {box.q1}</span>
                    <span>Q3: {box.q3}</span>
                  </div>
                </div>
              )
            })
          ) : (
            <p className="text-secondary-500 text-center py-4">No data available</p>
          )}
        </div>
        {boxPlotData.length > 0 && (
          <div className="mt-4 pt-4 border-t border-secondary-200">
            <div className="flex items-center justify-center space-x-6 text-xs text-secondary-600">
              <div className="flex items-center space-x-1">
                <div className="w-4 h-3 border-2 border-indigo-500 bg-indigo-100 rounded"></div>
                <span>Box (Q1-Q3)</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-0.5 h-3 bg-secondary-900"></div>
                <span>Median</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-indigo-600 transform rotate-45"></div>
                <span>Mean</span>
              </div>
            </div>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="text-xl font-bold text-secondary-900 mb-4">Student Performance Heatmap</h2>
        <p className="text-sm text-secondary-600 mb-4">
          Learning outcome scores for each student. Colors range from deep red (low) to bright green (high).
        </p>
        {heatmapData.students.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="sticky left-0 bg-secondary-50 px-4 py-3 text-left text-sm font-semibold text-secondary-700 border-b-2 border-r border-secondary-300 z-10">
                    Student Name
                  </th>
                  {heatmapData.loCodes.map((loCode) => (
                    <th key={loCode} className="px-4 py-3 text-center text-sm font-semibold text-secondary-700 border-b-2 border-secondary-200 min-w-[80px]">
                      {loCode}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapData.students.map((student, idx) => (
                  <tr key={student.studentId} className={idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50'}>
                    <td className="sticky left-0 px-4 py-2 text-sm font-medium text-secondary-900 border-b border-r border-secondary-200" style={{ backgroundColor: idx % 2 === 0 ? '#fff' : '#f9fafb' }}>
                      {student.studentName}
                    </td>
                    {heatmapData.loCodes.map((loCode) => {
                      const score = student.loScores[loCode] ?? 0
                      const bgColor = getHeatmapColor(score)
                      const textColor = getTextColor(score)
                      return (
                        <td
                          key={loCode}
                          className="px-2 py-2 text-center text-sm font-medium border-b border-secondary-200"
                          style={{ backgroundColor: bgColor, color: textColor }}
                        >
                          {score > 0 ? score.toFixed(1) : '-'}
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
          <div className="mt-6 flex items-center justify-center space-x-4">
            <span className="text-xs font-medium text-secondary-700">0%</span>
            <div className="w-64 h-4 rounded shadow-sm" style={{
              background: 'linear-gradient(to right, #ef4444 0%, #f97316 25%, #eab308 50%, #84cc16 75%, #22c55e 100%)'
            }}></div>
            <span className="text-xs font-medium text-secondary-700">100%</span>
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
