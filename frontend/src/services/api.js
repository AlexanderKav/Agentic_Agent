// frontend/src/services/api.js
import axios from 'axios';

// Use environment variable for API URL, fallback to localhost for development
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

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

// Helper function to get chart base URL
const getChartBaseUrl = () => {
  // Use the same base URL as the API
  return API_BASE_URL.replace('/api/v1', '');
};

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

// Get analysis history (handles pagination)
export const getAnalysisHistory = async (limit = 20, offset = 0) => {
  const response = await api.get(`/analysis/history?limit=${limit}&offset=${offset}`);
  return response.data;
};

// Get single analysis by ID
export const getAnalysisById = async (id, includeRaw = false) => {
  const response = await api.get(`/analysis/history/${id}?include_raw=${includeRaw}`);
  return response.data;
};

// Delete analysis
export const deleteAnalysis = async (id) => {
  const response = await api.delete(`/analysis/history/${id}`);
  return response.data;
};

// Get analysis metrics (lightweight)
export const getAnalysisMetrics = async (id, metricType = null, category = null) => {
  let url = `/analysis/history/${id}/metrics`;
  const params = [];
  if (metricType) params.push(`metric_type=${metricType}`);
  if (category) params.push(`category=${category}`);
  if (params.length) url += `?${params.join('&')}`;
  const response = await api.get(url);
  return response.data;
};

// Get analysis insights (lightweight)
export const getAnalysisInsights = async (id, insightType = null) => {
  let url = `/analysis/history/${id}/insights`;
  if (insightType) url += `?insight_type=${insightType}`;
  const response = await api.get(url);
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
  const chartBaseUrl = getChartBaseUrl();
  const response = await axios.get(`${chartBaseUrl}/health`);
  return response.data;
};

// Check if chart exists
export const checkChartExists = async (filename) => {
  try {
    const chartBaseUrl = getChartBaseUrl();
    const response = await axios.head(`${chartBaseUrl}/api/v1/analysis/chart/${filename}`);
    return response.status === 200;
  } catch (error) {
    return false;
  }
};

// Get chart URL
export const getChartUrl = (filename, key = 0) => {
  const chartBaseUrl = getChartBaseUrl();
  return `${chartBaseUrl}/api/v1/analysis/chart/${encodeURIComponent(filename)}?key=${key}`;
};

// SQLite file upload
export const uploadSQLiteFile = async (file, question, table) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('question', question);
  formData.append('table', table);
  
  const token = localStorage.getItem('token');
  const response = await axios.post(`${API_BASE_URL}/analysis/upload-sqlite`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      'Authorization': `Bearer ${token}`
    },
  });
  return response.data;
};

// Forgot Password
export const forgotPassword = async (email) => {
  const response = await api.post('/auth/forgot-password', { email });
  return response.data;
};

// Reset Password
export const resetPassword = async (token, new_password) => {
  const response = await api.post('/auth/reset-password', { 
    token, 
    new_password
  });
  return response.data;
};

// Verify Reset Token
export const verifyResetToken = async (token) => {
  const response = await api.get(`/auth/reset-password/verify?token=${token}`);
  return response.data;
};