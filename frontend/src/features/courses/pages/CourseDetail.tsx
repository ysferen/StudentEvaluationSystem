import { useState, useMemo, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { coreCoursesRetrieve, useCoreCoursesDestroy } from '../../../shared/api/generated/core/core'
import { coreLearningOutcomesList, coreLearningOutcomesDestroy } from '../../../shared/api/generated/outcomes/outcomes'
import { isRecord } from '@/shared/utils/guards'
import FileUploadModal from '../components/FileUploadModal'
import MappingEditor from '../components/MappingEditor'
import CourseEditModal from '../components/CourseEditModal'
import CreateEditLOModal from '../components/CreateEditLOModal'
import CreateEditAssessmentModal from '../components/CreateEditAssessmentModal'
import EnrollStudentsModal from '../components/EnrollStudentsModal'
import UnenrollStudentsModal from '../components/UnenrollStudentsModal'
import { LearningOutcomesPanel } from '../components/LearningOutcomesPanel'

import ConfirmDeleteModal from '@/components/ui/custom/ConfirmDeleteModal'
import Modal from '@/components/ui/custom/Modal'
import { useAuth } from '../../auth/hooks/useAuth'
import { coreStudentLoScoresList } from '../../../shared/api/generated/scores/scores'
import { evaluationGradesList, evaluationEnrollmentsList, evaluationAssessmentsDestroy } from '../../../shared/api/generated/evaluation/evaluation'
import { downloadReportPdf } from '@/shared/api/reportDownloads'
import { Card } from '@/components/ui/custom/Card'
import { ChartWidget } from '@/components/ui/custom/ChartWidget'
import { CourseHeader } from '../components/CourseHeader'
import { CourseInsightCards } from '../components/CourseInsightCards'
import { BoxPlotChart, BoxPlotLegend } from '../components/BoxPlotChart'
import { AssessmentHeatmap } from '../components/StudentHeatmap'
import { GradeDistributionChart } from '../../dashboard/components/GradeDistributionChart'
import {
  calculateCourseGradeFromAssessmentGrades,
  findWeakestLoAverageScore,
} from '../utils/courseInsights'
import { calculateGradeDistribution } from '../../dashboard/utils/analytics'
import type { BoxPlotData } from '../components/BoxPlotChart'
import type { HeatmapData } from '../components/StudentHeatmap'
import type {
  Course,
  CourseInstructorsItem,
  CoreLearningOutcome,
  EvaluationGradesListParams,
  PaginatedStudentGradeList,
  StudentGrade,
  StudentLearningOutcomeScore,
} from '../../../shared/api/model'

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
  overallScore: number | null
  assessmentScores: { name: string; score: number }[]
  loScores: { code: string; score: number }[]
}

type CourseAssignment = {
  id: number
  name: string
  assessment_type?: string
  total_score?: number
  weight?: number
  description?: string
  date?: string
}

type CourseGradesData = Omit<PaginatedStudentGradeList, 'results'> & {
  results: StudentGrade[]
  assignments?: CourseAssignment[]
  course_average?: number | null
}

const fetchAllCourseGrades = async (
  params: Omit<EvaluationGradesListParams, 'page'>
): Promise<CourseGradesData> => {
  const results: StudentGrade[] = []
  let page = 1
  let firstPage: CourseGradesData | null = null
  let hasNextPage = true

  while (hasNextPage) {
    const response = await evaluationGradesList({ ...params, page }) as CourseGradesData
    if (!firstPage) {
      firstPage = response
    }
    results.push(...(response.results || []))
    hasNextPage = Boolean(response.next)
    page += 1
  }

  return {
    count: firstPage?.count ?? results.length,
    next: null,
    previous: null,
    assignments: firstPage?.assignments ?? [],
    course_average: firstPage?.course_average ?? null,
    results,
  }
}

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

const atRiskCourseGradeThreshold = 60

