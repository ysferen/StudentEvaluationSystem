import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import {
  University,
  Department,
  Program,
  Course,
  Enrollment,
  ProgramOutcomeScore,
  CourseAverage,
  LoginCredentials,
  AuthTokens,
  User
} from '../../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token refresh state
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

/**
 * Process queued requests after token refresh
 */
const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

/**
 * Refresh access token using refresh token
 */
const refreshAccessToken = async (): Promise<string> => {
  const refreshToken = localStorage.getItem('refresh_token');

  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const response = await axios.post(`${API_URL}/api/users/auth/refresh/`, {
    refresh: refreshToken,
  });

  const { access, refresh: newRefresh } = response.data;

  // Store new access token
  localStorage.setItem('access_token', access);

  // Store new refresh token if rotation is enabled
  if (newRefresh) {
    localStorage.setItem('refresh_token', newRefresh);
  }

  return access;
};

/**
 * Request interceptor - Add auth token to all requests
 */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor - Handle token refresh on 401
 */
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {

      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to refresh the token
        const newToken = await refreshAccessToken();

        // Update default header
        api.defaults.headers.common.Authorization = `Bearer ${newToken}`;
        originalRequest.headers.Authorization = `Bearer ${newToken}`;

        // Process queued requests
        processQueue(null, newToken);

        // Retry original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        processQueue(refreshError, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Handle other errors
    return Promise.reject(error);
  }
);

