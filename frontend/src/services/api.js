import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post('/api/auth/login/json', { email, password }),
  register: (userData) => api.post('/api/auth/register', userData),
  getCurrentUser: () => api.get('/api/auth/me'),
};

// Videos API
export const videosAPI = {
  upload: (formData) => api.post('/api/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      return percentCompleted;
    },
  }),
  getAll: () => api.get('/api/videos/'),
  getOne: (fileId) => api.get(`/api/videos/${fileId}`),
  delete: (fileId) => api.delete(`/api/videos/${fileId}`),
};

// Summaries API
export const summariesAPI = {
  create: (videoPath, summaryRatio = 0.3, maxLength = 300) => 
    api.post('/api/summarize/', { 
      video_path: videoPath, 
      summary_ratio: summaryRatio,
      max_summary_length: maxLength 
    }),
  getHistory: () => api.get('/api/summarize/history'),
  getOne: (summaryId) => api.get(`/api/summarize/${summaryId}`),
};

// Chat API
export const chatAPI = {
  startSession: (summaryId) => api.post('/api/chat/session/start', null, { params: { summary_id: summaryId } }),
  askQuestion: (sessionId, question) => api.post(`/api/chat/session/${sessionId}/ask`, null, { params: { question } }),
};

export default api;