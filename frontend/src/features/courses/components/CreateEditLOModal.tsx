import React, { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import Modal from '../../../shared/components/ui/Modal'
import {
  useCoreLearningOutcomesCreate,
  useCoreLearningOutcomesPartialUpdate,
} from '../../../shared/api/generated/outcomes/outcomes'
import { coreCourseTemplatesLearningOutcomesRetrieve } from '../../../shared/api/generated/core/core'
import { useAuth } from '../../auth/hooks/useAuth'

interface CreateEditLOModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  mode: 'create' | 'edit'
  courseId: number
  courseTemplateId: number | null
  /** Only for edit mode */
  existingLo?: {
    id: number
    code: string
    description: string
  } | null
}

type TemplateLearningOutcome = {
  id: number
  code?: string
  description?: string
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const isTemplateLearningOutcome = (value: unknown): value is TemplateLearningOutcome =>
  isRecord(value) && typeof value.id === 'number'

const extractTemplateLearningOutcomes = (value: unknown): TemplateLearningOutcome[] => {
  if (Array.isArray(value)) {
    return value.filter(isTemplateLearningOutcome)
  }
  if (isRecord(value) && Array.isArray(value.results)) {
    return value.results.filter(isTemplateLearningOutcome)
  }
  return []
}

const inputClass = 'block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition'

const CreateEditLOModal: React.FC<CreateEditLOModalProps> = ({
  isOpen, onClose, onSuccess, mode, courseId, courseTemplateId, existingLo,
}) => {
  const { user } = useAuth()
  const canEdit = user?.permissions?.includes('learning_outcomes.change_learningoutcome') ?? false
  const canCreate = user?.permissions?.includes('learning_outcomes.add_learningoutcome') ?? false

  const [flowType, setFlowType] = useState<'blank' | 'template'>('blank')
  const [code, setCode] = useState('')
  const [description, setDescription] = useState('')
  const [templateLoId, setTemplateLoId] = useState<number | ''>('')
  const [error, setError] = useState<string | null>(null)

  // Fetch LO templates from the course template
  const { data: templateLOs } = useQuery({
    queryKey: ['template-los', courseTemplateId],
    queryFn: async () => {
      if (!courseTemplateId) return [] as TemplateLearningOutcome[]
      try {
        const resp = await coreCourseTemplatesLearningOutcomesRetrieve(courseTemplateId)
        return extractTemplateLearningOutcomes(resp)
      } catch {
        return [] as TemplateLearningOutcome[]
      }
    },
    enabled: isOpen && !!courseTemplateId && flowType === 'template',
  })

  // Get the list of templates
  const templateLOItems = useMemo(
    () => templateLOs ?? [],
    [templateLOs]
  )

  // Auto-populate fields when template is selected
  useEffect(() => {
    if (flowType === 'template' && templateLoId !== '' && templateLOItems.length > 0) {
      const tpl = templateLOItems.find((t) => t.id === Number(templateLoId))
      if (tpl) {
        setCode(tpl.code || '')
        setDescription(tpl.description || '')
      }
    }
  }, [flowType, templateLoId, templateLOItems])

  // Pre-fill on edit
  useEffect(() => {
    if (mode === 'edit' && existingLo) {
      setCode(existingLo.code)
      setDescription(existingLo.description)
      setFlowType('blank')
    } else if (mode === 'create') {
      setCode('')
      setDescription('')
      setTemplateLoId('')
      setFlowType(courseTemplateId ? 'blank' : 'blank')
      setError(null)
    }
  }, [mode, existingLo, isOpen, courseTemplateId])

  const createMutation = useCoreLearningOutcomesCreate()
  const updateMutation = useCoreLearningOutcomesPartialUpdate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!code.trim()) {
      setError('LO code is required')
      return
    }
    if (!description.trim()) {
      setError('Description is required')
      return
    }

    try {
      if (mode === 'create') {
        await createMutation.mutateAsync({
          data: {
            code: code.trim(),
            description: description.trim(),
            course_id: courseId,
          } as any,
        })
      } else if (existingLo) {
        await updateMutation.mutateAsync({
          id: existingLo.id,
          data: {
            code: code.trim(),
            description: description.trim(),
          },
        })
      }
      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save learning outcome')
    }
  }

  const handleClose = () => {
    setCode('')
    setDescription('')
    setTemplateLoId('')
    setFlowType('blank')
    setError(null)
    onClose()
  }

  if (mode === 'create' && !canCreate) return null
  if (mode === 'edit' && !canEdit) return null

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={mode === 'create' ? 'Create Learning Outcome' : 'Edit Learning Outcome'} size="md">
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
                <input
                  type="radio"
                  value="template"
                  checked={flowType === 'template'}
                  onChange={() => setFlowType('template')}
                  disabled={!courseTemplateId}
                  className="text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-secondary-700">From Template</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="blank"
                  checked={flowType === 'blank'}
                  onChange={() => setFlowType('blank')}
                  className="text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-secondary-700">Blank</span>
              </label>
            </div>
          </div>
        )}

        {mode === 'create' && flowType === 'template' && (
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">LO Template</label>
            <select
              value={templateLoId}
              onChange={(e) => setTemplateLoId(e.target.value === '' ? '' : Number(e.target.value))}
              className={inputClass}
            >
              <option value="">Select a template...</option>
              {templateLOItems.map((t: any) => (
                <option key={t.id} value={t.id}>{t.code} - {t.description}</option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Code *</label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={mode === 'create' && flowType === 'template'}
            className={`${inputClass} ${(mode === 'create' && flowType === 'template') ? 'bg-secondary-50 cursor-not-allowed' : ''}`}
            placeholder="e.g., LO1"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Description *</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={mode === 'create' && flowType === 'template'}
            className={`${inputClass} ${(mode === 'create' && flowType === 'template') ? 'bg-secondary-50 cursor-not-allowed' : ''}`}
            placeholder="Describe the learning outcome..."
            rows={3}
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={handleClose} className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors">
            Cancel
          </button>
          <button type="submit" disabled={createMutation.isPending || updateMutation.isPending} className="px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50">
            {createMutation.isPending || updateMutation.isPending ? 'Saving...' : mode === 'create' ? 'Create' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default CreateEditLOModal
