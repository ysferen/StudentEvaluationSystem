import React, { useState, useRef } from 'react'
import {
  useCoreFileImportAssignmentScoresUploadCreate,
  useCoreFileImportAssignmentScoresValidateCreate,
  useCoreFileImportAssignmentScoresResolveCreate,
} from '../../../shared/api/generated/core/core'
import {
  Upload,
  X,
  Check,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  FileSpreadsheet,
  Shield,
  Lightbulb,
  ChevronDown,
} from 'lucide-react'
import {
  MissingAssessmentsModal,
  MissingStudentsModal,
  UnenrolledStudentsModal,
  InvalidScoresModal
} from './ResolutionModals'

interface CheckResult {
  passed: boolean
  details?: Record<string, unknown>
}

type PhaseKey =
  | 'file_structure'
  | 'column_structure'
  | 'assessment_validation'
  | 'student_validation'
  | 'score_validation'

interface ValidationDetails {
  phases_completed?: Array<{ phase: string; passed: boolean }>
  file_parsed?: boolean
  column_structure?: Record<string, unknown> & { passed?: boolean }
  assessment_validation?: Record<string, unknown> & {
    passed?: boolean
    found_assessments?: Array<{ column: string; parsed_name: string; db_assessment?: string; db_name?: string }>
    missing_assessments?: Array<{ column: string; parsed_name: string }>
    available_in_database?: string[]
  }
  missing_students?: string[]
  student_validation?: Record<string, unknown> & {
    passed?: boolean
    total_in_file?: number
    found_in_database?: number
    missing_from_database?:
      | number
      | Array<{ student_id?: string; first_name?: string; last_name?: string }>
    not_enrolled?: Array<{ student_id: string; first_name: string; last_name: string }>
  }
  score_validation?: Record<string, unknown> & {
    passed?: boolean
    invalid_scores?: Array<{ row: number; column: string; value: string; error?: string }>
  }
}

interface ValidationResult {
  is_valid: boolean
  phase_reached?: string
  checks?: {
    file_structure?: CheckResult
    column_structure?: CheckResult
    assessment_validation?: {
      passed: boolean
      found_assessments?: Array<{ column: string; parsed_name: string; db_assessment?: string; db_name?: string }>
      missing_assessments?: Array<{ column: string; parsed_name: string }>
      available_in_database?: string[]
    }
    student_validation?: {
      passed: boolean
      total_in_file?: number
      found_in_database?: number
      missing_from_database?: Array<{ student_id: string; first_name: string; last_name: string }>
      not_enrolled?: Array<{ student_id: string; first_name: string; last_name: string }>
    }
    score_validation?: {
      passed: boolean
      invalid_scores?: Array<{ row: number; column: string; value: string; error?: string }>
    }
  }
  errors?: Array<{ message: string; category: string; severity: string }>
  warnings?: Array<{ message: string; category: string; severity: string }>
  suggestions?: Array<{ message: string; category: string; severity: string }>
  details?: ValidationDetails
  resolutions_applied?: {
    created?: { students?: number; enrollments?: number; assessments?: number }
    errors?: string[]
    policy?: Record<string, unknown>
  }
}

type NormalizedChecks = {
  file_structure?: { passed: boolean } | undefined
  column_structure?: { passed: boolean; details?: Record<string, unknown> } | undefined
  assessment_validation?: {
    passed: boolean
    found_assessments?: Array<{ column: string; parsed_name: string; db_assessment?: string; db_name?: string }>
    missing_assessments?: Array<{ column: string; parsed_name: string }>
    available_in_database?: string[]
  } | undefined
  student_validation?: {
    passed: boolean
    total_in_file?: number
    found_in_database?: number
    missing_from_database?: Array<{ student_id: string; first_name: string; last_name: string }>
    not_enrolled?: Array<{ student_id: string; first_name: string; last_name: string }>
  } | undefined
  score_validation?: {
    passed: boolean
    invalid_scores?: Array<{ row: number; column: string; value: string; error?: string }>
  } | undefined
}

