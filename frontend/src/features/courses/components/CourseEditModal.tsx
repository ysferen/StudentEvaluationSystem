import React, { useState, useCallback, useEffect } from 'react'
import Modal from '../../../shared/components/ui/Modal'
import { useCoreCoursesPartialUpdate } from '../../../shared/api/generated/core/core'
import type { Course } from '../../../shared/api/model'
import InstructorSelect from './InstructorSelect'

interface CourseEditModalProps {
  isOpen: boolean
  onClose: () => void
  course: Course
  onSuccess: () => void
}

const inputClass = 'block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition'

const CourseEditModal: React.FC<CourseEditModalProps> = React.memo(({
  isOpen, onClose, course, onSuccess
}) => {
  const [name, setName] = useState(course.name)
  const [code, setCode] = useState(course.code)
  const [credits, setCredits] = useState<number | ''>(course.credits ?? 3)
  const [instructorIds, setInstructorIds] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)

  const updateMutation = useCoreCoursesPartialUpdate({
    mutation: {
      onSuccess: () => {
        onSuccess()
        onClose()
      },
      onError: (err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to update course')
      }
    }
  })

  useEffect(() => {
    if (isOpen) {
      setName(course.name)
      setCode(course.code)
      setCredits(course.credits ?? '')
      setInstructorIds((course.instructors as Array<{ id: number }>)?.map(i => i.id) ?? [])
      setError(null)
    }
  }, [isOpen, course])

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Course name is required')
      return
    }
    if (!code.trim()) {
      setError('Course code is required')
      return
    }

    await updateMutation.mutateAsync({
      id: course.id,
      data: {
        name: name.trim(),
        code: code.trim(),
        credits: credits === '' ? undefined : Number(credits),
        instructor_ids: instructorIds
      }
    })
  }, [name, code, credits, instructorIds, course.id, updateMutation])

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Course" size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
            <p className="text-sm text-danger-600">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Course Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputClass}
            placeholder="e.g., Introduction to Computer Science"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Course Code</label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className={inputClass}
            placeholder="e.g., CS101"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Credits</label>
          <input
            type="number"
            value={credits}
            onChange={(e) => setCredits(e.target.value === '' ? '' : Number(e.target.value))}
            className={inputClass}
            placeholder="e.g., 3"
            min={0}
          />
        </div>

        <InstructorSelect
          selectedIds={instructorIds}
          onChange={setInstructorIds}
        />

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={updateMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  )
})

CourseEditModal.displayName = 'CourseEditModal'

export default CourseEditModal
