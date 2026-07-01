import React, { useState } from 'react'
import { axiosInstance } from '@/shared/api/mutator'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { AxiosError } from 'axios'

const passwordError = (error: unknown): string => {
  if (error instanceof AxiosError) {
    const data = error.response?.data as { error?: string | string[]; detail?: string } | undefined
    if (Array.isArray(data?.error)) return data.error.join(' ')
    if (typeof data?.error === 'string') return data.error
    if (typeof data?.detail === 'string') return data.detail
  }
  return error instanceof Error ? error.message : 'Could not change the password.'
}

const Safety: React.FC = () => {
  const { user } = useAuth()
  const [message, setMessage] = useState<string | null>(null)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage(null)
    setError(null)

    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('Please fill all fields')
      return
    }
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match")
      return
    }

    setLoading(true)
    try {
      await axiosInstance.post('/api/users/change_password/', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      {
        setMessage('Password changed successfully')
        setCurrentPassword('')
        setNewPassword('')
        setConfirmPassword('')
        const destination = user?.role === 'admin' ? '/system-admin' : user?.role === 'program_head' ? '/head' : '/instructor'
        window.location.href = destination
      }
    } catch (err: unknown) {
      setError(passwordError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-secondary-900">Security</h1>
      <p className="mt-4 text-secondary-600">
        {user?.must_change_password ? 'Change your temporary password before continuing.' : 'Manage your account security and privacy settings.'}
      </p>

      <section className="mt-8 max-w-md space-y-4">
        <section>
          <h2 className="text-lg font-semibold text-secondary-900">Change password</h2>
          <form onSubmit={handleChangePassword} className="mt-4 space-y-3">
            <div>
              <label className="text-sm text-secondary-600">Current password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border border-secondary-200 px-3 py-2"
              />
            </div>
            <div>
              <label className="text-sm text-secondary-600">New password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border border-secondary-200 px-3 py-2"
              />
            </div>
            <div>
              <label className="text-sm text-secondary-600">Confirm new password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border border-secondary-200 px-3 py-2"
              />
            </div>

            {error && <div className="text-sm text-red-600">{error}</div>}
            {message && <div className="text-sm text-emerald-700">{message}</div>}

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {loading ? 'Updating...' : 'Change password'}
              </button>
            </div>
          </form>
        </section>

      </section>
    </div>
  )
}

export default Safety
