// Mock file data for testing
export const mockFile = new File(['dummy content'], 'test.xlsx', {
  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
})

export const mockLargeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.xlsx', {
  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
})

export const mockValidationResult = {
  is_valid: true,
  errors: [],
  warnings: [],
  suggestions: [],
  validation_details: {
    file_info: {
      name: 'test.xlsx',
      size: 1024,
      size_mb: 0.001,
      extension: 'xlsx',
    },
    row_count: 10,
    available_sheets: ['Sheet1'],
  },
}

export const mockValidationResultWithErrors = {
  is_valid: false,
  errors: [
    {
      message: 'Missing required column: Student ID',
      category: 'validation',
      severity: 'error',
    },
  ],
  warnings: [],
  suggestions: [],
}

export const mockUploadInfo = {
  expected_columns: ['Student ID', 'Name', 'Midterm 1', 'Final'],
  description: 'Upload student assessment scores',
}

export const mockFileUploadResponse = {
  message: 'File uploaded successfully',
  created: 10,
  updated: 5,
  skipped: 0,
}
