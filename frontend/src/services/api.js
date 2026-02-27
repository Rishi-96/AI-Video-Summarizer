import axios from 'axios';

const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  `http://${window.location.hostname}:8000`;

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,          // needed for HttpOnly refresh-token cookie
  headers: { 'Content-Type': 'application/json' },
});

// ─── Request interceptor ────────────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response interceptor (auto-refresh on 401) ─────────────────────────────
let _isRefreshing = false;
let _refreshQueue = [];

const _processQueue = (error, token = null) => {
  _refreshQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  _refreshQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only attempt refresh on 401 that hasn't already been retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (_isRefreshing) {
        // Queue requests while a refresh is in flight
        return new Promise((resolve, reject) => {
          _refreshQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      _isRefreshing = true;

      try {
        // Cookie is sent automatically (withCredentials: true)
        const { data } = await api.post('/api/auth/refresh');
        const newToken = data.access_token;
        localStorage.setItem('token', newToken);
        _processQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        _processQueue(refreshError, null);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ─── Auth API ───────────────────────────────────────────────────────────────
export const authAPI = {
  login: (email, password) => api.post('/api/auth/login', { email, password }),
  register: (userData) => api.post('/api/auth/register', userData),
  getCurrentUser: () => api.get('/api/auth/me'),
  refresh: () => api.post('/api/auth/refresh'),
  logout: () => api.post('/api/auth/logout'),
};

// ─── Videos API ─────────────────────────────────────────────────────────────
export const videosAPI = {
  upload: (formData, onProgress) =>
    api.post('/api/videos/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    }),
  uploadYouTube: (url) => api.post('/api/videos/upload/youtube', { url }),
  getAll: () => api.get('/api/videos/'),
  getOne: (fileId) => api.get(`/api/videos/${fileId}`),
  delete: (fileId) => api.delete(`/api/videos/${fileId}`),
};

// ─── Summaries API ──────────────────────────────────────────────────────────
export const summariesAPI = {
  // Enqueue and return task_id (202 Accepted)
  create: (videoPath, summaryRatio = 0.3, maxLength = 300) =>
    api.post('/api/summarize/', {
      video_path: videoPath,
      summary_ratio: summaryRatio,
      max_summary_length: maxLength,
    }),

  // Poll task status
  getTaskStatus: (taskId) => api.get(`/api/summarize/status/${taskId}`),

  // History + individual
  getHistory: () => api.get('/api/summarize/history'),
  getOne: (summaryId) => api.get(`/api/summarize/${summaryId}`),
};

// ─── Chat API ───────────────────────────────────────────────────────────────
export const chatAPI = {
  startSession: (summaryId) => api.post('/api/chat/session/start', null, { params: { summary_id: summaryId } }),
  // question now goes in the request body, not query string
  askQuestion: (sessionId, question) => api.post(`/api/chat/session/${sessionId}/ask`, { question }),
  getMessages: (sessionId) => api.get(`/api/chat/session/${sessionId}/messages`),
};

export default api;