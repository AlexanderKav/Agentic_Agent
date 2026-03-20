import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if it exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ==================== AUTH ENDPOINTS ====================

export const register = async (userData) => {
  const response = await api.post('/auth/register', userData);
  return response.data;
};

export const login = async (username, password) => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  
  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

export const resendVerificationEmail = async (email) => {
  const response = await api.post('/auth/resend-verification', { email });
  return response.data;
};

// ==================== HISTORY ENDPOINTS ====================

export const getAnalysisHistory = async (limit = 20, offset = 0) => {
  const response = await api.get(`/analysis/history?limit=${limit}&offset=${offset}`);
  return response.data;
};

export const getAnalysisById = async (id) => {
  const response = await api.get(`/analysis/history/${id}`);
  return response.data;
};

// ==================== EMAIL ENDPOINTS ====================

export const sendAnalysisEmail = async (toEmail, analysisId = null) => {
  const response = await api.post('/email/send-analysis', {
    to_email: toEmail,
    analysis_id: analysisId
  });
  return response.data;
};

// ==================== ANALYSIS ENDPOINTS ====================

// File upload with question
export const uploadFile = async (file, question = '') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('question', question || '');

  const response = await axios.post(`${API_BASE_URL}/analysis/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    },
  });
  return response.data;
};

// Database analysis
export const analyzeDatabase = async (question, dbConfig) => {
  const response = await api.post('/analysis/database', {
    question: question || '',
    connection_config: dbConfig
  });
  return response.data;
};

// Test database connection
export const testDatabaseConnection = async (dbConfig) => {
  const response = await api.post('/analysis/test-connection', dbConfig);
  return response.data;
};

// Google Sheets analysis
export const analyzeGoogleSheets = async (question, sheetsConfig) => {
  const response = await api.post('/analysis/google-sheets', {
    question: question || '',
    sheet_config: sheetsConfig
  });
  return response.data;
};

// Test Google Sheets connection
export const testGoogleSheetsConnection = async (sheetsConfig) => {
  const response = await api.post('/analysis/test-google-sheets', sheetsConfig);
  return response.data;
};

// Health check
export const checkHealth = async () => {
  const response = await axios.get('http://localhost:8000/health');
  return response.data;
};

// Check if chart exists
export const checkChartExists = async (filename) => {
  try {
    const response = await axios.head(`http://localhost:8000/api/v1/analysis/chart/${filename}`);
    return response.status === 200;
  } catch (error) {
    return false;
  }
};

// Get chart URL
export const getChartUrl = (filename, key = 0) => {
  return `http://localhost:8000/api/v1/analysis/chart/${encodeURIComponent(filename)}?key=${key}`;
};