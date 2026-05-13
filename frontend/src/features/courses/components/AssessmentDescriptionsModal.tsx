import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/shadcn/Dialog'
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

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] flex flex-col" showCloseButton={false}>
        <DialogHeader className="flex-row items-start justify-between border-b border-gray-200 pb-4">
          <div>
            <DialogTitle className="text-xl font-bold text-gray-900">Assessment Descriptions</DialogTitle>
            <p className="text-sm text-gray-500 mt-1">
              Enter a brief description for each assessment to get accurate weight suggestions.
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors shrink-0">
            <X className="h-5 w-5" />
          </button>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4">
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

        <DialogFooter>
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
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default AssessmentDescriptionsModal
