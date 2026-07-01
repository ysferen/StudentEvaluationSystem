import { FormEvent, useEffect, useState } from 'react'
import { Save } from 'lucide-react'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { axiosInstance } from '@/shared/api/mutator'
import { Card } from '@/components/ui/custom/Card'

const inputClass = 'w-full rounded-xl border border-secondary-300 bg-white px-3 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20'

const Settings = () => {
  const { user } = useAuth()
  const [form, setForm] = useState({ username: '', email: '', first_name: '', last_name: '', title: '' })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user) setForm({ username: user.username, email: user.email ?? '', first_name: user.first_name ?? '', last_name: user.last_name ?? '', title: user.title ?? '' })
  }, [user])

  const save = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setMessage(null); setError(null)
    try {
      await axiosInstance.patch('/api/users/users/me/', form)
      setMessage('Account updated.')
      window.setTimeout(() => setMessage(null), 3000)
    } catch {
      setError('Could not update your account.')
    } finally { setSaving(false) }
  }

  const showTitle = user?.role === 'instructor' || user?.role === 'program_head'

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-2 sm:p-6">
      <div>
        <h1 className="text-3xl font-bold text-secondary-900">Account</h1>
        <p className="mt-1 text-secondary-600">Update the information shown across the system.</p>
      </div>
      <Card>
        <form onSubmit={save} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-secondary-700">
              First name
              <input className={inputClass} value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} />
            </label>
            <label className="text-sm font-medium text-secondary-700">
              Last name
              <input className={inputClass} value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} />
            </label>
          </div>
          <label className="block text-sm font-medium text-secondary-700">
            Username
            <input className={inputClass} value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} required />
          </label>
          <label className="block text-sm font-medium text-secondary-700">
            Email
            <input className={inputClass} type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
          </label>
          {showTitle && (
            <label className="block text-sm font-medium text-secondary-700">
              Academic title
              <input className={inputClass} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Professor, Associate Professor, Dr." />
            </label>
          )}
          <div className="rounded-xl bg-secondary-50 p-3 text-sm text-secondary-600">Role and department are managed by an administrator.</div>
          {message && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
          {error && <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <button disabled={saving} className="inline-flex items-center gap-2 rounded-xl bg-primary-600 px-5 py-2.5 font-semibold text-white hover:bg-primary-700 disabled:opacity-50">
            <Save className="h-4 w-4" />
            {saving ? 'Saving\u2026' : 'Save changes'}
          </button>
        </form>
      </Card>
    </div>
  )
}

export default Settings
