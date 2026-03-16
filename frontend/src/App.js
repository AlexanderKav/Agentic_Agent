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
import GoogleSheetsConnectionForm from './components/GoogleSheetsConnectionForm';
import QuestionInput from './components/QuestionInput';
import DataPreview from './components/DataPreview';
import ResultsDisplay from './components/ResultsDisplay';
import UploadIcon from '@mui/icons-material/CloudUpload';
import DatabaseIcon from '@mui/icons-material/Storage';
import GoogleIcon from '@mui/icons-material/Google';
import { 
  uploadFile, 
  analyzeDatabase, 
  testDatabaseConnection,
  analyzeGoogleSheets,
  testGoogleSheetsConnection 
} from './services/api';

function App() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [userQuestion, setUserQuestion] = useState('');
  
  // Store connection configs
  const [dbConfig, setDbConfig] = useState(null);
  const [sheetsConfig, setSheetsConfig] = useState(null);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    handleClearResults();
    setSelectedFile(null);
    setDbConfig(null);
    setSheetsConfig(null);
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    handleClearResults();
  };

  const handleDatabaseConnect = async (config) => {
    setDbConfig(config);
    setResults({ dbConfig: config });
    setPreview(null);
  };

  const handleGoogleSheetsConnect = async (config) => {
    setSheetsConfig(config);
    setResults({ sheetsConfig: config });
    setPreview(null);
  };

  const handleTestDatabaseConnection = async (config) => {
    try {
      const result = await testDatabaseConnection(config);
      return result;
    } catch (error) {
      throw error;
    }
  };

  const handleTestGoogleSheetsConnection = async (config) => {
    try {
      const result = await testGoogleSheetsConnection(config);
      return result;
    } catch (error) {
      throw error;
    }
  };

  const handleClearResults = () => {
    setResults(null);
    setPreview(null);
    setUserQuestion('');
  };

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
        
      } else if (tabValue === 1) {  // Database
        if (!dbConfig) {
          throw new Error('Please configure database connection first');
        }
        response = await analyzeDatabase(question, dbConfig);
        setPreview(response.preview);
        setResults(response.analysis_results);
        
      } else {  // Google Sheets
        if (!sheetsConfig) {
          throw new Error('Please configure Google Sheets connection first');
        }
        response = await analyzeGoogleSheets(question, sheetsConfig);
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

  // Determine if we have a data source configured
  const hasDataSource = 
    (tabValue === 0 && selectedFile) || 
    (tabValue === 1 && dbConfig) || 
    (tabValue === 2 && sheetsConfig);

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
            <Tab icon={<GoogleIcon />} label="Google Sheets" />
          </Tabs>
        </Paper>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {tabValue === 0 ? (
            <FileUpload onFileSelect={handleFileSelect} />
          ) : tabValue === 1 ? (
            <DatabaseConnectionForm 
              onConnect={handleDatabaseConnect}
              onTestConnection={handleTestDatabaseConnection}
              onClearResults={handleClearResults}
              loading={loading}
            />
          ) : (
            <GoogleSheetsConnectionForm
              onConnect={handleGoogleSheetsConnect}
              onTestConnection={handleTestGoogleSheetsConnection}
              onClearResults={handleClearResults}
              loading={loading}
            />
          )}

          {/* Show Question Input if we have data source */}
          {hasDataSource && (
            <QuestionInput onSubmit={handleQuestionSubmit} loading={loading} />
          )}

          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {preview && <DataPreview data={preview} />}

          {/* Show results only when we have actual results (not just config) */}
          {results && !results.dbConfig && !results.sheetsConfig && (
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