import { FormEvent, useEffect, useState } from 'react'
import { Check, Clipboard, KeyRound, Loader2, Pencil, Trash2, UserPlus, X } from 'lucide-react'
import { axiosInstance } from '@/shared/api/mutator'
import { Card } from '@/components/ui/custom/Card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/shadcn/Dialog'

type User = { id: number; username: string; email?: string; first_name: string; last_name: string; role: string; title?: string; must_change_password?: boolean }
type StudentProfile = { id: number; student_id: string; user: User; program: string | null }
type IssuedPassword = { id: number; username: string; password: string }

const inputClass = 'w-full rounded-xl border border-secondary-300 bg-white px-3 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20'

const PeoplePage = () => {
  const [instructors, setInstructors] = useState<User[]>([])
  const [students, setStudents] = useState<StudentProfile[]>([])
  const [form, setForm] = useState({ username: '', first_name: '', last_name: '', email: '', title: '', role: 'instructor' })
  const [passwords, setPasswords] = useState<IssuedPassword[]>([])
  const [copied, setCopied] = useState<number | null>(null)
  const [busyUser, setBusyUser] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<User | null>(null)
  const [editForm, setEditForm] = useState({ username: '', email: '', first_name: '', last_name: '', title: '' })

  const load = async () => {
    const [staffResponse, studentResponse] = await Promise.all([
      axiosInstance.get('/api/users/users/staff/'),
      axiosInstance.get('/api/users/students/'),
    ])
    setInstructors(staffResponse.data.results ?? staffResponse.data)
    setStudents(studentResponse.data.results ?? studentResponse.data)
  }
  useEffect(() => { void load() }, [])

  const rememberPassword = (id: number, username: string, password: string) => {
    setPasswords(current => [...current.filter(item => item.id !== id), { id, username, password }])
  }

  const createInstructor = async (event: FormEvent) => {
    event.preventDefault(); setError(null); setMessage(null)
    try {
      const response = await axiosInstance.post('/api/users/users/staff/', form)
      rememberPassword(response.data.user.id, response.data.user.username, response.data.temporary_password)
      setForm({ username: '', first_name: '', last_name: '', email: '', title: '', role: 'instructor' })
      setMessage('Instructor created. Copy the temporary password from the panel.')
      await load()
    } catch { setError('Could not create the instructor. Check the username and try again.') }
  }

  const reset = async (user: User) => {
    setBusyUser(user.id); setError(null); setMessage(null)
    try {
      const response = await axiosInstance.post(`/api/users/users/${user.id}/reset-temporary-password/`)
      rememberPassword(user.id, user.username, response.data.temporary_password)
      setMessage(`Temporary password reset for ${user.username}.`)
      await load()
    } catch { setError(`Could not reset the password for ${user.username}.`) }
    finally { setBusyUser(null) }
  }

  const openEdit = (user: User) => {
    setEditing(user)
    setEditForm({ username: user.username, email: user.email ?? '', first_name: user.first_name, last_name: user.last_name, title: user.title ?? '' })
  }

  const saveEdit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editing) return
    setBusyUser(editing.id); setError(null); setMessage(null)
    try {
      await axiosInstance.patch(`/api/users/users/${editing.id}/staff/`, editForm)
      setMessage(`${editForm.username} updated.`)
      setEditing(null)
      await load()
    } catch { setError(`Could not update ${editing.username}.`) }
    finally { setBusyUser(null) }
  }

  const deleteInstructor = async () => {
    if (!editing || !window.confirm(`Delete ${editing.username}? Their profile and permissions will also be removed.`)) return
    await axiosInstance.delete(`/api/users/users/${editing.id}/staff/`)
    setEditing(null); await load()
  }

  const impersonate = async (id: number) => {
    await axiosInstance.post(`/api/users/users/${id}/impersonate/`)
    window.location.href = '/student'
  }

  const copy = async (item: IssuedPassword) => {
    await navigator.clipboard.writeText(item.password)
    setCopied(item.id)
    window.setTimeout(() => setCopied(current => current === item.id ? null : current), 1800)
  }

  return <div className="space-y-6 pb-12">
    <div><h1 className="text-3xl font-bold text-secondary-900">People</h1><p className="text-secondary-600">Manage instructors and assist students in your department.</p></div>
    {message && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</div>}
    {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

    <Card className="p-5"><div className="mb-4 flex items-center gap-3"><div className="rounded-xl bg-primary-100 p-2"><UserPlus className="h-5 w-5 text-primary-700" /></div><div><h2 className="font-semibold">Create instructor</h2><p className="text-sm text-secondary-500">The account receives a one-time temporary password.</p></div></div><form onSubmit={createInstructor} className="grid gap-3 md:grid-cols-3"><input className={inputClass} placeholder="Username" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} required /><input className={inputClass} placeholder="First name" value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} /><input className={inputClass} placeholder="Last name" value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} /><input className={inputClass} type="email" placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /><input className={inputClass} placeholder="Title (e.g. Professor)" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /><button className="rounded-xl bg-primary-600 p-2.5 font-semibold text-white hover:bg-primary-700">Create instructor</button></form></Card>

    <Card className="p-5"><h2 className="mb-3 font-semibold">Instructors</h2><div className="space-y-2">{instructors.map(user => <div key={user.id} className="flex flex-wrap items-center gap-3 rounded-xl bg-secondary-50 px-4 py-3"><span className="font-medium">{user.title && `${user.title} `}{user.first_name} {user.last_name}</span><span className="text-sm text-secondary-500">@{user.username}</span>{user.must_change_password && <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700">Password change required</span>}<div className="ml-auto flex gap-2"><button disabled={busyUser === user.id} className="inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-medium text-primary-700 shadow-sm hover:bg-primary-50 disabled:opacity-50" onClick={() => void reset(user)}>{busyUser === user.id && <Loader2 className="h-4 w-4 animate-spin" />}Reset password</button><button aria-label={`Edit ${user.username}`} className="rounded-lg p-2 text-secondary-600 hover:bg-secondary-200" onClick={() => openEdit(user)}><Pencil className="h-4 w-4" /></button></div></div>)}</div></Card>

    <Card className="p-5"><h2 className="mb-3 font-semibold">Students</h2><div className="overflow-x-auto"><table className="w-full text-sm"><tbody>{students.map(profile => <tr key={profile.id} className="border-t"><td className="py-3">{profile.user.first_name} {profile.user.last_name} ({profile.student_id})</td><td>{profile.program}</td><td className="space-x-2 text-right"><button disabled={busyUser === profile.user.id} className="rounded-lg bg-secondary-100 px-3 py-2 font-medium text-secondary-700 hover:bg-secondary-200 disabled:opacity-50" onClick={() => void reset(profile.user)}>Reset password</button><button className="rounded-lg bg-primary-600 px-3 py-2 font-medium text-white hover:bg-primary-700" onClick={() => void impersonate(profile.user.id)}>View as student</button></td></tr>)}</tbody></table></div></Card>

    {passwords.length > 0 && <aside className="fixed bottom-5 right-5 z-40 w-[min(25rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-amber-300 bg-amber-50 shadow-2xl"><div className="flex gap-3 border-b border-amber-200 px-4 py-3"><KeyRound className="h-5 w-5 text-amber-700" /><div><h2 className="font-semibold text-amber-950">Temporary passwords</h2><p className="text-xs text-amber-700">Visible only during this session.</p></div></div><div className="max-h-64 divide-y divide-amber-200 overflow-y-auto">{passwords.map(item => <div key={item.id} className="flex items-center gap-2 px-4 py-3 text-sm"><div className="min-w-0 flex-1"><p className="font-medium">{item.username}</p><code className="font-semibold">{item.password}</code></div><button onClick={() => void copy(item)} className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-2 font-medium ${copied === item.id ? 'bg-emerald-600 text-white' : 'bg-white text-amber-800'}`}>{copied === item.id ? <Check className="h-4 w-4" /> : <Clipboard className="h-4 w-4" />}{copied === item.id ? 'Copied' : 'Copy'}</button><button aria-label="Dismiss password" onClick={() => setPasswords(items => items.filter(password => password.id !== item.id))} className="rounded-lg p-2 text-amber-700 hover:bg-amber-100"><X className="h-4 w-4" /></button></div>)}</div></aside>}

    <Dialog open={Boolean(editing)} onOpenChange={open => { if (!open) setEditing(null) }}>
      <DialogContent>
        <DialogHeader><DialogTitle>Edit instructor</DialogTitle></DialogHeader>
        {editing && <form onSubmit={saveEdit} className="space-y-3">
          <input className={inputClass} value={editForm.username} onChange={e => setEditForm({ ...editForm, username: e.target.value })} placeholder="Username" required />
          <div className="grid grid-cols-2 gap-3">
            <input className={inputClass} value={editForm.first_name} onChange={e => setEditForm({ ...editForm, first_name: e.target.value })} placeholder="First name" />
            <input className={inputClass} value={editForm.last_name} onChange={e => setEditForm({ ...editForm, last_name: e.target.value })} placeholder="Last name" />
          </div>
          <input className={inputClass} type="email" value={editForm.email} onChange={e => setEditForm({ ...editForm, email: e.target.value })} placeholder="Email" />
          <input className={inputClass} value={editForm.title} onChange={e => setEditForm({ ...editForm, title: e.target.value })} placeholder="Academic title (e.g. Professor)" />
          <div className="flex gap-3">
            <button type="button" onClick={() => void deleteInstructor()} className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2.5 font-semibold text-red-700 hover:bg-red-50"><Trash2 className="h-4 w-4" /> Delete</button>
            <button className="flex-1 rounded-xl bg-primary-600 px-4 py-2.5 font-semibold text-white">Save changes</button>
          </div>
        </form>}
      </DialogContent>
    </Dialog>
  </div>
}

export default PeoplePage
