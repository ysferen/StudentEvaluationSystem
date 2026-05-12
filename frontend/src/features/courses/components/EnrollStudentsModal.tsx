import { useState, useMemo } from 'react'
import { useUsersUsersList } from '../../../shared/api/generated/users/users'
import { useEvaluationEnrollmentsBulkEnrollCreate } from '../../../shared/api/generated/evaluation/evaluation'
import type { UsersUsersListParams } from '../../../shared/api/model/usersUsersListParams'
import Modal from '@/components/ui/custom/Modal'

interface EnrollStudentsModalProps {
  isOpen: boolean
  onClose: () => void
  courseId: number
  enrolledStudentIds: number[]
  onSuccess: () => void
}

const inputClass = 'block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition'

const EnrollStudentsModal = ({ isOpen, onClose, courseId, enrolledStudentIds, onSuccess }: EnrollStudentsModalProps) => {
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)

  const { data: usersData, isLoading } = useUsersUsersList(
    { role: 'student' } as UsersUsersListParams,
    { query: { enabled: isOpen } }
  )

  const bulkEnroll = useEvaluationEnrollmentsBulkEnrollCreate({
    mutation: {
      onSuccess: () => {
        onSuccess()
        handleClose()
      },
      onError: (err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to enroll students')
      }
    }
  })

  const handleClose = () => {
    setSearch('')
    setSelectedIds([])
    setError(null)
    onClose()
  }

  // Filter students not already enrolled, matching search
  const availableStudents = useMemo(() => {
    if (!usersData?.results) return []
    const q = search.toLowerCase().trim()
    return usersData.results
      .filter(u => !enrolledStudentIds.includes(u.id))
      .filter(u => {
        if (!q) return true
        const name = `${u.first_name ?? ''} ${u.last_name ?? ''} ${u.username}`.toLowerCase()
        return name.includes(q)
      })
  }, [usersData, search, enrolledStudentIds])

  const selectedStudents = useMemo(() => {
    if (!usersData?.results) return []
    return usersData.results.filter(u => selectedIds.includes(u.id))
  }, [usersData, selectedIds])

  const toggleStudent = (id: number) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id])
  }

  const handleSubmit = async () => {
    if (selectedIds.length === 0) {
      setError('Please select at least one student')
      return
    }
    setError(null)
    // The bulk_enroll endpoint expects { course_id, student_ids }
    // The generated type is incorrect (CourseEnrollment), so we cast
    await bulkEnroll.mutateAsync({
      data: { course_id: courseId, student_ids: selectedIds } as never
    })
  }

  if (!isOpen) return null

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Enroll Students" size="md">
      <div className="space-y-4">
        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
            <p className="text-sm text-danger-600">{error}</p>
          </div>
        )}

        {isLoading ? (
          <p className="text-sm text-secondary-500">Loading students...</p>
        ) : (
          <>
            {/* Selected chips */}
            {selectedStudents.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {selectedStudents.map(s => (
                  <span key={s.id} className="inline-flex items-center gap-1 px-2.5 py-1 bg-primary-100 text-primary-800 text-xs font-medium rounded-full">
                    {s.first_name} {s.last_name} ({s.username})
                    <button type="button" onClick={() => toggleStudent(s.id)} className="ml-0.5 text-primary-500 hover:text-primary-700">&#x2715;</button>
                  </span>
                ))}
              </div>
            )}

            {/* Search input */}
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className={inputClass}
              placeholder="Search students by name or username..."
            />

            {/* Student list */}
            <div className="max-h-48 overflow-y-auto border border-secondary-200 rounded-xl">
              {availableStudents.length === 0 ? (
                <p className="px-4 py-3 text-sm text-secondary-500">No matching students found</p>
              ) : (
                availableStudents.map(s => (
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
                    <span className="text-secondary-900">
                      {s.first_name} {s.last_name}
                      <span className="text-secondary-400 ml-1">({s.username})</span>
                    </span>
                  </label>
                ))
              )}
            </div>
          </>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={handleClose} className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg">
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={bulkEnroll.isPending || selectedIds.length === 0}
            className="px-6 py-2 text-sm font-semibold text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {bulkEnroll.isPending ? 'Enrolling...' : `Enroll (${selectedIds.length})`}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default EnrollStudentsModal
