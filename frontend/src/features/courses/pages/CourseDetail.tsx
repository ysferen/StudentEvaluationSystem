import { useState, useMemo, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { coreCoursesRetrieve, useCoreCoursesDestroy } from '../../../shared/api/generated/core/core'
import { coreLearningOutcomesList, coreLearningOutcomesDestroy } from '../../../shared/api/generated/outcomes/outcomes'
import FileUploadModal from '../components/FileUploadModal'
import MappingEditor from '../components/MappingEditor'
import CourseEditModal from '../components/CourseEditModal'
import CreateEditLOModal from '../components/CreateEditLOModal'
import CreateEditAssessmentModal from '../components/CreateEditAssessmentModal'

import ConfirmDeleteModal from '../../../shared/components/ui/ConfirmDeleteModal'
import Modal from '../../../shared/components/ui/Modal'
import { useAuth } from '../../auth/hooks/useAuth'
import { coreStudentLoScoresList } from '../../../shared/api/generated/scores/scores'
import { evaluationGradesList, evaluationEnrollmentsList, evaluationAssessmentsDestroy } from '../../../shared/api/generated/evaluation/evaluation'
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

interface StudentDetail {
  name: string
  overallScore: number
  assessmentScores: { name: string; score: number }[]
  loScores: { code: string; score: number }[]
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

const getQuantile = (arr: number[], q: number): number => {
  const pos = (arr.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  if (arr[base + 1] !== undefined) {
    return arr[base] + rest * (arr[base + 1] - arr[base])
  }
  return arr[base]
}

const CourseDetail = () => {
  const { id: courseId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [isFileUploadModalOpen, setIsFileUploadModalOpen] = useState(false)
  const [isMappingEditorOpen, setIsMappingEditorOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
  const [loChartView, setLoChartView] = useState<'radar' | 'boxplot' | 'heatmap'>('radar')
  const [assessmentChartView, setAssessmentChartView] = useState<'radar' | 'boxplot' | 'heatmap'>('radar')
  const [selectedStudent, setSelectedStudent] = useState<StudentDetail | null>(null)

  const canEdit = user?.permissions?.includes('courses.change_course') ?? false
  const canDelete = user?.permissions?.includes('courses.delete_course') ?? false

  // LO section state
  const [loEditMode, setLoEditMode] = useState(false)
  const [loCreateModalOpen, setLoCreateModalOpen] = useState(false)
  const [loEditTarget, setLoEditTarget] = useState<CoreLearningOutcome | null>(null)
  const [loDeleteTarget, setLoDeleteTarget] = useState<CoreLearningOutcome | null>(null)

  // Assessment section state
  const [assessEditMode, setAssessEditMode] = useState(false)
  const [assessCreateModalOpen, setAssessCreateModalOpen] = useState(false)
  const [assessEditTarget, setAssessEditTarget] = useState<{ id: number; name: string; assessment_type?: string; weight?: number; description?: string; total_score?: number } | null>(null)
  const [assessDeleteTarget, setAssessDeleteTarget] = useState<{ id: number; name: string } | null>(null)

  const queryClient = useQueryClient()
  const deleteMutation = useCoreCoursesDestroy()

  const handleDeleteConfirm = useCallback(async () => {
    await deleteMutation.mutateAsync({ id: Number(courseId) })
    // Invalidate courses list caches so the list refreshes after redirect
    queryClient.invalidateQueries({ queryKey: ['head-courses'] })
    queryClient.invalidateQueries({ queryKey: ['instructor-courses'] })
    queryClient.invalidateQueries({ queryKey: ['student-courses'] })
    navigate(user?.role === 'program_head' ? '/head/courses' :
      user?.role === 'instructor' ? '/instructor/courses' : '/courses')
  }, [courseId, deleteMutation, navigate, queryClient, user?.role])

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

  // Course template ID — used for template-based LO/Assessment creation
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const courseTemplateId: number | null = (data as any)?.course?.course_template_id ?? null

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

  const assignments = (gradesData as { assignments?: Array<{ id: number; name: string; assessment_type?: string; total_score?: number; weight?: number; description?: string; date?: string }> })?.assignments || []

  const assignmentsById = useMemo(() => {
    const map = new Map<number, { id: number; name: string; assessment_type?: string; total_score?: number; weight?: number; description?: string; date?: string }>()
    for (const assignment of assignments) {
      map.set(assignment.id, assignment)
    }
    return map
  }, [assignments])

  const { data: enrollmentsData, error: enrollmentsError } = useQuery({
    queryKey: ['enrollments', courseId],
    queryFn: async () => {
      if (!courseId) return { results: [] }
      const resp = await evaluationEnrollmentsList({ course: Number(courseId) })
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

  const studentDataMap = useMemo(() => {
    const map = new Map<string, StudentDetail>()

    for (const grade of gradesData?.results || []) {
      const name = grade.student.replace(/ \([^)]+\)$/, '')
      if (!map.has(name)) {
        map.set(name, { name, loScores: [], assessmentScores: [], overallScore: 0 })
      }
      const entry = map.get(name)!
      const total = grade.assessment.total_score ?? 100
      const pct = total > 0 ? Math.round((grade.score / total) * 1000) / 10 : 0
      entry.assessmentScores.push({ name: grade.assessment.name, score: pct })
    }

    for (const student of heatmapData.students) {
      if (!map.has(student.studentName)) {
        map.set(student.studentName, { name: student.studentName, loScores: [], assessmentScores: [], overallScore: 0 })
      }
      const entry = map.get(student.studentName)!
      entry.loScores = Object.entries(student.loScores).map(([code, score]) => ({ code, score }))
    }

    for (const entry of map.values()) {
      const scores = entry.assessmentScores.map(s => s.score)
      entry.overallScore = scores.length > 0
        ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
        : 0
    }

    return map
  }, [gradesData, heatmapData])

  const assessmentRadarData = useMemo(() => {
    const results = gradesData?.results || []
    const map = new Map<number, { name: string; scores: number[] }>()
    for (const grade of results) {
      const aId = grade.assessment.id
      if (!map.has(aId)) {
        map.set(aId, { name: grade.assessment.name, scores: [] })
      }
      const total = grade.assessment.total_score ?? 100
      const pct = total > 0 ? Math.round((grade.score / total) * 1000) / 10 : 0
      map.get(aId)!.scores.push(pct)
    }
    return Array.from(map.values()).map(a => ({
      id: Array.from(map.keys()).find(k => map.get(k) === a) || 0,
      name: a.name,
      avg: a.scores.length > 0 ? Math.round((a.scores.reduce((s, v) => s + v, 0) / a.scores.length) * 10) / 10 : 0
    }))
  }, [gradesData])

  const assessmentBoxPlotData = useMemo((): BoxPlotData[] => {
    const results = gradesData?.results || []
    const grouped = new Map<number, number[]>()
    const names = new Map<number, string>()
    for (const grade of results) {
      const aId = grade.assessment.id
      if (!grouped.has(aId)) grouped.set(aId, [])
      const total = grade.assessment.total_score ?? 100
      grouped.get(aId)!.push(total > 0 ? (grade.score / total) * 100 : 0)
      names.set(aId, grade.assessment.name)
    }

    return Array.from(grouped.entries()).map(([id, scores]) => {
      const sorted = [...scores].sort((a: number, b: number) => a - b)
      if (sorted.length === 0) {
        return {
          code: names.get(id) || String(id),
          min: 0, q1: 0, median: 0, q3: 0, max: 0, mean: 0
        }
      }
      const n = sorted.length
      const min = sorted[0]
      const max = sorted[n - 1]
      const mean = sorted.reduce((sum, val) => sum + val, 0) / n
      const q1 = getQuantile(sorted, 0.25)
      const median = getQuantile(sorted, 0.5)
      const q3 = getQuantile(sorted, 0.75)
      return {
        code: names.get(id) || String(id),
        min: Math.round(min * 100) / 100,
        q1: Math.round(q1 * 100) / 100,
        median: Math.round(median * 100) / 100,
        q3: Math.round(q3 * 100) / 100,
        max: Math.round(max * 100) / 100,
        mean: Math.round(mean * 100) / 100
      }
    })
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

  const handleStudentClick = useCallback((studentName: string) => {
    const info = studentDataMap.get(studentName)
    if (info) {
      setSelectedStudent(info)
    }
  }, [studentDataMap])

  const handleLODelete = useCallback(async () => {
    if (loDeleteTarget) {
      try {
        await coreLearningOutcomesDestroy(loDeleteTarget.id)
        setLoDeleteTarget(null)
        refetch()
      } catch { /* error handled silently */ }
    }
  }, [loDeleteTarget, refetch])

  const handleAssessmentDelete = useCallback(async () => {
    if (assessDeleteTarget) {
      try {
        await evaluationAssessmentsDestroy(assessDeleteTarget.id)
        setAssessDeleteTarget(null)
        refetch()
      } catch { /* error handled silently */ }
    }
  }, [assessDeleteTarget, refetch])

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
          <div className="flex items-center gap-2 mt-2">
            {canEdit && (
              <button
                onClick={() => setIsEditModalOpen(true)}
                className="bg-secondary-100 text-secondary-700 px-3 py-1.5 rounded-lg hover:bg-secondary-200 flex items-center space-x-1.5 transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                </svg>
                <span>Edit</span>
              </button>
            )}
            {canDelete && (
              <button
                onClick={() => setIsDeleteConfirmOpen(true)}
                className="bg-danger-50 text-danger-700 px-3 py-1.5 rounded-lg hover:bg-danger-100 flex items-center space-x-1.5 transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
                <span>Delete</span>
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
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
              <p className={`text-3xl font-bold ${scoreTextColor}`}>{avgScore}</p>
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
          {canEdit && (
            <button
              onClick={() => setLoEditMode(!loEditMode)}
              className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition-colors text-sm ${
                loEditMode
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-secondary-100 text-secondary-700 hover:bg-secondary-200'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
              <span>Edit</span>
            </button>
          )}
          {canEdit && (
            <button
              onClick={() => setLoCreateModalOpen(true)}
              className="bg-primary-600 text-white px-3 py-1.5 rounded-lg hover:bg-primary-700 flex items-center space-x-1.5 transition-colors text-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Create</span>
            </button>
          )}
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
          <button
            onClick={() => setLoChartView('heatmap')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              loChartView === 'heatmap'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Heatmap
          </button>
        </div>
        {data.learningOutcomes && data.learningOutcomes.length > 0 ? (
          <>
            {loChartView === 'radar' && (
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
            )}
            {loChartView === 'boxplot' && (
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
            {loChartView === 'heatmap' && (
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
                      <tr
                        key={student.studentId}
                        className={`cursor-pointer hover:bg-secondary-100/50 ${idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}`}
                        onClick={() => handleStudentClick(student.studentName)}
                      >
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
            )}
            {loChartView === 'heatmap' && heatmapData.students.length > 0 && (
              <div className="mt-4 flex items-center justify-center gap-1">
                {[0, 25, 50, 75, 100].map((val) => (
                  <div key={val} className="flex items-center gap-1">
                    <div className="w-4 h-4 rounded" style={{ backgroundColor: getHeatmapColor(val) }} />
                    <span className="text-xs text-secondary-600 tabular-nums">{val}%</span>
                  </div>
                ))}
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
                  <div key={lo.id} className="flex flex-col p-3 rounded-xl border border-secondary-200 bg-white shadow-sm relative group">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded text-xs">{lo.code}</span>
                      <span className={`font-bold px-2 py-0.5 rounded-full text-xs whitespace-nowrap ${
                        score >= 80 ? 'bg-emerald-100 text-emerald-700' : score >= 60 ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'
                      }`}>
                        {score}%
                      </span>
                    </div>
                    <span className="text-secondary-700 text-sm leading-snug">{lo.description}</span>
                    {loEditMode && (
                      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => { e.stopPropagation(); setLoEditTarget(lo) }}
                          className="p-1 rounded-md bg-secondary-100 text-secondary-600 hover:bg-primary-100 hover:text-primary-700 transition-colors"
                          title="Edit"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setLoDeleteTarget(lo) }}
                          className="p-1 rounded-md bg-secondary-100 text-secondary-600 hover:bg-danger-100 hover:text-danger-700 transition-colors"
                          title="Delete"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    )}
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
        <h2 className="text-xl font-bold text-secondary-900 mb-2">Assessments</h2>
        <div className="flex items-center gap-2 mb-4">
          {canEdit && (
            <button
              onClick={() => setAssessEditMode(!assessEditMode)}
              className={`px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition-colors text-sm ${
                assessEditMode
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-secondary-100 text-secondary-700 hover:bg-secondary-200'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
              </svg>
              <span>Edit</span>
            </button>
          )}
          {canEdit && (
            <button
              onClick={() => setAssessCreateModalOpen(true)}
              className="bg-primary-600 text-white px-3 py-1.5 rounded-lg hover:bg-primary-700 flex items-center space-x-1.5 transition-colors text-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Create</span>
            </button>
          )}
        </div>
<div className="flex items-center gap-2 mb-4">
          <button
            onClick={() => setAssessmentChartView('radar')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              assessmentChartView === 'radar'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Radar
          </button>
          <button
            onClick={() => setAssessmentChartView('boxplot')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              assessmentChartView === 'boxplot'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Box Plot
          </button>
          <button
            onClick={() => setAssessmentChartView('heatmap')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              assessmentChartView === 'heatmap'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Heatmap
          </button>
        </div>
{assessmentRadarData.length > 0 || assignments.length > 0 ? (
          <>
            {assessmentRadarData.length > 0 && (
              <>
            {assessmentChartView === 'radar' && (
              <ChartWidget
                title=""
                type="radar"
                series={[{
                  name: 'Average Score',
                  data: assessmentRadarData.map(a => a.avg)
                }]}
                options={{
                  xaxis: {
                    categories: assessmentRadarData.map(a => a.name)
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
            )}
            {assessmentChartView === 'boxplot' && (
              <div className="space-y-6">
                {assessmentBoxPlotData.length > 0 ? (
                  assessmentBoxPlotData.map((box) => {
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
            {assessmentChartView === 'boxplot' && assessmentBoxPlotData.length > 0 && (
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
            {assessmentChartView === 'heatmap' && (
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
                      <tr
                        key={idx}
                        className={`cursor-pointer hover:bg-secondary-100/50 ${idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}`}
                        onClick={() => handleStudentClick(student.name)}
                      >
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
            )}
            {assessmentChartView === 'heatmap' && assessmentHeatmap.students.length > 0 && (
              <div className="mt-4 flex items-center justify-center gap-1">
                {[0, 25, 50, 75, 100].map((val) => (
                  <div key={val} className="flex items-center gap-1">
                    <div className="w-4 h-4 rounded" style={{ backgroundColor: getHeatmapColor(val) }} />
                    <span className="text-xs text-secondary-600 tabular-nums">{val}%</span>
                  </div>
                ))}
              </div>
            )}
</>
            )}
            {assessmentRadarData.length > 0 ? (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
              {assessmentRadarData.map((a) => {
                const score = a.avg
                const assignmentData = assignmentsById.get(a.id)
                const editTarget = assignmentData || { id: a.id, name: a.name }
                return (
                  <div key={a.id} className="flex flex-col p-3 rounded-xl border border-secondary-200 bg-white shadow-sm relative group">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded text-xs truncate max-w-[200px]">{a.name}</span>
                      <span className={`font-bold px-2 py-0.5 rounded-full text-xs whitespace-nowrap ${
                        score >= 80 ? 'bg-emerald-100 text-emerald-700' : score >= 60 ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'
                      }`}>
                        {score}%
                      </span>
                    </div>
                    {assessEditMode && (
                      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setAssessEditTarget(editTarget)
                          }}
                          className="p-1 rounded-md bg-secondary-100 text-secondary-600 hover:bg-primary-100 hover:text-primary-700 transition-colors"
                          title="Edit"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setAssessDeleteTarget({ id: editTarget.id, name: editTarget.name })
                          }}
                          className="p-1 rounded-md bg-secondary-100 text-secondary-600 hover:bg-danger-100 hover:text-danger-700 transition-colors"
                          title="Delete"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
) : (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
              {assignments.map((a) => (
                <div key={a.id} className="flex flex-col p-3 rounded-xl border border-secondary-200 bg-white shadow-sm relative group">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded text-xs truncate max-w-[200px]">{a.name}</span>
                    <span className="text-xs text-secondary-400">0%</span>
                  </div>
                  {assessEditMode && (
                    <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setAssessEditTarget(a)
                        }}
                        className="p-1 rounded-md bg-secondary-100 text-secondary-600 hover:bg-primary-100 hover:text-primary-700 transition-colors"
                        title="Edit"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setAssessDeleteTarget({ id: a.id, name: a.name })
                        }}
                        className="p-1 rounded-md bg-secondary-100 text-secondary-600 hover:bg-danger-100 hover:text-danger-700 transition-colors"
                        title="Delete"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
            )}
          </>
        ) : (
          <p className="text-secondary-500 text-center py-4">No assessments defined for this course</p>
        )}
      </Card>

      <Card>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-secondary-900">Students</h2>
          <div className="flex items-center gap-2">
            <button className="bg-primary-600 text-white px-3 py-1.5 rounded-lg hover:bg-primary-700 flex items-center space-x-1.5 transition-colors text-sm cursor-default">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Enroll</span>
            </button>
            <button className="bg-danger-50 text-danger-700 px-3 py-1.5 rounded-lg hover:bg-danger-100 flex items-center space-x-1.5 transition-colors text-sm cursor-default">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
              </svg>
              <span>Unenroll</span>
            </button>
          </div>
        </div>
        {enrollmentsError ? (
          <p className="text-secondary-500 text-center py-8">You do not have permission to view enrolled students.</p>
        ) : (enrollmentsData?.results || []).length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-secondary-100">
                  <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Student Name</th>
                  <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Current Score</th>
                  <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Enrollment Term</th>
                </tr>
              </thead>
              <tbody>
                {(enrollmentsData?.results || []).map((enrollment, idx) => {
                  const studentName = enrollment.student.replace(/ \([^)]+\)$/, '')
                  const info = studentDataMap.get(studentName)
                  return (
                    <tr
                      key={enrollment.id}
                      className={`cursor-pointer hover:bg-secondary-100/50 ${idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}`}
                      onClick={() => handleStudentClick(studentName)}
                    >
                      <td className="px-2 py-1.5 text-sm font-medium text-secondary-900 border-b border-secondary-200">{studentName}</td>
                      <td className="px-2 py-1.5 text-sm text-secondary-700 border-b border-secondary-200">{info?.overallScore ?? 0}</td>
                      <td className="px-2 py-1.5 text-sm text-secondary-700 border-b border-secondary-200">{data?.course?.term?.name ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-secondary-500 text-center py-8">No students enrolled in this course</p>
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
              termId={data.course.term.id}
              onClose={() => setIsMappingEditorOpen(false)}
            />
          </div>
        </div>,
        document.body
      )}

      <CourseEditModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        course={data.course}
        onSuccess={refetch}
      />



      <ConfirmDeleteModal
        isOpen={isDeleteConfirmOpen}
        onClose={() => setIsDeleteConfirmOpen(false)}
        onConfirm={handleDeleteConfirm}
        title="Delete Course"
        itemName={`${data.course.code} - ${data.course.name}`}
        confirmText={data.course.code}
        inputLabel="course code"
        isConfirming={deleteMutation.isPending}
      />

      {/* LO modals */}
      <CreateEditLOModal
        isOpen={loCreateModalOpen}
        onClose={() => setLoCreateModalOpen(false)}
        onSuccess={() => { setLoCreateModalOpen(false); refetch() }}
        mode="create"
        courseId={Number(courseId)}
        courseTemplateId={courseTemplateId}
      />
      <CreateEditLOModal
        isOpen={!!loEditTarget}
        onClose={() => setLoEditTarget(null)}
        onSuccess={() => { setLoEditTarget(null); refetch() }}
        mode="edit"
        courseId={Number(courseId)}
        courseTemplateId={courseTemplateId}
        existingLo={loEditTarget ? { id: loEditTarget.id, code: loEditTarget.code, description: loEditTarget.description } : null}
      />
      <ConfirmDeleteModal
        isOpen={!!loDeleteTarget}
        onClose={() => setLoDeleteTarget(null)}
        onConfirm={handleLODelete}
        title="Delete Learning Outcome"
        itemName={loDeleteTarget?.code ?? ''}
        confirmText={loDeleteTarget?.code ?? ''}
        inputLabel="LO code"
      />

      {/* Assessment modals */}
      <CreateEditAssessmentModal
        isOpen={assessCreateModalOpen}
        onClose={() => setAssessCreateModalOpen(false)}
        onSuccess={() => { setAssessCreateModalOpen(false); refetch() }}
        mode="create"
        courseId={Number(courseId)}
        courseTemplateId={courseTemplateId}
      />
      <CreateEditAssessmentModal
        isOpen={!!assessEditTarget}
        onClose={() => setAssessEditTarget(null)}
        onSuccess={() => { setAssessEditTarget(null); refetch() }}
        mode="edit"
        courseId={Number(courseId)}
        courseTemplateId={courseTemplateId}
        existingAssessment={assessEditTarget}
      />
      <ConfirmDeleteModal
        isOpen={!!assessDeleteTarget}
        onClose={() => setAssessDeleteTarget(null)}
        onConfirm={handleAssessmentDelete}
        title="Delete Assessment"
        itemName={assessDeleteTarget?.name ?? ''}
        confirmText={assessDeleteTarget?.name ?? ''}
        inputLabel="assessment name"
      />

      <Modal
        isOpen={!!selectedStudent}
        onClose={() => setSelectedStudent(null)}
        title={selectedStudent?.name || ''}
        size="lg"
      >
        <div className="space-y-6">
          <div>
            <p className="text-sm text-secondary-600 font-medium">Overall Course Score</p>
            <p className="text-3xl font-bold text-secondary-900">{selectedStudent?.overallScore ?? 0}</p>
          </div>

          {selectedStudent && selectedStudent.assessmentScores.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-secondary-800 mb-2">Assessment Scores</h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="bg-secondary-100">
                      <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Assessment</th>
                      <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedStudent.assessmentScores.map((as, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}>
                        <td className="px-2 py-1.5 text-sm text-secondary-900 border-b border-secondary-200">{as.name}</td>
                        <td className="px-2 py-1.5 text-sm font-mono text-secondary-700 border-b border-secondary-200">{as.score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {selectedStudent && selectedStudent.loScores.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-secondary-800 mb-2">Learning Outcome Scores</h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="bg-secondary-100">
                      <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Learning Outcome</th>
                      <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedStudent.loScores.map((ls, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}>
                        <td className="px-2 py-1.5 text-sm font-mono text-secondary-900 border-b border-secondary-200">{ls.code}</td>
                        <td className="px-2 py-1.5 text-sm font-mono text-secondary-700 border-b border-secondary-200">{ls.score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}

export default CourseDetail
