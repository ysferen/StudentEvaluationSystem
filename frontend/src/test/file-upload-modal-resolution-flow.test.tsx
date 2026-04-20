import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FileUploadModal from '@/features/courses/components/FileUploadModal'

const validateMutate = vi.fn()
const resolveMutate = vi.fn()
const uploadMutate = vi.fn(async () => ({}))

vi.mock('@/shared/api/generated/core/core', async () => {
  return {
    useCoreFileImportAssignmentScoresValidateCreate: () => ({ isPending: false, mutateAsync: validateMutate }),
    useCoreFileImportAssignmentScoresResolveCreate: () => ({ isPending: false, mutateAsync: resolveMutate }),
    useCoreFileImportAssignmentScoresUploadCreate: () => ({ isPending: false, mutateAsync: uploadMutate }),
    useCoreFileImportAssignmentScoresUploadRetrieve: () => ({ data: null }),
    useCoreFileImportLearningOutcomesUploadRetrieve: () => ({ data: null }),
    useCoreFileImportLearningOutcomesUploadCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportLearningOutcomesValidateCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportProgramOutcomesUploadRetrieve: () => ({ data: null }),
    useCoreFileImportProgramOutcomesUploadCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportProgramOutcomesValidateCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
  }
})

describe('FileUploadModal solve flow', () => {
  beforeEach(() => {
    validateMutate.mockReset()
    resolveMutate.mockReset()
    uploadMutate.mockReset()
    uploadMutate.mockResolvedValue({})
  })

  it('sends only latest resolve payload and increments resolution action count once per solve', async () => {
    validateMutate.mockResolvedValueOnce({
      is_valid: false,
      phase_reached: 'assessment_validation',
      checks: {
        file_structure: { passed: true },
        column_structure: { passed: true },
        assessment_validation: {
          passed: false,
          missing_assessments: [{ column: 'Quiz(%10)_X', parsed_name: 'Quiz' }],
        },
        student_validation: { passed: true },
        score_validation: { passed: true },
      },
      errors: [], warnings: [], suggestions: [], details: {},
    })

    resolveMutate
      .mockResolvedValueOnce({
        is_valid: false,
        phase_reached: 'student_validation',
        checks: {
          file_structure: { passed: true },
          column_structure: { passed: true },
          assessment_validation: { passed: true, missing_assessments: [] },
          student_validation: {
            passed: false,
            missing_from_database: [{ student_id: '1001', first_name: 'Ada', last_name: 'Lovelace' }],
            not_enrolled: [],
          },
          score_validation: { passed: true },
        },
        errors: [], warnings: [], suggestions: [], details: {},
      })
      .mockResolvedValueOnce({
        is_valid: false,
        phase_reached: 'student_validation',
        checks: {
          file_structure: { passed: true },
          column_structure: { passed: true },
          assessment_validation: { passed: true, missing_assessments: [] },
          student_validation: { passed: true, missing_from_database: [], not_enrolled: [] },
          score_validation: { passed: true },
        },
        errors: [], warnings: [], suggestions: [], details: {},
      })

    const user = userEvent.setup()
    render(
      <FileUploadModal
        course="CS101"
        courseCode="CS101"
        termId={1}
        isOpen={true}
        type="assignment_scores"
        onClose={() => {}}
      />
    )

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['dummy'], 'scores.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    await user.upload(fileInput, file)
    await user.click(screen.getByRole('button', { name: /validate file/i }))

    await user.click(screen.getByRole('button', { name: /solve/i }))
    await user.click(screen.getByRole('button', { name: /create & continue/i }))

    expect(screen.getByText(/1 resolution\(s\) applied/i)).toBeInTheDocument()

    const firstResolvePayload = resolveMutate.mock.calls[0]?.[0]?.data?.resolutions
    expect(firstResolvePayload).toBeTruthy()
    const parsedFirstPayload = JSON.parse(firstResolvePayload)
    expect(parsedFirstPayload).toEqual({
      skip_missing_assessments: false,
      create_assessments: ['Quiz'],
    })

    await user.click(screen.getByRole('button', { name: /solve/i }))
    await user.click(screen.getByRole('button', { name: /create all/i }))

    expect(screen.getByText(/2 resolution\(s\) applied/i)).toBeInTheDocument()

    const latestResolveCall = resolveMutate.mock.calls[resolveMutate.mock.calls.length - 1]
    const secondResolvePayload = latestResolveCall?.[0]?.data?.resolutions
    expect(secondResolvePayload).toBeTruthy()
    const parsedSecondPayload = JSON.parse(secondResolvePayload)
    expect(parsedSecondPayload).toEqual({
      skip_missing_assessments: false,
      skip_missing_students: false,
      create_students: [{ student_id: '1001', first_name: 'Ada', last_name: 'Lovelace' }],
    })
    expect(parsedSecondPayload).not.toHaveProperty('create_assessments')
  })

  it('keeps skip-unenrolled policy when resolving scores in a later step', async () => {
    validateMutate.mockResolvedValueOnce({
      is_valid: false,
      phase_reached: 'student_validation',
      checks: {
        file_structure: { passed: true },
        column_structure: { passed: true },
        assessment_validation: { passed: true, missing_assessments: [] },
        student_validation: {
          passed: false,
          missing_from_database: [],
          not_enrolled: [{ student_id: '1002', first_name: 'Grace', last_name: 'Hopper' }],
        },
        score_validation: { passed: true },
      },
      errors: [], warnings: [], suggestions: [], details: {},
    })

    resolveMutate
      .mockResolvedValueOnce({
        is_valid: false,
        phase_reached: 'score_validation',
        checks: {
          file_structure: { passed: true },
          column_structure: { passed: true },
          assessment_validation: { passed: true, missing_assessments: [] },
          student_validation: { passed: true, missing_from_database: [], not_enrolled: [] },
          score_validation: {
            passed: false,
            invalid_scores: [{ row: 2, column: 'Midterm', value: '120' }],
          },
        },
        errors: [], warnings: [], suggestions: [], details: {},
      })
      .mockResolvedValueOnce({
        is_valid: true,
        phase_reached: 'score_validation',
        checks: {
          file_structure: { passed: true },
          column_structure: { passed: true },
          assessment_validation: { passed: true, missing_assessments: [] },
          student_validation: { passed: true, missing_from_database: [], not_enrolled: [] },
          score_validation: { passed: true, invalid_scores: [] },
        },
        errors: [], warnings: [], suggestions: [], details: {},
      })

    const user = userEvent.setup()
    render(
      <FileUploadModal
        course="CS101"
        courseCode="CS101"
        termId={1}
        isOpen={true}
        type="assignment_scores"
        onClose={() => {}}
      />
    )

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['dummy'], 'scores.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    await user.upload(fileInput, file)
    await user.click(screen.getByRole('button', { name: /validate file/i }))

    await user.click(screen.getByRole('button', { name: /solve/i }))
    await user.click(screen.getByRole('button', { name: /skip all/i }))

    await user.click(screen.getByRole('button', { name: /solve/i }))
    await user.click(screen.getByRole('button', { name: /clamp to range/i }))

    const secondResolvePayload = resolveMutate.mock.calls[1]?.[0]?.data?.resolutions
    expect(secondResolvePayload).toBeTruthy()
    const parsedSecondPayload = JSON.parse(secondResolvePayload)

    expect(parsedSecondPayload).toEqual({
      skip_unenrolled_students: true,
      skip_invalid_scores: false,
      clamp_scores: true,
    })
  })

  it('opens assessment modal when Solve is clicked for failed assessment check', async () => {
    validateMutate.mockResolvedValueOnce({
      is_valid: false,
      phase_reached: 'assessment_validation',
      checks: {
        file_structure: { passed: true },
        column_structure: { passed: true },
        assessment_validation: {
          passed: false,
          missing_assessments: [{ column: 'Quiz(%10)_X', parsed_name: 'Quiz' }],
        },
        student_validation: { passed: true },
        score_validation: { passed: true },
      },
      errors: [], warnings: [], suggestions: [], details: {},
    })

    resolveMutate.mockResolvedValueOnce({})

    const user = userEvent.setup()
    render(
      <FileUploadModal
        course="CS101"
        courseCode="CS101"
        termId={1}
        isOpen={true}
        type="assignment_scores"
        onClose={() => {}}
      />
    )

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['dummy'], 'scores.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    await user.upload(fileInput, file)
    await user.click(screen.getByRole('button', { name: /validate file/i }))

    await user.click(screen.getByRole('button', { name: /solve/i }))
    expect(screen.getByText(/missing assessments/i)).toBeInTheDocument()
  })
})
