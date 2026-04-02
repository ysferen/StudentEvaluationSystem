import Axios, { AxiosRequestConfig } from 'axios';

// API Configuration from environment variables
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE_PATH = import.meta.env.VITE_API_BASE_PATH || '';

// Construct full base URL
const baseURL = API_BASE_PATH
  ? `${API_URL}${API_BASE_PATH}`
  : API_URL;

// Create axios instance with base configuration
const axiosInstance = Axios.create({
  baseURL,
  timeout: 30000, // 30 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add JWT token to all requests
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Debug logging in development
    if (import.meta.env.VITE_ENABLE_DEBUG === 'true') {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle auth errors
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle specific error statuses
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // Token expired or invalid - clear storage and redirect to login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          break;
        case 403:
          console.error('[API] Permission denied:', error.response.data);
          break;
        case 429:
          console.error('[API] Rate limited. Please try again later.');
          break;
        case 500:
        case 502:
        case 503:
        case 504:
          console.error('[API] Server error:', error.response.data);
          break;
        default:
          console.error('[API] Error:', error.response.data);
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('[API] Network error - no response received');
    }

    return Promise.reject(error);
  }
);

// This is the mutator function that Orval will use
// It must return the response data, not the full AxiosResponse
export const customInstance = <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  const source = Axios.CancelToken.source();

  const promise = axiosInstance({
    ...config,
    ...options,
    cancelToken: source.token,
  }).then(({ data }) => data);

  // Add cancel function to the promise
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (promise as any).cancel = () => {
    source.cancel('Query was cancelled');
  };

  return promise;
};

// Default export for convenience
export default customInstance;

// Export axios instance if you need to use it directly
export { axiosInstance };

// Export config for reference
export { API_URL, API_BASE_PATH, baseURL };
