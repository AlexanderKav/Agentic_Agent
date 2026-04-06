// frontend/src/config.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const CHART_BASE_URL = API_BASE_URL.replace('/api/v1', '');

export { API_BASE_URL, CHART_BASE_URL };