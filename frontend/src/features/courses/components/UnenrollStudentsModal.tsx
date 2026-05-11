import { useState } from 'react'
import { evaluationEnrollmentsDestroy } from '../../../shared/api/generated/evaluation/evaluation'
import Modal from '../../../shared/components/ui/Modal'

interface EnrolledStudent {
  id: number
  name: string
}

interface UnenrollStudentsModalProps {
  isOpen: boolean
  onClose: () => void
  enrolledStudents: EnrolledStudent[]
  onSuccess: () => void
}

const UnenrollStudentsModal = ({ isOpen, onClose, enrolledStudents, onSuccess }: UnenrollStudentsModalProps) => {
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [isUnenrolling, setIsUnenrolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleClose = () => {
    setSelectedIds([])
    setError(null)
    onClose()
  }

  const toggleStudent = (id: number) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id])
  }

  const handleSubmit = async () => {
    if (selectedIds.length === 0) {
      setError('Please select at least one student')
      return
    }
    setIsUnenrolling(true)
    setError(null)
    try {
      for (const id of selectedIds) {
        await evaluationEnrollmentsDestroy(id)
      }
      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unenroll students')
    } finally {
      setIsUnenrolling(false)
    }
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Unenroll Students" size="md">
      <div className="space-y-4">
        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
            <p className="text-sm text-danger-600">{error}</p>
          </div>
        )}

        {enrolledStudents.length === 0 ? (
          <p className="text-sm text-secondary-500">No students enrolled in this course.</p>
        ) : (
          <div className="max-h-64 overflow-y-auto border border-secondary-200 rounded-xl">
            {enrolledStudents.map(s => (
              <label
                key={s.id}
                className="flex items-center gap-3 px-4 py-2.5 hover:bg-secondary-50 cursor-pointer text-sm"
              >
                <input
                  type="checkbox"
                  checked={selectedIds.includes(s.id)}
                  onChange={() => toggleStudent(s.id)}
                  className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-secondary-900">{s.name}</span>
              </label>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={handleClose} className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg">
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isUnenrolling || selectedIds.length === 0}
            className="px-6 py-2 text-sm font-semibold text-danger-700 bg-danger-50 rounded-lg hover:bg-danger-100 disabled:opacity-50"
          >
            {isUnenrolling ? 'Unenrolling...' : `Unenroll (${selectedIds.length})`}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default UnenrollStudentsModal
