import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Grid,
  TextField,
  Button,
  Box,
  Alert,
  CircularProgress,
  Link,
  InputAdornment,
  Divider,
  FormHelperText
} from '@mui/material';
import {
  Google as GoogleIcon,
  Refresh as RefreshIcon,
  Help as HelpIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Warning as WarningIcon
} from '@mui/icons-material';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
const MAX_SHEET_SIZE = 100000;

// Service account email - update this with your actual service account email
const SERVICE_ACCOUNT_EMAIL = 'agentic-analyst-bot@agentic-analyst-489012.iam.gserviceaccount.com';

const GoogleSheetsConnectionForm = ({ onConnect, onTestConnection, onClearResults, loading }) => {
  const [config, setConfig] = useState({
    sheet_id: '',
    sheet_range: 'A1:Z1000',
    sheet_name: ''
  });
  
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [connectionSuccess, setConnectionSuccess] = useState(false);
  const [permissionWarning, setPermissionWarning] = useState(null);
  const [sheetNameError, setSheetNameError] = useState(null);

  const validateSheetId = (id) => {
    const regex = /^[a-zA-Z0-9-_]+$/;
    return regex.test(id);
  };

  const handleChange = (field) => (event) => {
    const value = event.target.value;
    setConfig({ ...config, [field]: value });
    setValidationError(null);
    setPermissionWarning(null);
    setSheetNameError(null);
    if (connectionSuccess) {
      setConnectionSuccess(false);
      setTestResult(null);
    }
  };

  const handleTestConnection = async () => {
    // Validate sheet_id
    if (!config.sheet_id) {
      setValidationError('Sheet ID is required');
      return;
    }

    // Validate sheet_name is provided
    if (!config.sheet_name || config.sheet_name.trim() === '') {
      setSheetNameError('Sheet name is required. Please enter the exact name of the sheet/tab (e.g., "Sheet1", "Sales Data", etc.)');
      return;
    }

    const extractedId = extractSheetId(config.sheet_id);
    if (!validateSheetId(extractedId)) {
      setValidationError('Invalid Sheet ID format');
      return;
    }

    setTesting(true);
    setTestResult(null);
    setValidationError(null);
    setSheetNameError(null);
    setPermissionWarning(null);
    
    try {
      const result = await onTestConnection({ 
        ...config, 
        sheet_id: extractedId,
        sheet_name: config.sheet_name.trim()
      });
      
      console.log('Full response from parent:', result);
      
      // Check for success using the correct backend response structure
      if (result && result.status === 'success') {
        let successMessage = '✅ Successfully connected!';
        let warning = null;
        
        // Use result.message directly (backend sends this)
        if (result.message) {
          successMessage = result.message;
        } else if (result.rows_preview !== undefined) {
          successMessage = `✅ Connected to sheet "${config.sheet_name}"! Found ${result.rows_preview} rows with ${result.columns?.length || 0} columns.`;
        } else if (result.rows) {
          successMessage = `✅ Connected to sheet "${config.sheet_name}"! Found ${result.rows} rows.`;
        }
        
        // Check for permission warning
        if (result.warning) {
          warning = result.warning;
          setPermissionWarning(warning);
        }
        
        setTestResult({ 
          success: true, 
          message: successMessage
        });
        setConnectionSuccess(true);
        
        // Pass the config to parent with success flag and sheet info
        onConnect({ 
          ...config, 
          sheet_id: extractedId,
          sheet_name: config.sheet_name.trim(),
          rows: result.rows_preview || result.rows,
          columns: result.columns,
          preview: result.preview
        }, true);
        
      } else if (result && result.status === 'warning') {
        // Handle warning case (connected but something's off)
        setTestResult({ 
          success: true, 
          message: result.message || `Connected to sheet "${config.sheet_name}" with warnings`
        });
        setConnectionSuccess(true);
        onConnect({ ...config, sheet_id: extractedId, sheet_name: config.sheet_name.trim() }, true);
        
      } else if (result && result.status === 'error') {
        // Handle error from backend
        throw new Error(result.message || result.detail || 'Connection failed');
        
      } else {
        // Handle unexpected response format
        throw new Error('Invalid response from server');
      }
      
    } catch (error) {
      console.error("Google Sheets connection error:", error);
      
      let errorMessage = '❌ Connection failed';
      
      // Extract error message from various possible sources
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (typeof detail === 'object') {
          if (detail.msg) {
            errorMessage = detail.msg;
          } else if (detail.message) {
            errorMessage = detail.message;
          } else {
            errorMessage = JSON.stringify(detail);
          }
        }
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      // Make error messages more user-friendly
      if (errorMessage.includes('404') || errorMessage.includes('not found')) {
        errorMessage = '❌ Sheet not found. Check the Sheet ID and sharing settings.';
      } else if (errorMessage.includes('403') || errorMessage.includes('permission') || errorMessage.includes('access')) {
        errorMessage = `❌ Permission denied. Make sure the sheet is shared with:\n${SERVICE_ACCOUNT_EMAIL}`;
      } else if (errorMessage.includes('date') && errorMessage.includes('invalid')) {
        errorMessage = '❌ Schema validation failed: Date column contains invalid formats. Make sure dates are in a recognized format (e.g., YYYY-MM-DD).';
      } else if (errorMessage.includes('revenue') && errorMessage.includes('non-numeric')) {
        errorMessage = '❌ Schema validation failed: Revenue column contains non-numeric values. Make sure revenue values are numbers.';
      } else if (errorMessage.includes('Missing required columns')) {
        errorMessage = '❌ Missing required columns. Your sheet must contain "date" and "revenue" columns (case-insensitive).';
      } else if (errorMessage.includes('empty') || errorMessage.includes('no data')) {
        errorMessage = '❌ The sheet appears to be empty. Please check that your sheet contains data.';
      } else if (errorMessage.includes('sheet name') || errorMessage.includes('Sheet name')) {
        errorMessage = `❌ Sheet "${config.sheet_name}" not found. Please check the exact sheet/tab name.`;
      }
      
      setTestResult({ 
        success: false, 
        message: errorMessage
      });
      setConnectionSuccess(false);
      // Pass false to indicate invalid connection
      onConnect(config, false);
    } finally {
      setTesting(false);
    }
  };

  const handleReset = () => {
    setConnectionSuccess(false);
    setTestResult(null);
    setValidationError(null);
    setPermissionWarning(null);
    setSheetNameError(null);
    setConfig({ 
      sheet_id: '', 
      sheet_range: 'A1:Z1000',
      sheet_name: '' 
    });
    
    if (onClearResults) {
      onClearResults();
    }
  };

  const extractSheetId = (url) => {
    const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    return match ? match[1] : url;
  };

  const handlePaste = (event) => {
    const pastedText = event.clipboardData.getData('text');
    const extractedId = extractSheetId(pastedText);
    if (extractedId !== pastedText) {
      setConfig({ ...config, sheet_id: extractedId });
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <GoogleIcon sx={{ mr: 1, color: '#1976d2' }} />
        <Typography variant="h6">
          Connect to Google Sheets
        </Typography>
        <Typography variant="caption" sx={{ ml: 'auto', color: '#666' }}>
          Max rows: {MAX_SHEET_SIZE.toLocaleString()}
        </Typography>
      </Box>

      {/* CRITICAL INSTRUCTION BOX - Service Account Sharing */}
      <Alert 
        severity="info" 
        icon={<InfoIcon />}
        sx={{ mb: 3, bgcolor: '#e3f2fd' }}
      >
        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          🔐 Before connecting, share your Google Sheet with:
        </Typography>
        <Typography 
          variant="body2" 
          sx={{ 
            fontFamily: 'monospace', 
            bgcolor: '#fff', 
            p: 1, 
            borderRadius: 1,
            display: 'inline-block',
            mb: 1
          }}
        >
          {SERVICE_ACCOUNT_EMAIL}
        </Typography>
        <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
          Make sure to give this email address <strong>"Viewer" or "Reader"</strong> access to your Google Sheet.
          You can share it like you would share with any other email address.
        </Typography>
      </Alert>

      <Grid container spacing={2}>
        {/* Sheet ID Input */}
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Google Sheet ID or URL"
            value={config.sheet_id}
            onChange={handleChange('sheet_id')}
            onPaste={handlePaste}
            placeholder="https://docs.google.com/spreadsheets/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890/edit"
            helperText="Paste the full URL or just the Sheet ID"
            required
            disabled={connectionSuccess}
            error={!!validationError?.includes('Sheet ID')}
            InputProps={{
              endAdornment: connectionSuccess && (
                <InputAdornment position="end">
                  <CheckCircleIcon color="success" />
                </InputAdornment>
              )
            }}
          />
        </Grid>

        {/* Sheet Name Input - NOW REQUIRED */}
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Sheet/Tab Name"
            value={config.sheet_name}
            onChange={handleChange('sheet_name')}
            placeholder="e.g., Sheet1, Sales Data, Q1 2024"
            helperText="Enter the exact name of the sheet/tab in your Google Sheet (case-sensitive)"
            required
            disabled={connectionSuccess}
            error={!!sheetNameError}
            InputProps={{
              endAdornment: connectionSuccess && (
                <InputAdornment position="end">
                  <CheckCircleIcon color="success" />
                </InputAdornment>
              )
            }}
          />
          {sheetNameError && !connectionSuccess && (
            <FormHelperText error>{sheetNameError}</FormHelperText>
          )}
        </Grid>

        {/* Sheet Range Input (still optional) */}
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Sheet Range (optional)"
            value={config.sheet_range}
            onChange={handleChange('sheet_range')}
            placeholder="A1:Z1000"
            helperText="Default: A1:Z1000. Only change if you need a specific range."
            disabled={connectionSuccess}
          />
        </Grid>

        {/* Validation Error Alert */}
        {validationError && !connectionSuccess && (
          <Grid item xs={12}>
            <Alert 
              severity="error" 
              icon={<ErrorIcon />}
              onClose={() => setValidationError(null)}
            >
              {validationError}
            </Alert>
          </Grid>
        )}

        {/* Permission Warning Alert */}
        {permissionWarning && connectionSuccess && (
          <Grid item xs={12}>
            <Alert 
              severity="warning" 
              icon={<WarningIcon />}
              onClose={() => setPermissionWarning(null)}
            >
              {permissionWarning}
            </Alert>
          </Grid>
        )}

        {/* Test Connection Button */}
        {!connectionSuccess && (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                onClick={handleTestConnection}
                disabled={testing || !config.sheet_id || !config.sheet_name}
                startIcon={testing ? <CircularProgress size={20} /> : <RefreshIcon />}
              >
                {testing ? 'Testing...' : 'Test Connection'}
              </Button>
            </Box>
          </Grid>
        )}

        {/* Test Result Message */}
        {testResult && (
          <Grid item xs={12}>
            <Alert 
              severity={testResult.success ? 'success' : 'error'}
              sx={{ whiteSpace: 'pre-line' }}
            >
              {testResult.message}
            </Alert>
          </Grid>
        )}

        {/* ✅ "CONNECT TO DIFFERENT SHEET" BUTTON - Shows after successful connection */}
        {connectionSuccess && (
          <Grid item xs={12} sx={{ textAlign: 'center', mt: 2 }}>
            <Link
              component="button"
              variant="body2"
              onClick={handleReset}
              sx={{ 
                cursor: 'pointer',
                textDecoration: 'none',
                '&:hover': {
                  textDecoration: 'underline'
                }
              }}
            >
              ← Connect to a different sheet
            </Link>
          </Grid>
        )}

        {/* Help Section */}
        {!connectionSuccess && (
          <Grid item xs={12}>
            <Box sx={{ mt: 3, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <HelpIcon sx={{ mr: 1, fontSize: 18 }} />
                Requirements:
              </Typography>
              <Typography variant="body2" component="div">
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li>Sheet must be shared with <strong>{SERVICE_ACCOUNT_EMAIL}</strong> as a viewer</li>
                  <li><strong>Sheet/Tab Name is REQUIRED</strong> - enter the exact name of the sheet (case-sensitive)</li>
                  <li>Maximum {MAX_SHEET_SIZE.toLocaleString()} rows will be processed</li>
                  <li>First row must contain column headers</li>
                  <li><strong>Required columns:</strong> date and revenue (case-insensitive)</li>
                  <li>Date column must contain valid dates</li>
                  <li>Revenue column must contain numbers</li>
                </ul>
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default GoogleSheetsConnectionForm;