// Handle 401 errors and refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/users/auth/refresh/`, {
            refresh: refreshToken
          })

          const newAccessToken = response.data.access
          localStorage.setItem('access_token', newAccessToken)

          // Retry the original request with new token
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      } else {
        // No refresh token, redirect to login
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

// Auth services are now handled by Orval-generated hooks in useAuth.ts
// authService is deprecated - use useAuth hook instead
export const authService = {
  login: async (credentials: LoginCredentials) => {
    console.warn('authService.login is deprecated. Use useAuth hook instead.')
    const response = await api.post<AuthTokens>('/api/users/auth/login/', credentials)
    localStorage.setItem('access_token', response.data.access)
    localStorage.setItem('refresh_token', response.data.refresh)
    return response.data
  },
  logout: () => {
    console.warn('authService.logout is deprecated. Use useAuth hook instead.')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // Optional: Call backend logout endpoint if it exists
  },
  getCurrentUser: async () => {
    console.warn('authService.getCurrentUser is deprecated. Use useAuth hook instead.')
    const response = await api.get<User>('/api/users/auth/me/')
    return response.data
  }
}

export const coreService = {
  getUniversities: () => api.get<University[]>('/api/core/universities/'),
  getDepartments: (uniId?: number) => api.get<Department[]>('/api/core/departments/', { params: { university: uniId } }),
  getPrograms: (deptId?: number) => api.get<Program[]>('/api/core/programs/', { params: { department: deptId } }),
  getCourses: async (progId?: number, userId?: number) => {
    const response = await api.get('/api/core/courses/', { params: { program: progId, instructor: userId } })
    // Handle paginated response
    const data = response.data
    if (data && typeof data === 'object' && 'results' in data) {
      return { ...response, data: data.results }
    }
    return response
  },
  getCourse: (courseId: number) => api.get<Course>(`/api/core/courses/${courseId}/`),
  getCourseLearningOutcomes: (courseId: number) => api.get(`/api/core/courses/${courseId}/learning_outcomes/`),
  getStudentLOScores: async (studentId?: number, courseId?: number) => {
    const allResults: any[] = []
    let nextUrl: string | null = '/api/core/student-lo-scores/'

    // Fetch all pages by following the 'next' pagination links
    while (nextUrl) {
      const response: any = await api.get(nextUrl, {
        params: nextUrl === '/api/core/student-lo-scores/' ? { student: studentId, course: courseId } : undefined
      })

      allResults.push(...response.data.results)
      nextUrl = response.data.next

      // If next URL is absolute, convert to relative path
      if (nextUrl && nextUrl.startsWith('http')) {
        const url: URL = new URL(nextUrl)
        nextUrl = url.pathname + url.search
      }
    }

    // Return in the same format as api.get() to maintain consistency
    return {
      data: allResults,
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {} as any
    }
  },
  getStudentPOScores: (studentId?: number) => api.get<ProgramOutcomeScore[]>('/api/core/student-po-scores/', { params: { student: studentId } }),
  getLOBasedCourseAverages: async (studentId?: number, courseId?: number): Promise<CourseAverage[]> => {
    const response = await api.get<CourseAverage[]>('/api/core/student-lo-scores/course_averages/', { params: { student: studentId, course: courseId } })
    return response.data
  },
  getLOAveragesByCourse: async (courseId: number) => {
    const response = await api.get('/api/core/student-lo-scores/lo_averages/', { params: { course: courseId } })
    return response.data
  },
}

export const evaluationService = {
  getEnrollments: (studentId?: number) => api.get<Enrollment[]>('/api/evaluation/enrollments/', { params: { student: studentId } }),
  getAssessments: (courseId?: number) => api.get('/api/evaluation/assessments/', { params: { course: courseId } }),
  getStudentGrades: async (studentId?: number, courseId?: number) => {
    const response = await api.get('/api/evaluation/grades/', { params: { student: studentId, course: courseId } })
    const data = response.data
    if (data && typeof data === 'object' && 'results' in data) {
      return { ...response, data: data.results }
    }
    return response
  },
  getGradeBasedCourseAverages: async (studentId?: number, courseId?: number): Promise<CourseAverage[]> => {
    const response = await api.get<CourseAverage[]>('/api/evaluation/grades/course_averages/', {
      params: { student: studentId, course: courseId }
    })
    return response.data
  },
}

export const fileImportService = {
  // Assignment Scores (Turkish Excel format)
  uploadAssignmentScores: async (file: File, courseCode: string, termId: number) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post(
      `/api/core/file-import/assignment-scores/upload/?course_code=${encodeURIComponent(courseCode)}&term_id=${termId}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  validateAssignmentScores: async (file: File, courseCode: string, termId: number) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post(
      `/api/core/file-import/assignment-scores/validate/?course_code=${encodeURIComponent(courseCode)}&term_id=${termId}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  getAssignmentScoresUploadInfo: async () => {
    const response = await api.get('/api/core/file-import/assignment-scores/upload/')
    return response.data
  },

  // Legacy Assessment Scores
  uploadAssessmentScores: async (file: File, sheetName?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (sheetName) {
      formData.append('sheet_name', sheetName)
    }

    const response = await api.post('/api/core/file-import/assessment-scores/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  validateAssessmentScores: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/api/core/file-import/assessment-scores/validate/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getAssessmentScoresUploadInfo: async () => {
    const response = await api.get('/api/core/file-import/assessment-scores/upload/')
    return response.data
  },

  uploadLearningOutcomes: async (file: File, sheetName?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (sheetName) {
      formData.append('sheet_name', sheetName)
    }

    const response = await api.post('/api/core/file-import/learning-outcomes/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  validateLearningOutcomes: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/api/core/file-import/learning-outcomes/validate/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getLearningOutcomesUploadInfo: async () => {
    const response = await api.get('/api/core/file-import/learning-outcomes/upload/')
    return response.data
  },

  uploadProgramOutcomes: async (file: File, sheetName?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (sheetName) {
      formData.append('sheet_name', sheetName)
    }

    const response = await api.post('/api/core/file-import/program-outcomes/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  validateProgramOutcomes: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/api/core/file-import/program-outcomes/validate/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getProgramOutcomesUploadInfo: async () => {
    const response = await api.get('/api/core/file-import/program-outcomes/upload/')
    return response.data
  },
}

export default api;
