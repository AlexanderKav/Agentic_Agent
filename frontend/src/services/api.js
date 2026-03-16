import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// File upload with question (handles both CSV and Excel)
export const uploadFile = async (file, question = '') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('question', question || '');

  try {
    const response = await axios.post(`${API_BASE_URL}/analysis/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Upload error:', error.response?.data || error.message);
    throw error;
  }
};

// Direct analysis with database
export const analyzeDatabase = async (question, connectionConfig) => {
  try {
    const response = await api.post('/analysis/analyze', {
      question: question || '',
      data_source: 'database',
      source_config: connectionConfig,
    });
    return response.data;
  } catch (error) {
    console.error('Analysis error:', error.response?.data || error.message);
    throw error;
  }
};

// Health check
export const checkHealth = async () => {
  try {
    const response = await axios.get('http://localhost:8000/health');
    return response.data;
  } catch (error) {
    console.error('Health check error:', error.message);
    throw error;
  }
};