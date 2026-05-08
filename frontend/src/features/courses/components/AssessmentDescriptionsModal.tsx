import { useState, useEffect } from 'react'
import { useEvaluationAssessmentsBulkDescriptionsCreate } from '../../../shared/api/generated/evaluation/evaluation'
import type { Assessment } from '../../../shared/api/model'

interface AssessmentDescriptionsModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: () => void
  assessments: Assessment[]
}

const PLACEHOLDER_EXAMPLE = 'Vize sınavı: Temel kavramları ve uygulamaları değerlendirir.'

export const AssessmentDescriptionsModal = ({
  isOpen,
  onClose,
  onSubmit,
  assessments,
}: AssessmentDescriptionsModalProps) => {
  const [descriptions, setDescriptions] = useState<Record<number, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      const initial: Record<number, string> = {}
      for (const a of assessments) {
        initial[a.id] = a.description || ''
      }
      setDescriptions(initial)
    }
  }, [isOpen, assessments])

  const allFilled = assessments.every(a => descriptions[a.id]?.trim().length > 0)

  const updateDescription = (id: number, value: string) => {
    setDescriptions(prev => ({ ...prev, [id]: value }))
  }

  const bulkDescriptionsMutation = useEvaluationAssessmentsBulkDescriptionsCreate()

  const handleSubmit = async () => {
    if (!allFilled) return
    setIsSubmitting(true)
    try {
      const payload = assessments.map(a => ({
        id: a.id,
        description: descriptions[a.id].trim(),
      }))
      await bulkDescriptionsMutation.mutateAsync({
        data: { assessments: payload } as any,
      })
      onSubmit()
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Assessment Descriptions</h2>
          <p className="text-sm text-gray-500 mt-1">
            Enter a brief description for each assessment to get accurate weight suggestions.
          </p>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {assessments.map(assessment => (
            <div key={assessment.id}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-sm font-medium text-gray-900">{assessment.name}</span>
                <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded capitalize">
                  {assessment.assessment_type}
                </span>
              </div>
              <textarea
                value={descriptions[assessment.id] || ''}
                onChange={e => updateDescription(assessment.id, e.target.value)}
                placeholder={PLACEHOLDER_EXAMPLE}
                rows={2}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 placeholder:text-gray-400 placeholder:italic"
              />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!allFilled || isSubmitting}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed disabled:text-gray-500"
          >
            {isSubmitting ? 'Saving...' : 'Submit & Get Suggestions'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default AssessmentDescriptionsModal
