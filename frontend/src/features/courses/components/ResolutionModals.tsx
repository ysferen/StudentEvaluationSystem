import React, { useState } from 'react'
import { X, AlertTriangle, Users, BookOpen, FileX } from 'lucide-react'

interface MissingAssessmentsModalProps {
  isOpen: boolean
  missingAssessments: Array<{ column: string; parsed_name: string }>
  availableInDatabase: string[]
  onClose: () => void
  onResolve: (choice: 'skip' | 'create', assessmentNames: string[]) => void
}

export const MissingAssessmentsModal: React.FC<MissingAssessmentsModalProps> = ({
  isOpen,
  missingAssessments,
  availableInDatabase,
  onClose,
  onResolve
}) => {
  const [selectedForCreation, setSelectedForCreation] = useState<Set<string>>(
    new Set(missingAssessments.map(a => a.parsed_name))
  )

  if (!isOpen) return null

  const handleConfirm = () => {
    if (selectedForCreation.size > 0) {
      onResolve('create', Array.from(selectedForCreation))
    } else {
      onResolve('skip', [])
    }
  }

  return (
    <div className="fixed inset-0 z-[25] bg-secondary-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-secondary-200 shrink-0">
          <div className="flex items-center gap-3">
            <BookOpen className="w-5 h-5 text-warning-500" />
            <h2 className="text-lg font-bold text-secondary-900">Missing Assessments</h2>
          </div>
          <button
            onClick={onClose}
            className="text-secondary-400 hover:text-secondary-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 pt-4 flex-1 min-h-0 flex flex-col gap-4">
          <p className="text-sm text-secondary-600">
            {missingAssessments.length} assessment(s) in the file were not found in the database.
          </p>
          <div className="overflow-auto max-h-[50vh] rounded-lg border border-secondary-200 flex-1 min-h-0 p-2">
            <div className="space-y-2">
            {missingAssessments.map(a => (
              <label
                key={a.column}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-secondary-50 cursor-pointer border border-secondary-200"
              >
                <input
                  type="checkbox"
                  checked={selectedForCreation.has(a.parsed_name)}
                  onChange={(e) => {
                    const next = new Set(selectedForCreation)
                    if (e.target.checked) next.add(a.parsed_name)
                    else next.delete(a.parsed_name)
                    setSelectedForCreation(next)
                  }}
                  className="w-4 h-4 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                />
                <div className="flex-1">
                  <span className="font-medium text-sm text-secondary-900">{a.parsed_name}</span>
                  <span className="text-xs text-secondary-500 ml-2">({a.column})</span>
                </div>
              </label>
            ))}
            </div>
          </div>
          {availableInDatabase.length > 0 && (
            <div className="p-3 bg-secondary-50 rounded-lg">
              <p className="text-xs text-secondary-500 mb-1">Available in database:</p>
              <p className="text-sm text-secondary-700">{availableInDatabase.join(', ')}</p>
            </div>
          )}
          <div className="sticky bottom-0 bg-white border-t border-secondary-200 -mx-6 px-6 pt-4 pb-2 shrink-0">
            <div className="flex gap-3">
            <button
              onClick={() => onResolve('skip', [])}
              className="flex-1 px-4 py-2.5 border border-secondary-300 rounded-lg text-secondary-700 hover:bg-secondary-50 font-medium transition-colors"
            >
              Skip All
            </button>
            <button
              onClick={handleConfirm}
              className="flex-1 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium transition-colors"
            >
              Create & Continue ({selectedForCreation.size})
            </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface MissingStudentsModalProps {
  isOpen: boolean
  missingStudents: Array<{ student_id: string; first_name: string; last_name: string }>
  onClose: () => void
  onResolve: (choice: 'skip' | 'create', students: Array<{ student_id: string; first_name: string; last_name: string }>) => void
}

export const MissingStudentsModal: React.FC<MissingStudentsModalProps> = ({
  isOpen,
  missingStudents,
  onClose,
  onResolve
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[25] bg-secondary-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-secondary-200 shrink-0">
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-danger-500" />
            <h2 className="text-lg font-bold text-secondary-900">Missing Students</h2>
          </div>
          <button
            onClick={onClose}
            className="text-secondary-400 hover:text-secondary-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 pt-4 flex-1 min-h-0 flex flex-col gap-4">
          <p className="text-sm text-secondary-600">
            {missingStudents.length} student(s) in the file were not found in the database. They will be created with temporary passwords.
          </p>
          <div className="overflow-auto max-h-[50vh] rounded-lg border border-secondary-200 flex-1 min-h-0">
            <table className="min-w-full divide-y divide-secondary-200">
              <thead className="bg-secondary-50 sticky top-0 z-10">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">ID</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Name</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-secondary-200">
                {missingStudents.map(s => (
                  <tr key={s.student_id}>
                    <td className="px-3 py-2 text-sm font-mono text-secondary-700">{s.student_id}</td>
                    <td className="px-3 py-2 text-sm text-secondary-900">{s.first_name} {s.last_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="sticky bottom-0 bg-white border-t border-secondary-200 -mx-6 px-6 pt-4 pb-2 shrink-0">
            <div className="flex gap-3">
            <button
              onClick={() => onResolve('skip', [])}
              className="flex-1 px-4 py-2.5 border border-secondary-300 rounded-lg text-secondary-700 hover:bg-secondary-50 font-medium transition-colors"
            >
              Skip All
            </button>
            <button
              onClick={() => onResolve('create', missingStudents)}
              className="flex-1 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium transition-colors"
            >
              Create All ({missingStudents.length})
            </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface UnenrolledStudentsModalProps {
  isOpen: boolean
  unenrolledStudents: Array<{ student_id: string; first_name: string; last_name: string }>
  onClose: () => void
  onResolve: (choice: 'skip' | 'enroll', studentIds: string[]) => void
}

export const UnenrolledStudentsModal: React.FC<UnenrolledStudentsModalProps> = ({
  isOpen,
  unenrolledStudents,
  onClose,
  onResolve
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[25] bg-secondary-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-secondary-200 shrink-0">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-warning-500" />
            <h2 className="text-lg font-bold text-secondary-900">Unenrolled Students</h2>
          </div>
          <button
            onClick={onClose}
            className="text-secondary-400 hover:text-secondary-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 pt-4 flex-1 min-h-0 flex flex-col gap-4">
          <p className="text-sm text-secondary-600">
            {unenrolledStudents.length} student(s) exist in the database but are not enrolled in this course.
          </p>
          <div className="overflow-auto max-h-[50vh] rounded-lg border border-secondary-200 flex-1 min-h-0">
            <table className="min-w-full divide-y divide-secondary-200">
              <thead className="bg-secondary-50 sticky top-0 z-10">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">ID</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Name</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-secondary-200">
                {unenrolledStudents.map(s => (
                  <tr key={s.student_id}>
                    <td className="px-3 py-2 text-sm font-mono text-secondary-700">{s.student_id}</td>
                    <td className="px-3 py-2 text-sm text-secondary-900">{s.first_name} {s.last_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="sticky bottom-0 bg-white border-t border-secondary-200 -mx-6 px-6 pt-4 pb-2 shrink-0">
            <div className="flex gap-3">
            <button
              onClick={() => onResolve('skip', [])}
              className="flex-1 px-4 py-2.5 border border-secondary-300 rounded-lg text-secondary-700 hover:bg-secondary-50 font-medium transition-colors"
            >
              Skip All
            </button>
            <button
              onClick={() => onResolve('enroll', unenrolledStudents.map(s => s.student_id))}
              className="flex-1 px-4 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium transition-colors"
            >
              Enroll All ({unenrolledStudents.length})
            </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface InvalidScoresModalProps {
  isOpen: boolean
  invalidScores: Array<{ row: number; column: string; value: string; error?: string }>
  onClose: () => void
  onResolve: (choice: 'skip' | 'clamp') => void
}

export const InvalidScoresModal: React.FC<InvalidScoresModalProps> = ({
  isOpen,
  invalidScores,
  onClose,
  onResolve
}) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[25] bg-secondary-900/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-secondary-200 shrink-0">
          <div className="flex items-center gap-3">
            <FileX className="w-5 h-5 text-danger-500" />
            <h2 className="text-lg font-bold text-secondary-900">Invalid Scores</h2>
          </div>
          <button
            onClick={onClose}
            className="text-secondary-400 hover:text-secondary-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 pt-4 flex-1 min-h-0 flex flex-col gap-4">
          <p className="text-sm text-secondary-600">
            {invalidScores.length} score(s) have invalid values. They must be fixed or handled before import.
          </p>
          <div className="overflow-auto max-h-[50vh] rounded-lg border border-secondary-200 flex-1 min-h-0">
            <table className="min-w-full divide-y divide-secondary-200">
              <thead className="bg-secondary-50 sticky top-0 z-10">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Row</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Column</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Value</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">Issue</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-secondary-200">
                {invalidScores.slice(0, 20).map((score, idx) => (
                  <tr key={idx}>
                    <td className="px-3 py-2 text-sm text-secondary-700">{score.row}</td>
                    <td className="px-3 py-2 text-sm text-secondary-700 truncate max-w-[150px]" title={score.column}>
                      {score.column}
                    </td>
                    <td className="px-3 py-2 text-sm font-mono text-danger-600">{score.value}</td>
                    <td className="px-3 py-2 text-sm text-danger-500 capitalize">{score.error || 'invalid'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {invalidScores.length > 20 && (
            <p className="text-xs text-secondary-500">
              Showing 20 of {invalidScores.length} invalid scores
            </p>
          )}
          <div className="sticky bottom-0 bg-white border-t border-secondary-200 -mx-6 px-6 pt-4 pb-2 shrink-0">
            <div className="flex gap-3">
            <button
              onClick={() => onResolve('skip')}
              className="flex-1 px-4 py-2.5 border border-secondary-300 rounded-lg text-secondary-700 hover:bg-secondary-50 font-medium transition-colors"
            >
              Skip Invalid Rows
            </button>
            <button
              onClick={() => onResolve('clamp')}
              className="flex-1 px-4 py-2.5 bg-warning-500 text-white rounded-lg hover:bg-warning-600 font-medium transition-colors"
            >
              Clamp to Range
            </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
