// frontend/src/services/api.js
import axios from 'axios';

// Use environment variable for API URL, fallback to localhost for development
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

console.log("🔧 API Service initialized with base URL:", API_BASE_URL);

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
    console.log(`🔐 API Request to ${config.url} - Token added`);
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
  console.log("📝 API.register called with username:", userData.username);
  const response = await api.post('/auth/register', userData);
  console.log("✅ API.register response:", response.status);
  return response.data;
};

export const login = async (username, password) => {
  console.log("==========================================");
  console.log("🔐 API.login called");
  console.log("   Username:", username);
  console.log("   Password length:", password?.length || 0);
  console.log("   API_BASE_URL:", API_BASE_URL);
  console.log("==========================================");
  
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  
  try {
    console.log("📡 API.login - Making POST request to /auth/login");
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    
    console.log("✅ API.login - Response received");
    console.log("   Status:", response.status);
    console.log("   Has access_token:", !!response.data?.access_token);
    console.log("   User:", response.data?.user?.username);
    
    return response.data;
  } catch (error) {
    console.error("❌ API.login - Error:");
    console.error("   Status:", error.response?.status);
    console.error("   Data:", error.response?.data);
    console.error("   Message:", error.message);
    throw error;
  }
};

export const getCurrentUser = async () => {
  console.log("🔐 API.getCurrentUser called");
  const response = await api.get('/auth/me');
  console.log("✅ API.getCurrentUser response:", response.data?.username);
  return response.data;
};

export const resendVerificationEmail = async (email) => {
  console.log("📧 API.resendVerificationEmail called for:", email);
  const response = await api.post('/auth/resend-verification', { email });
  return response.data;
};

// ==================== HISTORY ENDPOINTS ====================

// Get analysis history (handles pagination)
export const getAnalysisHistory = async (limit = 20, offset = 0) => {
  console.log("📊 API.getAnalysisHistory called");
  const response = await api.get(`/analysis/history?limit=${limit}&offset=${offset}`);
  return response.data;
};

// Get single analysis by ID
export const getAnalysisById = async (id, includeRaw = false) => {
  console.log("📊 API.getAnalysisById called for id:", id);
  const response = await api.get(`/analysis/history/${id}?include_raw=${includeRaw}`);
  return response.data;
};

// Delete analysis
export const deleteAnalysis = async (id) => {
  console.log("🗑️ API.deleteAnalysis called for id:", id);
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
  console.log("📧 API.sendAnalysisEmail called to:", toEmail);
  const response = await api.post('/email/send-analysis', {
    to_email: toEmail,
    analysis_id: analysisId
  });
  return response.data;
};

// ==================== ANALYSIS ENDPOINTS ====================

// File upload with question
export const uploadFile = async (file, question = '') => {
  console.log("📁 API.uploadFile called for file:", file.name);
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
  console.log("🗄️ API.analyzeDatabase called");
  const response = await api.post('/analysis/database', {
    question: question || '',
    connection_config: dbConfig
  });
  return response.data;
};

// Test database connection
export const testDatabaseConnection = async (dbConfig) => {
  console.log("🔌 API.testDatabaseConnection called");
  const response = await api.post('/analysis/test-connection', dbConfig);
  return response.data;
};

// Google Sheets analysis
export const analyzeGoogleSheets = async (question, sheetsConfig) => {
  console.log("📊 API.analyzeGoogleSheets called");
  const response = await api.post('/analysis/google-sheets', {
    question: question || '',
    sheet_config: sheetsConfig
  });
  return response.data;
};

// Test Google Sheets connection
export const testGoogleSheetsConnection = async (sheetsConfig) => {
  console.log("📊 API.testGoogleSheetsConnection called");
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
  console.log("🗄️ API.uploadSQLiteFile called for file:", file.name);
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
  console.log("🔐 API.forgotPassword called for email:", email);
  const response = await api.post('/auth/forgot-password', { email });
  return response.data;
};

// Reset Password
export const resetPassword = async (token, new_password) => {
  console.log("🔐 API.resetPassword called");
  console.log("   Token:", token?.substring(0, 20) + "...");
  console.log("   New password length:", new_password?.length || 0);
  
  const response = await api.post('/auth/reset-password', { 
    token, 
    new_password
  });
  console.log("✅ API.resetPassword response:", response.status);
  return response.data;
};

// Verify Reset Token
export const verifyResetToken = async (token) => {
  console.log("🔐 API.verifyResetToken called");
  const response = await api.get(`/auth/reset-password/verify?token=${token}`);
  return response.data;
};