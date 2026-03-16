import React, { useState } from 'react';
import {
  Container,
  AppBar,
  Toolbar,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Snackbar,
  Tabs,
  Tab,
  Paper
} from '@mui/material';
import FileUpload from './components/FileUpload';
import DatabaseConnectionForm from './components/DatabaseConnectionForm';
import QuestionInput from './components/QuestionInput';
import DataPreview from './components/DataPreview';
import ResultsDisplay from './components/ResultsDisplay';
import UploadIcon from '@mui/icons-material/CloudUpload';
import DatabaseIcon from '@mui/icons-material/Storage';
import { uploadFile, analyzeDatabase, testDatabaseConnection } from './services/api';

function App() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [userQuestion, setUserQuestion] = useState('');

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    setResults(null);
    setPreview(null);
    setError(null);
    setSelectedFile(null);
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setResults(null);
    setError(null);
  };

  const handleDatabaseConnect = async (dbConfig) => {
    setLoading(true);
    setError(null);
    
    try {
      // For now, just store config and wait for question
      // The actual analysis will happen when user submits question
      setResults({ dbConfig }); // Temporary, will be replaced by actual results
      setPreview(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Database connection failed');
      setOpenSnackbar(true);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (dbConfig) => {
    try {
      const result = await testDatabaseConnection(dbConfig);
      return result;
    } catch (error) {
      throw error;
    }
  };

// In your handleQuestionSubmit function for database tab
const handleQuestionSubmit = async (question) => {
  setLoading(true);
  setError(null);
  setUserQuestion(question);

  try {
    let response;
    
    if (tabValue === 0) {  // File Upload
      if (!selectedFile) {
        throw new Error('Please select a file first');
      }
      response = await uploadFile(selectedFile, question);
      setPreview(response.preview);
      setResults(response.analysis_results);
    } else {  // Database
      if (!results?.dbConfig) {
        throw new Error('Please configure database connection first');
      }
      response = await analyzeDatabase(question, results.dbConfig);
      // The response now matches FileUploadResponse structure
      setPreview(response.preview);
      setResults(response.analysis_results);
    }
  } catch (err) {
    setError(err.response?.data?.detail || err.message || 'Analysis failed');
    setOpenSnackbar(true);
  } finally {
    setLoading(false);
  }
};
  const handleCloseSnackbar = () => {
    setOpenSnackbar(false);
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            🤖 Agentic Analyst
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={handleTabChange} centered>
            <Tab icon={<UploadIcon />} label="Upload File" />
            <Tab icon={<DatabaseIcon />} label="Connect Database" />
          </Tabs>
        </Paper>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {tabValue === 0 ? (
            <FileUpload onFileSelect={handleFileSelect} />
          ) : (
            <DatabaseConnectionForm 
              onConnect={handleDatabaseConnect}
              onTestConnection={handleTestConnection}
              loading={loading}
            />
          )}

          {/* Show Question Input if we have data source */}
          {((tabValue === 0 && selectedFile) || (tabValue === 1 && results?.dbConfig)) && (
            <QuestionInput onSubmit={handleQuestionSubmit} loading={loading} />
          )}

          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {preview && <DataPreview data={preview} />}

          {results && !results.dbConfig && (
            <ResultsDisplay results={results} userQuestion={userQuestion} />
          )}
        </Box>
      </Container>

      <Snackbar
        open={openSnackbar}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>
    </>
  );
}

export default App;