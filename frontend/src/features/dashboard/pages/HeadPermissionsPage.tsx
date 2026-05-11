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
  corePermissionsBulkUpdatePartialUpdate,
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

// Helper to clone arrays
const clone = <T,>(arr: T[]): T[] => arr.map(item => ({ ...item }))

// Compute diff between initial and working permissions
const computeDiff = (
  working: InstructorPermission[],
  initial: InstructorPermission[]
): { id: number; permission_tier: string }[] => {
  const initialMap = new Map(initial.map(p => [p.id, p]))
  return working
    .filter(wp => {
      const ip = initialMap.get(wp.id)
      return ip && ip.permission_tier !== wp.permission_tier
    })
    .map(wp => ({
      id: wp.id,
      permission_tier: wp.permission_tier ?? 'view',
    }))
}

const HeadPermissionsPage = () => {
  const queryClient = useQueryClient()
  const [editMode, setEditMode] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Initial state (frozen snapshot from server on modal open)
  const [initialPermissions, setInitialPermissions] = useState<InstructorPermission[]>([])
  // Working state (editable copy, all mutations applied here)
  const [workingPermissions, setWorkingPermissions] = useState<InstructorPermission[]>([])
  const [hasInitialized, setHasInitialized] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => corePermissionsList({}),
  })

  const bulkPartialUpdateMutation = useMutation({
    mutationFn: async (data: { updates: { id: number; permission_tier: string }[] }) => {
      // PATCH /api/core/permissions/bulk-update/ - sends only changed permissions
      return corePermissionsBulkUpdatePartialUpdate(data)
    },
    onSuccess: (newData) => {
      queryClient.invalidateQueries({ queryKey: ['permissions'] })
      setEditMode(false)
      setShowConfirmDialog(false)
      setErrorMessage(null)
      // Update working state with fresh data from server
      if (newData?.results) {
        setInitialPermissions(clone(newData.results))
        setWorkingPermissions(clone(newData.results))
      }
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || 'Failed to save permissions. Please try again.')
      setShowConfirmDialog(false)
    },
  })

  // Initialize state when data loads
  useEffect(() => {
    if (data?.results && !hasInitialized) {
      const perms = data.results as InstructorPermission[]
      setInitialPermissions(clone(perms))
      setWorkingPermissions(clone(perms))
      setHasInitialized(true)
    }
  }, [data?.results, hasInitialized])

  useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => setErrorMessage(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [errorMessage])

  const permissions = useMemo(() => workingPermissions, [workingPermissions])

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

  // Compute which permissions have changed
  const changedPermissions = useMemo(() => {
    return computeDiff(workingPermissions, initialPermissions)
  }, [workingPermissions, initialPermissions])

  const hasChanges = changedPermissions.length > 0

  const handleStartEdit = () => {
    setEditMode(true)
    setErrorMessage(null)
  }

  const handleCancelEdit = () => {
    // Reset working to initial
    setWorkingPermissions(clone(initialPermissions))
    setEditMode(false)
    setErrorMessage(null)
  }

  const handlePermissionChange = (
    permissionId: number,
    tier: PermissionTierEnum
  ) => {
    setWorkingPermissions(prev =>
      prev.map(p =>
        p.id === permissionId ? { ...p, permission_tier: tier } : p
      )
    )
  }

  // Handle column header click to change all instructors in that column
  const handleColumnHeaderClick = (resourceArea: string, tier: PermissionTierEnum) => {
    if (!editMode) return

    setWorkingPermissions(prev =>
      prev.map(p =>
        p.resource_area === resourceArea ? { ...p, permission_tier: tier } : p
      )
    )
  }

  const handleSaveBulk = () => {
    if (changedPermissions.length === 0) return
    setShowConfirmDialog(true)
  }

  const handleConfirmSave = () => {
    bulkPartialUpdateMutation.mutate({
      updates: changedPermissions,
    })
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
                disabled={!hasChanges || bulkPartialUpdateMutation.isPending}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                <CheckIcon className="h-4 w-4" />
                <span>{bulkPartialUpdateMutation.isPending ? 'Saving...' : 'Save Changes'}</span>
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
              You are about to update {changedPermissions.length} permission{changedPermissions.length !== 1 ? 's' : ''}.
              {editMode && ' Click a column header while editing to change all instructors in that column.'}
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
                disabled={bulkPartialUpdateMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
              >
                {bulkPartialUpdateMutation.isPending ? 'Saving...' : 'Confirm'}
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
          {editMode && (
            <p className="text-sm text-secondary-500">
              Click a column header to change all instructors in that column
            </p>
          )}
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
                      {editMode ? (
                        <select
                          className="px-2 py-1 border border-secondary-300 rounded text-sm bg-transparent cursor-pointer hover:bg-secondary-100"
                          onChange={(e) => handleColumnHeaderClick(area.value, e.target.value as PermissionTierEnum)}
                          value=""
                        >
                          <option value="" disabled>{area.label}</option>
                          {PERMISSION_TIERS.map((tier) => (
                            <option key={tier.value} value={tier.value}>
                              All: {tier.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        area.label
                      )}
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
                      <div>
                        <div className="font-medium text-secondary-900">
                          {instructor.instructor}
                        </div>
                        <div className="text-xs text-secondary-500">
                          ID: {instructor.instructor_id}
                        </div>
                      </div>
                    </td>
                    {RESOURCE_AREAS.map((area) => {
                      const key = `${instructor.instructor_id}-${area.value}`
                      const perm = groupedPermissions[key]?.[0]
                      const currentTier = perm?.permission_tier

                      return (
                        <td key={area.value} className="py-3 px-4 text-center">
                          {editMode && perm ? (
                            <select
                              value={currentTier || PermissionTierEnum.view}
                              onChange={(e) =>
                                handlePermissionChange(
                                  perm.id,
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
