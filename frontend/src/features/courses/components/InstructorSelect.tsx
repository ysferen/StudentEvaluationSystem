import { useState, useRef, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { axiosInstance } from '@/shared/api/mutator'

interface InstructorSelectProps {
  selectedIds: number[]
  onChange: (ids: number[]) => void
}

interface InstructorItem {
  id: number
  first_name: string
  last_name: string
  title: string
}

const inputClass = 'block w-full rounded-xl border border-secondary-300 px-4 py-2.5 text-sm text-secondary-900 placeholder-secondary-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition'

const InstructorSelect = ({ selectedIds, onChange }: InstructorSelectProps) => {
  const [search, setSearch] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [highlightIndex, setHighlightIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['course-instructor-options'],
    queryFn: async () => {
      const response = await axiosInstance.get('/api/users/instructors/')
      return response.data.results ?? response.data
    },
  })

  const allInstructors: InstructorItem[] = useMemo(() => {
    if (!data) return []
    return data.map((profile: { title?: string; user: { id: number; first_name?: string; last_name?: string } }) => ({
      id: profile.user.id,
      first_name: profile.user.first_name ?? '',
      last_name: profile.user.last_name ?? '',
      title: profile.title ?? '',
    }))
  }, [data])

  // Filter by search, exclude already selected
  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    const filtered = allInstructors.filter((inst) => {
      if (selectedIds.includes(inst.id)) return false
      if (!q) return true
      return (
        inst.first_name.toLowerCase().includes(q) ||
        inst.last_name.toLowerCase().includes(q) ||
        inst.title.toLowerCase().includes(q) ||
        `${inst.first_name} ${inst.last_name}`.toLowerCase().includes(q)
      )
    })
    return filtered
  }, [allInstructors, search, selectedIds])

  // Get display info for selected instructors
  const selectedItems = useMemo(() => {
    return allInstructors.filter((inst) => selectedIds.includes(inst.id))
  }, [allInstructors, selectedIds])

  const selectInstructor = (id: number) => {
    if (!selectedIds.includes(id)) {
      onChange([...selectedIds, id])
    }
    setSearch('')
    setIsOpen(false)
    setHighlightIndex(-1)
  }

  const removeInstructor = (id: number) => {
    onChange(selectedIds.filter((sid) => sid !== id))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || filtered.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightIndex((prev) => (prev < filtered.length - 1 ? prev + 1 : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightIndex((prev) => (prev > 0 ? prev - 1 : filtered.length - 1))
    } else if (e.key === 'Enter' && highlightIndex >= 0) {
      e.preventDefault()
      selectInstructor(filtered[highlightIndex].id)
    } else if (e.key === 'Escape') {
      setIsOpen(false)
      setHighlightIndex(-1)
    }
  }

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
        setHighlightIndex(-1)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleBlur = () => {
    // Timeout allows click events on dropdown items to register before closing
    setTimeout(() => setIsOpen(false), 150)
  }

  if (isLoading) {
    return <p className="text-sm text-secondary-500">Loading instructors...</p>
  }

  if (isError) {
    return <p className="text-sm text-danger-500">Failed to load instructors</p>
  }

  return (
    <div ref={containerRef} className="relative">
      <label className="block text-sm font-medium text-secondary-700 mb-1">Instructors</label>

      {/* Selected chips */}
      {selectedItems.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {selectedItems.map((inst) => (
            <span
              key={inst.id}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-primary-100 text-primary-800 text-xs font-medium rounded-full"
            >
              {inst.first_name} {inst.last_name}
              {inst.title && <span className="text-primary-500">({inst.title})</span>}
              <button
                type="button"
                onClick={() => removeInstructor(inst.id)}
                aria-label={`Remove ${inst.first_name} ${inst.last_name}`}
                className="ml-0.5 text-primary-500 hover:text-primary-700"
              >
                &#x2715;
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <input
        type="text"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value)
          setIsOpen(true)
          setHighlightIndex(-1)
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className={inputClass}
        placeholder="Search instructors..."
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-autocomplete="list"
        aria-activedescendant={highlightIndex >= 0 ? `instructor-option-${filtered[highlightIndex]?.id}` : undefined}
      />

      {/* Dropdown */}
      {isOpen && filtered.length > 0 && (
        <div role="listbox" className="absolute z-10 mt-1 w-full bg-white border border-secondary-200 rounded-xl shadow-lg max-h-48 overflow-y-auto">
          {filtered.map((inst, idx) => (
            <button
              key={inst.id}
              type="button"
              role="option"
              aria-selected={idx === highlightIndex}
              id={`instructor-option-${inst.id}`}
              onClick={() => selectInstructor(inst.id)}
              className={`w-full text-left px-4 py-2.5 text-sm hover:bg-primary-50 transition-colors ${
                idx === highlightIndex ? 'bg-primary-100' : ''
              }`}
            >
              <span className="font-medium text-secondary-900">
                {inst.first_name} {inst.last_name}
              </span>
              {inst.title && (
                <span className="ml-2 text-secondary-500 text-xs">({inst.title})</span>
              )}
            </button>
          ))}
        </div>
      )}

      {isOpen && search && filtered.length === 0 && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-secondary-200 rounded-xl shadow-lg px-4 py-2.5 text-sm text-secondary-500">
          No matching instructors
        </div>
      )}
    </div>
  )
}

export default InstructorSelect
