import { Dispatch, FormEvent, ReactNode, SetStateAction, useEffect, useMemo, useState } from 'react'
import { Check, ChevronDown, Circle, Clipboard, FileSpreadsheet, KeyRound, Pencil, Trash2, Users, X } from 'lucide-react'
import { axiosInstance } from '@/shared/api/mutator'
import { Card } from '@/components/ui/custom/Card'
import { ProgramTemplateImportModal } from '@/features/head/components/ProgramTemplateImportModal'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/shadcn/Dialog'

type Department = { id: number; name: string; code: string }
type Program = { id: number; name: string; code: string; department: number }
type Term = { id: number; name: string; is_active: boolean; academic_year: number; semester: string }
type StaffUser = {
  id: number
  username: string
  first_name: string
  last_name: string
  role: 'program_head' | 'instructor'
  department: string | null
  department_id?: number | null
  email: string
  title?: string
  must_change_password: boolean
}
type IssuedPassword = { id: number; username: string; role: string; password: string }
type Account = { username: string; first_name: string; last_name: string; email: string; title: string; role: string; department_id: string }

const inputClass = 'w-full rounded-xl border border-secondary-300 bg-white px-3 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20'

const Step = ({ number, title, description, complete, optional, open, onToggle, children }: {
  number: number
  title: string
  description: string
  complete: boolean
  optional?: boolean
  open: boolean
  onToggle: () => void
  children: ReactNode
}) => (
  <section className={`overflow-hidden rounded-2xl border transition ${complete ? 'border-emerald-200 bg-emerald-50/40' : open ? 'border-primary-300 bg-white shadow-lg' : 'border-secondary-200 bg-white'}`}>
    <button type="button" onClick={onToggle} className="flex w-full items-center gap-4 p-5 text-left sm:p-6">
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full font-bold ${complete ? 'bg-emerald-600 text-white' : open ? 'bg-primary-600 text-white' : 'bg-secondary-100 text-secondary-500'}`}>
        {complete ? <Check className="h-5 w-5" /> : number}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 text-lg font-semibold text-secondary-900">{title}{optional && <span className="rounded-full bg-secondary-100 px-2 py-0.5 text-xs font-medium text-secondary-500">Optional</span>}</span>
        <span className="mt-1 block text-sm text-secondary-500">{description}</span>
      </span>
      <ChevronDown className={`h-5 w-5 text-secondary-400 transition-transform ${open ? 'rotate-180' : ''}`} />
    </button>
    {open && <div className="border-t border-secondary-100 bg-white p-5 sm:p-6">{children}</div>}
  </section>
)

const SystemAdminDashboard = () => {
  const { logout } = useAuth()
  const [departments, setDepartments] = useState<Department[]>([])
  const [programs, setPrograms] = useState<Program[]>([])
  const [terms, setTerms] = useState<Term[]>([])
  const [staff, setStaff] = useState<StaffUser[]>([])
  const [activeStep, setActiveStep] = useState(1)
  const [department, setDepartment] = useState({ name: '', code: '' })
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null)
  const [editingProgram, setEditingProgram] = useState<Program | null>(null)
  const [editingStaff, setEditingStaff] = useState<StaffUser | null>(null)
  const [staffDraft, setStaffDraft] = useState({ username: '', first_name: '', last_name: '', email: '', title: '', department_id: '' })
  const [account, setAccount] = useState<Account>({ username: '', first_name: '', last_name: '', email: '', title: '', role: 'program_head', department_id: '' })
  const [issuedPasswords, setIssuedPasswords] = useState<IssuedPassword[]>([])
  const [selectedProgram, setSelectedProgram] = useState('')
  const [programDraft, setProgramDraft] = useState({ code: '', name: '', department: '' })
  const [termDraft, setTermDraft] = useState({ academic_year: String(new Date().getFullYear()), semester: 'fall' })
  const [importOpen, setImportOpen] = useState(false)
  const [importComplete, setImportComplete] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedPassword, setCopiedPassword] = useState<number | null>(null)

  const load = async () => {
    const [departmentResponse, programResponse, termResponse, staffResponse] = await Promise.all([
      axiosInstance.get('/api/core/departments/'),
      axiosInstance.get('/api/core/programs/'),
      axiosInstance.get('/api/core/terms/'),
      axiosInstance.get('/api/users/users/staff/'),
    ])
    const loadedDepartments: Department[] = departmentResponse.data.results ?? departmentResponse.data
    const loadedPrograms: Program[] = programResponse.data.results ?? programResponse.data
    const loadedTerms: Term[] = termResponse.data.results ?? termResponse.data
    const loadedStaff: StaffUser[] = staffResponse.data.results ?? staffResponse.data
    setDepartments(loadedDepartments)
    setPrograms(loadedPrograms)
    setTerms(loadedTerms)
    setStaff(loadedStaff)
    setActiveStep(current => {
      if (current !== 1) return current
      if (!loadedDepartments.length) return 1
      if (!loadedTerms.some(term => term.is_active)) return 2
      if (!loadedDepartments.every(item => loadedPrograms.some(program => program.department === item.id))) return 3
      const assigned = new Set(loadedStaff.filter(user => user.role === 'program_head').map(user => user.department))
      return loadedDepartments.every(item => assigned.has(`${item.code} - ${item.name}`)) ? 5 : 4
    })
  }
  useEffect(() => { void load() }, [])

  const heads = staff.filter(user => user.role === 'program_head')
  const instructors = staff.filter(user => user.role === 'instructor')
  const headDepartments = useMemo(() => new Set(heads.map(user => user.department)), [heads])
  const departmentsComplete = departments.length > 0
  const headsComplete = departmentsComplete && departments.every(item => headDepartments.has(`${item.code} - ${item.name}`))
  const programsComplete = departmentsComplete && departments.every(item => programs.some(program => program.department === item.id))
  const activeTerm = terms.find(term => term.is_active)
  const setupComplete = Boolean(activeTerm && programsComplete && headsComplete)

  const goNext = (step: number) => setActiveStep(step)
  const saveDepartment = async (event: FormEvent) => {
    event.preventDefault(); setError(null)
    try {
      await axiosInstance.post('/api/core/departments/', department)
      setDepartment({ name: '', code: '' })
      await load(); goNext(2)
    } catch { setError('Could not save the department.') }
  }

  const createAccount = async (event: FormEvent, role = account.role) => {
    event.preventDefault(); setError(null)
    try {
      const response = await axiosInstance.post('/api/users/users/staff/', { ...account, role, department_id: Number(account.department_id) })
      const user = response.data.user as StaffUser
      setIssuedPasswords(current => [...current, { id: user.id, username: user.username, role: user.role === 'program_head' ? 'Head' : 'Instructor', password: response.data.temporary_password }])
      const wasHead = role === 'program_head'
      setAccount({ username: '', first_name: '', last_name: '', email: '', title: '', role: 'program_head', department_id: '' })
      await load(); goNext(wasHead ? 5 : 6)
    } catch { setError('Could not create the account. Check that the username is unique.') }
  }

  const resetPassword = async (user: StaffUser) => {
    const response = await axiosInstance.post(`/api/users/users/${user.id}/reset-temporary-password/`)
    setIssuedPasswords(current => [...current.filter(item => item.id !== user.id), { id: user.id, username: user.username, role: user.role === 'program_head' ? 'Head' : 'Instructor', password: response.data.temporary_password }])
    await load()
  }

  const createProgram = async (event: FormEvent) => {
    event.preventDefault(); setError(null)
    const departmentId = Number(programDraft.department)
    try {
      const degreeResponse = await axiosInstance.get('/api/core/degree-levels/')
      const degrees = degreeResponse.data.results ?? degreeResponse.data
      let degreeId = degrees[0]?.id as number | undefined
      if (!degreeId) {
        const response = await axiosInstance.post('/api/core/degree-levels/', { name: "Bachelor's", level: 1 })
        degreeId = response.data.id
      }
      const response = await axiosInstance.post('/api/core/programs/', {
        code: programDraft.code,
        name: programDraft.name,
        department: departmentId,
        degree_level: degreeId,
        duration_years: 4,
      })
      setProgramDraft({ code: '', name: '', department: '' })
      await load(); setSelectedProgram(String(response.data.id))
      goNext(departments.every(item => item.id === departmentId || programs.some(program => program.department === item.id)) ? 4 : 3)
    } catch { setError('Could not create the program needed for import.') }
  }

  const createTerm = async (event: FormEvent) => {
    event.preventDefault(); setError(null)
    const year = Number(termDraft.academic_year)
    const labels: Record<string, string> = { fall: 'Fall', spring: 'Spring', summer: 'Summer' }
    try {
      await axiosInstance.post('/api/core/terms/', {
        academic_year: year,
        semester: termDraft.semester,
        name: `${labels[termDraft.semester]} ${year}`,
        is_active: true,
      })
      await load(); goNext(3)
    } catch { setError('Could not create the academic term.') }
  }

  const activateTerm = async (id: number) => {
    await axiosInstance.patch(`/api/core/terms/${id}/`, { is_active: true })
    await load(); goNext(3)
  }

  const saveDepartmentEdit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editingDepartment) return
    await axiosInstance.patch(`/api/core/departments/${editingDepartment.id}/`, { name: editingDepartment.name, code: editingDepartment.code })
    setEditingDepartment(null); await load()
  }

  const saveProgramEdit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editingProgram) return
    await axiosInstance.patch(`/api/core/programs/${editingProgram.id}/`, { name: editingProgram.name, code: editingProgram.code, department: editingProgram.department })
    setEditingProgram(null); await load()
  }

  const openStaffEdit = (user: StaffUser) => {
    setEditingStaff(user)
    setStaffDraft({ username: user.username, first_name: user.first_name, last_name: user.last_name, email: user.email, title: user.title ?? '', department_id: String(user.department_id ?? '') })
  }

  const saveStaffEdit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editingStaff) return
    await axiosInstance.patch(`/api/users/users/${editingStaff.id}/staff/`, { ...staffDraft, department_id: Number(staffDraft.department_id) })
    setEditingStaff(null); await load()
  }

  const deleteStaff = async () => {
    if (!editingStaff || !window.confirm(`Delete ${editingStaff.username}? Their profile and granted permissions will also be removed.`)) return
    await axiosInstance.delete(`/api/users/users/${editingStaff.id}/staff/`)
    setEditingStaff(null); await load()
  }

  const copyPassword = async (item: IssuedPassword) => {
    await navigator.clipboard.writeText(item.password)
    setCopiedPassword(item.id)
    window.setTimeout(() => setCopiedPassword(current => current === item.id ? null : current), 1800)
  }

  return <div className="mx-auto max-w-5xl space-y-8 pb-12">
    <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-indigo-950 to-primary-800 px-7 py-10 text-white sm:px-10">
      <div className="relative z-10 max-w-2xl"><p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-primary-200">First steps</p><h1 className="text-3xl font-bold sm:text-4xl">Let’s set up your institution</h1><p className="mt-3 text-primary-100">A short guided setup. Finish the required steps, then continue with the new head account.</p></div>
      <div className="absolute -right-14 -top-20 h-72 w-72 rounded-full bg-white/10 blur-2xl" />
    </header>

    {error && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

    <div className="space-y-4">
      <Step number={1} title="Create departments" description="Add the academic departments that will use this installation." complete={departmentsComplete} open={activeStep === 1} onToggle={() => setActiveStep(activeStep === 1 ? 0 : 1)}>
        <form onSubmit={saveDepartment} className="grid gap-3 sm:grid-cols-[1fr_2fr_auto]"><input className={inputClass} placeholder="Code" value={department.code} onChange={e => setDepartment({ ...department, code: e.target.value })} required /><input className={inputClass} placeholder="Department name" value={department.name} onChange={e => setDepartment({ ...department, name: e.target.value })} required /><button className="rounded-xl bg-primary-600 px-5 py-2.5 font-semibold text-white hover:bg-primary-700">Add department</button></form>
        <ul className="mt-5 grid gap-2 sm:grid-cols-2">{departments.map(item => <li key={item.id} className="flex items-center justify-between rounded-xl bg-secondary-50 px-4 py-3"><span><b>{item.code}</b> · {item.name}</span><button type="button" aria-label={`Edit ${item.name}`} className="rounded-lg p-2 text-primary-700 hover:bg-primary-50" onClick={() => setEditingDepartment({ ...item })}><Pencil className="h-4 w-4" /></button></li>)}</ul>
        {departmentsComplete && <button type="button" onClick={() => goNext(2)} className="mt-5 rounded-lg bg-primary-50 px-3 py-2 font-semibold text-primary-700 hover:bg-primary-100">Continue to terms →</button>}
      </Step>

      <Step number={2} title="Set the active academic term" description="Courses, imports, and analytics need a current semester." complete={Boolean(activeTerm)} open={activeStep === 2} onToggle={() => setActiveStep(activeStep === 2 ? 0 : 2)}>
        {activeTerm && <div className="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-emerald-900"><b>{activeTerm.name}</b> is currently active.</div>}
        <form onSubmit={createTerm} className="grid gap-3 sm:grid-cols-3"><input className={inputClass} type="number" min="2000" max="2100" aria-label="Academic year" value={termDraft.academic_year} onChange={e => setTermDraft({ ...termDraft, academic_year: e.target.value })} required /><select className={inputClass} value={termDraft.semester} onChange={e => setTermDraft({ ...termDraft, semester: e.target.value })}><option value="fall">Fall</option><option value="spring">Spring</option><option value="summer">Summer</option></select><button className="rounded-xl bg-primary-600 px-5 py-2.5 font-semibold text-white">Create term</button></form>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">{terms.map(term => <div key={term.id} className="flex items-center justify-between rounded-xl border border-secondary-200 px-4 py-3"><span className="font-medium">{term.name}</span>{term.is_active ? <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-700">Active</span> : <button type="button" onClick={() => void activateTerm(term.id)} className="rounded-lg bg-secondary-100 px-3 py-1.5 text-sm font-medium text-secondary-700 hover:bg-secondary-200">Set active</button>}</div>)}</div>
        {activeTerm && <button type="button" onClick={() => goNext(3)} className="mt-5 rounded-lg bg-primary-50 px-3 py-2 font-semibold text-primary-700 hover:bg-primary-100">Continue to programs →</button>}
      </Step>

      <Step number={3} title="Create academic programs" description="Each department needs a program before its dashboard and imports have context." complete={programsComplete} open={activeStep === 3} onToggle={() => setActiveStep(activeStep === 3 ? 0 : 3)}>
        <form onSubmit={createProgram} className="grid gap-3 sm:grid-cols-4"><select className={inputClass} value={programDraft.department} onChange={e => setProgramDraft({ ...programDraft, department: e.target.value })} required><option value="">Department</option>{departments.map(item => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select><input className={inputClass} placeholder="Program code" value={programDraft.code} onChange={e => setProgramDraft({ ...programDraft, code: e.target.value })} required /><input className={inputClass} placeholder="Program name" value={programDraft.name} onChange={e => setProgramDraft({ ...programDraft, name: e.target.value })} required /><button className="rounded-xl bg-primary-600 px-4 py-2 font-semibold text-white">Add program</button></form>
        <ul className="mt-5 grid gap-2 sm:grid-cols-2">{programs.map(program => <li key={program.id} className="flex items-center justify-between rounded-xl bg-secondary-50 px-4 py-3"><span><b>{program.code}</b> · {program.name}</span><button type="button" aria-label={`Edit ${program.name}`} className="rounded-lg p-2 text-primary-700 hover:bg-primary-50" onClick={() => setEditingProgram({ ...program })}><Pencil className="h-4 w-4" /></button></li>)}</ul>
        {programsComplete && <button type="button" onClick={() => goNext(4)} className="mt-5 rounded-lg bg-primary-50 px-3 py-2 font-semibold text-primary-700 hover:bg-primary-100">Continue to department heads →</button>}
      </Step>

      <Step number={4} title="Assign department heads" description="Every department needs a head before setup is complete." complete={headsComplete} open={activeStep === 4} onToggle={() => setActiveStep(activeStep === 4 ? 0 : 4)}>
        {!departmentsComplete ? <p className="text-sm text-secondary-500">Create a department first.</p> : <AccountForm account={account} setAccount={setAccount} departments={departments} role="program_head" onSubmit={createAccount} />}
        <StaffList users={heads} onReset={resetPassword} onEdit={openStaffEdit} />
        {headsComplete && <button type="button" onClick={() => goNext(5)} className="mt-5 rounded-lg bg-primary-50 px-3 py-2 font-semibold text-primary-700 hover:bg-primary-100">Continue to optional setup →</button>}
      </Step>

      <Step number={5} title="Add instructors" description="Create instructor accounts now, or let department heads do it later." complete={instructors.length > 0} optional open={activeStep === 5} onToggle={() => setActiveStep(activeStep === 5 ? 0 : 5)}>
        <AccountForm account={account} setAccount={setAccount} departments={departments} role="instructor" onSubmit={createAccount} />
        <StaffList users={instructors} onReset={resetPassword} onEdit={openStaffEdit} />
        <button type="button" onClick={() => goNext(6)} className="mt-5 rounded-lg bg-primary-50 px-3 py-2 font-semibold text-primary-700 hover:bg-primary-100">{instructors.length ? 'Continue' : 'Skip for now'} →</button>
      </Step>

      <Step number={6} title="Import course information" description="Optionally import templates into an existing program without leaving setup." complete={importComplete} optional open={activeStep === 6} onToggle={() => setActiveStep(activeStep === 6 ? 0 : 6)}>
        <div className="flex flex-col gap-3 sm:flex-row"><select className={inputClass} value={selectedProgram} onChange={e => setSelectedProgram(e.target.value)}><option value="">Select a program</option>{programs.map(program => <option key={program.id} value={program.id}>{program.code} · {program.name}</option>)}</select><button type="button" disabled={!selectedProgram} onClick={() => setImportOpen(true)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary-600 px-5 py-2.5 font-semibold text-white disabled:opacity-40"><FileSpreadsheet className="h-4 w-4" /> Open importer</button></div>
      </Step>
    </div>

    {setupComplete && <Card className="flex flex-col items-start justify-between gap-4 border-emerald-200 bg-emerald-50 sm:flex-row sm:items-center"><div><p className="font-semibold text-emerald-950">Required setup is complete</p><p className="text-sm text-emerald-700">Copy any passwords above, then log out and continue as a department head.</p></div><button type="button" onClick={() => void logout()} className="rounded-xl bg-emerald-700 px-5 py-2.5 font-semibold text-white">Log out and sign in as head</button></Card>}
    <ProgramTemplateImportModal isOpen={importOpen} onClose={() => setImportOpen(false)} programId={selectedProgram ? Number(selectedProgram) : undefined} onImported={() => setImportComplete(true)} />

    {issuedPasswords.length > 0 && <aside className="fixed bottom-5 right-5 z-40 w-[min(26rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-amber-300 bg-amber-50 shadow-2xl">
      <div className="flex items-start gap-3 border-b border-amber-200 px-4 py-3"><KeyRound className="mt-0.5 h-5 w-5 text-amber-700" /><div className="flex-1"><h2 className="font-semibold text-amber-950">Temporary passwords</h2><p className="text-xs text-amber-700">Visible only during this session.</p></div></div>
      <div className="max-h-64 divide-y divide-amber-200 overflow-y-auto">{issuedPasswords.map(item => <div key={item.id} className="grid grid-cols-[1fr_auto] gap-2 px-4 py-3 text-sm"><div><div className="font-medium text-amber-950">{item.username} <span className="text-xs font-normal text-amber-700">· {item.role}</span></div><code className="mt-1 block font-semibold">{item.password}</code></div><div className="flex items-center gap-1"><button type="button" className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-2 font-medium transition ${copiedPassword === item.id ? 'bg-emerald-600 text-white' : 'bg-white text-amber-800 hover:bg-amber-100'}`} onClick={() => void copyPassword(item)}>{copiedPassword === item.id ? <Check className="h-4 w-4" /> : <Clipboard className="h-4 w-4" />}{copiedPassword === item.id ? 'Copied' : 'Copy'}</button><button type="button" aria-label={`Dismiss ${item.username} password`} className="rounded-lg p-2 text-amber-700 hover:bg-amber-100" onClick={() => setIssuedPasswords(items => items.filter(password => password.id !== item.id))}><X className="h-4 w-4" /></button></div></div>)}</div>
    </aside>}

    <Dialog open={Boolean(editingDepartment)} onOpenChange={open => { if (!open) setEditingDepartment(null) }}><DialogContent><DialogHeader><DialogTitle>Edit department</DialogTitle></DialogHeader>{editingDepartment && <form onSubmit={saveDepartmentEdit} className="space-y-4"><input className={inputClass} value={editingDepartment.code} onChange={e => setEditingDepartment({ ...editingDepartment, code: e.target.value })} required /><input className={inputClass} value={editingDepartment.name} onChange={e => setEditingDepartment({ ...editingDepartment, name: e.target.value })} required /><button className="w-full rounded-xl bg-primary-600 px-4 py-2.5 font-semibold text-white">Save changes</button></form>}</DialogContent></Dialog>

    <Dialog open={Boolean(editingProgram)} onOpenChange={open => { if (!open) setEditingProgram(null) }}><DialogContent><DialogHeader><DialogTitle>Edit academic program</DialogTitle></DialogHeader>{editingProgram && <form onSubmit={saveProgramEdit} className="space-y-4"><select className={inputClass} value={editingProgram.department} onChange={e => setEditingProgram({ ...editingProgram, department: Number(e.target.value) })}>{departments.map(item => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select><input className={inputClass} value={editingProgram.code} onChange={e => setEditingProgram({ ...editingProgram, code: e.target.value })} required /><input className={inputClass} value={editingProgram.name} onChange={e => setEditingProgram({ ...editingProgram, name: e.target.value })} required /><button className="w-full rounded-xl bg-primary-600 px-4 py-2.5 font-semibold text-white">Save changes</button></form>}</DialogContent></Dialog>

    <Dialog open={Boolean(editingStaff)} onOpenChange={open => { if (!open) setEditingStaff(null) }}><DialogContent><DialogHeader><DialogTitle>Edit {editingStaff?.role === 'program_head' ? 'department head' : 'instructor'}</DialogTitle></DialogHeader>{editingStaff && <form onSubmit={saveStaffEdit} className="space-y-3"><select className={inputClass} value={staffDraft.department_id} onChange={e => setStaffDraft({ ...staffDraft, department_id: e.target.value })}>{departments.map(item => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select><input className={inputClass} value={staffDraft.username} onChange={e => setStaffDraft({ ...staffDraft, username: e.target.value })} placeholder="Username" required /><div className="grid grid-cols-2 gap-3"><input className={inputClass} value={staffDraft.first_name} onChange={e => setStaffDraft({ ...staffDraft, first_name: e.target.value })} placeholder="First name" /><input className={inputClass} value={staffDraft.last_name} onChange={e => setStaffDraft({ ...staffDraft, last_name: e.target.value })} placeholder="Last name" /></div><input className={inputClass} type="email" value={staffDraft.email} onChange={e => setStaffDraft({ ...staffDraft, email: e.target.value })} placeholder="Email" /><input className={inputClass} value={staffDraft.title} onChange={e => setStaffDraft({ ...staffDraft, title: e.target.value })} placeholder="Academic title (e.g. Professor)" /><div className="flex gap-3"><button type="button" onClick={() => void deleteStaff()} className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2.5 font-semibold text-red-700 hover:bg-red-50"><Trash2 className="h-4 w-4" /> Delete</button><button className="flex-1 rounded-xl bg-primary-600 px-4 py-2.5 font-semibold text-white">Save changes</button></div></form>}</DialogContent></Dialog>
  </div>
}

const AccountForm = ({ account, setAccount, departments, role, onSubmit }: { account: Account; setAccount: Dispatch<SetStateAction<Account>>; departments: Department[]; role: 'program_head' | 'instructor'; onSubmit: (event: FormEvent, role: string) => void }) => <form onSubmit={event => onSubmit(event, role)} className="grid gap-3 sm:grid-cols-2"><select className={inputClass} value={account.department_id} onChange={e => setAccount({ ...account, role, department_id: e.target.value })} required><option value="">Department</option>{departments.map(item => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select><input className={inputClass} placeholder="Username" value={account.username} onChange={e => setAccount({ ...account, role, username: e.target.value })} required /><input className={inputClass} placeholder="First name" value={account.first_name} onChange={e => setAccount({ ...account, role, first_name: e.target.value })} /><input className={inputClass} placeholder="Last name" value={account.last_name} onChange={e => setAccount({ ...account, role, last_name: e.target.value })} /><input className={inputClass} type="email" placeholder="Email" value={account.email} onChange={e => setAccount({ ...account, role, email: e.target.value })} /><input className={inputClass} placeholder="Academic title (e.g. Professor)" value={account.title} onChange={e => setAccount({ ...account, role, title: e.target.value })} /><button className="rounded-xl bg-primary-600 px-5 py-2.5 font-semibold text-white sm:col-span-2">Create {role === 'program_head' ? 'head' : 'instructor'} account</button></form>

const StaffList = ({ users, onReset, onEdit }: { users: StaffUser[]; onReset: (user: StaffUser) => Promise<void>; onEdit: (user: StaffUser) => void }) => users.length ? <div className="mt-5 space-y-2">{users.map(user => <div key={user.id} className="flex flex-wrap items-center gap-3 rounded-xl bg-secondary-50 px-4 py-3 text-sm"><Users className="h-4 w-4 text-secondary-500" /><span className="font-medium">{user.title && `${user.title} `}{user.first_name} {user.last_name || user.username}</span><span className="text-secondary-500">{user.department}</span><span className={`ml-auto inline-flex items-center gap-1 ${user.must_change_password ? 'text-amber-700' : 'text-emerald-700'}`}>{user.must_change_password ? <Circle className="h-3 w-3 fill-current" /> : <Check className="h-4 w-4" />}{user.must_change_password ? 'Change required' : 'Password changed'}</span><button type="button" className="rounded-lg bg-white px-3 py-1.5 font-medium text-primary-700 hover:bg-primary-50" onClick={() => void onReset(user)}>Reset password</button><button type="button" aria-label={`Edit ${user.username}`} className="rounded-lg p-2 text-secondary-600 hover:bg-secondary-200" onClick={() => onEdit(user)}><Pencil className="h-4 w-4" /></button></div>)}</div> : null

export default SystemAdminDashboard
