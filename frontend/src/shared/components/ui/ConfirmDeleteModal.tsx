import React, { useState, useEffect } from 'react'
import Modal from './Modal'

interface ConfirmDeleteModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  /** The name of the item to display in the confirmation message */
  itemName: string
  /** The exact text the user must type to confirm */
  confirmText: string
  /** Label for the text input (e.g. "course name", "LO code", "assessment name") */
  inputLabel?: string
  isConfirming?: boolean
}

const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  itemName,
  confirmText,
  inputLabel = 'name',
  isConfirming = false,
}) => {
  const [typed, setTyped] = useState('')
  const matches = typed === confirmText

  // Reset when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setTyped('')
    }
  }, [isOpen])

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="space-y-4">
        <p className="text-sm text-secondary-600">
          This action cannot be undone. Please type <span className="font-semibold text-secondary-900">{confirmText}</span> to confirm deletion of <span className="font-semibold text-secondary-900">{itemName}</span>.
        </p>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">
            Enter {inputLabel} to confirm
          </label>
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder={confirmText}
            className="block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-danger-500 focus:ring-2 focus:ring-danger-500/20 transition"
            autoFocus
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isConfirming}
            className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!matches || isConfirming}
            className="px-6 py-2 text-sm font-semibold text-white bg-danger-600 rounded-lg hover:bg-danger-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isConfirming ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default ConfirmDeleteModal
