import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FileUploadModal from '@/features/courses/components/FileUploadModal'

vi.mock('@/shared/api/generated/core/core', async () => {
  const validateMutate = vi.fn(async () => ({
    is_valid: false,
    phase_reached: 'assessment_validation',
    checks: {
      file_structure: { passed: true },
      column_structure: { passed: true },
      assessment_validation: { passed: false, missing_assessments: [{ column: 'Quiz(%10)_X', parsed_name: 'Quiz' }] },
      student_validation: { passed: true },
      score_validation: { passed: true },
    },
    errors: [], warnings: [], suggestions: [], details: {},
  }))

  return {
    useCoreFileImportAssignmentScoresValidateCreate: () => ({ isPending: false, mutateAsync: validateMutate }),
    useCoreFileImportAssignmentScoresResolveCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
    useCoreFileImportAssignmentScoresUploadCreate: () => ({ isPending: false, mutateAsync: vi.fn(async () => ({})) }),
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
  it('opens assessment modal when Solve is clicked for failed assessment check', async () => {
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
