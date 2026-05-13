import { useState, useEffect, useMemo } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  DndContext,
  DragOverlay,
  pointerWithin,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from '@dnd-kit/core'
import { useDraggable, useDroppable } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { Card } from '@/components/ui/custom/Card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/shadcn/Dialog'
import {
  XMarkIcon,
  LinkIcon,
  AcademicCapIcon,
  ClipboardDocumentListIcon,
  ChartBarIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline'
import {
  useEvaluationAssessmentsList,
  useEvaluationAssessmentLoMappingsList,
  useEvaluationAssessmentLoMappingsBulkSyncCreate,
  getEvaluationAssessmentLoMappingsListQueryKey,
} from '../../../shared/api/generated/evaluation/evaluation'
import {
  useCoreLoPoMappingsList,
  useCoreLoPoMappingsBulkSyncCreate,
  useCoreCoursesLearningOutcomesRetrieve,
  getCoreLoPoMappingsListQueryKey,
} from '../../../shared/api/generated/core/core'
import {
  useCoreProgramOutcomesList,
} from '../../../shared/api/generated/outcomes/outcomes'
import {
  useV1CoreWeightSuggestionCreate,
} from '../../../shared/api/generated/v1/v1'
import { v1CoreWeightSuggestionRetrieve } from '../../../shared/api/generated/v1/v1'
import type {
  Assessment as OrvalAssessment,
  AssessmentLearningOutcomeMapping,
  LearningOutcomeProgramOutcomeMapping,
  CoreLearningOutcome,
  ProgramOutcome,
  WeightSuggestionJobResult,
} from '../../../shared/api/model'
import { isRecord } from '@/shared/utils/guards'
import { useRecomputeJobs } from '../../../shared/contexts/RecomputeJobsContext'
import { AssessmentDescriptionsModal } from './AssessmentDescriptionsModal'

type Assessment = OrvalAssessment & { assessment_type: string }
type LearningOutcome = CoreLearningOutcome
type DragItemData = {
  id: number
  name?: string
  code?: string
}

const toList = <T,>(value: unknown): T[] => {
  if (Array.isArray(value)) {
    return value as T[]
  }

  if (isRecord(value) && Array.isArray(value.results)) {
    return value.results as T[]
  }

  return []
}

const toDragItemData = (value: unknown): DragItemData | null => {
  if (!isRecord(value) || typeof value.id !== 'number') {
    return null
  }

  return {
    id: value.id,
    name: typeof value.name === 'string' ? value.name : undefined,
    code: typeof value.code === 'string' ? value.code : undefined,
  }
}

const clone = <T,>(arr: T[]): T[] => arr.map(item => ({ ...item }))

interface MappingEditorProps {
  courseId: number
  termId: number
  onClose?: () => void
}

// Draggable Item Component
const DraggableItem = ({
  id,
  type,
  children,
  data,
}: {
  id: string
  type: 'assessment' | 'lo' | 'po'
  children: React.ReactNode
  data: DragItemData
}) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id,
    data: { type, ...data },
  })

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="cursor-grab active:cursor-grabbing"
    >
      {children}
    </div>
  )
}

// Droppable Zone Component
const DroppableZone = ({
  id,
  accepts,
  children,
  className = '',
}: {
  id: string
  accepts: string[]
  children: React.ReactNode
  className?: string
}) => {
  const { isOver, setNodeRef, active } = useDroppable({
    id,
    data: { accepts },
  })

  const canDrop = active?.data?.current?.type && accepts.includes(active.data.current.type)

  return (
    <div
      ref={setNodeRef}
      className={`${className} ${isOver && canDrop ? 'ring-2 ring-primary-500 bg-primary-50' : ''}`}
    >
      {children}
    </div>
  )
}

// Weight Input Modal
const WeightModal = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  fromLabel,
  toLabel,
  editMode = false,
  initialWeight = 0,
}: {
  isOpen: boolean
  onClose: () => void
  onConfirm: (weight: number) => void
  title: string
  fromLabel: string
  toLabel: string
  editMode?: boolean
  initialWeight?: number
}) => {
  const [weight, setWeight] = useState(0)
  const [isInitialized, setIsInitialized] = useState(false)

  const step = 1
  const maxAllowedWeight = 5

  // Reset weight when modal opens
  useEffect(() => {
    if (isOpen && !isInitialized) {
      if (editMode && initialWeight > 0) {
        setWeight(Math.round(initialWeight))
      } else {
        setWeight(1)
      }
      setIsInitialized(true)
    }
    if (!isOpen) {
      setIsInitialized(false)
    }
  }, [isOpen, isInitialized, editMode, initialWeight])

  if (!isOpen) return null

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-sm !z-[10000]" overlayClassName="!z-[10000]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="font-medium">{fromLabel}</span>
            <LinkIcon className="h-4 w-4" />
            <span className="font-medium">{toLabel}</span>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Weight for this mapping
            </label>
            <input
              id="weight-slider"
              type="range"
              min="0"
              max={maxAllowedWeight}
              step={step}
              value={Math.min(Math.max(0, weight), maxAllowedWeight)}
              onChange={(e) => {
                const raw = parseInt(e.target.value, 10)
                setWeight(raw)
              }}
              className="w-full"
              aria-label="Weight"
            />
            <div className="flex justify-between text-sm text-gray-500 mt-1">
              <span>0</span>
              <span className="font-bold text-primary-600">
                {weight}
              </span>
              <span>{maxAllowedWeight}</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              const finalWeight = weight
              onConfirm(finalWeight)
            }}
            disabled={weight <= 0}
            className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {editMode ? 'Update Mapping' : 'Create Mapping'}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// Main Component
