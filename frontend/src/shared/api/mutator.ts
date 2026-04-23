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

const baseURL = API_BASE_PATH ? `${API_URL}${API_BASE_PATH}` : API_URL;

// Token refresh state
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

const refreshAccessToken = async (): Promise<string> => {
  const response = await Axios.post(
    `${API_URL}/api/users/auth/refresh/`,
    {},
    { withCredentials: true }
  );
  const { access } = response.data;
  return access;
};

// Create axios instance with base configuration
const axiosInstance = Axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

const AUTH_ENDPOINTS = ['/auth/login', '/auth/logout', '/auth/refresh', '/auth/csrf'];

const isAuthEndpoint = (url: string): boolean => {
  return AUTH_ENDPOINTS.some((endpoint) => url.includes(endpoint));
};

const getCookie = (name: string): string | null => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
};

const bootstrapCsrf = async (): Promise<void> => {
  await Axios.get(`${API_URL}/api/users/auth/csrf/`, { withCredentials: true });
};

let csrfBootstrapPromise: Promise<void> | null = null;

const ensureCsrfToken = async (): Promise<string | null> => {
  let csrfToken = getCookie('csrftoken');
  if (csrfToken) return csrfToken;

  if (!csrfBootstrapPromise) {
    csrfBootstrapPromise = bootstrapCsrf().finally(() => {
      csrfBootstrapPromise = null;
    });
  }
  await csrfBootstrapPromise;

  return getCookie('csrftoken');
};

// Request interceptor - No Authorization header needed, cookies are sent automatically
axiosInstance.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const method = config.method?.toUpperCase();
    const url = config.url || '';

    if (method && method !== 'GET' && !isAuthEndpoint(url)) {
      const csrfToken = await ensureCsrfToken();
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
      }
    }

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
    const requestPath = originalRequest?.url || '';

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (requestPath.includes('/auth/login') || requestPath.includes('/auth/refresh') || requestPath.includes('/auth/logout')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => axiosInstance(originalRequest))
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await refreshAccessToken();
        processQueue(null);
        return axiosInstance(originalRequest);
      } catch {
        processQueue(error);
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

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
