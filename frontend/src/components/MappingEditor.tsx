import { useState, useEffect } from 'react'
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
import { Card } from './ui/Card'
import {
  XMarkIcon,
  LinkIcon,
  AcademicCapIcon,
  ClipboardDocumentListIcon,
  ChartBarIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline'
import api from '../services/api'

// Types
interface Assessment {
  id: number
  name: string
  assessment_type: string
  weight: number
}

interface LearningOutcome {
  id: number
  code: string
  description: string
}

interface ProgramOutcome {
  id: number
  code: string
  description: string
}

interface AssessmentLOMapping {
  id?: number
  assessment: number
  learning_outcome: number | LearningOutcome
  weight: number
}

interface LOPOMapping {
  id?: number
  course: number
  learning_outcome: number | LearningOutcome
  program_outcome: number | ProgramOutcome
  weight: number
}

interface MappingEditorProps {
  courseId: number
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
  data: any
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
  maxWeight = 1,
  usedWeight = 0,
  editMode = false,
  initialWeight = 0,
}: {
  isOpen: boolean
  onClose: () => void
  onConfirm: (weight: number) => void
  title: string
  fromLabel: string
  toLabel: string
  maxWeight?: number
  usedWeight?: number
  editMode?: boolean
  initialWeight?: number
}) => {
  // In edit mode, exclude current mapping from used weight calculation
  const effectiveUsedWeight = editMode ? usedWeight - initialWeight : usedWeight
  // Fix floating point precision issues by rounding to 2 decimal places
  const remainingWeight = Math.round(Math.max(0, maxWeight - effectiveUsedWeight) * 100) / 100
  const [weight, setWeight] = useState(0)
  const [isInitialized, setIsInitialized] = useState(false)

  // Slider step and max allowed - remainingWeight already accounts for edit mode
  const step = 0.05
  const maxAllowedWeight = Math.max(0, Math.min(maxWeight, remainingWeight))
  // Clamp max to proper step value (round to nearest step)
  const maxSliderValue = Math.round(maxAllowedWeight / step) * step

  // Reset weight when modal opens with new remaining weight
  useEffect(() => {
    if (isOpen && !isInitialized) {
      if (editMode && initialWeight > 0) {
        // In edit mode, start with current weight
        const roundedWeight = Math.round(initialWeight / step) * step
        setWeight(roundedWeight)
      } else {
        // Set initial weight to half of remaining, rounded to step
        const defaultWeight = Math.min(0.5, maxSliderValue)
        const roundedWeight = Math.round(defaultWeight / step) * step
        setWeight(roundedWeight)
      }
      setIsInitialized(true)
    }
    if (!isOpen) {
      setIsInitialized(false)
    }
  }, [isOpen, maxSliderValue, isInitialized, editMode, initialWeight])

  if (!isOpen) return null

  // Check if weight exceeds allowed maximum (with small tolerance for floating point precision)
  const isOverLimit = weight > maxSliderValue + 0.001

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-96 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="font-medium">{fromLabel}</span>
            <LinkIcon className="h-4 w-4" />
            <span className="font-medium">{toLabel}</span>
          </div>

          {/* Weight budget info */}
          <div className="p-3 bg-gray-50 rounded-lg text-sm">
            <div className="flex justify-between text-gray-600">
              <span>Already allocated{editMode ? ' (excluding this)' : ''}:</span>
              <span className="font-medium">{(effectiveUsedWeight * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Available before edit:</span>
              <span className={`font-medium ${remainingWeight <= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {(remainingWeight * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Total after save:</span>
              <span className="font-medium">
                {((effectiveUsedWeight + weight) * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Weight for this mapping
            </label>
            <input
              id="weight-slider"
              type="range"
              min="0"
              max={maxSliderValue}
              step={step}
              value={Math.min(Math.max(0, weight), maxSliderValue)}
              onChange={(e) => {
                const raw = parseFloat(e.target.value)
                const rounded = Math.round(raw / step) * step
                const clamped = Math.min(Math.max(0, rounded), maxSliderValue)
                setWeight(clamped)
              }}
              className="w-full"
              aria-label="Weight percentage"
              disabled={!editMode && remainingWeight <= 0}
            />
            <div className="flex justify-between text-sm text-gray-500 mt-1">
              <span>0%</span>
              <span className={`font-bold ${isOverLimit ? 'text-red-600' : 'text-primary-600'}`}>
                {(weight * 100).toFixed(0)}%
              </span>
              <span>{(maxSliderValue * 100).toFixed(0)}%</span>
            </div>
          </div>

          {remainingWeight <= 0 && !editMode && (
            <p className="text-sm text-red-600">
              No remaining weight available. Total weight is already at 100%.
            </p>
          )}

          <div className="flex gap-3 mt-6">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                // Ensure weight does not exceed maxAllowedWeight
                const finalWeight = Math.min(weight, maxSliderValue)
                onConfirm(finalWeight)
              }}
              disabled={weight <= 0}
              className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {editMode ? 'Update Mapping' : 'Create Mapping'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Main Component
const MappingEditor = ({ courseId, onClose }: MappingEditorProps) => {
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [learningOutcomes, setLearningOutcomes] = useState<LearningOutcome[]>([])
  const [programOutcomes, setProgramOutcomes] = useState<ProgramOutcome[]>([])
  const [assessmentLOMappings, setAssessmentLOMappings] = useState<AssessmentLOMapping[]>([])
  const [loPOMappings, setLoPOMappings] = useState<LOPOMapping[]>([])
  const [loading, setLoading] = useState(true)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [activeData, setActiveData] = useState<any>(null)

  // Weight modal state
  const [weightModal, setWeightModal] = useState<{
    isOpen: boolean
    type: 'assessment-lo' | 'lo-po'
    fromId: number
    toId: number
    fromLabel: string
    toLabel: string
    usedWeight: number
    editMode?: boolean
    mappingId?: number
    initialWeight?: number
  } | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor)
  )

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      console.log('MappingEditor: Fetching data for courseId:', courseId)
      try {
        const [assessmentsRes, losRes, posRes, aloMappingsRes, lopMappingsRes] = await Promise.all([
          api.get(`/api/evaluation/assessments/?course=${courseId}`),
          api.get(`/api/core/courses/${courseId}/learning_outcomes/`),
          api.get(`/api/core/program-outcomes/`),
          api.get(`/api/evaluation/assessment-lo-mappings/?course=${courseId}`),
          api.get(`/api/core/lo-po-mappings/?course=${courseId}`),
        ])

        console.log('MappingEditor API responses:', {
          assessments: assessmentsRes.data,
          los: losRes.data,
          pos: posRes.data,
        })

        setAssessments(assessmentsRes.data.results || assessmentsRes.data || [])
        setLearningOutcomes(losRes.data.results || losRes.data || [])
        setProgramOutcomes(posRes.data.results || posRes.data || [])
        setAssessmentLOMappings(aloMappingsRes.data.results || aloMappingsRes.data || [])
        setLoPOMappings(lopMappingsRes.data.results || lopMappingsRes.data || [])
      } catch (error) {
        console.error('Error fetching mapping data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [courseId])

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
    setActiveData(event.active.data.current)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)
    setActiveData(null)

    if (!over) return

    const activeType = active.data.current?.type
    const overId = over.id as string

    // Assessment dropped on LO
    if (activeType === 'assessment' && overId.startsWith('lo-drop-')) {
      const loId = parseInt(overId.replace('lo-drop-', ''))
      const assessmentId = active.data.current?.id
      const assessment = assessments.find((a) => a.id === assessmentId)
      const lo = learningOutcomes.find((l) => l.id === loId)

      // Check if mapping already exists (learning_outcome can be object or id)
      const existingMapping = assessmentLOMappings.find(
        (m) => m.assessment === assessmentId &&
          (typeof m.learning_outcome === 'object'
            ? m.learning_outcome?.id === loId
            : m.learning_outcome === loId)
      )

      // Calculate already used weight for this LO (sum of all assessment mappings for this LO)
      const usedWeight = assessmentLOMappings
        .filter((m) => {
          const loIdOfMapping = typeof m.learning_outcome === 'object' ? m.learning_outcome?.id : m.learning_outcome
          return loIdOfMapping === loId
        })
        .reduce((sum, m) => sum + (m.weight || 0), 0)

      if (existingMapping) {
        // Edit existing mapping
        setWeightModal({
          isOpen: true,
          type: 'assessment-lo',
          fromId: assessmentId,
          toId: loId,
          fromLabel: assessment?.name || '',
          toLabel: lo?.code || '',
          usedWeight,
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
          usedWeight,
        })
      }
    }

    // LO dropped on PO
    if (activeType === 'lo' && overId.startsWith('po-drop-')) {
      const poId = parseInt(overId.replace('po-drop-', ''))
      const loId = active.data.current?.id
      const lo = learningOutcomes.find((l) => l.id === loId)
      const po = programOutcomes.find((p) => p.id === poId)

      // Check if mapping already exists (learning_outcome and program_outcome can be object or id)
      const existingMapping = loPOMappings.find(
        (m) => (typeof m.learning_outcome === 'object'
                  ? m.learning_outcome?.id === loId
                  : m.learning_outcome === loId) &&
               (typeof m.program_outcome === 'object'
                  ? m.program_outcome?.id === poId
                  : m.program_outcome === poId)
      )

      // Calculate already used weight for this PO (sum of all LO mappings for this PO)
      const usedWeight = loPOMappings
        .filter((m) =>
          typeof m.program_outcome === 'object'
            ? m.program_outcome?.id === poId
            : m.program_outcome === poId
        )
        .reduce((sum, m) => sum + m.weight, 0)

      if (existingMapping) {
        // Edit existing mapping
        setWeightModal({
          isOpen: true,
          type: 'lo-po',
          fromId: loId,
          toId: poId,
          fromLabel: lo?.code || '',
          toLabel: po?.code || '',
          usedWeight,
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
          usedWeight,
        })
      }
    }

    setActiveId(null)
  }

  const handleCreateOrUpdateMapping = async (weight: number) => {
    if (!weightModal) return

    try {
      if (weightModal.editMode && weightModal.mappingId) {
        // Update existing mapping
        if (weightModal.type === 'assessment-lo') {
          // Optimistic update
          const previousMappings = assessmentLOMappings
          setAssessmentLOMappings(assessmentLOMappings.map((m) =>
            m.id === weightModal.mappingId ? { ...m, weight } : m
          ))
          setWeightModal(null)

          try {
            await api.patch(`/api/evaluation/assessment-lo-mappings/${weightModal.mappingId}/`, {
              weight,
            })
          } catch (error) {
            // Rollback on error
            setAssessmentLOMappings(previousMappings)
            throw error
          }
        } else {
          const response = await api.patch(`/api/core/lo-po-mappings/${weightModal.mappingId}/`, {
            weight,
          })
          setLoPOMappings(loPOMappings.map((m) =>
            m.id === weightModal.mappingId ? { ...m, weight: response.data.weight } : m
          ))
          setWeightModal(null)
        }
      } else {
        // Create new mapping
        if (weightModal.type === 'assessment-lo') {
          // Optimistic update with temporary ID
          const tempId = -Date.now() // Temporary negative ID
          const tempMapping = {
            id: tempId,
            assessment: weightModal.fromId,
            learning_outcome: weightModal.toId,
            weight,
          }
          setAssessmentLOMappings([...assessmentLOMappings, tempMapping as any])
          setWeightModal(null)

          // Update with real data from backend
          try {
            const response = await api.post('/api/evaluation/assessment-lo-mappings/', {
              assessment_id: weightModal.fromId,
              learning_outcome_id: weightModal.toId,
              weight,
            })
            // Replace temp mapping with real one
            setAssessmentLOMappings(prev =>
              prev.map(m => m.id === tempId ? response.data : m)
            )
          } catch (error) {
            // Remove temp mapping on error
            setAssessmentLOMappings(prev => prev.filter(m => m.id !== tempId))
            throw error
          }
        } else {
          const response = await api.post('/api/core/lo-po-mappings/', {
            course: courseId,
            learning_outcome_id: weightModal.fromId,
            program_outcome_id: weightModal.toId,
            weight,
          })
          setLoPOMappings([...loPOMappings, response.data])
          setWeightModal(null)
        }
      }
    } catch (error: any) {
      console.error('Error creating/updating mapping:', error)
      console.error('Error response data:', error.response?.data)

      // Show user-friendly error
      const errorMsg = error.response?.data?.non_field_errors?.[0]
        || error.response?.data?.detail
        || 'Failed to save mapping'
      alert(errorMsg)
    }
  }

  const handleDeleteALOMapping = async (mappingId: number) => {
    // Optimistic update - remove immediately
    const previousMappings = assessmentLOMappings
    setAssessmentLOMappings(assessmentLOMappings.filter((m) => m.id !== mappingId))

    try {
      await api.delete(`/api/evaluation/assessment-lo-mappings/${mappingId}/`)
    } catch (error) {
      console.error('Error deleting mapping:', error)
      // Rollback on error
      setAssessmentLOMappings(previousMappings)
      alert('Failed to delete mapping. Please try again.')
    }
  }

  const handleDeleteLOPOMapping = async (mappingId: number) => {
    try {
      await api.delete(`/api/core/lo-po-mappings/${mappingId}/`)
      setLoPOMappings(loPOMappings.filter((m) => m.id !== mappingId))
    } catch (error) {
      console.error('Error deleting mapping:', error)
    }
  }

  // Get mappings for a specific LO
  const getAssessmentMappingsForLO = (loId: number) => {
    return assessmentLOMappings.filter((m) =>
      typeof m.learning_outcome === 'object'
        ? m.learning_outcome?.id === loId
        : m.learning_outcome === loId
    )
  }

  const getPOMappingsForLO = (loId: number) => {
    return loPOMappings.filter((m) =>
      typeof m.learning_outcome === 'object'
        ? m.learning_outcome?.id === loId
        : m.learning_outcome === loId
    )
  }

  // Get LO mappings for a specific PO
  const getLOMappingsForPO = (poId: number) => {
    return loPOMappings.filter((m) =>
      typeof m.program_outcome === 'object'
        ? m.program_outcome?.id === poId
        : m.program_outcome === poId
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-primary-600"></div>
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
      <div className="space-y-6">
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
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg"
              aria-label="Close"
            >
              <XMarkIcon className="h-6 w-6 text-gray-500" />
            </button>
          )}
        </div>

        {/* Three Column Layout */}
        <div className="grid grid-cols-3 gap-6" style={{ height: 'calc(95vh - 100px)', minHeight: '600px' }}>
          {/* Assessments Column */}
          <Card className="p-4 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <div className="flex items-center gap-2">
                <ClipboardDocumentListIcon className="h-5 w-5 text-primary-600" />
                <h3 className="font-semibold text-gray-900">Assessments</h3>
              </div>
              {(() => {
                const unmappedCount = assessments.filter(a =>
                  !assessmentLOMappings.some(m => m.assessment === a.id)
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
                <p className="text-sm text-gray-500 text-center py-4">No assessments found</p>
              ) : (
                assessments.map((assessment) => {
                  const isMapped = assessmentLOMappings.some(m => m.assessment === assessment.id)
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
                            {assessment.assessment_type} • {(assessment.weight * 100).toFixed(0)}%
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
          <Card className="p-4 flex flex-col overflow-hidden">
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
                <p className="text-sm text-gray-500 text-center py-4">No learning outcomes found</p>
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
                          {(() => {
                            const totalWeight = getAssessmentMappingsForLO(lo.id).reduce((sum, m) => sum + m.weight, 0)
                            const percentage = Math.round(totalWeight * 100)
                            return (
                              <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                                percentage >= 100 ? 'bg-green-100 text-green-700' :
                                percentage > 0 ? 'bg-amber-100 text-amber-700' :
                                'bg-gray-100 text-gray-500'
                              }`}>
                                {percentage}%/100%
                              </span>
                            )
                          })()}
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
                                const usedWeight = assessmentLOMappings
                                  .filter((m) => {
                                    const loIdOfMapping = typeof m.learning_outcome === 'object' ? m.learning_outcome?.id : m.learning_outcome
                                    return loIdOfMapping === lo.id
                                  })
                                  .reduce((sum, m) => sum + (m.weight || 0), 0)
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
                                        usedWeight,
                                        editMode: true,
                                        mappingId: mapping.id,
                                        initialWeight: mapping.weight,
                                      })
                                    }}
                                    title="Click to edit weight"
                                  >
                                    {assessment?.name?.substring(0, 15)}
                                    <span className="text-blue-500">
                                      ({(mapping.weight * 100).toFixed(0)}%)
                                    </span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleDeleteALOMapping(mapping.id!)
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
                                const poId = typeof mapping.program_outcome === 'object'
                                  ? mapping.program_outcome?.id
                                  : mapping.program_outcome
                                const po = programOutcomes.find((p) => p.id === poId)
                                const usedWeight = loPOMappings
                                  .filter((m) =>
                                    typeof m.program_outcome === 'object'
                                      ? m.program_outcome?.id === poId
                                      : m.program_outcome === poId
                                  )
                                  .reduce((sum, m) => sum + m.weight, 0)
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
                                        toId: poId!,
                                        fromLabel: lo.code,
                                        toLabel: po?.code || '',
                                        usedWeight,
                                        editMode: true,
                                        mappingId: mapping.id,
                                        initialWeight: mapping.weight,
                                      })
                                    }}
                                    title="Click to edit weight"
                                  >
                                    {po?.code}
                                    <span className="text-purple-500">
                                      ({(mapping.weight * 100).toFixed(0)}%)
                                    </span>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleDeleteLOPOMapping(mapping.id!)
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
          <Card className="p-4 flex flex-col overflow-hidden">
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
                <p className="text-sm text-gray-500 text-center py-4">No program outcomes found</p>
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
                        {(() => {
                          const totalWeight = getLOMappingsForPO(po.id).reduce((sum, m) => sum + m.weight, 0)
                          const percentage = Math.round(totalWeight * 100)
                          return (
                            <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                              percentage >= 100 ? 'bg-green-100 text-green-700' :
                              percentage > 0 ? 'bg-amber-100 text-amber-700' :
                              'bg-gray-100 text-gray-500'
                            }`}>
                              {percentage}%/100%
                            </span>
                          )
                        })()}
                      </div>
                      <p className="text-xs text-purple-700 mt-2 line-clamp-2">{po.description}</p>

                      {/* Linked Learning Outcomes */}
                      {getLOMappingsForPO(po.id).length > 0 && (
                        <div className="mt-2 pt-2 border-t border-purple-200">
                          <p className="text-xs text-purple-600 mb-1">Linked Learning Outcomes:</p>
                          <div className="flex flex-wrap gap-1">
                            {getLOMappingsForPO(po.id).map((mapping) => {
                              const loId = typeof mapping.learning_outcome === 'object'
                                ? mapping.learning_outcome?.id
                                : mapping.learning_outcome
                              const lo = learningOutcomes.find((l) => l.id === loId)
                              const usedWeight = loPOMappings
                                .filter((m) =>
                                  typeof m.program_outcome === 'object'
                                    ? m.program_outcome?.id === po.id
                                    : m.program_outcome === po.id
                                )
                                .reduce((sum, m) => sum + m.weight, 0)
                              return (
                                <span
                                  key={mapping.id}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-teal-100 text-teal-700 rounded text-xs cursor-pointer hover:bg-teal-200"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setWeightModal({
                                      isOpen: true,
                                      type: 'lo-po',
                                      fromId: loId!,
                                      toId: po.id,
                                      fromLabel: lo?.code || '',
                                      toLabel: po.code,
                                      usedWeight,
                                      editMode: true,
                                      mappingId: mapping.id,
                                      initialWeight: mapping.weight,
                                    })
                                  }}
                                  title="Click to edit weight"
                                >
                                  {lo?.code}
                                  <span className="text-teal-500">
                                    ({(mapping.weight * 100).toFixed(0)}%)
                                  </span>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleDeleteLOPOMapping(mapping.id!)
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
          usedWeight={weightModal.usedWeight}
          editMode={weightModal.editMode}
          initialWeight={weightModal.initialWeight}
        />
      )}
    </DndContext>
  )
}

export default MappingEditor
