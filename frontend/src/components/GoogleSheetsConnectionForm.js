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
} from '@mui/material';
import {
  Google as GoogleIcon,
  Refresh as RefreshIcon,
  Help as HelpIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';

const API_BASE_URL = 'http://localhost:8000/api/v1';
const MAX_SHEET_SIZE = 100000;

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

  const validateSheetId = (id) => {
    const regex = /^[a-zA-Z0-9-_]+$/;
    return regex.test(id);
  };

  const handleChange = (field) => (event) => {
    const value = event.target.value;
    setConfig({ ...config, [field]: value });
    setValidationError(null);
    if (connectionSuccess) {
      setConnectionSuccess(false);
      setTestResult(null);
    }
  };

 const handleTestConnection = async () => {
  if (!config.sheet_id) {
    setValidationError('Sheet ID is required');
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
  
  try {
    const result = await onTestConnection({ 
      ...config, 
      sheet_id: extractedId 
    });
    
    // Check for specific success scenarios
    let successMessage = '✅ Successfully connected!';
    if (result.message) {
      successMessage = result.message;
    } else if (result.rows) {
      successMessage = `✅ Connected! Found ${result.rows} rows.`;
    }
    
    setTestResult({ 
      success: true, 
      message: successMessage
    });
    setConnectionSuccess(true);
    
    // Pass the config to parent
    onConnect({ ...config, sheet_id: extractedId });
    
  } catch (error) {
    console.error("Google Sheets connection error:", error);
    
    // Extract detailed error message
    let errorMessage = '❌ Connection failed';
    
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      
      // Handle different types of error details
      if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (typeof detail === 'object') {
        // Handle validation errors
        if (detail.msg) {
          errorMessage = detail.msg;
        } else if (detail.message) {
          errorMessage = detail.message;
        } else {
          errorMessage = JSON.stringify(detail);
        }
      }
      
      // Make error messages more user-friendly
      if (errorMessage.includes('404')) {
        errorMessage = '❌ Sheet not found. Check the Sheet ID and sharing settings.';
      } else if (errorMessage.includes('403')) {
        errorMessage = '❌ Permission denied. Make sure the sheet is shared with your service account.';
      } else if (errorMessage.includes('date')) {
        errorMessage = '❌ Schema validation failed: Date column contains invalid formats.';
      } else if (errorMessage.includes('revenue')) {
        errorMessage = '❌ Schema validation failed: Revenue column contains non-numeric values.';
      } else if (errorMessage.includes('Missing required columns')) {
        errorMessage = '❌ Missing required columns. Your sheet must contain "date" and "revenue" columns.';
      }
    } else if (error.message) {
      errorMessage = error.message;
    }
    
    setTestResult({ 
      success: false, 
      message: errorMessage
    });
    setConnectionSuccess(false);
  } finally {
    setTesting(false);
  }
};
  const handleReset = () => {
    setConnectionSuccess(false);
    setTestResult(null);
    setValidationError(null);
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
            error={validationError?.includes('Sheet ID')}
            InputProps={{
              endAdornment: connectionSuccess && (
                <InputAdornment position="end">
                  <CheckCircleIcon color="success" />
                </InputAdornment>
              )
            }}
          />
        </Grid>

        {/* Optional Settings */}
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="Sheet Range (optional)"
            value={config.sheet_range}
            onChange={handleChange('sheet_range')}
            placeholder="A1:Z1000"
            helperText="Default: A1:Z1000"
            disabled={connectionSuccess}
          />
        </Grid>

        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="Specific Sheet Name (optional)"
            value={config.sheet_name}
            onChange={handleChange('sheet_name')}
            placeholder="Sheet1"
            helperText="Leave empty for first sheet"
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

        {/* Test Connection Button */}
        {!connectionSuccess && (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                onClick={handleTestConnection}
                disabled={testing || !config.sheet_id}
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
            <Alert severity={testResult.success ? 'success' : 'error'}>
              {testResult.message}
            </Alert>
          </Grid>
        )}

        {/* Reset Connection Link - Only shown after successful connection */}
        {connectionSuccess && (
          <Grid item xs={12} sx={{ textAlign: 'center', mt: 2 }}>
            <Link
              component="button"
              variant="body2"
              onClick={handleReset}
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
                  <li>Sheet must be shared with your service account</li>
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