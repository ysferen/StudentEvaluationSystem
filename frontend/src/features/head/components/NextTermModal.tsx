import React, { useState, useMemo } from 'react'
import { X } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/shadcn/Dialog'
import {
  useCoreCourseTemplatesList,
  useCoreTermsActiveRetrieve,
  useCoreTermsNextTermCreate,
} from '@/shared/api/generated/core/core'
import { JobProgressBar } from '@/shared/components/JobProgressBar'

interface NextTermModalProps {
  isOpen: boolean
  onClose: () => void
}

const SEMESTER_CYCLE: Record<string, string> = {
  fall: 'spring',
  spring: 'fall',
  summer: 'fall',
}

export const NextTermModal: React.FC<NextTermModalProps> = ({ isOpen, onClose }) => {
  const { data: activeTerm } = useCoreTermsActiveRetrieve()
  const { data: templatesData } = useCoreCourseTemplatesList()
  const { mutateAsync: nextTermMutate } = useCoreTermsNextTermCreate()

  const [semester, setSemester] = useState('fall')
  const [academicYear, setAcademicYear] = useState(new Date().getFullYear())
  const [selectedTemplates, setSelectedTemplates] = useState<Set<number>>(new Set())
  const [jobId, setJobId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const templates = (templatesData as any)?.results ?? (templatesData as any) ?? []

  useMemo(() => {
    if (activeTerm && isOpen) {
      const nextSem = SEMESTER_CYCLE[activeTerm.semester ?? 'fall'] ?? 'fall'
      setSemester(nextSem)
      const year = nextSem === 'spring' ? (activeTerm.academic_year ?? 2025) : (activeTerm.academic_year ?? 2025) + 1
      setAcademicYear(year)
    }
  }, [activeTerm, isOpen])

  const academicYearRange = useMemo(() => {
    if (semester === 'fall') return `${academicYear}–${academicYear + 1}`
    return `${academicYear - 1}–${academicYear}`
  }, [semester, academicYear])

  const toggleTemplate = (id: number) => {
    setSelectedTemplates((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => {
    if (Array.isArray(templates)) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setSelectedTemplates(new Set(templates.map((t: any) => t.id)))
    }
  }

  const deselectAll = () => {
    setSelectedTemplates(new Set())
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const result = await nextTermMutate({
        data: {
          semester,
          academic_year: academicYear,
          template_ids: Array.from(selectedTemplates),
        },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setJobId((result as any)?.job_id ?? null)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start term transition.'
      setError(message)
      setSubmitting(false)
    }
  }

  const handleComplete = () => {
    onClose()
    window.location.reload()
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto" showCloseButton={false}>
        <DialogHeader className="flex-row items-center justify-between border-b border-secondary-200 pb-4">
          <DialogTitle className="text-xl font-bold text-secondary-900">Start New Term</DialogTitle>
          <button onClick={onClose} className="text-secondary-400 hover:text-secondary-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </DialogHeader>

        <div className="space-y-4">
          {activeTerm && (
            <p className="text-sm text-secondary-500">
              Current active term: <span className="font-medium text-secondary-700">{activeTerm.name}</span>
            </p>
          )}

          <div>
            <label htmlFor="semester" className="block text-sm font-medium text-secondary-700 mb-2">
              Semester
            </label>
            <select
              id="semester"
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
              className="block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition"
              aria-label="Semester"
            >
              <option value="fall">Güz</option>
              <option value="spring">Bahar</option>
              <option value="summer">Yaz</option>
            </select>
          </div>

          <div>
            <label htmlFor="academicYear" className="block text-sm font-medium text-secondary-700 mb-2">
              Academic Year
            </label>
            <div className="flex items-center gap-3">
              <input
                id="academicYear"
                type="number"
                value={academicYear}
                onChange={(e) => setAcademicYear(Number(e.target.value))}
                min={2000}
                max={2100}
                className="w-24 rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition"
              />
              <span className="text-sm text-secondary-500">→ {academicYearRange}</span>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-secondary-700">
                Select Course Templates to Instantiate
              </label>
              <div className="flex gap-2">
                <button type="button" onClick={selectAll} className="text-xs text-primary-600 hover:text-primary-700 font-medium">
                  Select All
                </button>
                <button type="button" onClick={deselectAll} className="text-xs text-secondary-500 hover:text-secondary-600 font-medium">
                  Deselect All
                </button>
              </div>
            </div>
            <div className="border border-secondary-200 rounded-xl divide-y divide-secondary-100 max-h-48 overflow-y-auto">
              {Array.isArray(templates) && templates.map((template: { id: number; code?: string; name?: string; credits?: number }) => (
                <label key={template.id} className="flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-secondary-50">
                  <input
                    type="checkbox"
                    checked={selectedTemplates.has(template.id)}
                    onChange={() => toggleTemplate(template.id)}
                    className="h-4 w-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-secondary-900 font-medium">{template.code}</span>
                  <span className="text-sm text-secondary-500">{template.name}</span>
                  <span className="text-xs text-secondary-400 ml-auto">{template.credits}cr</span>
                </label>
              ))}
              {(!Array.isArray(templates) || templates.length === 0) && (
                <p className="px-4 py-3 text-sm text-secondary-400">No course templates available.</p>
              )}
            </div>
          </div>

          {jobId && (
            <JobProgressBar jobId={jobId} onComplete={handleComplete} label="Creating courses..." />
          )}

          {error && (
            <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
              <p className="text-danger-800 text-sm">{error}</p>
            </div>
          )}
        </div>

        {!jobId && (
          <DialogFooter>
            <button onClick={onClose} disabled={submitting} className="px-4 py-2 text-sm font-medium text-secondary-600 hover:text-secondary-900 transition-colors">
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 text-white text-sm font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Start New Term"
            >
              {submitting ? 'Starting...' : 'Start New Term'}
            </button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
