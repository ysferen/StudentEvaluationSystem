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
  onError?: (error: string) => void
}

const FileUploadModal: React.FC<FileUploadModalProps> = ({
  course,
  courseCode,
  termId,
  isOpen,
  onClose,
  type,
  onUploadComplete,
  onError
}) => {
  const [file, setFile] = useState<File | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
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

  // Create mutations for assignment scores (already existed)
  const validationMutation = useCoreFileImportAssignmentScoresValidateCreate({
    request: {
      params: {
        course_code: courseCode,
        term_id: termId
      },
      data: file ? { file } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' }
    },
    mutation: {
      onSuccess: (data) => {
        setValidationResult(toValidationResult(data, true))
      },
      onError: (error) => {
        const errorData = getErrorData(error)
        if (errorData) {
          setValidationResult(toValidationResult(errorData, false))
        } else {
          onError?.(getErrorMessage(error, 'Validation failed'))
        }
      }
    }
  })

  const uploadMutation = useCoreFileImportAssignmentScoresUploadCreate({
    request: {
      params: {
        course_code: courseCode,
        term_id: termId
      }
    },
    mutation: {
      onSuccess: (data) => {
        onUploadComplete?.(data)
        onClose()
      },
      onError: (error) => {
        const errorData = getErrorData(error)
        if (errorData?.errors) {
          setValidationResult(toValidationResult(errorData, false))
        } else {
          onError?.(getErrorMessage(error, 'Upload failed'))
        }
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
      setValidationResult(null) // Reset validation when new file selected
    }
  }

  const handleValidate = async () => {
    if (!file) {
      onError?.('Please select a file first')
      return
    }

    // Clear previous validation result
    setValidationResult(null)

    switch (type) {
      case 'assignment_scores':
        validationMutation.mutate()
        break
      case 'learning_outcomes':
        try {
          const result = await loValidateMutation.mutateAsync()
          setValidationResult(toValidationResult(result, true))
        } catch (error) {
          const errorData = getErrorData(error)
          if (errorData) {
            setValidationResult(toValidationResult(errorData, false))
          } else {
            onError?.(getErrorMessage(error, 'Validation failed'))
          }
        }
        break
      case 'program_outcomes':
        try {
          const result = await poValidateMutation.mutateAsync()
          setValidationResult(toValidationResult(result, true))
        } catch (error) {
          const errorData = getErrorData(error)
          if (errorData) {
            setValidationResult(toValidationResult(errorData, false))
          } else {
            onError?.(getErrorMessage(error, 'Validation failed'))
          }
        }
        break
      default:
        onError?.('Unknown import type')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      onError?.('Please select a file first')
      return
    }

    switch (type) {
      case 'assignment_scores':
        uploadMutation.mutate({ data: { file } })
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
            onError?.(getErrorMessage(error, 'Upload failed'))
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
            onError?.(getErrorMessage(error, 'Upload failed'))
          }
        }
        break
      default:
        onError?.('Unknown import type')
    }
  }

  const handleModalClose = () => {
    onClose()
  }

  const renderValidationResult = () => {
    if (!validationResult) return null

    const { is_valid, errors, warnings, suggestions, validation_details } = validationResult

    return (
      <div className={`mt-4 p-4 rounded-lg ${is_valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
        <div className="flex items-center mb-3">
          {is_valid ? (
            <>
              <svg className="w-5 h-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold text-green-700">Validation Passed</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold text-red-700">Validation Failed</span>
            </>
          )}
        </div>

        {/* Errors */}
        {errors && errors.length > 0 && (
          <div className="mb-3">
            <h4 className="text-sm font-semibold text-red-700 mb-1">Errors:</h4>
            <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
              {errors.map((error, idx) => (
                <li key={idx}>{error.message}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Warnings */}
        {warnings && warnings.length > 0 && (
          <div className="mb-3">
            <h4 className="text-sm font-semibold text-yellow-700 mb-1">Warnings:</h4>
            <ul className="list-disc list-inside text-sm text-yellow-600 space-y-1">
              {warnings.map((warning, idx) => (
                <li key={idx}>{warning.message}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Suggestions */}
        {suggestions && suggestions.length > 0 && (
          <div className="mb-3">
            <h4 className="text-sm font-semibold text-blue-700 mb-1">Suggestions:</h4>
            <ul className="list-disc list-inside text-sm text-blue-600 space-y-1">
              {suggestions.map((suggestion, idx) => (
                <li key={idx}>{suggestion.message}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Validation Details */}
        {validation_details && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Details:</h4>

            {/* File Info */}
            {validation_details.file_info && (
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-medium">File:</span> {validation_details.file_info.name} ({validation_details.file_info.size_mb} MB)
              </div>
            )}

            {/* Row Count */}
            {validation_details.row_count !== undefined && (
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-medium">Rows in file:</span> {validation_details.row_count}
              </div>
            )}

            {/* Assessment Validation */}
            {validation_details.assessment_validation && (
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-medium">Assessments found:</span> {validation_details.assessment_validation.found_assessments?.length || 0} / {validation_details.assessment_validation.total_columns_found || 0}
                {validation_details.assessment_validation.found_assessments && validation_details.assessment_validation.found_assessments.length > 0 && (
                  <ul className="mt-1 ml-4 list-disc text-green-600">
                    {validation_details.assessment_validation.found_assessments.map((a, idx) => (
                      <li key={idx}>{a.parsed_name} → {a.db_assessment}</li>
                    ))}
                  </ul>
                )}
                {validation_details.assessment_validation.missing_assessments && validation_details.assessment_validation.missing_assessments.length > 0 && (
                  <ul className="mt-1 ml-4 list-disc text-red-600">
                    {validation_details.assessment_validation.missing_assessments.map((a, idx) => (
                      <li key={idx}>{a.parsed_name} (not found)</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Student Validation */}
            {validation_details.student_validation && (
              <div className="text-sm text-gray-600 mb-2">
                <span className="font-medium">Students:</span> {validation_details.student_validation.found_in_database} found / {validation_details.student_validation.total_in_file} in file
                {validation_details.student_validation.missing_from_database > 0 && (
                  <span className="text-red-600"> ({validation_details.student_validation.missing_from_database} missing)</span>
                )}
              </div>
            )}

            {/* Missing Students */}
            {validation_details.missing_students && validation_details.missing_students.length > 0 && (
              <div className="text-sm text-red-600 mt-2">
                <span className="font-medium">Missing student IDs:</span> {validation_details.missing_students.slice(0, 10).join(', ')}
                {validation_details.missing_students.length > 10 && ` and ${validation_details.missing_students.length - 10} more...`}
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`fixed inset-0 z-50 overflow-auto bg-black bg-opacity-50 flex items-center justify-center p-4 ${isOpen ? '' : 'hidden'}`}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl relative">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Import {getTypeDisplayName(type)} - {course}</h2>
          <button
            onClick={handleModalClose}
            disabled={uploadMutation.isPending || validationMutation.isPending}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 max-h-[70vh] overflow-y-auto">
          {/* Upload Info for Assignment Scores */}
          {type === 'assignment_scores' && (
            <div className="mb-4 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold mb-2 text-blue-800">Expected Format:</h3>
              <p className="text-sm text-blue-700 mb-2">
                Excel format with columns like:
              </p>
              <ul className="text-sm text-blue-600 space-y-1 ml-4 list-disc">
                <li><code className="bg-blue-100 px-1 rounded">Öğrenci No_XXXXX</code> - Student ID</li>
                <li><code className="bg-blue-100 px-1 rounded">Adı_XXXXX</code> - First Name</li>
                <li><code className="bg-blue-100 px-1 rounded">Soyadı_XXXXX</code> - Last Name</li>
                <li><code className="bg-blue-100 px-1 rounded">Midterm 1(%XX)_XXXXX</code> - Assessment</li>
                <li><code className="bg-blue-100 px-1 rounded">Project(%XX)_XXXXX</code> - Assessment</li>
              </ul>
              <p className="text-sm text-blue-600 mt-1">
                <strong>Max file size:</strong> 10 MB
              </p>
            </div>
          )}

          {uploadInfo && type !== 'assignment_scores' && (
            <div className="mb-4 p-4 bg-blue-50 rounded">
              <h3 className="font-semibold mb-2">Expected Columns:</h3>
              <ul className="text-sm space-y-1">
                {uploadInfo.expected_columns?.map((column: string, index: number) => (
                  <li key={index}>• {column}</li>
                ))}
              </ul>
              {uploadInfo.description && (
                <p className="text-sm mt-2 text-gray-600">{uploadInfo.description}</p>
              )}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select File (.xlsx, .xls)
              </label>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                disabled={isAnyUploadPending || isAnyValidatePending}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
              />
            </div>

            {file && (
              <div className="p-3 bg-gray-50 rounded">
                <p className="text-sm text-gray-600">
                  Selected file: <span className="font-medium">{file.name}</span>
                  ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </p>
                {file.size > 10 * 1024 * 1024 && (
                  <p className="text-sm text-red-600 mt-1">
                    ⚠️ File exceeds 10 MB limit
                  </p>
                )}
              </div>
            )}

            {/* Validation Result */}
            {renderValidationResult()}

            <div className="flex space-x-3">
              <button
                onClick={handleValidate}
                disabled={!file || isAnyValidatePending || (file && file.size > 10 * 1024 * 1024)}
                className="flex-1 bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAnyValidatePending ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Validating...
                  </span>
                ) : 'Validate File'}
              </button>

              <button
                onClick={handleUpload}
                disabled={!file || isAnyUploadPending || isAnyValidatePending || (file && file.size > 10 * 1024 * 1024)}
                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAnyUploadPending ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Uploading...
                  </span>
                ) : 'Upload & Import'}
              </button>
            </div>

            <p className="text-xs text-gray-500 text-center">
              Tip: Click "Validate File" first to check for errors before uploading
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileUploadModal
