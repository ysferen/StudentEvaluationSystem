import Axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';

type RuntimeEnv = {
  VITE_API_URL?: string;
  VITE_API_BASE_PATH?: string;
  VITE_ENABLE_DEBUG?: string;
};

const runtimeEnv =
  typeof globalThis !== 'undefined' && (globalThis as { __SES_ENV__?: RuntimeEnv }).__SES_ENV__
    ? (globalThis as { __SES_ENV__?: RuntimeEnv }).__SES_ENV__
    : {};

const API_URL = runtimeEnv?.VITE_API_URL || 'http://localhost:8000';
const API_BASE_PATH = runtimeEnv?.VITE_API_BASE_PATH || '';

// Construct full base URL
const baseURL = API_BASE_PATH
  ? `${API_URL}${API_BASE_PATH}`
  : API_URL;

// Token refresh state
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const refreshAccessToken = async (): Promise<string> => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  const response = await Axios.post(`${API_URL}/api/users/auth/refresh/`, {
    refresh: refreshToken,
  });
  const { access, refresh: newRefresh } = response.data;
  localStorage.setItem('access_token', access);
  if (newRefresh) {
    localStorage.setItem('refresh_token', newRefresh);
  }
  return access;
};

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
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Debug logging in development
    if (runtimeEnv?.VITE_ENABLE_DEBUG === 'true') {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle token refresh with request queuing
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return axiosInstance(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const newToken = await refreshAccessToken();
        axiosInstance.defaults.headers.common.Authorization = `Bearer ${newToken}`;
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        processQueue(null, newToken);
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Handle other error statuses with logging
    if (error.response) {
      switch (error.response.status) {
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
