import React, { useState, useRef } from 'react'
import {
  useCoreFileImportAssignmentScoresUploadCreate,
  useCoreFileImportAssignmentScoresValidateCreate,
  useCoreFileImportAssignmentScoresUploadRetrieve,
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
  Lightbulb
} from 'lucide-react'

// Validation result types
interface ValidationError {
  message: string
  category: string
  severity: string
}

interface ValidationDetails {
  file_info?: {
    name: string
    size: number
    size_mb: number
    extension: string
  }
  available_sheets?: string[]
  assessment_validation?: {
    total_columns_found: number
    found_assessments: Array<{
      column: string
      parsed_name: string
      db_assessment: string
    }>
    missing_assessments: Array<{
      column: string
      parsed_name: string
    }>
    available_in_database: string[]
  }
  student_validation?: {
    total_in_file: number
    found_in_database: number
    missing_from_database: number
    student_id_column: string
  }
  row_count?: number
  columns?: string[]
  missing_students?: string[]
}

interface ValidationResult {
  is_valid: boolean
  errors?: ValidationError[]
  warnings?: ValidationError[]
  suggestions?: ValidationError[]
  validation_details?: ValidationDetails
  course_info?: {
    code: string
    name: string
    term: string
  }
  file_info?: {
    name: string
    size: number
    format: string
  }
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
    errors: Array.isArray(value.errors) ? value.errors as ValidationError[] : undefined,
    warnings: Array.isArray(value.warnings) ? value.warnings as ValidationError[] : undefined,
    suggestions: Array.isArray(value.suggestions) ? value.suggestions as ValidationError[] : undefined,
    validation_details: isRecord(value.validation_details) ? value.validation_details as ValidationDetails : undefined,
    course_info: isRecord(value.course_info) ? value.course_info as ValidationResult['course_info'] : undefined,
    file_info: isRecord(value.file_info) ? value.file_info as ValidationResult['file_info'] : undefined,
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
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Upload info queries
  const { data: assignmentUploadInfo } = useCoreFileImportAssignmentScoresUploadRetrieve<UploadInfoResponse>({
    query: { enabled: type === 'assignment_scores' && isOpen }
  })
  const { data: loUploadInfo } = useCoreFileImportLearningOutcomesUploadRetrieve<UploadInfoResponse>({
    query: { enabled: type === 'learning_outcomes' && isOpen }
  })
  const { data: poUploadInfo } = useCoreFileImportProgramOutcomesUploadRetrieve<UploadInfoResponse>({
    query: { enabled: type === 'program_outcomes' && isOpen }
  })

  const uploadInfo = type === 'assignment_scores' ? assignmentUploadInfo
    : type === 'learning_outcomes' ? loUploadInfo
    : poUploadInfo

  // LO mutation hooks
  const loValidateMutation = useCoreFileImportLearningOutcomesValidateCreate({
    request: {
      data: file ? { file } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' }
    }
  })
  const loUploadMutation = useCoreFileImportLearningOutcomesUploadCreate()

  // PO mutation hooks
  const poValidateMutation = useCoreFileImportProgramOutcomesValidateCreate({
    request: {
      data: file ? { file } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' }
    }
  })
  const poUploadMutation = useCoreFileImportProgramOutcomesUploadCreate()

  // Assignment scores mutations
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

