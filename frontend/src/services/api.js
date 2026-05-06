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
  create: (fileId, summaryRatio = 0.3, maxLength = 300) =>
    api.post('/api/summarize/', {
      file_id: fileId,
      summary_ratio: summaryRatio,
      max_summary_length: maxLength,
    }),

  // Poll task status (legacy — use SSE progress instead)
  getTaskStatus: (taskId) => api.get(`/api/summarize/status/${taskId}`),

  // SSE real-time progress stream (replaces polling)
  getProgressUrl: (taskId) => `${API_BASE_URL}/api/summarize/progress/${taskId}`,

  // History + individual
  getHistory: () => api.get('/api/summarize/history'),
  getOne: (summaryId) => api.get(`/api/summarize/${summaryId}`),

  // Get summary video stream URL (for <video> element src)
  getSummaryVideoUrl: (summaryId) => {
    const token = localStorage.getItem('token') || '';
    return `${API_BASE_URL}/api/summarize/video/${summaryId}/stream?token=${encodeURIComponent(token)}`;
  },

  // Synchronous summarization (Transformers/Whisper)
  summarizeYouTube: (url) => api.post('/api/summarize/summarize-youtube', { url }),
  summarizeVideo: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/summarize/summarize-video', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // ── Subtitles ───────────────────────────────────────────────────────
  getSubtitleUrl: (summaryId, format = 'srt') => {
    const token = localStorage.getItem('token') || '';
    return `${API_BASE_URL}/api/summarize/subtitles/${summaryId}/${format}?token=${encodeURIComponent(token)}`;
  },
  downloadSubtitles: (summaryId, format = 'srt') =>
    api.get(`/api/summarize/subtitles/${summaryId}/${format}`, { responseType: 'blob' }),

  // ── Text-to-Speech ──────────────────────────────────────────────────
  generateTTS: (summaryId, voice = 'en-US-AriaNeural', source = 'summary', rate = '+0%') =>
    api.post('/api/summarize/tts/generate', { summary_id: summaryId, voice, source, rate }),
  getTTSVoices: (language = 'en') => api.get('/api/summarize/tts/voices', { params: { language } }),
  getTTSStreamUrl: (filename) => {
    const token = localStorage.getItem('token') || '';
    return `${API_BASE_URL}/api/summarize/tts/stream/${filename}?token=${encodeURIComponent(token)}`;
  },

  // ── Descriptions ────────────────────────────────────────────────────
  generateDescriptions: (summaryId, types = ['oneliner', 'short', 'detailed', 'seo']) =>
    api.post('/api/summarize/descriptions/generate', { summary_id: summaryId, types }),

  // ── Thumbnail ───────────────────────────────────────────────────────
  generateThumbnail: (summaryId) => api.post(`/api/summarize/thumbnail/${summaryId}`),
  getThumbnailUrl: (summaryId) => {
    const token = localStorage.getItem('token') || '';
    return `${API_BASE_URL}/api/summarize/thumbnail/view/${summaryId}?token=${encodeURIComponent(token)}`;
  },

  // ── Highlights ──────────────────────────────────────────────────────
  detectHighlights: (summaryId) => api.post(`/api/summarize/highlights/${summaryId}`),

  // ── Translation ─────────────────────────────────────────────────────
  translateSummary: (summaryId, targetLang) =>
    api.post('/api/summarize/translate', { summary_id: summaryId, target_lang: targetLang }),
  getLanguages: () => api.get('/api/summarize/languages'),
};

// ─── Chat API ───────────────────────────────────────────────────────────────
export const chatAPI = {
  startSession: (summaryId) => api.post('/api/chat/session/start', null, { params: { summary_id: summaryId } }),
  getSession: (sessionId) => api.get(`/api/chat/session/${sessionId}/info`),
  // question now goes in the request body, not query string
  askQuestion: (sessionId, question) => api.post(`/api/chat/session/${sessionId}/ask`, { question }),
  getMessages: (sessionId) => api.get(`/api/chat/session/${sessionId}/messages`),
};

export default api;