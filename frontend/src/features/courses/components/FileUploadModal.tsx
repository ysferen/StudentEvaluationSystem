import React, { useState, useRef } from 'react'
import {
  useCoreFileImportAssignmentScoresUploadCreate,
  useCoreFileImportAssignmentScoresValidateCreate,
  useCoreFileImportAssignmentScoresUploadRetrieve,
  useCoreFileImportAssignmentScoresResolveCreate,
  useCoreFileImportLearningOutcomesUploadRetrieve,
  useCoreFileImportLearningOutcomesUploadCreate,
  useCoreFileImportLearningOutcomesValidateCreate,
  useCoreFileImportProgramOutcomesUploadRetrieve,
  useCoreFileImportProgramOutcomesUploadCreate,
  useCoreFileImportProgramOutcomesValidateCreate,
} from '../../../shared/api/generated/core/core'
import {
  Upload,
  X,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  FileSpreadsheet,
  Shield,
  Lightbulb,
  ChevronDown,
  ChevronRight
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

interface ValidationResult {
  is_valid: boolean
  phase_reached?: string
  checks?: {
    file_structure?: CheckResult
    column_structure?: CheckResult
    assessment_validation?: {
      passed: boolean
      found_assessments?: Array<{ column: string; parsed_name: string; db_name: string }>
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
}

interface UploadInfoResponse {
  expected_columns?: string[]
  description?: string
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

interface FileUploadModalProps {
  course: string
  courseCode: string
  termId: number
  isOpen: boolean
  type: 'assignment_scores' | 'learning_outcomes' | 'program_outcomes'
  onClose: () => void
  onUploadComplete?: (result: unknown) => void
}

type ActiveProblem = 'assessments' | 'students' | 'unenrolled' | 'scores' | null

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
  const [resolutions, setResolutions] = useState<Record<string, unknown>>({})
  const [expandedChecks, setExpandedChecks] = useState<Set<string>>(new Set())
  const fileInputRef = useRef<HTMLInputElement>(null)

  const uploadInfoQueries = {
    assignment_scores: useCoreFileImportAssignmentScoresUploadRetrieve<UploadInfoResponse>({
      query: { enabled: type === 'assignment_scores' && isOpen }
    }),
    learning_outcomes: useCoreFileImportLearningOutcomesUploadRetrieve<UploadInfoResponse>({
      query: { enabled: type === 'learning_outcomes' && isOpen }
    }),
    program_outcomes: useCoreFileImportProgramOutcomesUploadRetrieve<UploadInfoResponse>({
      query: { enabled: type === 'program_outcomes' && isOpen }
    }),
  }

  const uploadInfo = uploadInfoQueries[type]?.data

  const loValidateMutation = useCoreFileImportLearningOutcomesValidateCreate({
    request: {
      data: file ? { file } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' }
    }
  })
  const loUploadMutation = useCoreFileImportLearningOutcomesUploadCreate()

  const poValidateMutation = useCoreFileImportProgramOutcomesValidateCreate({
    request: {
      data: file ? { file } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' }
    }
  })
  const poUploadMutation = useCoreFileImportProgramOutcomesUploadCreate()

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

  const uploadMutation = useCoreFileImportAssignmentScoresUploadCreate({
    request: {
      params: {
        course_code: courseCode,
        term_id: termId
      }
    }
  })

  const resolveMutation = useCoreFileImportAssignmentScoresResolveCreate({
    request: {
      params: {
        course_code: courseCode,
        term_id: termId
      }
    }
  })

  const isAnyValidatePending = validationMutation.isPending || loValidateMutation.isPending || poValidateMutation.isPending
  const isAnyUploadPending = uploadMutation.isPending || loUploadMutation.isPending || poUploadMutation.isPending
  const isResolving = resolveMutation.isPending

  const getTypeDisplayName = (type: string) => {
    switch (type) {
      case 'assignment_scores':
        return 'Assessment Scores'
      case 'learning_outcomes':
        return 'Learning Outcomes'
      case 'program_outcomes':
        return 'Program Outcomes'
      default:
        return 'File'
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setValidationResult(null)
      setModalError(null)
      setResolutions({})
    }
  }

  const handleResolve = async (newResolutions: Record<string, unknown>) => {
    if (!file) return

    setResolutions(prev => ({ ...prev, ...newResolutions }))
    setActiveProblem(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('resolutions', JSON.stringify({ ...resolutions, ...newResolutions }))

      const result = await resolveMutation.mutateAsync({
        data: { file, resolutions: JSON.stringify({ ...resolutions, ...newResolutions }) } as any,
        params: { course_code: courseCode, term_id: termId }
      } as any)
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
    setResolutions({})

    switch (type) {
      case 'assignment_scores':
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
        break
      case 'learning_outcomes':
        try {
          const result = await loValidateMutation.mutateAsync({ data: { file } } as any)
          setValidationResult(toValidationResult(result, true))
        } catch (error) {
          const errorData = getErrorData(error)
          if (errorData) {
            setValidationResult(toValidationResult(errorData, false))
          } else {
            setModalError(getErrorMessage(error, 'Validation failed'))
          }
        }
        break
      case 'program_outcomes':
        try {
          const result = await poValidateMutation.mutateAsync({ data: { file } } as any)
          setValidationResult(toValidationResult(result, true))
        } catch (error) {
          const errorData = getErrorData(error)
          if (errorData) {
            setValidationResult(toValidationResult(errorData, false))
          } else {
            setModalError(getErrorMessage(error, 'Validation failed'))
          }
        }
        break
      default:
        setModalError('Unknown import type')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setModalError('Please select a file first')
      return
    }

    setModalError(null)

    switch (type) {
      case 'assignment_scores':
        try {
          const result = await uploadMutation.mutateAsync({ data: { file } })
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
        break
      case 'learning_outcomes':
        try {
          const result = await loUploadMutation.mutateAsync({ data: { file } })
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
        break
      case 'program_outcomes':
        try {
          const result = await poUploadMutation.mutateAsync({ data: { file } })
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
        break
      default:
        setModalError('Unknown import type')
    }
  }

  const handleModalClose = () => {
    onClose()
  }

  const toggleCheckExpanded = (checkName: string) => {
    const next = new Set(expandedChecks)
    if (next.has(checkName)) {
      next.delete(checkName)
    } else {
      next.add(checkName)
    }
    setExpandedChecks(next)
  }

  const renderCheckRow = (checkName: string, check: CheckResult | undefined, extra?: React.ReactNode) => {
    if (!check) return null
    const passed = check.passed
    const isExpanded = expandedChecks.has(checkName)

    return (
      <div key={checkName} className="border border-secondary-200 rounded-lg overflow-hidden">
        <div
          className={`flex items-center justify-between p-3 ${passed ? 'bg-emerald-50' : 'bg-danger-50'}`}
        >
          <div className="flex items-center gap-3">
            {passed ? (
              <CheckCircle className="w-5 h-5 text-emerald-500" />
            ) : (
              <XCircle className="w-5 h-5 text-danger-500" />
            )}
            <span className="font-medium text-sm text-secondary-900 capitalize">
              {checkName.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {!passed && (
              <button
                onClick={() => {
                  if (checkName === 'assessment validation') setActiveProblem('assessments')
                  else if (checkName === 'student validation') setActiveProblem('students')
                  else if (checkName === 'score validation') setActiveProblem('scores')
                }}
                className="text-sm bg-warning-100 text-warning-700 px-3 py-1 rounded-md hover:bg-warning-200 font-medium transition-colors"
              >
                Solve
              </button>
            )}
            {extra && (
              <button
                onClick={() => toggleCheckExpanded(checkName)}
                className="text-secondary-400 hover:text-secondary-600"
              >
                {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>
        {isExpanded && extra && (
          <div className="p-3 bg-white border-t border-secondary-200">
            {extra}
          </div>
        )}
      </div>
    )
  }

  const renderValidationResult = () => {
    if (!validationResult) return null

    const { is_valid, checks, errors, warnings, suggestions } = validationResult

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

        {validationResult.phase_reached && (
          <p className="text-xs text-secondary-500 mb-3">
            Phase reached: <span className="font-medium">{validationResult.phase_reached.replace(/_/g, ' ')}</span>
          </p>
        )}

        {checks && (
          <div className="space-y-2 mb-4">
            {renderCheckRow('file structure', checks.file_structure)}
            {renderCheckRow('column structure', checks.column_structure)}
            {renderCheckRow(
              'assessment validation',
              checks.assessment_validation,
              checks.assessment_validation && !checks.assessment_validation.passed && (
                <div className="space-y-1">
                  {checks.assessment_validation.missing_assessments?.map((a, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      <XCircle className="w-3 h-3 text-danger-500" />
                      <span className="text-danger-600">{a.parsed_name}</span>
                      <span className="text-secondary-400">({a.column})</span>
                    </div>
                  ))}
                </div>
              )
            )}
            {renderCheckRow(
              'student validation',
              checks.student_validation,
              checks.student_validation && !checks.student_validation.passed && (
                <div className="space-y-2">
                  {checks.student_validation.missing_from_database && checks.student_validation.missing_from_database.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-danger-600 mb-1">
                        Missing from database ({checks.student_validation.missing_from_database.length}):
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {checks.student_validation.missing_from_database.slice(0, 5).map((s, idx) => (
                          <span key={idx} className="text-xs bg-danger-100 text-danger-700 px-2 py-0.5 rounded">
                            {s.student_id}
                          </span>
                        ))}
                        {(checks.student_validation.missing_from_database.length ?? 0) > 5 && (
                          <span className="text-xs text-secondary-500">
                            +{(checks.student_validation.missing_from_database.length ?? 0) - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  {checks.student_validation.not_enrolled && checks.student_validation.not_enrolled.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-warning-600 mb-1">
                        Not enrolled ({checks.student_validation.not_enrolled.length}):
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {checks.student_validation.not_enrolled.slice(0, 5).map((s, idx) => (
                          <span key={idx} className="text-xs bg-warning-100 text-warning-700 px-2 py-0.5 rounded">
                            {s.student_id}
                          </span>
                        ))}
                        {(checks.student_validation.not_enrolled.length ?? 0) > 5 && (
                          <span className="text-xs text-secondary-500">
                            +{(checks.student_validation.not_enrolled.length ?? 0) - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            )}
            {checks.student_validation && !checks.student_validation.passed && (
              <button
                onClick={() => {
                  const hasMissing = (checks.student_validation?.missing_from_database?.length ?? 0) > 0
                  const hasUnenrolled = (checks.student_validation?.not_enrolled?.length ?? 0) > 0
                  if (hasMissing) setActiveProblem('students')
                  else if (hasUnenrolled) setActiveProblem('unenrolled')
                }}
                className="text-sm bg-warning-100 text-warning-700 px-3 py-1 rounded-md hover:bg-warning-200 font-medium transition-colors"
              >
                Solve
              </button>
            )}
            {renderCheckRow(
              'score validation',
              checks.score_validation,
              checks.score_validation && !checks.score_validation.passed && checks.score_validation.invalid_scores && (
                <div>
                  <p className="text-xs text-danger-600 mb-1">
                    Invalid scores ({checks.score_validation.invalid_scores.length}):
                  </p>
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {checks.score_validation.invalid_scores.slice(0, 10).map((s, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <span className="text-secondary-500">Row {s.row}:</span>
                        <span className="text-secondary-700 truncate max-w-[150px]">{s.column}</span>
                        <span className="font-mono text-danger-600">={s.value}</span>
                        <span className="text-danger-400">({s.error})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            )}
          </div>
        )}

        {errors && errors.length > 0 && (
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-1">
              <XCircle className="w-4 h-4 text-danger-500" />
              <h4 className="text-sm font-semibold text-danger-800">Errors:</h4>
            </div>
            <ul className="list-disc list-inside text-sm text-danger-600 space-y-1 ml-6">
              {errors.map((error, idx) => {
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

        {Object.keys(resolutions).length > 0 && (
          <div className="mt-3 pt-3 border-t border-secondary-200">
            <p className="text-xs text-secondary-500">
              {Object.keys(resolutions).length} resolution(s) applied
            </p>
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

  return (
    <div className={`fixed inset-0 z-50 overflow-auto bg-secondary-900/50 backdrop-blur-sm flex items-center justify-center p-4 ${isOpen ? '' : 'hidden'}`}>
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

          {uploadInfo && type !== 'assignment_scores' && (
            <div className="mb-4 p-4 bg-primary-50 border border-primary-200 rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <FileSpreadsheet className="w-4 h-4 text-primary-600" />
                <h3 className="font-semibold text-primary-800">Expected Columns:</h3>
              </div>
              <ul className="text-sm text-primary-700 space-y-1 ml-4 list-disc">
                {uploadInfo.expected_columns?.map((column: string, index: number) => (
                  <li key={index}>• {column}</li>
                ))}
              </ul>
              {uploadInfo.description && (
                <p className="text-sm mt-2 text-primary-700">{uploadInfo.description}</p>
              )}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-2">
                Select File (.xlsx, .xls)
              </label>
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-secondary-300 rounded-xl p-8 text-center hover:border-primary-500 transition-colors cursor-pointer"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileChange}
                  disabled={isAnyUploadPending || isAnyValidatePending || isResolving}
                  className="hidden"
                />
                <Upload className="w-8 h-8 text-secondary-400 mx-auto mb-2" />
                <p className="text-sm text-secondary-600">
                  {file ? file.name : 'Click to select or drag and drop your file'}
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
                disabled={!file || isAnyUploadPending || isAnyValidatePending || isResolving || (file && file.size > 10 * 1024 * 1024)}
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
              Tip: Click "Validate File" first to check for errors before uploading
            </p>
          </div>
        </div>

        {activeProblem === 'assessments' && validationResult?.checks?.assessment_validation && (
          <MissingAssessmentsModal
            isOpen={true}
            missingAssessments={validationResult.checks.assessment_validation.missing_assessments || []}
            availableInDatabase={validationResult.checks.assessment_validation.available_in_database || []}
            onClose={() => setActiveProblem(null)}
            onResolve={(choice, assessmentNames) => {
              handleResolve({
                skip_missing_assessments: choice === 'skip',
                create_assessments: choice === 'create' ? assessmentNames : []
              })
            }}
          />
        )}

        {activeProblem === 'students' && validationResult?.checks?.student_validation?.missing_from_database && (
          <MissingStudentsModal
            isOpen={true}
            missingStudents={validationResult.checks.student_validation.missing_from_database || []}
            onClose={() => setActiveProblem(null)}
            onResolve={(choice, students) => {
              handleResolve({
                skip_missing_students: choice === 'skip',
                create_students: choice === 'create' ? students : []
              })
            }}
          />
        )}

        {activeProblem === 'unenrolled' && validationResult?.checks?.student_validation?.not_enrolled && (
          <UnenrolledStudentsModal
            isOpen={true}
            unenrolledStudents={validationResult.checks.student_validation.not_enrolled || []}
            onClose={() => setActiveProblem(null)}
            onResolve={(choice, studentIds) => {
              handleResolve({
                skip_unenrolled_students: choice === 'skip',
                enroll_students: choice === 'enroll' ? studentIds : []
              })
            }}
          />
        )}

        {activeProblem === 'scores' && validationResult?.checks?.score_validation?.invalid_scores && (
          <InvalidScoresModal
            isOpen={true}
            invalidScores={validationResult.checks.score_validation.invalid_scores || []}
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
