import React, { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import Modal from '../../../shared/components/ui/Modal'
import {
  useEvaluationAssessmentsCreate,
  useEvaluationAssessmentsPartialUpdate,
} from '../../../shared/api/generated/evaluation/evaluation'
import { coreCourseTemplatesAssessmentsRetrieve } from '../../../shared/api/generated/core/core'
import { useAuth } from '../../auth/hooks/useAuth'
import { AssessmentTypeEnum } from '../../../shared/api/model'

interface CreateEditAssessmentModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  mode: 'create' | 'edit'
  courseId: number
  courseTemplateId: number | null
  existingAssessment?: {
    id: number
    name: string
    assessment_type?: string
    weight?: number
    description?: string
    total_score?: number
  } | null
}

type TemplateAssessment = {
  id: number
  name?: string
  assessment_type?: string
  weight?: number
  description?: string
  total_score?: number
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const isTemplateAssessment = (value: unknown): value is TemplateAssessment =>
  isRecord(value) && typeof value.id === 'number'

const extractTemplateAssessments = (value: unknown): TemplateAssessment[] => {
  if (Array.isArray(value)) {
    return value.filter(isTemplateAssessment)
  }
  if (isRecord(value) && Array.isArray(value.results)) {
    return value.results.filter(isTemplateAssessment)
  }
  return []
}

const inputClass = 'block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition'

const CreateEditAssessmentModal: React.FC<CreateEditAssessmentModalProps> = ({
  isOpen, onClose, onSuccess, mode, courseId, courseTemplateId, existingAssessment,
}) => {
  const { user } = useAuth()
  const canEdit = user?.permissions?.includes('assessments.change_assessment') ?? false
  const canCreate = user?.permissions?.includes('assessments.add_assessment') ?? false

  const [flowType, setFlowType] = useState<'blank' | 'template'>('blank')
  const [name, setName] = useState('')
  const [assessmentType, setAssessmentType] = useState<string>('')
  const [weight, setWeight] = useState<string>('')
  const [description, setDescription] = useState('')
  const [totalScore, setTotalScore] = useState<string>('')
  const [templateAssessmentId, setTemplateAssessmentId] = useState<number | ''>('')
  const [error, setError] = useState<string | null>(null)

  const { data: templateAssessments } = useQuery({
    queryKey: ['template-assessments', courseTemplateId],
    queryFn: async () => {
      if (!courseTemplateId) return [] as TemplateAssessment[]
      try {
        const resp = await coreCourseTemplatesAssessmentsRetrieve(courseTemplateId)
        return extractTemplateAssessments(resp)
      } catch {
        return [] as TemplateAssessment[]
      }
    },
    enabled: isOpen && !!courseTemplateId && flowType === 'template',
  })

  const templateItems = useMemo(
    () => templateAssessments ?? [],
    [templateAssessments]
  )

  useEffect(() => {
    if (flowType === 'template' && templateAssessmentId !== '' && templateItems.length > 0) {
      const tpl = templateItems.find((t) => t.id === Number(templateAssessmentId))
      if (tpl) {
        setName(tpl.name || '')
        setAssessmentType(tpl.assessment_type || '')
        setWeight(tpl.weight != null ? String(tpl.weight) : '')
        setDescription(tpl.description || '')
        setTotalScore(tpl.total_score != null ? String(tpl.total_score) : '')
      }
    }
  }, [flowType, templateAssessmentId, templateItems])

  useEffect(() => {
    if (mode === 'edit' && existingAssessment) {
      setName(existingAssessment.name)
      setAssessmentType(existingAssessment.assessment_type || '')
      setWeight(existingAssessment.weight != null ? String(existingAssessment.weight) : '')
      setDescription(existingAssessment.description || '')
      setTotalScore(existingAssessment.total_score != null ? String(existingAssessment.total_score) : '')
      setFlowType('blank')
    } else if (mode === 'create') {
      setName('')
      setAssessmentType('')
      setWeight('')
      setDescription('')
      setTotalScore('')
      setTemplateAssessmentId('')
      setFlowType('blank')
      setError(null)
    }
  }, [mode, existingAssessment, isOpen])

  const createMutation = useEvaluationAssessmentsCreate()
  const updateMutation = useEvaluationAssessmentsPartialUpdate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Assessment name is required')
      return
    }

    const payload = {
      name: name.trim(),
      course: courseId,
      assessment_type: assessmentType || undefined,
      weight: weight !== '' ? Number(weight) : undefined,
      description: description.trim() || undefined,
      total_score: totalScore !== '' ? Number(totalScore) : undefined,
    }

    try {
      if (mode === 'create') {
        await createMutation.mutateAsync({ data: payload as any })
      } else if (existingAssessment) {
        await updateMutation.mutateAsync({
          id: existingAssessment.id,
          data: {
            ...payload,
            course: undefined,
            assessment_type: assessmentType || undefined,
          } as any,
        })
      }
      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save assessment')
    }
  }

  const handleClose = () => {
    setName('')
    setAssessmentType('')
    setWeight('')
    setDescription('')
    setTotalScore('')
    setTemplateAssessmentId('')
    setFlowType('blank')
    setError(null)
    onClose()
  }

  if (mode === 'create' && !canCreate) return null
  if (mode === 'edit' && !canEdit) return null

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={mode === 'create' ? 'Create Assessment' : 'Edit Assessment'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
            <p className="text-sm text-danger-600">{error}</p>
          </div>
        )}

        {mode === 'create' && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-secondary-700">Create Method</label>
            <div className="flex gap-4">
              <label className={`flex items-center gap-2 cursor-pointer ${!courseTemplateId ? 'opacity-50' : ''}`}>
                <input type="radio" value="template" checked={flowType === 'template'} onChange={() => setFlowType('template')}
                  disabled={!courseTemplateId} className="text-primary-600 focus:ring-primary-500" />
                <span className="text-sm text-secondary-700">From Template</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" value="blank" checked={flowType === 'blank'} onChange={() => setFlowType('blank')}
                  className="text-primary-600 focus:ring-primary-500" />
                <span className="text-sm text-secondary-700">Blank</span>
              </label>
            </div>
          </div>
        )}

        {mode === 'create' && flowType === 'template' && (
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">Assessment Template</label>
            <select value={templateAssessmentId} onChange={(e) => setTemplateAssessmentId(e.target.value === '' ? '' : Number(e.target.value))} className={inputClass}>
              <option value="">Select a template...</option>
              {templateItems.map((t: any) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Name *</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)}
            disabled={mode === 'create' && flowType === 'template'}
            className={`${inputClass} ${(mode === 'create' && flowType === 'template') ? 'bg-secondary-50 cursor-not-allowed' : ''}`}
            placeholder="e.g., Midterm Exam" />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Assessment Type</label>
          <select value={assessmentType} onChange={(e) => setAssessmentType(e.target.value)} className={inputClass}>
            <option value="">Select type...</option>
            {Object.values(AssessmentTypeEnum).map((t) => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">Weight (0-1)</label>
            <input type="number" value={weight} onChange={(e) => setWeight(e.target.value)}
              className={inputClass} placeholder="e.g., 0.3" min={0} max={1} step={0.01} />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">Total Score</label>
            <input type="number" value={totalScore} onChange={(e) => setTotalScore(e.target.value)}
              className={inputClass} placeholder="e.g., 100" min={0} />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)}
            className={inputClass} placeholder="Brief description of this assessment..."
            rows={2} />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={handleClose} className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors">Cancel</button>
          <button type="submit" disabled={createMutation.isPending || updateMutation.isPending} className="px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50">
            {createMutation.isPending || updateMutation.isPending ? 'Saving...' : mode === 'create' ? 'Create' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default CreateEditAssessmentModal