type UploadErrorPayload = Partial<ValidationResult> & {
  message?: string
  error?: string
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const toValidationResult = (value: unknown, defaultIsValid: boolean): ValidationResult => {
  if (!isRecord(value)) {
    return { is_valid: defaultIsValid }
  }

  return {
    is_valid: typeof value.is_valid === 'boolean' ? value.is_valid : defaultIsValid,
    phase_reached: typeof value.phase_reached === 'string' ? value.phase_reached : undefined,
    checks: isRecord(value.checks) ? value.checks as ValidationResult['checks'] : undefined,
    errors: Array.isArray(value.errors) ? value.errors as ValidationResult['errors'] : undefined,
    warnings: Array.isArray(value.warnings) ? value.warnings as ValidationResult['warnings'] : undefined,
    suggestions: Array.isArray(value.suggestions) ? value.suggestions as ValidationResult['suggestions'] : undefined,
    details: isRecord(value.details) ? value.details as ValidationDetails : undefined,
  }
}

const getErrorData = (error: unknown): UploadErrorPayload | undefined => {
  if (!isRecord(error) || !isRecord(error.response)) {
    return undefined
  }

  return isRecord(error.response.data) ? error.response.data as UploadErrorPayload : undefined
}

const getErrorMessage = (error: unknown, fallback: string): string => {
  const errorData = getErrorData(error)
  if (typeof errorData?.error === 'string') {
    return errorData.error
  }
  if (typeof errorData?.message === 'string') {
    return errorData.message
  }
  if (isRecord(error) && typeof error.message === 'string') {
    return error.message
  }
  return fallback
}

const getPhaseKeyFromText = (phaseText?: string): PhaseKey | undefined => {
  if (!phaseText) return undefined

  const normalized = phaseText.toLowerCase()

  if (normalized.includes('file structure')) return 'file_structure'
  if (normalized.includes('column structure')) return 'column_structure'
  if (normalized.includes('assessment')) return 'assessment_validation'
  if (normalized.includes('student validation')) return 'student_validation'
  if (normalized.includes('score validation')) return 'score_validation'

  return undefined
}

const getErrorCategoriesForPhase = (phase: PhaseKey): string[] => {
  switch (phase) {
    case 'file_structure':
      return ['file_structure', 'file_format', 'file_parse']
    case 'column_structure':
      return ['column_structure']
    case 'assessment_validation':
      return ['assessment_validation', 'assignment_columns']
    case 'student_validation':
      return ['student_validation', 'student_column']
    case 'score_validation':
      return ['score_validation']
    default:
      return []
  }
}

const filterErrorsForCurrentPhase = (
  errors: ValidationResult['errors'],
  currentPhase?: PhaseKey,
): ValidationResult['errors'] => {
  if (!errors || errors.length === 0 || !currentPhase) return errors

  const categories = getErrorCategoriesForPhase(currentPhase)
  return errors.filter((error) => {
    if (typeof error === 'string') return false
    const category = String(error?.category ?? '').toLowerCase()
    return categories.includes(category)
  })
}

const normalizeMissingStudents = (
  detail: ValidationDetails | undefined
): Array<{ student_id: string; first_name: string; last_name: string }> => {
  const studentValidation = detail?.student_validation

  if (Array.isArray(studentValidation?.missing_from_database)) {
    return studentValidation.missing_from_database.map((entry, idx) => ({
      student_id: String(entry?.student_id ?? idx),
      first_name: entry?.first_name ?? '',
      last_name: entry?.last_name ?? '',
    }))
  }

  if (Array.isArray(detail?.missing_students)) {
    return detail.missing_students.map((studentId) => ({
      student_id: String(studentId),
      first_name: '',
      last_name: '',
    }))
  }

  return []
}

const normalizeChecks = (result: ValidationResult | null): NormalizedChecks => {
  if (!result) return {}

  const checks = result.checks
  const details = result.details
  const phaseResultsFallback = details?.phases_completed?.reduce<Partial<Record<PhaseKey, boolean>>>((acc, phaseInfo) => {
    const key = getPhaseKeyFromText(phaseInfo.phase)
    if (key) {
      acc[key] = phaseInfo.passed
    }
    return acc
  }, {}) ?? {}

  if (checks) {
    return {
      file_structure: checks.file_structure,
      column_structure: checks.column_structure ?? (details?.column_structure
        ? {
            passed:
              typeof details.column_structure.passed === 'boolean'
                ? details.column_structure.passed
                : (phaseResultsFallback.column_structure ?? false),
            details: details.column_structure,
          }
        : undefined),
      assessment_validation: checks.assessment_validation
        ? {
            ...checks.assessment_validation,
            missing_assessments:
              checks.assessment_validation.missing_assessments
              ?? details?.assessment_validation?.missing_assessments
              ?? [],
            available_in_database:
              checks.assessment_validation.available_in_database
              ?? details?.assessment_validation?.available_in_database
              ?? [],
            found_assessments:
              checks.assessment_validation.found_assessments
              ?? details?.assessment_validation?.found_assessments
              ?? [],
          }
        : details?.assessment_validation
          ? {
              passed:
                typeof details.assessment_validation.passed === 'boolean'
                  ? details.assessment_validation.passed
                  : typeof phaseResultsFallback.assessment_validation === 'boolean'
                    ? phaseResultsFallback.assessment_validation
                    : (details.assessment_validation.missing_assessments?.length ?? 0) === 0,
              found_assessments: details.assessment_validation.found_assessments,
              missing_assessments: details.assessment_validation.missing_assessments ?? [],
              available_in_database: details.assessment_validation.available_in_database ?? [],
            }
          : undefined,
      student_validation: checks.student_validation
        ? {
            ...checks.student_validation,
            missing_from_database:
              checks.student_validation.missing_from_database
              ?? normalizeMissingStudents(details)
              ?? [],
            not_enrolled:
              checks.student_validation.not_enrolled
              ?? (Array.isArray(details?.student_validation?.not_enrolled)
                ? details.student_validation.not_enrolled
                : []),
          }
        : details?.student_validation
          ? {
              passed:
                typeof details.student_validation.passed === 'boolean'
                  ? details.student_validation.passed
                  : typeof phaseResultsFallback.student_validation === 'boolean'
                    ? phaseResultsFallback.student_validation
                    : normalizeMissingStudents(details).length === 0,
              total_in_file: details.student_validation.total_in_file,
              found_in_database: details.student_validation.found_in_database,
              missing_from_database: normalizeMissingStudents(details),
              not_enrolled: Array.isArray(details.student_validation.not_enrolled)
                ? details.student_validation.not_enrolled
                : [],
            }
          : undefined,
      score_validation: checks.score_validation
        ? {
            ...checks.score_validation,
            invalid_scores:
              checks.score_validation.invalid_scores
              ?? (Array.isArray(details?.score_validation?.invalid_scores)
                ? details.score_validation.invalid_scores
                : []),
          }
        : details?.score_validation
          ? {
              passed:
                typeof details.score_validation.passed === 'boolean'
                  ? details.score_validation.passed
                  : (phaseResultsFallback.score_validation ?? false),
              invalid_scores: Array.isArray(details.score_validation.invalid_scores)
                ? details.score_validation.invalid_scores
                : [],
            }
          : undefined,
    }
  }

  return {
    file_structure:
      typeof phaseResultsFallback.file_structure === 'boolean'
        ? { passed: phaseResultsFallback.file_structure }
        : typeof details?.file_parsed === 'boolean'
          ? { passed: details.file_parsed }
          : undefined,
    column_structure:
      details?.column_structure
        ? {
            passed:
              typeof details.column_structure.passed === 'boolean'
                ? details.column_structure.passed
                : (phaseResultsFallback.column_structure ?? false),
            details: details.column_structure,
          }
        : typeof phaseResultsFallback.column_structure === 'boolean'
          ? { passed: phaseResultsFallback.column_structure }
          : undefined,
    assessment_validation:
      details?.assessment_validation
        ? {
            passed:
              typeof details.assessment_validation.passed === 'boolean'
                ? details.assessment_validation.passed
                : typeof phaseResultsFallback.assessment_validation === 'boolean'
                  ? phaseResultsFallback.assessment_validation
                  : (details.assessment_validation.missing_assessments?.length ?? 0) === 0,
            found_assessments: details.assessment_validation.found_assessments,
            missing_assessments: details.assessment_validation.missing_assessments,
            available_in_database: details.assessment_validation.available_in_database,
          }
        : typeof phaseResultsFallback.assessment_validation === 'boolean'
          ? { passed: phaseResultsFallback.assessment_validation }
          : undefined,
    student_validation:
      details?.student_validation
        ? {
            passed:
              typeof details.student_validation.passed === 'boolean'
                ? details.student_validation.passed
                : typeof phaseResultsFallback.student_validation === 'boolean'
                  ? phaseResultsFallback.student_validation
                  : normalizeMissingStudents(details).length === 0,
            total_in_file: details.student_validation.total_in_file,
            found_in_database: details.student_validation.found_in_database,
            missing_from_database: normalizeMissingStudents(details),
            not_enrolled: Array.isArray(details.student_validation.not_enrolled)
              ? details.student_validation.not_enrolled
              : [],
          }
        : typeof phaseResultsFallback.student_validation === 'boolean'
          ? { passed: phaseResultsFallback.student_validation }
          : undefined,
    score_validation:
      details?.score_validation
        ? {
            passed:
              typeof details.score_validation.passed === 'boolean'
                ? details.score_validation.passed
                : (phaseResultsFallback.score_validation ?? false),
            invalid_scores: Array.isArray(details.score_validation.invalid_scores)
              ? details.score_validation.invalid_scores
              : [],
          }
        : typeof phaseResultsFallback.score_validation === 'boolean'
          ? { passed: phaseResultsFallback.score_validation }
          : undefined,
  }
}

interface FileUploadModalProps {
  course: string
  courseCode: string
  termId: number
  isOpen: boolean
  type: 'assignment_scores'
  onClose: () => void
  onUploadComplete?: (result: unknown) => void
}

type ActiveProblem = 'assessments' | 'students' | 'unenrolled' | 'scores' | null

const RESOLUTION_POLICY_KEYS = [
  'skip_missing_assessments',
  'skip_missing_students',
  'skip_unenrolled_students',
  'skip_invalid_scores',
  'clamp_scores',
]

const extractResolutionPolicy = (resolutions: Record<string, unknown>): Record<string, unknown> => {
  return RESOLUTION_POLICY_KEYS.reduce<Record<string, unknown>>((policy, key) => {
    if (key in resolutions) {
      policy[key] = resolutions[key]
    }
    return policy
  }, {})
}

const FileUploadModal: React.FC<FileUploadModalProps> = ({
  course,
  courseCode,
  termId,
  isOpen,
  onClose,
  type,
  onUploadComplete
}) => {
  const [file, setFile] = useState<File | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [modalError, setModalError] = useState<string | null>(null)
  const [activeProblem, setActiveProblem] = useState<ActiveProblem>(null)
  const [resolvedOperationCount, setResolvedOperationCount] = useState(0)
  const resolutionPolicyRef = useRef<Record<string, unknown>>({})
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)



  const validationMutation = useCoreFileImportAssignmentScoresValidateCreate({
    request: {
      params: {
        course_code: courseCode,
        term_id: termId
      },
      data: file ? { file } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' }
    }
  })

  const uploadMutation = useCoreFileImportAssignmentScoresUploadCreate()

  const resolveMutation = useCoreFileImportAssignmentScoresResolveCreate({
    request: {
      params: {
        course_code: courseCode,
        term_id: termId
      }
    }
  })

  const isAnyValidatePending = validationMutation.isPending
  const isAnyUploadPending = uploadMutation.isPending
  const isResolving = resolveMutation.isPending
  const hasSuccessfulValidation = validationResult?.is_valid === true
  const normalizedChecks = normalizeChecks(validationResult)

  const getTypeDisplayName = (type: string) => {
    switch (type) {
      case 'assignment_scores':
        return 'Assessment Scores'
      default:
        return 'File'
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setValidationResult(null)
      setModalError(null)
      setResolvedOperationCount(0)
      resolutionPolicyRef.current = {}
    }
  }

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) {
      const validTypes = ['.xlsx', '.xls']
      const ext = droppedFile.name.substring(droppedFile.name.lastIndexOf('.')).toLowerCase()
      if (validTypes.includes(ext)) {
        setFile(droppedFile)
        setValidationResult(null)
        setModalError(null)
        setResolvedOperationCount(0)
        resolutionPolicyRef.current = {}
      } else {
        setModalError('Please drop an Excel file (.xlsx or .xls)')
      }
    }
  }

  const handleResolve = async (newResolutions: Record<string, unknown>) => {
    if (!file) return

    setActiveProblem(null)

    try {
      const newPolicy = extractResolutionPolicy(newResolutions)
      if (Object.keys(newPolicy).length > 0) {
        resolutionPolicyRef.current = { ...resolutionPolicyRef.current, ...newPolicy }
      }

      const result = await resolveMutation.mutateAsync({
        data: { file, resolutions: JSON.stringify(newResolutions) },
        params: { course_code: courseCode, term_id: termId }
      })
      setResolvedOperationCount((count) => count + 1)
      setValidationResult(toValidationResult(result, false))
    } catch (error) {
      const errorData = getErrorData(error)
      if (errorData) {
        setValidationResult(toValidationResult(errorData, false))
      } else {
        setModalError(getErrorMessage(error, 'Resolution failed'))
      }
    }
  }

  const handleValidate = async () => {
    if (!file) {
      setModalError('Please select a file first')
      return
    }

    setValidationResult(null)
    setModalError(null)
    setResolvedOperationCount(0)
    resolutionPolicyRef.current = {}

    try {
      const result = await validationMutation.mutateAsync({ data: { file } } as any)
      setValidationResult(toValidationResult(result, true))
    } catch (error) {
      const errorData = getErrorData(error)
      if (errorData) {
        setValidationResult(toValidationResult(errorData, false))
      } else {
        setModalError(getErrorMessage(error, 'Validation failed'))
      }
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setModalError('Please select a file first')
      return
    }

    setModalError(null)

    try {
      const result = await uploadMutation.mutateAsync({
        params: { course_code: courseCode, term_id: termId },
        data: {
          file,
          resolution_policy: JSON.stringify(resolutionPolicyRef.current),
        }
      } as any)
      onUploadComplete?.(result)
      onClose()
    } catch (error) {
      const errorData = getErrorData(error)
      if (errorData?.errors) {
        setValidationResult(toValidationResult(errorData, false))
      } else {
        setModalError(getErrorMessage(error, 'Upload failed'))
      }
    }
  }

  const handleModalClose = () => {
    onClose()
  }

  const getSolveTarget = (phase: PhaseKey, checks: NormalizedChecks, result: ValidationResult): ActiveProblem => {
    if (phase === "assessment_validation" && checks?.assessment_validation?.passed === false) return "assessments"
    if (phase === "student_validation" && checks?.student_validation?.passed === false) {
      if ((checks.student_validation.not_enrolled || []).length > 0) return "unenrolled"
      if ((checks.student_validation.missing_from_database || []).length > 0) return "students"

      const studentErrors = (result.errors ?? []).filter(
        (error) => (error?.category ?? '').toLowerCase().includes('student')
      )
      if (studentErrors.some((error) => {
        const message = error?.message ?? ''
        return message.toLowerCase().includes('not enrolled')
      })) {
        return 'unenrolled'
      }

      return 'students'
    }
    if (phase === "score_validation" && checks?.score_validation?.passed === false) return "scores"
    return null
  }

  const renderValidationResult = () => {
    if (!validationResult) return null

    const { is_valid, errors, warnings, suggestions, phase_reached } = validationResult

    const { details } = validationResult

    const phaseResults = details?.phases_completed?.reduce<Partial<Record<PhaseKey, boolean>>>((acc, phaseInfo) => {
      const key = getPhaseKeyFromText(phaseInfo.phase)
      if (key) {
        acc[key] = phaseInfo.passed
      }
      return acc
    }, {}) ?? {}

    const normalizedPhaseReached = getPhaseKeyFromText(phase_reached)
    const visibleErrors = filterErrorsForCurrentPhase(errors, normalizedPhaseReached)

    const phases = [
      { key: 'file_structure' as PhaseKey, label: 'File Structure', description: 'Validates file exists, is Excel format, and under 10MB', check: normalizedChecks.file_structure, phasePassed: phaseResults.file_structure },
      { key: 'column_structure' as PhaseKey, label: 'Column Structure', description: 'Checks required columns: student ID, name, surname + assessment columns', check: normalizedChecks.column_structure, phasePassed: phaseResults.column_structure },
      { key: 'assessment_validation' as PhaseKey, label: 'Assessments', description: 'Verifies assessment columns exist in course', check: normalizedChecks.assessment_validation, phasePassed: phaseResults.assessment_validation },
      { key: 'student_validation' as PhaseKey, label: 'Students', description: 'Confirms students exist and are enrolled', check: normalizedChecks.student_validation, phasePassed: phaseResults.student_validation },
      { key: 'score_validation' as PhaseKey, label: 'Scores', description: 'Validates score values are within range', check: normalizedChecks.score_validation, phasePassed: phaseResults.score_validation },
    ]

    const firstFailedIndex = phases.findIndex((phase) =>
      typeof phase.phasePassed === 'boolean' ? phase.phasePassed === false : phase.check?.passed === false
    )
    const reachedPhaseIndex = normalizedPhaseReached ? phases.findIndex((phase) => phase.key === normalizedPhaseReached) : -1
    const firstFailedFromChecksOnlyIndex = phases.findIndex(
      (phase) => typeof phase.phasePassed !== 'boolean' && phase.check?.passed === false
    )
    const lastEvaluatedIndex = phases.reduce((lastIndex, phase, idx) => {
      if (typeof phase.phasePassed === 'boolean') return idx
      return typeof phase.check?.passed === 'boolean' ? idx : lastIndex
    }, -1)

    return (
      <div className={`mt-4 p-4 rounded-xl ${is_valid ? 'bg-emerald-50 border border-emerald-200' : 'bg-secondary-50 border border-secondary-200'}`}>
        <div className="flex items-center mb-3">
          {is_valid ? (
            <>
              <CheckCircle className="w-5 h-5 text-emerald-500 mr-2" />
              <span className="font-semibold text-emerald-800">Validation Passed</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-5 h-5 text-warning-500 mr-2" />
              <span className="font-semibold text-secondary-800">Validation Issues Found</span>
            </>
          )}
        </div>

        <div className="mb-4">
          <p className="text-xs text-secondary-500 mb-3 uppercase tracking-wide font-medium">Validation Phases</p>
          <div className="space-y-2">
            {phases.map((phase, idx) => {
              let phaseState: 'passed' | 'failed' | 'active' | 'pending' = 'pending'

              // Treat phases after the reached phase as neutral/pending, even if backend
              // sends default passed:false placeholders for them.
              const isBeyondReachedPhase = reachedPhaseIndex !== -1 && idx > reachedPhaseIndex

              if (isBeyondReachedPhase) {
                phaseState = 'pending'
              } else if (typeof phase.phasePassed === 'boolean') {
                phaseState = phase.phasePassed ? 'passed' : 'failed'
              } else if (phase.check?.passed === true) {
                phaseState = 'passed'
              } else if (phase.check?.passed === false) {
                // If backend did not send explicit per-phase progression, treat only
                // the first failed check as failed and keep subsequent phases neutral.
                if (reachedPhaseIndex === -1 && firstFailedFromChecksOnlyIndex !== -1) {
                  phaseState = idx === firstFailedFromChecksOnlyIndex ? 'failed' : 'pending'
                } else {
                  phaseState = 'failed'
                }
              } else if (firstFailedIndex !== -1) {
                phaseState = idx < firstFailedIndex ? 'passed' : 'pending'
              } else if (is_valid) {
                phaseState = 'passed'
              } else if (reachedPhaseIndex !== -1) {
                phaseState = idx <= reachedPhaseIndex ? 'active' : 'pending'
              } else if (idx <= lastEvaluatedIndex) {
                phaseState = 'active'
              }

              const isPassed = phaseState === 'passed'
              const isFailed = phaseState === 'failed'
              const isActive = phaseState === 'active'
              const isPending = phaseState === 'pending'
              const solveTarget = isFailed ? getSolveTarget(phase.key, normalizedChecks, validationResult) : null

              let circleClass = 'bg-secondary-300'
              let statusTextClass = 'text-secondary-400'
              let statusBgClass = 'bg-secondary-50'
              let statusBorderClass = 'border-secondary-200'
              let statusLabel = 'Pending'
              let StatusIcon = null

              if (isPassed) {
                circleClass = 'bg-emerald-500'
                statusTextClass = 'text-emerald-700'
                statusBgClass = 'bg-emerald-50'
                statusBorderClass = 'border-emerald-200'
                statusLabel = 'Passed'
                StatusIcon = <Check className="w-3 h-3 text-white" />
              } else if (isFailed) {
                circleClass = 'bg-danger-500'
                statusTextClass = 'text-danger-700'
                statusBgClass = 'bg-danger-50'
                statusBorderClass = 'border-danger-200'
                statusLabel = 'Failed'
                StatusIcon = <X className="w-3 h-3 text-white" />
              } else if (isActive) {
                circleClass = 'bg-primary-500'
                statusTextClass = 'text-primary-700'
                statusBgClass = 'bg-primary-50'
                statusBorderClass = 'border-primary-200'
                statusLabel = 'In Progress'
              }

              return (
                <div key={phase.key} className="flex items-start gap-3">
                  <div className="flex flex-col items-center flex-shrink-0 pt-1">
                    <div className={`w-6 h-6 rounded-full ${circleClass} flex items-center justify-center`}>
                      {StatusIcon ?? <span className="text-white text-xs font-medium">{idx + 1}</span>}
                    </div>
                    {idx < phases.length - 1 && (
                      <div className="h-6 flex items-center justify-center text-secondary-300">
                        <ChevronDown className="w-4 h-4" />
                      </div>
                    )}
                  </div>

                  <div className={`flex items-center gap-3 p-2 rounded-lg border flex-1 ${statusBgClass} ${statusBorderClass}`}>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${statusTextClass}`}>
                        {phase.label}
                      </p>
                      <p className={`text-xs ${isPending ? 'text-secondary-400' : 'text-secondary-500'}`}>
                        {phase.description}
                      </p>
                    </div>
                    <div className="flex-shrink-0 flex items-center gap-2">
                      <span className={`text-xs font-medium ${isPassed ? 'text-emerald-600' : isFailed ? 'text-danger-600' : isActive ? 'text-primary-600' : 'text-secondary-400'}`}>
                        {statusLabel}
                      </span>
                      {!isPassed && !isPending && solveTarget && (
                        <button
                          type="button"
                          onClick={() => {
                            setActiveProblem(solveTarget)
                          }}
                          className="text-xs bg-warning-100 text-warning-700 px-2 py-1 rounded-md hover:bg-warning-200"
                        >
                          Solve
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {visibleErrors && visibleErrors.length > 0 && (
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-1">
              <XCircle className="w-4 h-4 text-danger-500" />
              <h4 className="text-sm font-semibold text-danger-800">Errors:</h4>
            </div>
            <ul className="list-disc list-inside text-sm text-danger-600 space-y-1 ml-6">
              {visibleErrors.map((error, idx) => {
                const msg = typeof error === 'string' ? error : error?.message ?? 'Unknown error'
                return <li key={idx}>{msg}</li>
              })}
            </ul>
          </div>
        )}

        {warnings && warnings.length > 0 && (
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-4 h-4 text-warning-500" />
              <h4 className="text-sm font-semibold text-warning-800">Warnings:</h4>
            </div>
            <ul className="list-disc list-inside text-sm text-warning-600 space-y-1 ml-6">
              {warnings.map((warning, idx) => {
                const msg = typeof warning === 'string' ? warning : warning?.message ?? 'Unknown warning'
                return <li key={idx}>{msg}</li>
              })}
            </ul>
          </div>
        )}

        {suggestions && suggestions.length > 0 && (
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-1">
              <Lightbulb className="w-4 h-4 text-primary-500" />
              <h4 className="text-sm font-semibold text-primary-800">Suggestions:</h4>
            </div>
            <ul className="list-disc list-inside text-sm text-primary-700 space-y-1 ml-6">
              {suggestions.map((suggestion, idx) => {
                const msg = typeof suggestion === 'string' ? suggestion : suggestion?.message ?? 'Unknown suggestion'
                return <li key={idx}>{msg}</li>
              })}
            </ul>
          </div>
        )}

        {resolvedOperationCount > 0 && (
          <div className="mt-3 pt-3 border-t border-secondary-200">
            <p className="text-xs text-secondary-500">
              {resolvedOperationCount} resolution(s) applied
            </p>
            {validationResult.resolutions_applied?.created && (
              <p className="text-xs text-secondary-500 mt-1">
                Created: {validationResult.resolutions_applied.created.students ?? 0} student(s), {validationResult.resolutions_applied.created.enrollments ?? 0} enrollment(s), {validationResult.resolutions_applied.created.assessments ?? 0} assessment(s)
              </p>
            )}
          </div>
        )}
      </div>
    )
  }

  const renderModalError = () => {
    if (!modalError) return null

    return (
      <div className="bg-danger-50 border border-danger-200 rounded-xl p-4 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <XCircle className="w-5 h-5 text-danger-500" />
            <span className="text-sm font-semibold text-danger-800">{modalError}</span>
          </div>
          <button
            onClick={() => setModalError(null)}
            className="text-danger-400 hover:text-danger-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Only close if clicking directly on the backdrop (not the modal content)
    if (e.target === e.currentTarget && !isAnyUploadPending && !isAnyValidatePending && !isResolving) {
      handleModalClose()
    }
  }

  return (
    <div
      onClick={handleBackdropClick}
      className={`fixed inset-0 z-20 isolate overflow-auto bg-secondary-900/60 flex items-center justify-center p-4 ${isOpen ? '' : 'hidden'}`}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl relative">
        <div className="flex items-center justify-between p-6 border-b border-secondary-200">
          <h2 className="text-xl font-bold text-secondary-900">Import {getTypeDisplayName(type)} - {course}</h2>
          <button
            onClick={handleModalClose}
            disabled={isAnyUploadPending || isAnyValidatePending || isResolving}
            className="text-secondary-400 hover:text-secondary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {renderModalError()}

          {type === 'assignment_scores' && (
            <div className="mb-4 p-4 bg-primary-50 border border-primary-200 rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <Info className="w-4 h-4 text-primary-600" />
                <h3 className="font-semibold text-primary-800">Expected Format:</h3>
              </div>
              <p className="text-sm text-primary-700 mb-2">
                Excel format with columns like:
              </p>
              <ul className="text-sm text-primary-700 space-y-1 ml-4 list-disc">
                <li><code className="bg-primary-100 px-1 rounded">Öğrenci No_XXXXX</code> - Student ID</li>
                <li><code className="bg-primary-100 px-1 rounded">Adı_XXXXX</code> - First Name</li>
                <li><code className="bg-primary-100 px-1 rounded">Soyadı_XXXXX</code> - Last Name</li>
                <li><code className="bg-primary-100 px-1 rounded">Midterm 1(%XX)_XXXXX</code> - Assessment</li>
                <li><code className="bg-primary-100 px-1 rounded">Project(%XX)_XXXXX</code> - Assessment</li>
              </ul>
              <p className="text-sm text-primary-700 mt-1">
                <strong>Max file size:</strong> 10 MB
              </p>
            </div>
          )}



          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-2">
                Select File (.xlsx, .xls)
              </label>
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragEnter={handleDragEnter}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
                  isDragging
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-secondary-300 hover:border-primary-500'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileChange}
                  disabled={isAnyUploadPending || isAnyValidatePending || isResolving}
                  className="hidden"
                />
                <Upload className={`w-8 h-8 mx-auto mb-2 ${isDragging ? 'text-primary-500' : 'text-secondary-400'}`} />
                <p className={`text-sm ${isDragging ? 'text-primary-600' : 'text-secondary-600'}`}>
                  {file ? file.name : isDragging ? 'Drop file here' : 'Click to select or drag and drop your file'}
                </p>
                <p className="text-xs text-secondary-500 mt-1">.xlsx, .xls files only</p>
              </div>
            </div>

            {file && (
              <div className="bg-secondary-50 border border-secondary-200 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-secondary-700 font-medium">{file.name}</p>
                    <p className="text-xs text-secondary-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                  <FileSpreadsheet className="w-5 h-5 text-secondary-400" />
                </div>
                {file.size > 10 * 1024 * 1024 && (
                  <div className="flex items-center gap-2 mt-2 text-danger-600">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-sm">File exceeds 10 MB limit</span>
                  </div>
                )}
              </div>
            )}

            {renderValidationResult()}

            <div className="flex space-x-3">
              <button
                onClick={handleValidate}
                disabled={!file || isAnyValidatePending || isResolving || (file && file.size > 10 * 1024 * 1024)}
                className="flex-1 flex items-center justify-center gap-2 bg-secondary-100 text-secondary-700 px-4 py-2 rounded-lg hover:bg-secondary-200 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAnyValidatePending ? (
                  <>
                    <div className="w-4 h-4 border-2 border-secondary-600 border-t-transparent rounded-full animate-spin" />
                    Validating...
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4" />
                    Validate File
                  </>
                )}
              </button>

              <button
                onClick={handleUpload}
                disabled={!file || !hasSuccessfulValidation || isAnyUploadPending || isAnyValidatePending || isResolving || (file && file.size > 10 * 1024 * 1024)}
                className="flex-1 flex items-center justify-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAnyUploadPending || isResolving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    {isResolving ? 'Resolving...' : 'Uploading...'}
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Upload & Import
                  </>
                )}
              </button>
            </div>

            <p className="text-xs text-secondary-500 text-center mt-3">
              Tip: Upload is enabled only after a successful validation
            </p>
          </div>
        </div>

        {activeProblem === 'assessments' && normalizedChecks.assessment_validation && (
          <MissingAssessmentsModal
            isOpen={true}
            missingAssessments={normalizedChecks.assessment_validation.missing_assessments || []}
            availableInDatabase={normalizedChecks.assessment_validation.available_in_database || []}
            onClose={() => setActiveProblem(null)}
            onResolve={(choice, assessmentNames) => {
              handleResolve({
                skip_missing_assessments: choice === 'skip',
                create_assessments: choice === 'create' ? assessmentNames : []
              })
            }}
          />
        )}

        {activeProblem === 'students' && (
          <MissingStudentsModal
            isOpen={true}
            missingStudents={normalizedChecks.student_validation?.missing_from_database || []}
            onClose={() => setActiveProblem(null)}
            onResolve={(choice, students) => {
              handleResolve({
                skip_missing_students: choice === 'skip',
                create_students: choice === 'create' ? students : []
              })
            }}
          />
        )}

        {activeProblem === 'unenrolled' && (
          <UnenrolledStudentsModal
            isOpen={true}
            unenrolledStudents={normalizedChecks.student_validation?.not_enrolled || []}
            onClose={() => setActiveProblem(null)}
            onResolve={(choice, studentIds) => {
              handleResolve({
                skip_unenrolled_students: choice === 'skip',
                enroll_students: choice === 'enroll' ? studentIds : []
              })
            }}
          />
        )}

        {activeProblem === 'scores' && (
          <InvalidScoresModal
            isOpen={true}
            invalidScores={normalizedChecks.score_validation?.invalid_scores || []}
            onClose={() => setActiveProblem(null)}
            onResolve={(choice) => {
              handleResolve({
                skip_invalid_scores: choice === 'skip',
                clamp_scores: choice === 'clamp'
              })
            }}
          />
        )}
      </div>
    </div>
  )
}

export default FileUploadModal
