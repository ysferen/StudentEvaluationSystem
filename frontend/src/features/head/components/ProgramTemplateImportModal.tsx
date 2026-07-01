import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronDown, FileSpreadsheet, Upload, X } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/shadcn/Dialog'
import { customInstance } from '@/shared/api'

interface TemplateAssessmentPreview {
  name: string
  assessment_type: string
  total_score: number
  weight: number
  action: 'create' | 'update'
}

interface TemplateLearningOutcomePreview {
  code: string
  description: string
  action: 'create' | 'update'
}

interface TemplateCoursePreview {
  code: string
  name: string
  credits: number
  action: 'create' | 'update'
  assessments: TemplateAssessmentPreview[]
  learning_outcomes: TemplateLearningOutcomePreview[]
}

interface ProgramTemplatePreview {
  message?: string
  summary: {
    created: Record<string, number>
    updated: Record<string, number>
  }
  skipped?: Record<string, number>
  errors?: string[]
  courses: TemplateCoursePreview[]
  program_outcomes: Array<{ code: string; description: string; action: 'create' | 'update' }>
}

interface ProgramTemplateImportModalProps {
  isOpen: boolean
  onClose: () => void
  programId?: number
  onImported?: () => void
}

const postProgramTemplateFile = async (
  path: 'upload' | 'confirm',
  file: File,
  programId: number,
): Promise<ProgramTemplatePreview> => {
  const formData = new FormData()
  formData.append('file', file)

  return customInstance<ProgramTemplatePreview>({
    url: `/api/core/file-import/program-templates/${path}/`,
    method: 'POST',
    params: { program_id: programId },
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

const getErrorMessage = (error: unknown): string => {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { error?: unknown } } }).response
    const errorValue = response?.data?.error
    if (typeof errorValue === 'string') return errorValue
    if (errorValue && typeof errorValue === 'object') return Object.values(errorValue).join(', ')
  }
  return error instanceof Error ? error.message : 'Template import failed.'
}

const ActionPill = ({ action }: { action: 'create' | 'update' }) => (
  <span
    className={
      action === 'create'
        ? 'rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700'
        : 'rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700'
    }
  >
    {action}
  </span>
)

