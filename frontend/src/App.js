import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
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
  Paper,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Button,
  Badge
} from '@mui/material';
import FileUpload from './components/FileUpload';
// Keep the import but we'll use SimpleDatabaseConnection instead
// import DatabaseConnectionForm from './components/DatabaseConnectionForm';
import SimpleDatabaseConnection from './components/SimpleDatabaseConnection';
import GoogleSheetsConnectionForm from './components/GoogleSheetsConnectionForm';
import QuestionInput from './components/QuestionInput';
import DataPreview from './components/DataPreview';
import ResultsDisplay from './components/ResultsDisplay';
import Login from './components/Login';
import LoginPage from './components/LoginPage';
import HistoryDrawer from './components/HistoryDrawer';
import ProtectedRoute from './components/ProtectedRoute';
import VerificationSuccess from './components/VerificationSuccess';
import UploadIcon from '@mui/icons-material/CloudUpload';
import DatabaseIcon from '@mui/icons-material/Storage';
import GoogleIcon from '@mui/icons-material/Google';
import HistoryIcon from '@mui/icons-material/History';
import EmailIcon from '@mui/icons-material/Email';
import LogoutIcon from '@mui/icons-material/Logout';
import { 
  uploadFile, 
  analyzeDatabase, 
  testDatabaseConnection,
  analyzeGoogleSheets,
  testGoogleSheetsConnection,
  getAnalysisById,
  sendAnalysisEmail
} from './services/api';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Main app content component (protected)
function DashboardContent() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [openSnackbar, setOpenSnackbar] = useState(false);
  const [userQuestion, setUserQuestion] = useState('');
  const [loginOpen, setLoginOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const [emailSending, setEmailSending] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  
  const [dataSourceReady, setDataSourceReady] = useState(false);
  const [dbConfig, setDbConfig] = useState(null);
  const [sheetsConfig, setSheetsConfig] = useState(null);
  
  const { user, logout, isAuthenticated, refreshUser } = useAuth();

  // Listen for verification messages from the verification tab
  useEffect(() => {
    const handleMessage = (event) => {
      if (event.data === 'email-verified') {
        // Refresh user data to get updated verification status
        refreshUser();
      }
    };

    window.addEventListener('message', handleMessage);
    
    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, [refreshUser]);

  const handleMenu = (event) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const handleLogout = () => {
    logout();
    handleMenuClose();
    handleClearResults();
  };

  const handleHistoryOpen = () => {
    setHistoryOpen(true);
    handleMenuClose();
  };

  const handleHistoryClose = () => setHistoryOpen(false);

const handleLoadHistoryItem = async (id) => {
  try {
    setLoading(true);
    // Use includeRaw=true to get full results
    const analysis = await getAnalysisById(id, true);
    
    // Handle both old and new response formats
    if (analysis.results) {
      // Old format: results directly in response
      setResults(analysis.results);
    } else if (analysis.raw_results) {
      // New format: raw_results contains the analysis data
      setResults(analysis.raw_results);
    } else {
      // Build results from structured data
      const structuredResults = {};
      
      // Add metrics if available
      if (analysis.structured_metrics) {
        structuredResults.metrics = analysis.structured_metrics;
      }
      
      // Add insights if available
      if (analysis.insights) {
        structuredResults.insights = analysis.insights;
      }
      
      // Add charts if available
      if (analysis.charts) {
        structuredResults.charts = analysis.charts;
      }
      
      setResults(structuredResults);
    }
    
    setUserQuestion(analysis.question);
    setHistoryOpen(false);
  } catch (err) {
    console.error('Failed to load analysis:', err);
    setError('Failed to load analysis');
    setOpenSnackbar(true);
  } finally {
    setLoading(false);
  }
};

  const handleEmailResults = async () => {
    if (!user?.email) {
      setError('No email address associated with your account');
      setOpenSnackbar(true);
      return;
    }

    setEmailSending(true);
    try {
      await sendAnalysisEmail(user.email);
      setEmailSent(true);
      setTimeout(() => setEmailSent(false), 3000);
    } catch (err) {
      setError('Failed to send email');
      setOpenSnackbar(true);
    } finally {
      setEmailSending(false);
    }
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    handleClearResults();
    setSelectedFile(null);
    setDbConfig(null);
    setSheetsConfig(null);
    setDataSourceReady(false);
    setUserQuestion('');
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setDataSourceReady(!!file);
    handleClearResults();
    setUserQuestion('');
  };

  const handleDatabaseConnect = (config, isValid) => {
    if (isValid) {
      setDbConfig(config);
      setDataSourceReady(true);
      setResults({ dbConfig: config });
      setPreview(null);
    } else {
      setDbConfig(null);
      setDataSourceReady(false);
      setUserQuestion('');
    }
  };

  const handleGoogleSheetsConnect = (config, isValid) => {
    if (isValid) {
      setSheetsConfig(config);
      setDataSourceReady(true);
      setResults({ sheetsConfig: config });
      setPreview(null);
    } else {
      setSheetsConfig(null);
      setDataSourceReady(false);
      setUserQuestion('');
    }
  };

  const handleTestDatabaseConnection = async (config) => {
    try {
      const result = await testDatabaseConnection(config);
      return { success: true, data: result };
    } catch (error) {
      setDataSourceReady(false);
      setUserQuestion('');
      throw error;
    }
  };

  const handleTestGoogleSheetsConnection = async (config) => {
    try {
      const result = await testGoogleSheetsConnection(config);
      return { success: true, data: result };
    } catch (error) {
      setDataSourceReady(false);
      setUserQuestion('');
      throw error;
    }
  };

  const handleClearResults = () => {
    setResults(null);
    setPreview(null);
    setUserQuestion('');
    setDataSourceReady(false);
  };

  // handleQuestionSubmit function
  const handleQuestionSubmit = async (question) => {
    setLoading(true);
    setError(null);
    setUserQuestion(question);

    try {
      let response;
      
      if (tabValue === 0) {
        // File upload (CSV, Excel, or SQLite file)
        if (!selectedFile) throw new Error('Please select a file first');
        response = await uploadFile(selectedFile, question);
        setPreview(response.preview);
        setResults(response.analysis_results);
        
      } else if (tabValue === 1) {
        // Database connection
        if (!dbConfig) throw new Error('Please configure database connection first');
        
        // Check if this is a SQLite connection (file upload via database form)
        if (dbConfig.db_type === 'sqlite' && dbConfig.sqlite_file) {
          console.log("📤 SQLite file upload detected, using upload-sqlite endpoint");
          
          // Use the file upload approach for SQLite
          const formData = new FormData();
          formData.append('file', dbConfig.sqlite_file);
          formData.append('question', question);
          formData.append('table', dbConfig.selected_sqlite_table);
          
          const token = localStorage.getItem('token');
          const apiResponse = await fetch('http://localhost:8000/api/v1/analysis/upload-sqlite', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`
            },
            body: formData
          });
          
          if (!apiResponse.ok) {
            const errorData = await apiResponse.json();
            throw new Error(errorData.detail || 'SQLite analysis failed');
          }
          
          response = await apiResponse.json();
          setPreview(response.preview);
          setResults(response.analysis_results);
        } else {
          // Regular PostgreSQL/MySQL database connection
          console.log("💾 Regular database connection");
          response = await analyzeDatabase(question, dbConfig);
          setPreview(response.preview);
          setResults(response.analysis_results);
        }
        
      } else if (tabValue === 2) {
        // Google Sheets
        if (!sheetsConfig) throw new Error('Please configure Google Sheets connection first');
        response = await analyzeGoogleSheets(question, sheetsConfig);
        setPreview(response.preview);
        setResults(response.analysis_results);
      }
      
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err.response?.data?.detail || err.message || 'Analysis failed');
      setOpenSnackbar(true);
      setDataSourceReady(false);
      setUserQuestion('');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSnackbar = () => setOpenSnackbar(false);

  const hasValidDataSource = 
    (tabValue === 0 && selectedFile) || 
    (tabValue === 1 && dbConfig && dataSourceReady) || 
    (tabValue === 2 && sheetsConfig && dataSourceReady);

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, display: 'flex', alignItems: 'center' }}>
            🤖 Agentic Analyst
          </Typography>
          
          {isAuthenticated ? (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <IconButton color="inherit" onClick={() => setHistoryOpen(true)} sx={{ mr: 1 }}>
                <Badge color="secondary" variant="dot" invisible={false}>
                  <HistoryIcon />
                </Badge>
              </IconButton>
              
              <IconButton onClick={handleMenu} color="inherit">
                <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                  {user?.username?.charAt(0).toUpperCase()}
                </Avatar>
              </IconButton>
              
              <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
                <MenuItem disabled>
                  <Typography variant="body2">
                    Signed in as <strong>{user?.username}</strong>
                  </Typography>
                </MenuItem>
                <MenuItem onClick={handleHistoryOpen}>
                  <HistoryIcon sx={{ mr: 1, fontSize: 20 }} />
                  History
                </MenuItem>
                <MenuItem onClick={handleLogout}>
                  <LogoutIcon sx={{ mr: 1, fontSize: 20 }} />
                  Logout
                </MenuItem>
              </Menu>
            </Box>
          ) : (
            <Button color="inherit" onClick={() => setLoginOpen(true)}>
              Login
            </Button>
          )}
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
            <FileUpload onFileSelect={handleFileSelect} onClearResults={handleClearResults} />
          ) : tabValue === 1 ? (
            <SimpleDatabaseConnection 
              onConnect={handleDatabaseConnect}
              onClearResults={handleClearResults}
            />
          ) : (
            <GoogleSheetsConnectionForm
              onConnect={handleGoogleSheetsConnect}
              onTestConnection={handleTestGoogleSheetsConnection}
              onClearResults={handleClearResults}
              loading={loading}
            />
          )}

          {hasValidDataSource && (
            <QuestionInput 
              onSubmit={handleQuestionSubmit} 
              loading={loading}
              onClear={() => setUserQuestion('')}
            />
          )}

          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {preview && <DataPreview data={preview} />}

          {results && !results.dbConfig && !results.sheetsConfig && (
            <Box>
              {isAuthenticated && (
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                  <Button
                    variant="outlined"
                    startIcon={<EmailIcon />}
                    onClick={handleEmailResults}
                    disabled={emailSending}
                    size="small"
                  >
                    {emailSending ? 'Sending...' : 'Email Results'}
                  </Button>
                </Box>
              )}
              <ResultsDisplay results={results} userQuestion={userQuestion} />
            </Box>
          )}
        </Box>
      </Container>

      {/* Login Modal - for in-app login */}
      <Login open={loginOpen} onClose={() => setLoginOpen(false)} />
      
      {/* History Drawer */}
      <HistoryDrawer open={historyOpen} onClose={handleHistoryClose} onLoadAnalysis={handleLoadHistoryItem} />
      
      {/* Email Success Snackbar */}
      <Snackbar open={emailSent} autoHideDuration={3000} onClose={() => setEmailSent(false)}>
        <Alert severity="success">Results sent to your email!</Alert>
      </Snackbar>
      
      {/* Error Snackbar */}
      <Snackbar open={openSnackbar} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity="error">{error}</Alert>
      </Snackbar>
    </>
  );
}

// Main App with Router
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public route - Login page (full page) */}
          <Route path="/login" element={<LoginPage />} />

          {/* Public route - Email verification success page */}
          <Route path="/verification-success" element={<VerificationSuccess />} />
          
          {/* Protected routes - everything else */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <DashboardContent />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;