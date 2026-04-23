import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../../../shared/components/ui/Card'
import { Badge } from '../../../shared/components/ui/Badge'
import {
  ShieldCheckIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import {
  corePermissionsList,
  corePermissionsBulkUpdate,
} from '../../../shared/api/generated/core/core'
import type { InstructorPermission } from '../../../shared/api/model'
import {
  ResourceAreaEnum,
  PermissionTierEnum,
} from '../../../shared/api/model'

const RESOURCE_AREAS = [
  { value: ResourceAreaEnum.courses, label: 'Courses' },
  { value: ResourceAreaEnum.programs, label: 'Programs' },
  { value: ResourceAreaEnum.learning_outcomes, label: 'Learning Outcomes' },
  { value: ResourceAreaEnum.program_outcomes, label: 'Program Outcomes' },
  { value: ResourceAreaEnum.students, label: 'Students' },
  { value: ResourceAreaEnum.lo_po_weights, label: 'LO-PO Weights' },
  { value: ResourceAreaEnum.assessment_lo_weights, label: 'Assessment-LO Weights' },
  { value: ResourceAreaEnum.assessments, label: 'Assessments' },
]

const PERMISSION_TIERS = [
  { value: PermissionTierEnum.view, label: 'View Only', color: 'secondary' as const },
  { value: PermissionTierEnum.edit, label: 'Edit', color: 'warning' as const },
  { value: PermissionTierEnum.full, label: 'Full Control', color: 'primary' as const },
]

const HeadPermissionsPage = () => {
  const queryClient = useQueryClient()
  const [selectedInstructors, setSelectedInstructors] = useState<number[]>([])
  const [editMode, setEditMode] = useState(false)
  const [pendingChanges, setPendingChanges] = useState<Record<string, PermissionTierEnum>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => corePermissionsList({}),
  })

  const bulkUpdateMutation = useMutation({
    mutationFn: (permissions: InstructorPermission[]) =>
      corePermissionsBulkUpdate(permissions as unknown as InstructorPermission),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['permissions'] })
      setEditMode(false)
      setPendingChanges({})
      setShowConfirmDialog(false)
      setErrorMessage(null)
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || 'Failed to save permissions. Please try again.')
      setShowConfirmDialog(false)
    },
  })

  useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => setErrorMessage(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [errorMessage])

  const permissions = useMemo(() => data?.results || [], [data])

  const groupedPermissions = useMemo(() => {
    const groups: Record<string, InstructorPermission[]> = {}
    permissions.forEach((perm) => {
      const key = `${perm.instructor_id}-${perm.resource_area}`
      groups[key] = groups[key] || []
      groups[key].push(perm)
    })
    return groups
  }, [permissions])

  const uniqueInstructors = useMemo(() => {
    const seen = new Set<number>()
    return permissions.filter((p) => {
      if (seen.has(p.instructor_id)) return false
      seen.add(p.instructor_id)
      return true
    })
  }, [permissions])

  const filteredInstructors = useMemo(() => {
    if (!searchQuery.trim()) return uniqueInstructors
    const query = searchQuery.toLowerCase()
    return uniqueInstructors.filter((p) =>
      p.instructor?.toLowerCase().includes(query)
    )
  }, [uniqueInstructors, searchQuery])

  const handleSelectAll = () => {
    if (selectedInstructors.length === filteredInstructors.length) {
      setSelectedInstructors([])
    } else {
      setSelectedInstructors(filteredInstructors.map((p) => p.instructor_id))
    }
  }

  const handleSelectInstructor = (id: number) => {
    setSelectedInstructors((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  const handleStartEdit = () => {
    const changes: Record<string, PermissionTierEnum> = {}
    permissions.forEach((p) => {
      const key = `${p.instructor_id}-${p.resource_area}`
      changes[key] = p.permission_tier || PermissionTierEnum.view
    })
    setPendingChanges(changes)
    setEditMode(true)
    setErrorMessage(null)
  }

  const handleCancelEdit = () => {
    setEditMode(false)
    setPendingChanges({})
    setErrorMessage(null)
  }

  const handlePermissionChange = (
    instructorId: number,
    resourceArea: string,
    tier: PermissionTierEnum
  ) => {
    const key = `${instructorId}-${resourceArea}`
    setPendingChanges((prev) => ({ ...prev, [key]: tier }))
  }

  const handleSaveBulk = () => {
    setShowConfirmDialog(true)
  }

  const handleConfirmSave = () => {
    const updates: InstructorPermission[] = []
    Object.entries(pendingChanges).forEach(([key, tier]) => {
      const [instructorId, resourceArea] = key.split('-')
      const existing = permissions.find(
        (p) =>
          p.instructor_id === parseInt(instructorId) &&
          p.resource_area === resourceArea
      )
      if (existing) {
        updates.push({
          ...existing,
          permission_tier: tier,
        })
      }
    })
    if (updates.length > 0) {
      bulkUpdateMutation.mutate(updates)
    }
  }

  const getPermissionTierBadgeVariant = (tier?: PermissionTierEnum) => {
    switch (tier) {
      case PermissionTierEnum.full:
        return 'primary'
      case PermissionTierEnum.edit:
        return 'warning'
      case PermissionTierEnum.view:
      default:
        return 'secondary'
    }
  }

  const getPermissionTierLabel = (tier?: PermissionTierEnum) => {
    const found = PERMISSION_TIERS.find((t) => t.value === tier)
    return found ? found.label : 'None'
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-secondary-600 font-medium">Loading permissions...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">Instructor Permissions</h1>
          <p className="text-secondary-500 mt-1">
            Manage access rights for instructors across resource areas
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {editMode ? (
            <>
              <button
                onClick={handleCancelEdit}
                className="flex items-center space-x-2 px-4 py-2 border border-secondary-300 rounded-lg text-secondary-700 hover:bg-secondary-50 transition-colors"
              >
                <XMarkIcon className="h-4 w-4" />
                <span>Cancel</span>
              </button>
              <button
                onClick={handleSaveBulk}
                disabled={bulkUpdateMutation.isPending}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                <CheckIcon className="h-4 w-4" />
                <span>{bulkUpdateMutation.isPending ? 'Saving...' : 'Save Changes'}</span>
              </button>
            </>
          ) : (
            <button
              onClick={handleStartEdit}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              <PencilIcon className="h-4 w-4" />
              <span>Edit Permissions</span>
            </button>
          )}
        </div>
      </div>

      {/* Error toast */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center space-x-3">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
          <p className="text-red-700 text-sm">{errorMessage}</p>
          <button
            onClick={() => setErrorMessage(null)}
            className="ml-auto text-red-500 hover:text-red-700"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <div className="fixed inset-0 bg-secondary-900/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-secondary-900 mb-2">Confirm Permission Changes</h3>
            <p className="text-secondary-600 mb-6">
              You are about to update {Object.keys(pendingChanges).length} permission{Object.keys(pendingChanges).length !== 1 ? 's' : ''}. This action will override the existing permission tiers for the selected instructors and resource areas.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowConfirmDialog(false)}
                className="px-4 py-2 border border-secondary-300 rounded-lg text-secondary-700 hover:bg-secondary-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSave}
                disabled={bulkUpdateMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {bulkUpdateMutation.isPending ? 'Saving...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card variant="flat" className="bg-primary-50 border-primary-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-primary-100 rounded-xl">
              <ShieldCheckIcon className="h-8 w-8 text-primary-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Total Permissions</p>
              <p className="text-3xl font-bold text-primary-700">{permissions.length}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <ShieldCheckIcon className="h-8 w-8 text-emerald-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Instructors</p>
              <p className="text-3xl font-bold text-emerald-700">
                {uniqueInstructors.length}
              </p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-amber-50 border-amber-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-amber-100 rounded-xl">
              <ShieldCheckIcon className="h-8 w-8 text-amber-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Resource Areas</p>
              <p className="text-3xl font-bold text-amber-700">{RESOURCE_AREAS.length}</p>
            </div>
          </div>
        </Card>

        <Card variant="flat" className="bg-cyan-50 border-cyan-200">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-cyan-100 rounded-xl">
              <ShieldCheckIcon className="h-8 w-8 text-cyan-700" />
            </div>
            <div>
              <p className="text-sm text-secondary-600 font-medium">Full Access</p>
              <p className="text-3xl font-bold text-cyan-700">
                {permissions.filter((p) => p.permission_tier === PermissionTierEnum.full).length}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Search input */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
        <input
          type="text"
          placeholder="Search instructors..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
        />
      </div>

      {/* Permissions Table */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-secondary-900">Permission Matrix</h2>
          <div className="flex items-center space-x-2">
            <label className="flex items-center space-x-2 text-sm text-secondary-600">
              <input
                type="checkbox"
                checked={selectedInstructors.length === filteredInstructors.length && filteredInstructors.length > 0}
                onChange={handleSelectAll}
                className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
              />
              <span>Select All Instructors</span>
            </label>
          </div>
        </div>

        {permissions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-secondary-200">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-secondary-900">
                    Instructor
                  </th>
                  {RESOURCE_AREAS.map((area) => (
                    <th
                      key={area.value}
                      className="text-center py-3 px-4 text-sm font-semibold text-secondary-900 min-w-[120px]"
                    >
                      {area.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredInstructors.map((instructor) => (
                  <tr
                    key={instructor.instructor_id}
                    className="border-b border-secondary-100 hover:bg-secondary-50 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          checked={selectedInstructors.includes(instructor.instructor_id)}
                          onChange={() => handleSelectInstructor(instructor.instructor_id)}
                          className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                        />
                        <div>
                          <div className="font-medium text-secondary-900">
                            {instructor.instructor}
                          </div>
                          <div className="text-xs text-secondary-500">
                            ID: {instructor.instructor_id}
                          </div>
                        </div>
                      </div>
                    </td>
                    {RESOURCE_AREAS.map((area) => {
                      const key = `${instructor.instructor_id}-${area.value}`
                      const perm = groupedPermissions[key]?.[0]
                      const currentTier = editMode
                        ? pendingChanges[key] || perm?.permission_tier
                        : perm?.permission_tier

                      return (
                        <td key={area.value} className="py-3 px-4 text-center">
                          {editMode ? (
                            <select
                              value={currentTier || PermissionTierEnum.view}
                              onChange={(e) =>
                                handlePermissionChange(
                                  instructor.instructor_id,
                                  area.value,
                                  e.target.value as PermissionTierEnum
                                )
                              }
                              className="px-2 py-1 border border-secondary-300 rounded text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                            >
                              {PERMISSION_TIERS.map((tier) => (
                                <option key={tier.value} value={tier.value}>
                                  {tier.label}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <Badge
                              variant={getPermissionTierBadgeVariant(currentTier as PermissionTierEnum)}
                              className="text-xs"
                            >
                              {getPermissionTierLabel(currentTier as PermissionTierEnum)}
                            </Badge>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-16">
            <ShieldCheckIcon className="h-16 w-16 mx-auto mb-4 text-secondary-300" />
            <h3 className="text-lg font-semibold text-secondary-900 mb-2">
              No permissions found
            </h3>
            <p className="text-secondary-500 mb-4">
              No instructor permissions have been configured yet.
            </p>
            <p className="text-sm text-secondary-400">
              Use the management interface to add instructor permissions, or contact an administrator.
            </p>
          </div>
        )}
      </Card>
    </div>
  )
}

export default HeadPermissionsPage
