import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// File upload with question
export const uploadFile = async (file, question = '') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('question', question || '');

  const response = await axios.post(`${API_BASE_URL}/analysis/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
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