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
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';

const GoogleSheetsConnectionForm = ({ onConnect, onTestConnection, onClearResults, loading }) => {
  const [config, setConfig] = useState({
    sheet_id: '',
    sheet_range: 'A1:Z1000',
    sheet_name: ''
  });
  
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [connectionSuccess, setConnectionSuccess] = useState(false);

  const handleChange = (field) => (event) => {
    setConfig({ ...config, [field]: event.target.value });
    // Reset connection status when config changes
    if (connectionSuccess) {
      setConnectionSuccess(false);
      setTestResult(null);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    
    try {
      const result = await onTestConnection(config);
      setTestResult({ success: true, message: '✅ Successfully connected to Google Sheet!' });
      setConnectionSuccess(true);
      // Notify parent that connection is successful and pass the config
      onConnect(config);
    } catch (error) {
      setTestResult({ 
        success: false, 
        message: error.response?.data?.detail || '❌ Connection failed' 
      });
      setConnectionSuccess(false);
    } finally {
      setTesting(false);
    }
  };

  const handleReset = () => {
    setConnectionSuccess(false);
    setTestResult(null);
    setConfig({ 
      sheet_id: '', 
      sheet_range: 'A1:Z1000',
      sheet_name: '' 
    });
    
    // Clear parent's results
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

        {/* Help Section - Always visible when not connected */}
        {!connectionSuccess && (
          <Grid item xs={12}>
            <Box sx={{ mt: 3, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <HelpIcon sx={{ mr: 1, fontSize: 18 }} />
                How to get your Sheet ID:
              </Typography>
              <Typography variant="body2" component="div">
                <ol style={{ margin: 0, paddingLeft: 20 }}>
                  <li>Open your Google Sheet in a browser</li>
                  <li>Look at the URL: <code style={{ backgroundColor: '#e0e0e0', padding: '2px 4px', borderRadius: 2 }}>
                    https://docs.google.com/spreadsheets/d/<strong>1aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890</strong>/edit
                  </code></li>
                  <li>Copy the long string between <code>/d/</code> and <code>/edit</code></li>
                  <li>Paste it in the field above</li>
                </ol>
              </Typography>
              <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mt: 2 }}>
                Your sheet must be shared with this email: 
                <Box component="span" sx={{ fontWeight: 'bold', ml: 1, color: '#1976d2' }}>
                  your-service-account@project.iam.gserviceaccount.com
                </Box>
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default GoogleSheetsConnectionForm;