  // Computed loading states for the various mutation types
  const isAnyValidatePending = validationMutation.isPending || loValidateMutation.isPending || poValidateMutation.isPending
  const isAnyUploadPending = uploadMutation.isPending || loUploadMutation.isPending || poUploadMutation.isPending

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
    }
  }

  const handleValidate = async () => {
    if (!file) {
      setModalError('Please select a file first')
      return
    }

    setValidationResult(null)
    setModalError(null)

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

  const renderValidationResult = () => {
    if (!validationResult) return null

    const { is_valid, errors, warnings, suggestions, validation_details } = validationResult

    return (
      <div className={`mt-4 p-4 rounded-xl ${is_valid ? 'bg-emerald-50 border border-emerald-200' : 'bg-danger-50 border border-danger-200'}`}>
        <div className="flex items-center mb-3">
          {is_valid ? (
            <>
              <CheckCircle className="w-5 h-5 text-emerald-500 mr-2" />
              <span className="font-semibold text-emerald-800">Validation Passed</span>
            </>
          ) : (
            <>
              <XCircle className="w-5 h-5 text-danger-500 mr-2" />
              <span className="font-semibold text-danger-800">Validation Failed</span>
            </>
          )}
        </div>

        {/* Errors */}
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

        {/* Warnings */}
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

        {/* Suggestions */}
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

        {/* Validation Details */}
        {validation_details && (
          <div className="border-t border-secondary-200 mt-3 pt-3">
            <div className="flex items-center gap-2 mb-2">
              <Info className="w-4 h-4 text-secondary-500" />
              <h4 className="text-sm font-semibold text-secondary-700">Details:</h4>
            </div>

            {/* File Info */}
            {validation_details.file_info && (
              <div className="bg-white shadow-sm border border-secondary-200 rounded-lg p-3 mb-2">
                <div className="flex items-center gap-2 text-sm text-secondary-600">
                  <FileSpreadsheet className="w-4 h-4 text-secondary-400" />
                  <span className="font-medium">{validation_details.file_info.name}</span>
                  <span className="text-secondary-500">({validation_details.file_info.size_mb} MB)</span>
                </div>
              </div>
            )}

            {/* Row Count */}
            {validation_details.row_count !== undefined && (
              <div className="text-sm text-secondary-600 mb-2">
                <span className="font-medium">Rows in file:</span> {validation_details.row_count}
              </div>
            )}

            {/* Assessment Validation */}
            {validation_details.assessment_validation && (
              <div className="bg-white shadow-sm border border-secondary-200 rounded-lg p-3 mb-2">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span className="text-sm font-semibold text-secondary-700">Assessments found:</span>
                  <span className="text-sm text-secondary-600">
                    {validation_details.assessment_validation.found_assessments?.length || 0} / {validation_details.assessment_validation.total_columns_found || 0}
                  </span>
                </div>
                {validation_details.assessment_validation.found_assessments && validation_details.assessment_validation.found_assessments.length > 0 && (
                  <ul className="mt-1 ml-6 list-disc text-emerald-600 text-sm">
                    {validation_details.assessment_validation.found_assessments.map((a, idx) => (
                      <li key={idx}>{a.parsed_name} → {a.db_assessment}</li>
                    ))}
                  </ul>
                )}
                {validation_details.assessment_validation.missing_assessments && validation_details.assessment_validation.missing_assessments.length > 0 && (
                  <ul className="mt-1 ml-6 list-disc text-danger-600 text-sm">
                    {validation_details.assessment_validation.missing_assessments.map((a, idx) => (
                      <li key={idx}>{a.parsed_name} (not found)</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Student Validation */}
            {validation_details.student_validation && (
              <div className="bg-white shadow-sm border border-secondary-200 rounded-lg p-3 mb-2">
                <div className="flex items-center gap-2 mb-1">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span className="text-sm font-semibold text-secondary-700">Students:</span>
                  <span className="text-sm text-secondary-600">
                    {validation_details.student_validation.found_in_database} found / {validation_details.student_validation.total_in_file} in file
                  </span>
                </div>
                {validation_details.student_validation.missing_from_database > 0 && (
                  <div className="flex items-center gap-2 mt-1 ml-6 text-danger-600 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    <span>{validation_details.student_validation.missing_from_database} missing</span>
                  </div>
                )}
              </div>
            )}

            {/* Missing Students */}
            {validation_details.missing_students && validation_details.missing_students.length > 0 && (
              <div className="text-sm text-danger-600 mt-2">
                <span className="font-medium">Missing student IDs:</span> {validation_details.missing_students.slice(0, 10).join(', ')}
                {validation_details.missing_students.length > 10 && ` and ${validation_details.missing_students.length - 10} more...`}
              </div>
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

  return (
    <div className={`fixed inset-0 z-50 overflow-auto bg-secondary-900/50 backdrop-blur-sm flex items-center justify-center p-4 ${isOpen ? '' : 'hidden'}`}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl relative">
        <div className="flex items-center justify-between p-6 border-b border-secondary-200">
          <h2 className="text-xl font-bold text-secondary-900">Import {getTypeDisplayName(type)} - {course}</h2>
          <button
            onClick={handleModalClose}
            disabled={uploadMutation.isPending || validationMutation.isPending}
            className="text-secondary-400 hover:text-secondary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {/* Modal Error Display */}
          {renderModalError()}

          {/* Upload Info for Assignment Scores */}
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
                  disabled={isAnyUploadPending || isAnyValidatePending}
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

            {/* Validation Result */}
            {renderValidationResult()}

            <div className="flex space-x-3">
              <button
                onClick={handleValidate}
                disabled={!file || isAnyValidatePending || (file && file.size > 10 * 1024 * 1024)}
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
                disabled={!file || isAnyUploadPending || isAnyValidatePending || (file && file.size > 10 * 1024 * 1024)}
                className="flex-1 flex items-center justify-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAnyUploadPending ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Uploading...
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
      </div>
    </div>
  )
}

export default FileUploadModal