const CourseDetail = () => {
  const { id: courseId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [isFileUploadModalOpen, setIsFileUploadModalOpen] = useState(false)
  const [isMappingEditorOpen, setIsMappingEditorOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const [assessmentChartView, setAssessmentChartView] = useState<'bar' | 'radar' | 'boxplot' | 'distribution' | 'heatmap'>('bar')
  const [selectedStudent, setSelectedStudent] = useState<StudentDetail | null>(null)

  const canEdit = user?.permissions?.includes('courses.change_course') ?? false
  const canDelete = user?.permissions?.includes('courses.delete_course') ?? false
  const canCreateLO = user?.permissions?.includes('learning_outcomes.add_learningoutcome') ?? false
  const canEditLO = user?.permissions?.includes('learning_outcomes.change_learningoutcome') ?? false
  const canDeleteLO = user?.permissions?.includes('learning_outcomes.delete_learningoutcome') ?? false

  // LO section state
  const [loCreateModalOpen, setLoCreateModalOpen] = useState(false)
  const [loEditTarget, setLoEditTarget] = useState<CoreLearningOutcome | null>(null)
  const [loDeleteTarget, setLoDeleteTarget] = useState<CoreLearningOutcome | null>(null)

  // Assessment section state
  const [assessCreateModalOpen, setAssessCreateModalOpen] = useState(false)
  const [assessEditTarget, setAssessEditTarget] = useState<{ id: number; name: string; assessment_type?: string; weight?: number; description?: string; total_score?: number } | null>(null)
  const [assessDeleteTarget, setAssessDeleteTarget] = useState<{ id: number; name: string } | null>(null)

  // Enrollment modals state
  const [enrollModalOpen, setEnrollModalOpen] = useState(false)
  const [unenrollModalOpen, setUnenrollModalOpen] = useState(false)

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
      const [courseResponse, loResponse, loScoresResponse] = await Promise.all([
        coreCoursesRetrieve(Number(courseId)),
        coreLearningOutcomesList({ course: Number(courseId) }),
        coreStudentLoScoresList({ course: Number(courseId) }),
      ])
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

  const handleUploadComplete = useCallback(() => {
    refetch()
  }, [refetch])

  const getInstructorNames = () => {
    if (!data?.course?.instructors || data.course.instructors.length === 0) {
      return 'Not assigned'
    }
    return data.course.instructors.map(getInstructorName).join(', ')
  }

  const getAverageCourseGrade = (): number => {
    return (gradesData as { course_average?: number })?.course_average ?? 0
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
    queryFn: async (): Promise<CourseGradesData> => {
      if (!courseId) {
        return {
          count: 0,
          next: null,
          previous: null,
          assignments: [],
          course_average: null,
          results: [],
        }
      }
      const resp = await fetchAllCourseGrades({ course: Number(courseId) })
      return resp
    },
    enabled: !!courseId
  })

  const assignments = useMemo(() => {
    return gradesData?.assignments || []
  }, [gradesData])

  const { data: enrollmentsData, error: enrollmentsError } = useQuery({
    queryKey: ['enrollments', courseId],
    queryFn: async () => {
      if (!courseId) return { results: [] }
      const resp = await evaluationEnrollmentsList({ course: Number(courseId) })
      return resp
    },
    enabled: !!courseId
  })

  const enrolledStudents = useMemo(() => {
    return (enrollmentsData?.results || []).map(e => ({
      id: e.id,
      name: e.student.replace(/ \([^)]+\)$/, ''),
    }))
  }, [enrollmentsData])

  const enrolledStudentIds = useMemo(() => {
    return (enrollmentsData?.results || []).map(e => e.student_id)
  }, [enrollmentsData])

  const handleEnrollSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['enrollments', courseId] })
    queryClient.invalidateQueries({ queryKey: ['grades', courseId] })
    refetch()
  }, [courseId, queryClient, refetch])

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
      const assessment = assessmentMap.get(aId)
      const studentEntry = studentMap.get(studentName)
      if (!assessment || !studentEntry) continue
      const total = assessment.totalScore
      const pct = total > 0 ? Math.round((grade.score / total) * 1000) / 10 : 0
      studentEntry.scores[aId] = pct
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
        map.set(name, { name, loScores: [], assessmentScores: [], overallScore: null })
      }
      const entry = map.get(name)
      if (!entry) continue
      const total = grade.assessment.total_score ?? 100
      const pct = total > 0 ? Math.round((grade.score / total) * 1000) / 10 : 0
      entry.assessmentScores.push({ name: grade.assessment.name, score: pct })
    }

    for (const student of heatmapData.students) {
      if (!map.has(student.studentName)) {
        map.set(student.studentName, { name: student.studentName, loScores: [], assessmentScores: [], overallScore: null })
      }
      const entry = map.get(student.studentName)
      if (!entry) continue
      entry.loScores = Object.entries(student.loScores).map(([code, score]) => ({ code, score }))
    }

    const gradesByStudent = new Map<string, NonNullable<typeof gradesData>['results']>()

    for (const grade of gradesData?.results || []) {
      const studentName = grade.student.replace(/ \([^)]+\)$/, '')
      const existingGrades = gradesByStudent.get(studentName) ?? []
      existingGrades.push(grade)
      gradesByStudent.set(studentName, existingGrades)
    }

    for (const [studentName, entry] of map.entries()) {
      entry.overallScore = calculateCourseGradeFromAssessmentGrades(gradesByStudent.get(studentName) ?? [])
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
      const entry = map.get(aId)
      if (!entry) continue
      const total = grade.assessment.total_score ?? 100
      const pct = total > 0 ? Math.round((grade.score / total) * 1000) / 10 : 0
      entry.scores.push(pct)
    }
    return Array.from(map.values()).map(a => ({
      id: Array.from(map.keys()).find(k => map.get(k) === a) || 0,
      name: a.name,
      avg: a.scores.length > 0 ? Math.round((a.scores.reduce((s, v) => s + v, 0) / a.scores.length) * 10) / 10 : 0
    }))
  }, [gradesData])

  const unifiedAssessments = useMemo(() => {
    const avgMap = new Map<number, number>()
    for (const item of assessmentRadarData) {
      avgMap.set(item.id, item.avg)
    }
    return assignments.map(a => ({
      ...a,
      avg: avgMap.get(a.id) ?? 0,
    })).sort((a, b) => a.name.localeCompare(b.name))
  }, [assignments, assessmentRadarData])

  const assessmentBoxPlotData = useMemo((): BoxPlotData[] => {
    const results = gradesData?.results || []
    const grouped = new Map<number, number[]>()
    const names = new Map<number, string>()
    for (const grade of results) {
      const aId = grade.assessment.id
      if (!grouped.has(aId)) grouped.set(aId, [])
      const total = grade.assessment.total_score ?? 100
      const scores = grouped.get(aId)
      if (!scores) continue
      scores.push(total > 0 ? (grade.score / total) * 100 : 0)
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

  const weakestLoInsight = useMemo(() => {
    if (!data?.learningOutcomes || !data?.loScores) return { code: null, averageLoScore: null }

    return findWeakestLoAverageScore(data.learningOutcomes, data.loScores)
  }, [data?.learningOutcomes, data?.loScores])

  const assessmentDifficultyInsights = useMemo(() => {
    const rankedByAverage = [...assessmentRadarData].sort((a, b) => a.avg - b.avg)
    const rankedBySpread = [...assessmentBoxPlotData]
      .map(item => ({ name: item.code, spread: Math.round((item.max - item.min) * 10) / 10 }))
      .sort((a, b) => b.spread - a.spread)

    return {
      mostDifficultAssessment: rankedByAverage[0] ?? null,
      highestSpreadAssessment: rankedBySpread[0] ?? null,
    }
  }, [assessmentRadarData, assessmentBoxPlotData])

  const studentsBelowCourseGradeThreshold = useMemo(() => {
    return Array.from(studentDataMap.values())
      .filter(student => student.overallScore !== null && student.overallScore < atRiskCourseGradeThreshold)
      .length
  }, [studentDataMap])

  const courseGradeDistribution = useMemo(() => (
    calculateGradeDistribution(
      Array.from(studentDataMap.values()).map(student => ({
        averageCourseGrade: student.overallScore,
      }))
    )
  ), [studentDataMap])

  const handleStudentClick = useCallback((studentName: string) => {
    const info = studentDataMap.get(studentName)
    if (info) {
      setSelectedStudent(info)
    }
  }, [studentDataMap])

  const handleGenerateReport = useCallback(async () => {
    const id = Number(courseId)
    if (!Number.isFinite(id) || !data?.course) return

    setReportError(null)
    setIsGeneratingReport(true)
    try {
      await downloadReportPdf({
        kind: 'course',
        id,
        fallbackFilename: `${data.course.code}-course-report.pdf`,
      })
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Failed to generate report.')
    } finally {
      setIsGeneratingReport(false)
    }
  }, [courseId, data?.course])

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
        queryClient.invalidateQueries({ queryKey: ['grades', courseId] })
      } catch { /* error handled silently */ }
    }
  }, [assessDeleteTarget, courseId, refetch, queryClient])

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
        <button
          onClick={() => refetch()}
          className="mt-3 px-4 py-2 bg-danger-600 text-white text-sm font-semibold rounded-lg hover:bg-danger-700 transition-colors"
        >
          Try Again
        </button>
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

  const averageCourseGrade = getAverageCourseGrade()

  return (
    <div className="space-y-6">
      <CourseHeader
        course={data.course}
        averageCourseGrade={averageCourseGrade}
        loCount={data.learningOutcomes?.length || 0}
        canEdit={canEdit}
        canDelete={canDelete}
        onEdit={() => setIsEditModalOpen(true)}
        onDelete={() => setIsDeleteConfirmOpen(true)}
        onImport={() => setIsFileUploadModalOpen(true)}
        onGenerateReport={handleGenerateReport}
        isGeneratingReport={isGeneratingReport}
        getInstructorNames={getInstructorNames}
      />

      {reportError && (
        <div className="rounded-lg border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-800">
          {reportError}
        </div>
      )}

      <CourseInsightCards
        weakestLoCode={weakestLoInsight.code}
        weakestLoAverageScore={weakestLoInsight.averageLoScore}
        mostDifficultAssessmentName={assessmentDifficultyInsights.mostDifficultAssessment?.name ?? null}
        mostDifficultAssessmentAverageScore={assessmentDifficultyInsights.mostDifficultAssessment?.avg ?? null}
        highestVarianceAssessmentName={assessmentDifficultyInsights.highestSpreadAssessment?.name ?? null}
        highestVarianceAssessmentSpread={assessmentDifficultyInsights.highestSpreadAssessment?.spread ?? null}
        studentsBelowThresholdCount={studentsBelowCourseGradeThreshold}
        atRiskThreshold={atRiskCourseGradeThreshold}
      />

      <section id="outcomes" className="scroll-mt-24">
        <LearningOutcomesPanel
          learningOutcomes={data.learningOutcomes}
          loScores={data.loScores}
          boxPlotData={boxPlotData}
          heatmapData={heatmapData}
          courseId={data.course.id}
          canCreate={canCreateLO}
          canEdit={canEditLO}
          canDelete={canDeleteLO}
          onCreate={() => setLoCreateModalOpen(true)}
          onEdit={(lo) => setLoEditTarget(lo as CoreLearningOutcome)}
          onDelete={(lo) => setLoDeleteTarget(lo as CoreLearningOutcome)}
          onStudentClick={handleStudentClick}
          headerAction={(
            <button
              onClick={() => setIsMappingEditorOpen(true)}
              className="flex items-center space-x-1 rounded-lg bg-primary-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-primary-700"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <span>Outcome Mapping</span>
            </button>
          )}
        />
      </section>

      <section id="assessments" className="scroll-mt-24">
      <Card>
        <h2 className="text-xl font-bold text-secondary-900 mb-2">Assessments</h2>
        <div className="flex items-center gap-2 mb-4">
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
            onClick={() => setAssessmentChartView('bar')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              assessmentChartView === 'bar'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Difficulty Bars
          </button>
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
          <button
            onClick={() => setAssessmentChartView('distribution')}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              assessmentChartView === 'distribution'
                ? 'bg-primary-600 text-white'
                : 'bg-secondary-100 text-secondary-600 hover:bg-secondary-200'
            }`}
          >
            Distribution
          </button>
        </div>
        {assessmentRadarData.length > 0 || assignments.length > 0 || courseGradeDistribution.length > 0 ? (
          <>
            {assessmentChartView === 'distribution' && (
              courseGradeDistribution.length > 0 ? (
                <GradeDistributionChart
                  data={courseGradeDistribution}
                  courseId={data.course.id}
                />
              ) : (
                <p className="text-secondary-500 text-center py-4">No grade distribution data available</p>
              )
            )}
            {assessmentRadarData.length > 0 && (
              <>
            {assessmentChartView === 'bar' && (
              <div className="space-y-3">
                {[...assessmentRadarData].sort((a, b) => a.avg - b.avg).map(assessment => (
                  <div key={assessment.id} className="grid grid-cols-[12rem_1fr_4rem] items-center gap-3">
                    <span className="text-sm font-medium text-secondary-700 truncate">{assessment.name}</span>
                    <div className="h-3 rounded-full bg-secondary-100 overflow-hidden">
                      <div className="h-full rounded-full bg-primary-500" style={{ width: `${Math.min(100, assessment.avg)}%` }} />
                    </div>
                    <span className="text-sm font-semibold text-secondary-900 text-right">{assessment.avg}%</span>
                  </div>
                ))}
              </div>
            )}
            {assessmentChartView === 'radar' && (
              <ChartWidget
                title=""
                type="radar"
                series={[{
                  name: 'Assessment average score',
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
            {assessmentChartView === 'boxplot' && <BoxPlotChart data={assessmentBoxPlotData} />}
            {assessmentChartView === 'boxplot' && assessmentBoxPlotData.length > 0 && (
              <div className="mt-5 pt-4 border-t border-secondary-100">
                <BoxPlotLegend />
              </div>
            )}
            {assessmentChartView === 'heatmap' && (
              <AssessmentHeatmap
                assessments={assessmentHeatmap.assessments}
                students={assessmentHeatmap.students}
                onStudentClick={handleStudentClick}
              />
            )}
</>
            )}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
              {unifiedAssessments.map((a) => {
                const score = a.avg
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
                    {a.weight !== undefined && a.weight !== null && (
                      <span className="text-xs text-secondary-500 mb-1">Assessment weight: {a.weight}</span>
                    )}
                    {a.description && (
                      <span className="text-secondary-700 text-sm leading-snug line-clamp-2">{a.description}</span>
                    )}
                      <div className="absolute bottom-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
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
                    </div>
                )
              })}
            </div>
          </>
        ) : (
          <p className="text-secondary-500 text-center py-4">No assessments defined for this course</p>
        )}
      </Card>
      </section>

      <section id="students" className="scroll-mt-24">
      <Card>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-secondary-900">Students</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setEnrollModalOpen(true)}
              className="bg-primary-600 text-white px-3 py-1.5 rounded-lg hover:bg-primary-700 flex items-center space-x-1.5 transition-colors text-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Enroll</span>
            </button>
            <button
              onClick={() => setUnenrollModalOpen(true)}
              className="bg-danger-50 text-danger-700 px-3 py-1.5 rounded-lg hover:bg-danger-100 flex items-center space-x-1.5 transition-colors text-sm"
            >
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
                  <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Current course grade</th>
                  <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Enrollment Term</th>
                </tr>
              </thead>
              <tbody>
                {(enrollmentsData?.results || []).sort((a, b) => a.student.localeCompare(b.student)).map((enrollment, idx) => {
                  const studentName = enrollment.student.replace(/ \([^)]+\)$/, '')
                  const info = studentDataMap.get(studentName)
                  return (
                    <tr
                      key={enrollment.id}
                      className={`cursor-pointer hover:bg-secondary-100/50 ${idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}`}
                      onClick={() => handleStudentClick(studentName)}
                    >
                      <td className="px-2 py-1.5 text-sm font-medium text-secondary-900 border-b border-secondary-200">{studentName}</td>
                      <td className="px-2 py-1.5 text-sm text-secondary-700 border-b border-secondary-200">{info?.overallScore ?? 'N/A'}</td>
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
      </section>

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
              onClose={() => { setIsMappingEditorOpen(false); queryClient.invalidateQueries({ queryKey: ['grades', courseId] }) }}
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

      <EnrollStudentsModal
        isOpen={enrollModalOpen}
        onClose={() => setEnrollModalOpen(false)}
        courseId={Number(courseId)}
        enrolledStudentIds={enrolledStudentIds}
        onSuccess={handleEnrollSuccess}
      />
      <UnenrollStudentsModal
        isOpen={unenrollModalOpen}
        onClose={() => setUnenrollModalOpen(false)}
        enrolledStudents={enrolledStudents}
        onSuccess={handleEnrollSuccess}
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
        onSuccess={() => { setAssessCreateModalOpen(false); refetch(); queryClient.invalidateQueries({ queryKey: ['grades', courseId] }) }}
        mode="create"
        courseId={Number(courseId)}
        courseTemplateId={courseTemplateId}
      />
      <CreateEditAssessmentModal
        isOpen={!!assessEditTarget}
        onClose={() => setAssessEditTarget(null)}
        onSuccess={() => { setAssessEditTarget(null); refetch(); queryClient.invalidateQueries({ queryKey: ['grades', courseId] }) }}
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
            <p className="text-sm text-secondary-600 font-medium">Overall course grade</p>
            <p className="text-3xl font-bold text-secondary-900">{selectedStudent?.overallScore ?? 'N/A'}</p>
          </div>

          {selectedStudent && selectedStudent.assessmentScores.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-secondary-800 mb-2">Assessment Scores</h3>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="bg-secondary-100">
                      <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Assessment</th>
                      <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">Assessment score (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedStudent.assessmentScores.map((as, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}>
                        <td className="px-2 py-1.5 text-sm text-secondary-900 border-b border-secondary-200">{as.name}</td>
                        <td className="px-2 py-1.5 text-sm text-secondary-700 border-b border-secondary-200">{as.score}</td>
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
                      <th className="px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-secondary-200">LO score (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedStudent.loScores.map((ls, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}>
                        <td className="px-2 py-1.5 text-sm text-secondary-900 border-b border-secondary-200">{ls.code}</td>
                        <td className="px-2 py-1.5 text-sm text-secondary-700 border-b border-secondary-200">{ls.score}</td>
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