export const ProgramTemplateImportModal = ({ isOpen, onClose, programId, onImported }: ProgramTemplateImportModalProps) => {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ProgramTemplatePreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [importComplete, setImportComplete] = useState(false)

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile || !programId) throw new Error('Select a file before previewing.')
      return postProgramTemplateFile('upload', selectedFile, programId)
    },
    onSuccess: (result) => {
      setPreview(result)
      setImportComplete(false)
      setError(null)
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile || !programId) throw new Error('Select a file before confirming.')
      return postProgramTemplateFile('confirm', selectedFile, programId)
    },
    onSuccess: () => {
      setImportComplete(true)
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['coreCourseTemplatesList'] })
      queryClient.invalidateQueries({ queryKey: ['head-courses'] })
      onImported?.()
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const resetAndClose = () => {
    setSelectedFile(null)
    setPreview(null)
    setError(null)
    setImportComplete(false)
    onClose()
  }

  const isBusy = previewMutation.isPending || confirmMutation.isPending
  const canPreview = Boolean(selectedFile && programId && !isBusy)
  const canConfirm = Boolean(preview && selectedFile && programId && !isBusy && !importComplete)

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) resetAndClose() }}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto" showCloseButton={false}>
        <DialogHeader className="flex-row items-center justify-between border-b border-secondary-200 pb-4">
          <DialogTitle className="text-xl font-bold text-secondary-900">Import Program Templates</DialogTitle>
          <button onClick={resetAndClose} className="text-secondary-400 hover:text-secondary-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </DialogHeader>

        <div className="space-y-5">
          <div className="flex flex-col gap-3 rounded-lg border border-secondary-200 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <FileSpreadsheet className="h-5 w-5 flex-shrink-0 text-emerald-700" />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-secondary-900">
                  {selectedFile?.name ?? 'No file selected'}
                </p>
                <p className="text-xs text-secondary-500">Preview parses the file without creating templates.</p>
              </div>
            </div>
            <div className="flex gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xls,.xlsx"
                className="hidden"
                onChange={(event) => {
                  setSelectedFile(event.target.files?.[0] ?? null)
                  setPreview(null)
                  setImportComplete(false)
                  setError(null)
                }}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-lg border border-secondary-300 px-3 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
              >
                <Upload className="h-4 w-4" />
                Choose File
              </button>
              <button
                type="button"
                disabled={!canPreview}
                onClick={() => previewMutation.mutate()}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-3 py-2 text-sm font-semibold text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Preview
              </button>
            </div>
          </div>

          {!programId && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              Program context is not available yet.
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-danger-200 bg-danger-50 p-3 text-sm text-danger-900">
              {error}
            </div>
          )}

          {preview && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-secondary-200 p-3">
                  <p className="text-xs text-secondary-500">Courses</p>
                  <p className="text-lg font-semibold text-secondary-900">{preview.courses.length}</p>
                </div>
                <div className="rounded-lg border border-secondary-200 p-3">
                  <p className="text-xs text-secondary-500">Assessments</p>
                  <p className="text-lg font-semibold text-secondary-900">
                    {preview.courses.reduce((sum, course) => sum + course.assessments.length, 0)}
                  </p>
                </div>
                <div className="rounded-lg border border-secondary-200 p-3">
                  <p className="text-xs text-secondary-500">LOs</p>
                  <p className="text-lg font-semibold text-secondary-900">
                    {preview.courses.reduce((sum, course) => sum + course.learning_outcomes.length, 0)}
                  </p>
                </div>
                <div className="rounded-lg border border-secondary-200 p-3">
                  <p className="text-xs text-secondary-500">POs</p>
                  <p className="text-lg font-semibold text-secondary-900">{preview.program_outcomes.length}</p>
                </div>
              </div>

              <div className="space-y-2">
                {preview.courses.map((course) => (
                  <details key={course.code} className="group rounded-lg border border-secondary-200">
                    <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3">
                      <ChevronDown className="h-4 w-4 text-secondary-500 transition group-open:rotate-180" />
                      <span className="font-semibold text-secondary-900">{course.code}</span>
                      <span className="min-w-0 flex-1 truncate text-sm text-secondary-600">{course.name}</span>
                      <ActionPill action={course.action} />
                    </summary>
                    <div className="grid gap-4 border-t border-secondary-100 p-4 md:grid-cols-2">
                      <div>
                        <p className="mb-2 text-sm font-semibold text-secondary-800">Assessments</p>
                        <div className="space-y-2">
                          {course.assessments.map((assessment) => (
                            <div key={assessment.name} className="rounded-md bg-secondary-50 px-3 py-2 text-sm">
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-medium text-secondary-900">{assessment.name}</span>
                                <ActionPill action={assessment.action} />
                              </div>
                              <p className="text-xs text-secondary-500">
                                {assessment.assessment_type} · {(assessment.weight * 100).toFixed(1)}%
                              </p>
                            </div>
                          ))}
                          {course.assessments.length === 0 && (
                            <p className="text-sm text-secondary-400">No assessments in this file.</p>
                          )}
                        </div>
                      </div>
                      <div>
                        <p className="mb-2 text-sm font-semibold text-secondary-800">Learning Outcomes</p>
                        <div className="space-y-2">
                          {course.learning_outcomes.map((outcome) => (
                            <div key={outcome.code} className="rounded-md bg-secondary-50 px-3 py-2 text-sm">
                              <div className="mb-1 flex items-center justify-between gap-2">
                                <span className="font-medium text-secondary-900">{outcome.code}</span>
                                <ActionPill action={outcome.action} />
                              </div>
                              <p className="text-secondary-600">{outcome.description}</p>
                            </div>
                          ))}
                          {course.learning_outcomes.length === 0 && (
                            <p className="text-sm text-secondary-400">No learning outcomes in this file.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </details>
                ))}
              </div>

              {preview.errors && preview.errors.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <p className="mb-2 text-sm font-semibold text-amber-900">Rows needing attention</p>
                  <ul className="space-y-1 text-sm text-amber-900">
                    {preview.errors.slice(0, 8).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {importComplete && (
                <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-medium text-emerald-800">
                  <Check className="h-4 w-4" />
                  Templates were imported.
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <button
            type="button"
            onClick={resetAndClose}
            className="rounded-lg border border-secondary-300 px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50"
          >
            Close
          </button>
          <button
            type="button"
            disabled={!canConfirm}
            onClick={() => confirmMutation.mutate()}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Approve Import
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
