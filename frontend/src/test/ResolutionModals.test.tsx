import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  MissingAssessmentsModal,
  MissingStudentsModal,
  UnenrolledStudentsModal,
  InvalidScoresModal
} from '@/features/courses/components/ResolutionModals'

const renderModal = (ui: React.ReactElement) => {
  return render(ui)
}

describe('MissingAssessmentsModal', () => {
  const defaultProps = {
    isOpen: true,
    missingAssessments: [
      { column: 'Quiz(%10)_XYZ', parsed_name: 'Quiz' },
      { column: 'Homework(%20)_ABC', parsed_name: 'Homework' }
    ],
    availableInDatabase: ['Midterm', 'Final', 'Project'],
    onClose: vi.fn(),
    onResolve: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows missing assessments list', () => {
    renderModal(<MissingAssessmentsModal {...defaultProps} />)
    expect(screen.getByText('Quiz')).toBeInTheDocument()
    expect(screen.getByText('Homework')).toBeInTheDocument()
  })

  it('shows count of missing assessments', () => {
    renderModal(<MissingAssessmentsModal {...defaultProps} />)
    expect(screen.getByText(/2 assessment.*not found/i)).toBeInTheDocument()
  })

  it('calls onResolve with skip when Skip All is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<MissingAssessmentsModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /skip all/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('skip', [])
  })

  it('calls onResolve with create and selected names when Create & Continue is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<MissingAssessmentsModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /create & continue/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('create', ['Quiz', 'Homework'])
  })

  it('allows toggling individual assessments', async () => {
    const user = userEvent.setup()
    renderModal(<MissingAssessmentsModal {...defaultProps} />)
    const quizCheckbox = screen.getByRole('checkbox', { name: /quiz/i })
    await user.click(quizCheckbox)
    await user.click(screen.getByRole('button', { name: /create & continue/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('create', ['Homework'])
  })
})

describe('MissingStudentsModal', () => {
  const defaultProps = {
    isOpen: true,
    missingStudents: [
      { student_id: 'S1234', first_name: 'Ali', last_name: 'Veli' },
      { student_id: 'S5678', first_name: 'Ayşe', last_name: 'Demir' }
    ],
    onClose: vi.fn(),
    onResolve: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows student list with IDs and names', () => {
    renderModal(<MissingStudentsModal {...defaultProps} />)
    expect(screen.getByText('S1234')).toBeInTheDocument()
    expect(screen.getByText('Ali Veli')).toBeInTheDocument()
    expect(screen.getByText('S5678')).toBeInTheDocument()
    expect(screen.getByText('Ayşe Demir')).toBeInTheDocument()
  })

  it('calls onResolve with create when Create All is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<MissingStudentsModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /create all/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('create', defaultProps.missingStudents)
  })

  it('calls onResolve with skip when Skip All is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<MissingStudentsModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /skip all/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('skip', [])
  })

  it('uses scrollable table region and sticky action footer layout', () => {
    const { container } = renderModal(<MissingStudentsModal {...defaultProps} />)

    const card = Array.from(container.querySelectorAll('div')).find((el) =>
      el.className.includes('max-h-[90vh]') && el.className.includes('flex') && el.className.includes('flex-col')
    )
    expect(card).toBeTruthy()

    const tableScrollRegion = Array.from(container.querySelectorAll('div')).find((el) =>
      el.className.includes('overflow-auto') && el.className.includes('max-h-[50vh]')
    )
    expect(tableScrollRegion).toBeTruthy()

    const stickyFooter = Array.from(container.querySelectorAll('div')).find((el) =>
      el.className.includes('sticky')
      && el.className.includes('bottom-0')
      && el.className.includes('bg-white')
      && el.className.includes('border-t')
    )
    expect(stickyFooter).toBeTruthy()
  })
})

describe('UnenrolledStudentsModal', () => {
  const defaultProps = {
    isOpen: true,
    unenrolledStudents: [
      { student_id: 'S9012', first_name: 'Mehmet', last_name: 'Yılmaz' }
    ],
    onClose: vi.fn(),
    onResolve: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows unenrolled student list', () => {
    renderModal(<UnenrolledStudentsModal {...defaultProps} />)
    expect(screen.getByText('S9012')).toBeInTheDocument()
    expect(screen.getByText('Mehmet Yılmaz')).toBeInTheDocument()
  })

  it('calls onResolve with enroll when Enroll All is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<UnenrolledStudentsModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /enroll all/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('enroll', ['S9012'])
  })

  it('calls onResolve with skip when Skip All is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<UnenrolledStudentsModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /skip all/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('skip', [])
  })

  it('uses scrollable table region and sticky action footer layout', () => {
    const { container } = renderModal(<UnenrolledStudentsModal {...defaultProps} />)

    const card = Array.from(container.querySelectorAll('div')).find((el) =>
      el.className.includes('max-h-[90vh]') && el.className.includes('flex') && el.className.includes('flex-col')
    )
    expect(card).toBeTruthy()

    const tableScrollRegion = Array.from(container.querySelectorAll('div')).find((el) =>
      el.className.includes('overflow-auto') && el.className.includes('max-h-[50vh]')
    )
    expect(tableScrollRegion).toBeTruthy()

    const stickyFooter = Array.from(container.querySelectorAll('div')).find((el) =>
      el.className.includes('sticky')
      && el.className.includes('bottom-0')
      && el.className.includes('bg-white')
      && el.className.includes('border-t')
    )
    expect(stickyFooter).toBeTruthy()
  })
})

describe('InvalidScoresModal', () => {
  const defaultProps = {
    isOpen: true,
    invalidScores: [
      { row: 5, column: 'Midterm(%30)_ABC', value: '150', error: 'out of range' },
      { row: 12, column: 'Project(%40)_DEF', value: '-20', error: 'out of range' }
    ],
    onClose: vi.fn(),
    onResolve: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows invalid scores with row, column, and value', () => {
    renderModal(<InvalidScoresModal {...defaultProps} />)
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('150')).toBeInTheDocument()
    expect(screen.getByText('-20')).toBeInTheDocument()
  })

  it('calls onResolve with skip when Skip Invalid is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<InvalidScoresModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /skip invalid/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('skip')
  })

  it('calls onResolve with clamp when Clamp Values is clicked', async () => {
    const user = userEvent.setup()
    renderModal(<InvalidScoresModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /clamp to range/i }))
    expect(defaultProps.onResolve).toHaveBeenCalledWith('clamp')
  })
})
