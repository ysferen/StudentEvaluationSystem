import React from 'react'
import Modal from './Modal'

interface ConfirmDialogProps {
  isOpen: boolean
  onCancel: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmLabel?: string
  isConfirming?: boolean
  variant?: 'danger' | 'primary'
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen, onCancel, onConfirm, title, message,
  confirmLabel = 'Yes, delete', isConfirming = false, variant = 'danger'
}) => {
  const btn = {
    danger: 'px-4 py-2 text-sm font-semibold text-white bg-danger-600 rounded-lg hover:bg-danger-700 transition-colors disabled:opacity-50',
    primary: 'px-4 py-2 text-sm font-semibold text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50'
  }
  return (
    <Modal isOpen={isOpen} onClose={onCancel} title={title} size="sm">
      <p className="text-sm text-secondary-600 mb-6">{message}</p>
      <div className="flex justify-end gap-3">
        <button onClick={onCancel} disabled={isConfirming} className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors">Cancel</button>
        <button onClick={onConfirm} disabled={isConfirming} className={btn[variant]}>{isConfirming ? 'Processing...' : confirmLabel}</button>
      </div>
    </Modal>
  )
}

export default ConfirmDialog