const MappingEditor = ({ courseId, termId, onClose }: MappingEditorProps) => {

  // Data fetching
  const assessmentsQuery = useEvaluationAssessmentsList({ course: courseId })
  const losQuery = useCoreCoursesLearningOutcomesRetrieve(courseId)
  const posQuery = useCoreProgramOutcomesList({ term: termId })
  const aloQuery = useEvaluationAssessmentLoMappingsList(undefined, {
    request: { params: { course: courseId } },
  })
  const lopoQuery = useCoreLoPoMappingsList(undefined, {
    request: { params: { course: courseId } },
  })

  // Derived data from queries
  const assessments = useMemo(() => {
    return toList<Assessment>(assessmentsQuery.data)
  }, [assessmentsQuery.data])

  const learningOutcomes = useMemo(() => {
    return toList<LearningOutcome>(losQuery.data)
  }, [losQuery.data])

  const programOutcomes = useMemo(() => {
    return toList<ProgramOutcome>(posQuery.data)
  }, [posQuery.data])

  // Initial state (frozen snapshot from server on modal open)
  const [initialAssessmentLOMappings, setInitialAssessmentLOMappings] = useState<AssessmentLearningOutcomeMapping[]>([])
  const [initialLoPOMappings, setInitialLoPOMappings] = useState<LearningOutcomeProgramOutcomeMapping[]>([])
  // Working state (editable copy, all mutations applied here)
  const [workingAssessmentLOMappings, setWorkingAssessmentLOMappings] = useState<AssessmentLearningOutcomeMapping[]>([])
  const [workingLoPOMappings, setWorkingLoPOMappings] = useState<LearningOutcomeProgramOutcomeMapping[]>([])

  const [hasInitialized, setHasInitialized] = useState(false)

  useEffect(() => {
    if (!hasInitialized && aloQuery.data && lopoQuery.data && !aloQuery.isFetching && !lopoQuery.isFetching) {
      const aloData = toList<AssessmentLearningOutcomeMapping>(aloQuery.data)
      const lopoData = toList<LearningOutcomeProgramOutcomeMapping>(lopoQuery.data)
      setInitialAssessmentLOMappings(clone(aloData))
      setInitialLoPOMappings(clone(lopoData))
      setWorkingAssessmentLOMappings(clone(aloData))
      setWorkingLoPOMappings(clone(lopoData))
      setHasInitialized(true)
    }
  }, [aloQuery.data, lopoQuery.data, aloQuery.isFetching, lopoQuery.isFetching, hasInitialized])

  // Loading state
  const isLoading = assessmentsQuery.isLoading || losQuery.isLoading || posQuery.isLoading || aloQuery.isLoading || lopoQuery.isLoading

  const [isSaving, setIsSaving] = useState(false)
  const [showCloseConfirm, setShowCloseConfirm] = useState(false)

  const [isSuggesting, setIsSuggesting] = useState(false)
  const [suggestionError, setSuggestionError] = useState<string | null>(null)

  const [showDescriptionsModal, setShowDescriptionsModal] = useState(false)

  const aloBulkSyncMutation = useEvaluationAssessmentLoMappingsBulkSyncCreate()
  const lopoBulkSyncMutation = useCoreLoPoMappingsBulkSyncCreate()

  const queryClient = useQueryClient()

  const { enqueueJobs } = useRecomputeJobs()

  const createSuggestionMutation = useV1CoreWeightSuggestionCreate()

  const [activeId, setActiveId] = useState<string | null>(null)
  const [activeData, setActiveData] = useState<DragItemData | null>(null)

  // Weight modal state
  const [weightModal, setWeightModal] = useState<{
    isOpen: boolean
    type: 'assessment-lo' | 'lo-po'
    fromId: number
    toId: number
    fromLabel: string
    toLabel: string
    editMode?: boolean
    mappingId?: number
    initialWeight?: number
  } | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  )

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
    setActiveData(toDragItemData(event.active.data.current))
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)
    setActiveData(null)

    if (!over) return

    const activeType = isRecord(active.data.current) && typeof active.data.current.type === 'string'
      ? active.data.current.type
      : undefined
    const activeDragData = toDragItemData(active.data.current)
    const overId = over.id as string

    // Assessment dropped on LO
    if (activeType === 'assessment' && activeDragData && overId.startsWith('lo-drop-')) {
      const loId = parseInt(overId.replace('lo-drop-', ''))
      const assessmentId = activeDragData.id
      const assessment = assessments.find((a) => a.id === assessmentId)
      const lo = learningOutcomes.find((l) => l.id === loId)

      // Check if mapping already exists
      const existingMapping = workingAssessmentLOMappings.find(
        (m) => m.assessment === assessmentId && m.learning_outcome?.id === loId
      )

      if (existingMapping) {
        // Edit existing mapping
        setWeightModal({
          isOpen: true,
          type: 'assessment-lo',
          fromId: assessmentId,
          toId: loId,
          fromLabel: assessment?.name || '',
          toLabel: lo?.code || '',
          editMode: true,
          mappingId: existingMapping.id,
          initialWeight: existingMapping.weight,
        })
      } else {
        // Create new mapping
        setWeightModal({
          isOpen: true,
          type: 'assessment-lo',
          fromId: assessmentId,
          toId: loId,
          fromLabel: assessment?.name || '',
          toLabel: lo?.code || '',
        })
      }
    }

    // LO dropped on PO
    if (activeType === 'lo' && activeDragData && overId.startsWith('po-drop-')) {
      const poId = parseInt(overId.replace('po-drop-', ''))
      const loId = activeDragData.id
      const lo = learningOutcomes.find((l) => l.id === loId)
      const po = programOutcomes.find((p) => p.id === poId)

      // Check if mapping already exists
      const existingMapping = workingLoPOMappings.find(
        (m) => m.learning_outcome?.id === loId && m.program_outcome?.id === poId
      )

      if (existingMapping) {
        // Edit existing mapping
        setWeightModal({
          isOpen: true,
          type: 'lo-po',
          fromId: loId,
          toId: poId,
          fromLabel: lo?.code || '',
          toLabel: po?.code || '',
          editMode: true,
          mappingId: existingMapping.id,
          initialWeight: existingMapping.weight,
        })
      } else {
        // Create new mapping
        setWeightModal({
          isOpen: true,
          type: 'lo-po',
          fromId: loId,
          toId: poId,
          fromLabel: lo?.code || '',
          toLabel: po?.code || '',
        })
      }
    }

    setActiveId(null)
  }

  const computeDiff = <T extends { id: number; weight: number }>(
    working: T[],
    initial: T[]
  ): { creates: T[]; updates: { id: number; weight: number }[]; deletes: number[] } => {
    const workingMap = new Map(working.map(m => [m.id, m]))
    const initialMap = new Map(initial.map(m => [m.id, m]))
    const workingIds = new Set(workingMap.keys())
    const initialIds = new Set(initialMap.keys())

    const creates = working.filter(m => m.id < 0)
    const deletes = initial.filter(m => !workingIds.has(m.id)).map(m => m.id)
    const updates = working
      .filter(m => m.id > 0 && initialIds.has(m.id))
      .filter(m => {
        const initialItem = initialMap.get(m.id)
        return initialItem && initialItem.weight !== m.weight
      })
      .map(m => ({ id: m.id, weight: m.weight }))

    return { creates, updates, deletes }
  }

  const hasChanges = useMemo(() => {
    const aloDiff = computeDiff(workingAssessmentLOMappings, initialAssessmentLOMappings)
    const lopoDiff = computeDiff(workingLoPOMappings, initialLoPOMappings)
    return (
      aloDiff.creates.length > 0 ||
      aloDiff.updates.length > 0 ||
      aloDiff.deletes.length > 0 ||
      lopoDiff.creates.length > 0 ||
      lopoDiff.updates.length > 0 ||
      lopoDiff.deletes.length > 0
    )
  }, [workingAssessmentLOMappings, initialAssessmentLOMappings, workingLoPOMappings, initialLoPOMappings])

  const handleSave = async (closeAfterSave = false) => {
    setIsSaving(true)
    try {
      const aloDiff = computeDiff(workingAssessmentLOMappings, initialAssessmentLOMappings)
      const lopoDiff = computeDiff(workingLoPOMappings, initialLoPOMappings)

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const aloResult: any = await aloBulkSyncMutation.mutateAsync({
        /* eslint-disable @typescript-eslint/no-explicit-any */
        data: {
          course_id: courseId,
          creates: aloDiff.creates.map(m => ({
            temp_id: m.id,
            assessment_id: (m as any).assessment_id ?? (m as any).assessment,
            learning_outcome_id: (m as any).learning_outcome_id ?? (m as any).learning_outcome?.id,
            weight: m.weight,
          })),
          updates: aloDiff.updates,
          deletes: aloDiff.deletes,
        } as any,
        /* eslint-enable @typescript-eslint/no-explicit-any */
      })

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const lopoResult: any = await lopoBulkSyncMutation.mutateAsync({
        /* eslint-disable @typescript-eslint/no-explicit-any */
        data: {
          course_id: courseId,
          creates: lopoDiff.creates.map(m => ({
            temp_id: m.id,
            learning_outcome_id: (m as any).learning_outcome_id ?? (m as any).learning_outcome?.id,
            program_outcome_id: (m as any).program_outcome_id ?? (m as any).program_outcome?.id,
            weight: m.weight,
          })),
          updates: lopoDiff.updates,
          deletes: lopoDiff.deletes,
        } as any,
        /* eslint-enable @typescript-eslint/no-explicit-any */
      })

      // Replace temp IDs with real IDs
      const tempIdMap = new Map<number, number>()
      for (const item of aloResult.created || []) {
        if (item.temp_id) tempIdMap.set(item.temp_id, item.id)
      }
      for (const item of lopoResult.created || []) {
        if (item.temp_id) tempIdMap.set(item.temp_id, item.id)
      }

      const updatedALO = workingAssessmentLOMappings.map(m => {
        const newId = tempIdMap.get(m.id)
        return newId !== undefined ? { ...m, id: newId } : m
      })
      const updatedLOPO = workingLoPOMappings.map(m => {
        const newId = tempIdMap.get(m.id)
        return newId !== undefined ? { ...m, id: newId } : m
      })

      setWorkingAssessmentLOMappings(updatedALO)
      setWorkingLoPOMappings(updatedLOPO)
      setInitialAssessmentLOMappings(clone(updatedALO))
      setInitialLoPOMappings(clone(updatedLOPO))

      // Invalidate mapping list queries to prevent stale data when the modal reopens.
      // The global QueryClient has a 5-minute staleTime, so without invalidation
      // the cached data would remain "fresh" and React Query would not refetch
      // when this component remounts after the modal is closed and reopened.
      queryClient.invalidateQueries({
        queryKey: getEvaluationAssessmentLoMappingsListQueryKey(),
      })
      queryClient.invalidateQueries({
        queryKey: getCoreLoPoMappingsListQueryKey(),
      })

      const allJobIds = [
        ...(aloResult?.recompute_job_ids || []),
        ...(lopoResult?.recompute_job_ids || []),
      ].map((id: number) => ({ id, status: 'pending' as const }))
      if (allJobIds.length > 0) {
        enqueueJobs(allJobIds)
      }

      if (closeAfterSave) {
        onClose?.()
      }
    } catch (error) {
      console.error('Bulk sync failed:', error)
      alert('Failed to save changes. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleCreateOrUpdateMapping = (weight: number) => {
    if (!weightModal) return

    if (weightModal.editMode && weightModal.mappingId) {
      // Update existing mapping in working state (no API call)
      if (weightModal.type === 'assessment-lo') {
        setWorkingAssessmentLOMappings(prev =>
          prev.map(m => m.id === weightModal.mappingId ? { ...m, weight } : m)
        )
      } else {
        setWorkingLoPOMappings(prev =>
          prev.map(m => m.id === weightModal.mappingId ? { ...m, weight } : m)
        )
      }
    } else {
      // Create new mapping in working state with temp negative ID
      const tempId = -Date.now()
      if (weightModal.type === 'assessment-lo') {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const newMapping: any = {
          id: tempId,
          assessment: weightModal.fromId,
          learning_outcome: { id: weightModal.toId },
          learning_outcome_id: weightModal.toId,
          weight,
        }
        setWorkingAssessmentLOMappings(prev => [...prev, newMapping])
      } else {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const newMapping: any = {
          id: tempId,
          course: courseId,
          learning_outcome: { id: weightModal.fromId },
          program_outcome: { id: weightModal.toId },
          weight,
        }
        setWorkingLoPOMappings(prev => [...prev, newMapping])
      }
    }
    setWeightModal(null)
  }

  const handleDeleteMapping = (mappingId: number, type: 'assessment-lo' | 'lo-po') => {
    if (type === 'assessment-lo') {
      setWorkingAssessmentLOMappings(prev => prev.filter(m => m.id !== mappingId))
    } else {
      setWorkingLoPOMappings(prev => prev.filter(m => m.id !== mappingId))
    }
  }

  const handleReset = () => {
    setWorkingAssessmentLOMappings(clone(initialAssessmentLOMappings))
    setWorkingLoPOMappings(clone(initialLoPOMappings))
  }

  // Get mappings for a specific LO
  const getAssessmentMappingsForLO = (loId: number) => {
    return workingAssessmentLOMappings.filter((m) => m.learning_outcome?.id === loId)
  }

  const getPOMappingsForLO = (loId: number) => {
    return workingLoPOMappings.filter((m) => m.learning_outcome?.id === loId)
  }

  // Get LO mappings for a specific PO
  const getLOMappingsForPO = (poId: number) => {
    return workingLoPOMappings.filter((m) => m.program_outcome?.id === poId)
  }

  const queueWeightSuggestion = async () => {
    /* eslint-disable @typescript-eslint/no-explicit-any */
    setIsSuggesting(true)
    setSuggestionError(null)
    try {
      const job = await createSuggestionMutation.mutateAsync({
        data: { course_id: courseId } as any,
      })

      let attempts = 0
      const maxAttempts = 60
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        const updated = await v1CoreWeightSuggestionRetrieve(job.id)
        if (updated.status === 'success') {
          const result = updated.result as WeightSuggestionJobResult
          if (result && typeof result === 'object' && 'assessment_lo' in result) {
            const assessmentLo = (result as any).assessment_lo as Record<string, Record<string, number>>
            setWorkingAssessmentLOMappings(prev => {
              const existingByKey = new Map<string, AssessmentLearningOutcomeMapping>()
              for (const m of prev) {
                const aId = typeof m.assessment === 'number' ? m.assessment : (m as any).assessment_id
                const loId = m.learning_outcome?.id
                if (aId !== undefined && loId !== undefined) {
                  existingByKey.set(`${aId}-${loId}`, m)
                }
              }

              const next: AssessmentLearningOutcomeMapping[] = []

              for (const m of prev) {
                const assessmentId = typeof m.assessment === 'number' ? m.assessment : (m as any).assessment_id
                const assessmentName = assessments.find(a => a.id === assessmentId)?.name
                const loId = m.learning_outcome?.id
                const loCode = learningOutcomes.find(lo => lo.id === loId)?.code
                if (assessmentName && loCode && assessmentLo[assessmentName]?.[loCode] !== undefined) {
                  next.push({ ...m, weight: assessmentLo[assessmentName][loCode] })
                } else {
                  next.push(m)
                }
              }

              for (const [assessmentName, loWeights] of Object.entries(assessmentLo)) {
                const assessment = assessments.find(a => a.name === assessmentName)
                if (!assessment) continue
                for (const [loCode, weight] of Object.entries(loWeights)) {
                  const lo = learningOutcomes.find(l => l.code === loCode)
                  if (!lo) continue
                  const key = `${assessment.id}-${lo.id}`
                  if (!existingByKey.has(key)) {
                    const tempId = -Date.now()
                    next.push({
                      id: tempId,
                      assessment: assessment.id,
                      assessment_id: assessment.id,
                      learning_outcome: { id: lo.id },
                      learning_outcome_id: lo.id,
                      weight,
                    } as AssessmentLearningOutcomeMapping)
                  }
                }
              }

              return next
            })
          }

          const loPo = (result as any).lo_po as Record<string, Record<string, number>> | undefined
          if (loPo) {
            setWorkingLoPOMappings(prev => {
              const existingByKey = new Map<string, LearningOutcomeProgramOutcomeMapping>()
              for (const m of prev) {
                const loId = m.learning_outcome?.id
                const poId = m.program_outcome?.id
                if (loId !== undefined && poId !== undefined) {
                  existingByKey.set(`${loId}-${poId}`, m)
                }
              }

              const next: LearningOutcomeProgramOutcomeMapping[] = []

              for (const m of prev) {
                const loId = m.learning_outcome?.id
                const loCode = learningOutcomes.find(lo => lo.id === loId)?.code
                const poId = m.program_outcome?.id
                const poCode = programOutcomes.find(po => po.id === poId)?.code
                if (loCode && poCode && loPo?.[loCode]?.[poCode] !== undefined) {
                  next.push({ ...m, weight: loPo[loCode][poCode] })
                } else {
                  next.push(m)
                }
              }

              for (const [loCode, poWeights] of Object.entries(loPo)) {
                const lo = learningOutcomes.find(l => l.code === loCode)
                if (!lo) continue
                for (const [poCode, weight] of Object.entries(poWeights)) {
                  const po = programOutcomes.find(p => p.code === poCode)
                  if (!po) continue
                  const key = `${lo.id}-${po.id}`
                  if (!existingByKey.has(key)) {
                    next.push({
                      id: -Date.now(),
                      course: courseId,
                      learning_outcome: { id: lo.id },
                      learning_outcome_id: lo.id,
                      program_outcome: { id: po.id },
                      program_outcome_id: po.id,
                      weight,
                    } as LearningOutcomeProgramOutcomeMapping)
                  }
                }
              }

              return next
            })
          }
          break
        } else if (updated.status === 'failed') {
          setSuggestionError('Weight suggestion failed. Please try again.')
          break
        }
        attempts++
      }
      if (attempts >= maxAttempts) {
        setSuggestionError('Weight suggestion timed out. Please try again.')
      }
    } catch (err) {
      setSuggestionError('Failed to get weight suggestions. Please try again.')
      console.error('Weight suggestion error:', err)
    } finally {
      setIsSuggesting(false)
    }
    /* eslint-enable @typescript-eslint/no-explicit-any */
  }

  const handleSuggestWeights = async () => {
    const needsDescriptions = assessments.some(a => !a.description?.trim())
    if (needsDescriptions) {
      setShowDescriptionsModal(true)
    } else {
      await queueWeightSuggestion()
    }
  }

  const handleDescriptionsSubmit = async () => {
    setShowDescriptionsModal(false)
    await queueWeightSuggestion()
  }

  const showSkeleton = isLoading || !hasInitialized

  if (showSkeleton) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-7 w-56 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 w-96 bg-gray-100 rounded animate-pulse" />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-9 w-36 bg-gray-200 rounded-lg animate-pulse" />
            <div className="h-9 w-9 bg-gray-200 rounded-lg animate-pulse" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-6">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-5 w-5 bg-gray-200 rounded animate-pulse" />
                <div className="h-5 w-28 bg-gray-200 rounded animate-pulse" />
              </div>
              {[0, 1, 2, 3].map((j) => (
                <div
                  key={j}
                  className="h-12 bg-gray-100 rounded-lg animate-pulse"
                  style={{ animationDelay: `${j * 100}ms` }}
                />
              ))}
            </div>
          ))}
        </div>
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
          <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse" />
          <div className="h-10 w-32 bg-gray-200 rounded-lg animate-pulse" />
        </div>
      </div>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={pointerWithin}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full flex-col gap-6" data-has-changes={String(hasChanges)}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Outcome Mapping Editor</h2>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-gray-500">
                Drag assessments to learning outcomes, and learning outcomes to program outcomes
              </p>
              <div className="group relative flex-shrink-0">
                <QuestionMarkCircleIcon className="h-5 w-5 text-gray-400 hover:text-gray-600 cursor-help" />
                <div className="absolute left-0 top-8 hidden group-hover:block z-50 w-80 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl">
                  <div className="space-y-1.5">
                    <p><span className="font-semibold">Drag & Drop:</span> Assessment → LO or LO → PO</p>
                    <p><span className="font-semibold">Edit:</span> Click badge to change weight</p>
                    <p><span className="font-semibold">Delete:</span> Click X on badge</p>
                    <p className="text-gray-300 mt-2">Each column scrolls independently</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
           <div className="flex items-center gap-2">
            <button
              onClick={handleSuggestWeights}
              disabled={isSuggesting || assessments.length === 0}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="AI Weight Suggestion"
            >
              {isSuggesting ? (
                <div className="h-4 w-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              )}
              <span>{isSuggesting ? 'Suggesting...' : 'Suggest Weights'}</span>
            </button>
            {suggestionError && (
              <p className="text-xs text-red-600 mt-1">{suggestionError}</p>
            )}
            {onClose && (
              <button
                onClick={() => {
                  if (hasChanges) {
                    setShowCloseConfirm(true)
                  } else {
                    onClose()
                  }
                }}
                className="p-2 hover:bg-gray-100 rounded-lg"
                aria-label="Close"
              >
                <XMarkIcon className="h-6 w-6 text-gray-500" />
              </button>
            )}
          </div>
        </div>

        {/* Three Column Layout */}
        <div className="grid grid-cols-3 gap-6 flex-1 min-h-0">
          {/* Assessments Column */}
          <Card className="p-4 flex flex-col overflow-hidden min-h-0">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <div className="flex items-center gap-2">
                <ClipboardDocumentListIcon className="h-5 w-5 text-primary-600" />
                <h3 className="font-semibold text-gray-900">Assessments</h3>
              </div>
              {(() => {
                const unmappedCount = assessments.filter(a =>
                  !workingAssessmentLOMappings.some(m => m.assessment === a.id)
                ).length
                if (unmappedCount > 0) {
                  return (
                    <span className="text-xs font-medium px-2 py-1 bg-red-100 text-red-700 rounded">
                      {unmappedCount} unmapped
                    </span>
                  )
                }
                return null
              })()}
            </div>
            <div className="space-y-2 overflow-y-auto flex-1 pr-2">
              {assessments.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No assessments are defined for this course</p>
              ) : (
                assessments.map((assessment) => {
                  const isMapped = workingAssessmentLOMappings.some(m => m.assessment === assessment.id)
                  return (
                  <DraggableItem
                    key={assessment.id}
                    id={`assessment-${assessment.id}`}
                    type="assessment"
                    data={{ id: assessment.id, name: assessment.name }}
                  >
                    <div className={`p-3 rounded-lg hover:bg-blue-100 transition-colors ${
                      isMapped ? 'bg-blue-50 border border-blue-200' : 'bg-red-50 border-2 border-red-300'
                    }`}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className={`font-medium ${
                            isMapped ? 'text-blue-900' : 'text-red-900'
                          }`}>{assessment.name}</p>
                          <p className={`text-xs capitalize ${
                            isMapped ? 'text-blue-600' : 'text-red-600'
                          }`}>
                            {assessment.assessment_type} • {((assessment.weight ?? 0) * 100).toFixed(0)}%
                          </p>
                        </div>
                        {!isMapped && (
                          <span className="text-xs font-medium px-1.5 py-0.5 bg-red-200 text-red-800 rounded whitespace-nowrap">
                            Not mapped
                          </span>
                        )}
                      </div>
                    </div>
                  </DraggableItem>
                )})
              )}
            </div>
          </Card>

          {/* Learning Outcomes Column */}
          <Card className="p-4 flex flex-col overflow-hidden min-h-0">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <div className="flex items-center gap-2">
                <AcademicCapIcon className="h-5 w-5 text-teal-600" />
                <h3 className="font-semibold text-gray-900">Learning Outcomes</h3>
              </div>
              {(() => {
                const completedCount = learningOutcomes.filter(lo => {
                  const total = getAssessmentMappingsForLO(lo.id).reduce((sum, m) => sum + m.weight, 0)
                  return Math.round(total * 100) >= 100
                }).length
                const totalCount = learningOutcomes.length
                const isAllComplete = completedCount === totalCount && totalCount > 0
                return (
                  <span className={`text-xs font-medium px-2 py-1 rounded ${
                    isAllComplete ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {completedCount}/{totalCount} complete
                  </span>
                )
              })()}
            </div>
            <div className="space-y-3 overflow-y-auto flex-1 pr-2">
              {learningOutcomes.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No learning outcomes are defined for this course</p>
              ) : (
                learningOutcomes.map((lo) => (
                  <DroppableZone
                    key={lo.id}
                    id={`lo-drop-${lo.id}`}
                    accepts={['assessment']}
                    className="rounded-lg transition-all"
                  >
                    <DraggableItem
                      id={`lo-${lo.id}`}
                      type="lo"
                      data={{ id: lo.id, code: lo.code }}
                    >
                      <div className="p-3 bg-teal-50 border border-teal-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="px-2 py-1 bg-teal-100 text-teal-800 rounded text-sm font-bold">
                            {lo.code}
                          </span>

                        </div>
                        <p className="text-xs text-teal-700 line-clamp-2">{lo.description}</p>

                        {/* Linked Assessments */}
                        {getAssessmentMappingsForLO(lo.id).length > 0 && (
                          <div className="mt-2 pt-2 border-t border-teal-200">
                            <p className="text-xs text-teal-600 mb-1">Linked Assessments:</p>
                            <div className="flex flex-wrap gap-1">
                              {getAssessmentMappingsForLO(lo.id).map((mapping) => {
                                const assessment = assessments.find(
                                  (a) => a.id === mapping.assessment
                                )
                                return (
                                  <span
                                    key={mapping.id}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs cursor-pointer hover:bg-blue-200"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setWeightModal({
                                        isOpen: true,
                                        type: 'assessment-lo',
                                        fromId: mapping.assessment,
                                        toId: lo.id,
                                        fromLabel: assessment?.name || '',
                                        toLabel: lo.code,
                                        editMode: true,
                                        mappingId: mapping.id,
                                        initialWeight: mapping.weight,
                                      })
                                    }}
                                    title="Click to edit weight"
                                  >
                                    {assessment?.name?.substring(0, 15)}
                                    <span className="text-blue-500">
                                      ({mapping.weight})
                                    </span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleDeleteMapping(mapping.id, 'assessment-lo')
                                      }}
                                      className="p-0.5 hover:text-red-600 -mr-1"
                                      title="Remove mapping"
                                      aria-label="Remove mapping"
                                    >
                                      <XMarkIcon className="h-3 w-3" />
                                    </button>
                                  </span>
                                )
                              })}
                            </div>
                          </div>
                        )}

                        {/* Linked POs */}
                        {getPOMappingsForLO(lo.id).length > 0 && (
                          <div className="mt-2 pt-2 border-t border-teal-200">
                            <p className="text-xs text-teal-600 mb-1">→ Program Outcomes:</p>
                            <div className="flex flex-wrap gap-1">
                              {getPOMappingsForLO(lo.id).map((mapping) => {
                                const poId = mapping.program_outcome?.id
                                const po = programOutcomes.find((p) => p.id === poId)
                                if (!poId) {
                                  return null
                                }
                                return (
                                  <span
                                    key={mapping.id}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs cursor-pointer hover:bg-purple-200"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setWeightModal({
                                        isOpen: true,
                                        type: 'lo-po',
                                        fromId: lo.id,
                                        toId: poId,
                                        fromLabel: lo.code,
                                        toLabel: po?.code || '',
                                        editMode: true,
                                        mappingId: mapping.id,
                                        initialWeight: mapping.weight,
                                      })
                                    }}
                                    title="Click to edit weight"
                                  >
                                    {po?.code}
                                    <span className="text-purple-500">
                                      ({mapping.weight})
                                    </span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleDeleteMapping(mapping.id, 'lo-po')
                                      }}
                                      className="p-0.5 hover:text-red-600 -mr-1"
                                      title="Remove mapping"
                                      aria-label="Remove mapping"
                                    >
                                      <XMarkIcon className="h-3 w-3" />
                                    </button>
                                  </span>
                                )
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    </DraggableItem>
                  </DroppableZone>
                ))
              )}
            </div>
          </Card>

          {/* Program Outcomes Column */}
          <Card className="p-4 flex flex-col overflow-hidden min-h-0">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <div className="flex items-center gap-2">
                <ChartBarIcon className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold text-gray-900">Program Outcomes</h3>
              </div>
              {(() => {
                const completedCount = programOutcomes.filter(po => {
                  const total = getLOMappingsForPO(po.id).reduce((sum, m) => sum + m.weight, 0)
                  return Math.round(total * 100) >= 100
                }).length
                const totalCount = programOutcomes.length
                const isAllComplete = completedCount === totalCount && totalCount > 0
                return (
                  <span className={`text-xs font-medium px-2 py-1 rounded ${
                    isAllComplete ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {completedCount}/{totalCount} complete
                  </span>
                )
              })()}
            </div>
            <div className="space-y-2 overflow-y-auto flex-1 pr-2">
              {programOutcomes.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">No program outcomes are defined for this course</p>
              ) : (
                programOutcomes.map((po) => (
                  <DroppableZone
                    key={po.id}
                    id={`po-drop-${po.id}`}
                    accepts={['lo']}
                    className="rounded-lg transition-all"
                  >
                    <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors">
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-sm font-bold">
                          {po.code}
                        </span>

                      </div>
                      <p className="text-xs text-purple-700 mt-2 line-clamp-2">{po.description}</p>

                      {/* Linked Learning Outcomes */}
                      {getLOMappingsForPO(po.id).length > 0 && (
                        <div className="mt-2 pt-2 border-t border-purple-200">
                          <p className="text-xs text-purple-600 mb-1">Linked Learning Outcomes:</p>
                          <div className="flex flex-wrap gap-1">
                            {getLOMappingsForPO(po.id).map((mapping) => {
                              const loId = mapping.learning_outcome?.id
                              const lo = learningOutcomes.find((l) => l.id === loId)
                              if (!loId) {
                                return null
                              }
                              return (
                                <span
                                  key={mapping.id}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-teal-100 text-teal-700 rounded text-xs cursor-pointer hover:bg-teal-200"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setWeightModal({
                                      isOpen: true,
                                      type: 'lo-po',
                                      fromId: loId,
                                      toId: po.id,
                                      fromLabel: lo?.code || '',
                                      toLabel: po.code,
                                      editMode: true,
                                      mappingId: mapping.id,
                                      initialWeight: mapping.weight,
                                    })
                                  }}
                                  title="Click to edit weight"
                                >
                                  {lo?.code}
                                  <span className="text-teal-500">
                                    ({mapping.weight})
                                  </span>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleDeleteMapping(mapping.id, 'lo-po')
                                    }}
                                    className="p-0.5 hover:text-red-600 -mr-1"
                                    title="Remove mapping"
                                    aria-label="Remove mapping"
                                  >
                                    <XMarkIcon className="h-3 w-3" />
                                  </button>
                                </span>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </DroppableZone>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 mt-6">
          <button
            onClick={handleReset}
            disabled={!hasChanges}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              hasChanges
                ? 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                : 'border border-gray-200 text-gray-300 cursor-not-allowed'
            }`}
          >
            ↺ Reset Changes
          </button>
          <button
            onClick={() => handleSave(true)}
            disabled={!hasChanges || isSaving}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              hasChanges && !isSaving
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Drag Overlay */}
      <DragOverlay>
        {activeId && activeData && (
          <div className="p-3 bg-white border-2 border-primary-500 rounded-lg shadow-lg">
            <p className="font-medium">{activeData.name || activeData.code}</p>
          </div>
        )}
      </DragOverlay>

      {/* Weight Modal */}
      {weightModal && (
        <WeightModal
          isOpen={weightModal.isOpen}
          onClose={() => setWeightModal(null)}
          onConfirm={handleCreateOrUpdateMapping}
          title={
            weightModal.editMode
              ? 'Edit Mapping Weight'
              : weightModal.type === 'assessment-lo'
                ? 'Link Assessment to Learning Outcome'
                : 'Link Learning Outcome to Program Outcome'
          }
          fromLabel={weightModal.fromLabel}
          toLabel={weightModal.toLabel}
          editMode={weightModal.editMode}
          initialWeight={weightModal.initialWeight}
        />
      )}
      {/* Close Confirmation Dialog */}
      <Dialog open={showCloseConfirm} onOpenChange={(open) => { if (!open) setShowCloseConfirm(false) }}>
        <DialogContent className="sm:max-w-sm !z-[10000]" overlayClassName="!z-[10000]">
          <DialogHeader>
            <DialogTitle>Unsaved Changes</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">
            You have unsaved mapping changes. What would you like to do?
          </p>
          <DialogFooter>
            <button
              onClick={() => setShowCloseConfirm(false)}
              className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Keep Editing
            </button>
            <button
              onClick={() => {
                handleReset()
                setShowCloseConfirm(false)
                onClose?.()
              }}
              className="px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
            >
              Discard
            </button>
            <button
              onClick={async () => {
                setShowCloseConfirm(false)
                await handleSave(true)
              }}
              className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              Save & Close
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <AssessmentDescriptionsModal
        isOpen={showDescriptionsModal}
        onClose={() => setShowDescriptionsModal(false)}
        onSubmit={handleDescriptionsSubmit}
        assessments={assessments}
      />
    </DndContext>
  )
}

export default MappingEditor
