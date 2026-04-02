import Axios, { AxiosRequestConfig } from 'axios';

const runtime = typeof window !== 'undefined' ? (window as unknown as Record<string, unknown>) : {};

const apiUrlFromWindow = typeof runtime.__SES_API_URL__ === 'string' ? (runtime.__SES_API_URL__ as string) : undefined;
const apiBasePathFromWindow =
	typeof runtime.__SES_API_BASE_PATH__ === 'string' ? (runtime.__SES_API_BASE_PATH__ as string) : undefined;

const API_URL = apiUrlFromWindow || 'http://localhost:8000';
const API_BASE_PATH = apiBasePathFromWindow || '';

const baseURL = API_BASE_PATH ? `${API_URL}${API_BASE_PATH}` : API_URL;

const axiosInstance = Axios.create({
	baseURL,
	timeout: 30000,
	headers: {
		'Content-Type': 'application/json',
	},
});

axiosInstance.interceptors.request.use((config) => {
	const token = localStorage.getItem('access_token');
	if (token) {
		config.headers = config.headers || {};
		config.headers.Authorization = `Bearer ${token}`;
	}
	return config;
});

axiosInstance.interceptors.response.use(
	(response) => response,
	(error) => {
		if (error.response?.status === 401) {
			localStorage.removeItem('access_token');
			localStorage.removeItem('refresh_token');
			window.location.href = '/login';
		}

		return Promise.reject(error);
	}
);

export const customInstance = <T>(config: AxiosRequestConfig, options?: AxiosRequestConfig): Promise<T> => {
	const source = Axios.CancelToken.source();

	const promise = axiosInstance({
		...config,
		...options,
		cancelToken: source.token,
	}).then(({ data }) => data);

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	(promise as any).cancel = () => {
		source.cancel('Query was cancelled');
	};

	return promise;
};
