import React, { useState } from 'react'

const Safety: React.FC = () => {
  const [twoFAEnabled, setTwoFAEnabled] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const toggleTwoFA = async () => {
    // placeholder: call backend to enable/disable 2FA
    setMessage(null)
    try {
      // simulate API call
      await new Promise((res) => setTimeout(res, 600))
      setTwoFAEnabled((s) => !s)
      setMessage('Security settings updated')
    } catch {
      setMessage('Failed to update settings')
    }
  }

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
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/users/change_password/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
      })

      if (res.ok) {
        setMessage('Password changed successfully')
        setCurrentPassword('')
        setNewPassword('')
        setConfirmPassword('')
      } else {
        const data = await res.json().catch(() => null)
        const errMsg = data?.detail || data?.error || JSON.stringify(data) || `Request failed (${res.status})`
        setError(String(errMsg))
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Network error'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-secondary-900">Security</h1>
      <p className="mt-4 text-secondary-600">Manage your account security and privacy settings.</p>

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

        <div className="flex items-center justify-between p-4 border border-secondary-200 rounded-lg">
          <div>
            <h2 className="text-lg font-semibold text-secondary-900">Two-Factor Authentication</h2>
            <p className="text-sm text-secondary-600">Add an extra layer of security to your account.</p>
          </div>
          <button
            onClick={toggleTwoFA}
            className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            {twoFAEnabled ? 'Disable' : 'Enable'}
          </button>
        </div>

        <div className="p-4 border border-secondary-200 rounded-lg">
          <h2 className="text-lg font-semibold text-secondary-900">Active Sessions</h2>
          <p className="text-sm text-secondary-600 mt-2">Sign out of other devices to protect your account.</p>
          <div className="mt-3">
            <button className="px-3 py-2 bg-white border border-secondary-200 rounded-lg hover:bg-secondary-50">Sign out other sessions</button>
          </div>
        </div>

        {message && <div className="text-sm text-emerald-700">{message}</div>}
      </section>
    </div>
  )
}

export default Safety
