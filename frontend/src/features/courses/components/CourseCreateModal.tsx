import React, { useState, useCallback, useMemo, useEffect } from 'react'
import Modal from '../../../shared/components/ui/Modal'
import {
  useCoreCoursesCreate,
  useCoreCoursesPartialUpdate,
  useCoreCourseTemplatesList,
  useCoreCourseTemplatesInstantiateCreate,
  useCoreCourseTemplatesCreate,
  useCoreProgramsList,
  useCoreTermsList,
  useCoreTermsActiveRetrieve
} from '../../../shared/api/generated/core/core'
import { useCoreAnalyticsProgramStatsRetrieve } from '../../../shared/api/generated/analytics/analytics'
import { useAuth } from '../../auth/hooks/useAuth'
import type { CourseTemplate } from '../../../shared/api/model'
import InstructorSelect from './InstructorSelect'

interface CourseCreateModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const inputClass = 'block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition'

const CourseCreateModal: React.FC<CourseCreateModalProps> = React.memo(({
  isOpen, onClose, onSuccess
}) => {
  const { user } = useAuth()

  const [flowType, setFlowType] = useState<'blank' | 'template'>('blank')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [credits, setCredits] = useState<number | ''>(3)
  const [programOption, setProgramOption] = useState<'my_program' | 'select'>('my_program')
  const [programId, setProgramId] = useState<number | ''>('')
  const [termOption, setTermOption] = useState<'active' | 'select'>('active')
  const [termId, setTermId] = useState<number | ''>('')
  const [courseTemplateId, setCourseTemplateId] = useState<number | ''>('')
  const [instructorIds, setInstructorIds] = useState<number[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showTemplatePrompt, setShowTemplatePrompt] = useState(false)
  const [templatePromptCourse, setTemplatePromptCourse] = useState<{
    name: string; code: string; credits: number | undefined; program_id: number
  } | null>(null)

  // Fetch program head's program stats to resolve program for "My program" option
  const { data: statsData } = useCoreAnalyticsProgramStatsRetrieve({
    query: { enabled: isOpen && user?.role === 'program_head' }
  })

  const myProgramId = useMemo(() => {
    // For program heads, the program comes from the analytics stats endpoint
    if (user?.role === 'program_head') {
      return statsData?.programs?.[0]?.id ?? null
    }
    // For other user types, try legacy nested profile fields (may not exist)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const u = user as any
    return u?.program_head_profile?.program_id ?? u?.student_profile?.program_id ?? null
  }, [user, statsData])

  const { data: activeTerm } = useCoreTermsActiveRetrieve({
    query: { enabled: isOpen && termOption === 'active' }
  })

  const { data: templatesData } = useCoreCourseTemplatesList(undefined, {
    query: { enabled: isOpen && flowType === 'template' }
  })

  // Auto-populate name/code/credits when a template is selected
  useEffect(() => {
    if (flowType === 'template' && courseTemplateId !== '' && templatesData?.results) {
      const template = templatesData.results.find((t: CourseTemplate) => t.id === Number(courseTemplateId))
      if (template) {
        setName(template.name)
        setCode(template.code)
        setCredits(template.credits ?? 3)
      }
    }
  }, [flowType, courseTemplateId, templatesData])

  const { data: programsData } = useCoreProgramsList(undefined, {
    query: { enabled: isOpen && programOption === 'select' }
  })

  const { data: termsData } = useCoreTermsList(undefined, {
    query: { enabled: isOpen && termOption === 'select' }
  })

  const createMutation = useCoreCoursesCreate({
    mutation: {
      onError: (err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to create course')
      }
    }
  })

  const instantiateMutation = useCoreCourseTemplatesInstantiateCreate({
    mutation: {
      onSuccess: async (createdCourse) => {
        try {
          await patchMutation.mutateAsync({
            id: (createdCourse as { id: number }).id,
            data: {
              name: name.trim(),
              code: code.trim(),
              credits: credits === '' ? undefined : Number(credits),
              program_id: programOption === 'my_program' && myProgramId ? myProgramId : (programId === '' ? undefined : Number(programId)),
              instructor_ids: instructorIds,
            }
          })
          onSuccess()
          handleClose()
        } catch (err: unknown) {
          setError(err instanceof Error ? err.message : 'Failed to update instantiated course')
        }
      },
      onError: (err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to instantiate template')
      }
    }
  })

  const patchMutation = useCoreCoursesPartialUpdate()

  const templateCreateMutation = useCoreCourseTemplatesCreate()

  const handleClose = useCallback(() => {
    setFlowType('blank')
    setName('')
    setCode('')
    setCredits('')
    setInstructorIds([])
    setProgramOption('my_program')
    setProgramId('')
    setTermOption('active')
    setTermId('')
    setCourseTemplateId('')
    setError(null)
    setShowTemplatePrompt(false)
    setTemplatePromptCourse(null)
    onClose()
  }, [onClose])

  const handleTemplatePromptYes = useCallback(async () => {
    if (templatePromptCourse) {
      try {
        await templateCreateMutation.mutateAsync({
          data: {
            name: templatePromptCourse.name,
            code: templatePromptCourse.code,
            credits: templatePromptCourse.credits,
            program_id: templatePromptCourse.program_id
          }
        })
      } catch {
        // Silently fail template creation — course was already created
      }
    }
    onSuccess()
    handleClose()
  }, [onSuccess, handleClose, templatePromptCourse, templateCreateMutation])

  const handleTemplatePromptNo = useCallback(() => {
    onSuccess()
    handleClose()
  }, [onSuccess, handleClose])

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (flowType !== 'template') {
      if (!name.trim()) {
        setError('Course name is required')
        return
      }
      if (!code.trim()) {
        setError('Course code is required')
        return
      }
    }

    const resolvedProgramId = programOption === 'my_program' && myProgramId
      ? myProgramId
      : (programId === '' ? undefined : Number(programId))

    const resolvedTermId = termOption === 'active' && activeTerm
      ? activeTerm.id
      : (termId === '' ? undefined : Number(termId))

    if (resolvedProgramId === undefined) {
      setError('Please select a program')
      return
    }

    if (resolvedTermId === undefined) {
      setError('Please select a term')
      return
    }

    if (flowType === 'blank') {
      await createMutation.mutateAsync({
        data: {
          name: name.trim(),
          code: code.trim(),
          credits: credits === '' ? undefined : Number(credits),
          program_id: resolvedProgramId,
          term_id: resolvedTermId,
          instructor_ids: instructorIds,
        }
      })
      setTemplatePromptCourse({
        name: name.trim(),
        code: code.trim(),
        credits: credits === '' ? undefined : Number(credits),
        program_id: resolvedProgramId
      })
      setShowTemplatePrompt(true)
    } else {
      if (courseTemplateId === '') {
        setError('Please select a course template')
        return
      }
      await instantiateMutation.mutateAsync({
        id: Number(courseTemplateId),
        data: {
          term_id: resolvedTermId
        }
      })
    }
  }, [name, code, credits, instructorIds, flowType, programOption, myProgramId, programId, termOption, activeTerm, termId, courseTemplateId, createMutation, instantiateMutation])

  if (showTemplatePrompt) {
    return (
      <Modal isOpen={isOpen} onClose={handleTemplatePromptNo} title="Create Template?" size="sm">
        <p className="text-sm text-secondary-600 mb-6">
          Would you like to create a corresponding template for this course?
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={handleTemplatePromptNo}
            className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors"
          >
            No
          </button>
          <button
            onClick={handleTemplatePromptYes}
            className="px-4 py-2 text-sm font-semibold text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
          >
            Yes
          </button>
        </div>
      </Modal>
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Create Course" size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-danger-50 border border-danger-200 rounded-xl p-4">
            <p className="text-sm text-danger-600">{error}</p>
          </div>
        )}

        <div className="space-y-2">
          <label className="block text-sm font-medium text-secondary-700">Create Method</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="blank"
                checked={flowType === 'blank'}
                onChange={() => setFlowType('blank')}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-secondary-700">Blank</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="template"
                checked={flowType === 'template'}
                onChange={() => setFlowType('template')}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-secondary-700">From Template</span>
            </label>
          </div>
        </div>

        {flowType === 'template' && (
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-1">Course Template</label>
            <select
              value={courseTemplateId}
              onChange={(e) => setCourseTemplateId(e.target.value === '' ? '' : Number(e.target.value))}
              className={inputClass}
            >
              <option value="">Select a template...</option>
              {templatesData?.results?.map((t) => (
                <option key={t.id} value={t.id}>{t.code} - {t.name}</option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Course Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={flowType === 'template'}
            className={`${inputClass} ${flowType === 'template' ? 'bg-secondary-50 cursor-not-allowed' : ''}`}
            placeholder="e.g., Introduction to Computer Science"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Course Code</label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={flowType === 'template'}
            className={`${inputClass} ${flowType === 'template' ? 'bg-secondary-50 cursor-not-allowed' : ''}`}
            placeholder="e.g., CS101"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-1">Credits</label>
          <input
            type="number"
            value={credits}
            onChange={(e) => setCredits(e.target.value === '' ? '' : Number(e.target.value))}
            disabled={flowType === 'template'}
            className={`${inputClass} ${flowType === 'template' ? 'bg-secondary-50 cursor-not-allowed' : ''}`}
            placeholder="e.g., 3"
            min={0}
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-secondary-700">Program</label>
          <div className="flex gap-4">
            <label className={`flex items-center gap-2 cursor-pointer ${!myProgramId ? 'opacity-50 cursor-not-allowed' : ''}`}>
              <input
                type="radio"
                value="my_program"
                checked={programOption === 'my_program'}
                onChange={() => setProgramOption('my_program')}
                disabled={!myProgramId}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-secondary-700">My program</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="select"
                checked={programOption === 'select'}
                onChange={() => setProgramOption('select')}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-secondary-700">Select</span>
            </label>
          </div>
          {programOption === 'select' && (
            <select
              value={programId}
              onChange={(e) => setProgramId(e.target.value === '' ? '' : Number(e.target.value))}
              className={inputClass}
            >
              <option value="">Select a program...</option>
              {programsData?.results?.map((p) => (
                <option key={p.id} value={p.id}>{p.code} - {p.name}</option>
              ))}
            </select>
          )}
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-secondary-700">Term</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="active"
                checked={termOption === 'active'}
                onChange={() => setTermOption('active')}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-secondary-700">Active term</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                value="select"
                checked={termOption === 'select'}
                onChange={() => setTermOption('select')}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-secondary-700">Select</span>
            </label>
          </div>
          {termOption === 'select' && (
            <select
              value={termId}
              onChange={(e) => setTermId(e.target.value === '' ? '' : Number(e.target.value))}
              className={inputClass}
            >
              <option value="">Select a term...</option>
              {termsData?.results?.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          )}
        </div>

        <InstructorSelect
          key={isOpen ? 'create-open' : 'create-closed'}
          selectedIds={instructorIds}
          onChange={setInstructorIds}
        />

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={handleClose}
            disabled={createMutation.isPending || instantiateMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending || instantiateMutation.isPending}
            className="px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50"
          >
            {createMutation.isPending || instantiateMutation.isPending ? 'Creating...' : 'Create Course'}
          </button>
        </div>
      </form>
    </Modal>
  )
})

CourseCreateModal.displayName = 'CourseCreateModal'

export default CourseCreateModal
