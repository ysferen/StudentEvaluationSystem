module.exports = {
  'student-evaluation-api': {
    input: {
      // Both Docker and local dev use this path - volume mount handles the rest
      target: './schema.yml',
    },
    output: {
      mode: 'tags-split',
      target: './src/shared/api/generated',
      schemas: './src/shared/api/model',
      client: 'react-query',
      mock: false,
      override: {
        mutator: {
          path: './src/shared/api/mutator.ts',
          name: 'customInstance',
        },
        query: {
          useQuery: true,
          useInfinite: true,
          useInfiniteQueryParam: 'page',
          version: 5,
        },
        operations: {
          // Disable infinite queries for file import endpoints (they don't support pagination)
          core_file_import_assignment_scores_upload_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          core_file_import_assignment_scores_validate_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          core_file_import_learning_outcomes_upload_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          core_file_import_learning_outcomes_validate_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          core_file_import_program_outcomes_upload_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          core_file_import_program_outcomes_validate_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          // Disable infinite queries for analytics endpoints
          core_student_lo_scores_course_averages_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          core_student_lo_scores_lo_averages_retrieve: {
            query: {
              useInfinite: false,
            },
          },
          // Disable infinite queries for evaluation endpoints
          v1_evaluation_grades_course_averages_retrieve: {
            query: {
              useInfinite: false,
            },
          },
        },
      },
    },
  },
};
