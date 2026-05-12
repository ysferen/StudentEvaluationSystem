import React, { useState, useMemo } from 'react'
import { X } from 'lucide-react'
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

  const templates = (templatesData as any)?.results ?? (templatesData as any) ?? []

  // Auto-calculate next semester when modal opens
  useMemo(() => {
    if (activeTerm && isOpen) {
      const nextSem = SEMESTER_CYCLE[activeTerm.semester ?? 'fall'] ?? 'fall'
      setSemester(nextSem)
      const year = nextSem === 'spring' ? (activeTerm.academic_year ?? 2025) : (activeTerm.academic_year ?? 2025) + 1
      setAcademicYear(year)
    }
  }, [activeTerm, isOpen])

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
        } as any,
      })
      setJobId((result as any)?.job_id ?? null)
    } catch (err: any) {
      setError(err?.message ?? 'Failed to start term transition.')
      setSubmitting(false)
    }
  }

  const handleComplete = () => {
    onClose()
    window.location.reload()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-secondary-200">
          <h2 className="text-xl font-bold text-secondary-900">Start New Term</h2>
          <button onClick={onClose} className="text-secondary-400 hover:text-secondary-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
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
              <option value="fall">Fall</option>
              <option value="spring">Spring</option>
              <option value="summer">Summer</option>
            </select>
          </div>

          <div>
            <label htmlFor="academicYear" className="block text-sm font-medium text-secondary-700 mb-2">
              Academic Year
            </label>
            <input
              id="academicYear"
              type="number"
              value={academicYear}
              onChange={(e) => setAcademicYear(Number(e.target.value))}
              min={2000}
              max={2100}
              className="block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition"
            />
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
              {Array.isArray(templates) && templates.map((template: any) => (
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
          <div className="flex items-center justify-end gap-3 p-6 border-t border-secondary-200">
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
          </div>
        )}
      </div>
    </div>
  )
}
