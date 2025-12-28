module.exports = {
  'student-evaluation-api': {
    input: {
      target: '../backend/student_evaluation_system/schema.yml',
    },
    output: {
      mode: 'tags-split',
      target: './src/api/generated',
      schemas: './src/api/model',
      client: 'react-query',
      mock: false,
      override: {
        mutator: {
          path: './src/api/mutator.ts',
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
          evaluation_grades_course_averages_retrieve: {
            query: {
              useInfinite: false,
            },
          },
        },
      },
    },
  },
};
