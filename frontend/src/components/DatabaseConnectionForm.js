import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Grid,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Alert,
  CircularProgress,
  Link,
  InputAdornment
} from '@mui/material';
import {
  Storage as DatabaseIcon,
  Refresh as RefreshIcon,
  Help as HelpIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Visibility,
  VisibilityOff
} from '@mui/icons-material';

const MAX_QUERY_LENGTH = 2000;

const DatabaseConnectionForm = ({ onConnect, onTestConnection, onClearResults, loading }) => {
  const [config, setConfig] = useState({
    db_type: 'postgresql',
    host: 'localhost',
    port: '5432',
    database: '',
    username: '',
    password: '',
    table: '',
    query: '',
    use_query: false
  });

  const [showPassword, setShowPassword] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [connectionSuccess, setConnectionSuccess] = useState(false);

  const validateConfig = () => {
    if (!config.database) {
      setValidationError('Database name is required');
      return false;
    }

    if (!config.use_query && !config.table) {
      setValidationError('Table name is required');
      return false;
    }

    if (config.use_query && config.query.length > MAX_QUERY_LENGTH) {
      setValidationError(`Query too long. Maximum ${MAX_QUERY_LENGTH} characters`);
      return false;
    }

    if (config.use_query && config.query) {
      const dangerousKeywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE'];
      const upperQuery = config.query.toUpperCase();
      for (const keyword of dangerousKeywords) {
        if (upperQuery.includes(keyword)) {
          setValidationError(`Dangerous SQL keyword '${keyword}' not allowed. Only SELECT queries are permitted.`);
          return false;
        }
      }
    }

    if (config.port) {
      const portNum = parseInt(config.port);
      if (isNaN(portNum) || portNum < 1024 || portNum > 65535) {
        setValidationError('Port must be between 1024 and 65535');
        return false;
      }
    }

    setValidationError(null);
    return true;
  };

  const handleChange = (field) => (event) => {
    setConfig({ ...config, [field]: event.target.value });
    setValidationError(null);
    if (connectionSuccess) {
      setConnectionSuccess(false);
      setTestResult(null);
    }
  };

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

const handleTestConnection = async () => {
  if (!validateConfig()) return;

  setTesting(true);
  setTestResult(null);
  setValidationError(null);
  
  try {
    // Prepare the config for the API
    const apiConfig = {
      db_type: config.db_type,
      host: config.host,
      port: config.port,
      username: config.username,
      password: config.password,
      table: config.use_query ? null : config.table,
      query: config.use_query ? config.query : null,
      use_query: config.use_query
    };
    
    // Handle SQLite specially - just pass the filename, not the full path
    if (config.db_type === 'sqlite') {
      // Extract just the filename from the path
      const fileName = config.database.split('\\').pop().split('/').pop();
      apiConfig.database = fileName || config.database;
    } else {
      apiConfig.database = config.database;
    }
    
    const result = await onTestConnection(apiConfig);
    
    setTestResult({ 
      success: true, 
      message: result.message || '✅ Successfully connected!' 
    });
    setConnectionSuccess(true);
    onConnect(config);
    
  } catch (error) {
    console.error("Connection error:", error);
    
    // Extract error message safely
    let errorMessage = '❌ Connection failed';
    if (error.response?.data?.detail) {
      if (typeof error.response.data.detail === 'string') {
        errorMessage = error.response.data.detail;
      } else if (typeof error.response.data.detail === 'object') {
        errorMessage = error.response.data.detail.msg || 
                      error.response.data.detail.message || 
                      JSON.stringify(error.response.data.detail);
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
      db_type: 'postgresql',
      host: 'localhost',
      port: '5432',
      database: '',
      username: '',
      password: '',
      table: '',
      query: '',
      use_query: false
    });
    setShowPassword(false);
    
    if (onClearResults) {
      onClearResults();
    }
  };

  const getDefaultPort = (dbType) => {
    const ports = {
      'postgresql': '5432',
      'mysql': '3306',
      'sqlite': ''
    };
    return ports[dbType] || '5432';
  };

  const handleDbTypeChange = (event) => {
    const newType = event.target.value;
    setConfig({
      ...config,
      db_type: newType,
      port: getDefaultPort(newType)
    });
  };

  const isSQLite = config.db_type === 'sqlite';

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <DatabaseIcon sx={{ mr: 1, color: '#1976d2' }} />
        <Typography variant="h6">
          Connect to Database
        </Typography>
      </Box>

      <Grid container spacing={2}>
        {/* Database Type */}
        <Grid item xs={12} md={4}>
          <FormControl fullWidth disabled={connectionSuccess}>
            <InputLabel>Database Type</InputLabel>
            <Select
              value={config.db_type}
              label="Database Type"
              onChange={handleDbTypeChange}
            >
              <MenuItem value="postgresql">PostgreSQL</MenuItem>
              <MenuItem value="mysql">MySQL</MenuItem>
              <MenuItem value="sqlite">SQLite</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        {/* Host - not needed for SQLite */}
        {!isSQLite && (
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Host"
              value={config.host}
              onChange={handleChange('host')}
              placeholder="localhost or db.example.com"
              disabled={connectionSuccess}
            />
          </Grid>
        )}

        {/* Port - not needed for SQLite */}
        {!isSQLite && (
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Port"
              value={config.port}
              onChange={handleChange('port')}
              placeholder={getDefaultPort(config.db_type)}
              disabled={connectionSuccess}
              error={validationError?.includes('Port')}
            />
          </Grid>
        )}

        {/* Database Name / File Path */}
        <Grid item xs={12} md={isSQLite ? 12 : 6}>
          <TextField
            fullWidth
            label={isSQLite ? "Database File Path" : "Database Name"}
            value={config.database}
            onChange={handleChange('database')}
            required
            placeholder={isSQLite ? "C:/data/mydb.sqlite" : "sales_db"}
            helperText={isSQLite ? "Full path to SQLite database file" : ""}
            disabled={connectionSuccess}
            error={validationError?.includes('Database')}
            InputProps={{
              endAdornment: connectionSuccess && (
                <InputAdornment position="end">
                  <CheckCircleIcon color="success" />
                </InputAdornment>
              )
            }}
          />
        </Grid>

        {/* Username - not needed for SQLite */}
        {!isSQLite && (
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Username"
              value={config.username}
              onChange={handleChange('username')}
              disabled={connectionSuccess}
            />
          </Grid>
        )}

        {/* Password - not needed for SQLite */}
        {!isSQLite && (
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type={showPassword ? 'text' : 'password'}
              label="Password"
              value={config.password}
              onChange={handleChange('password')}
              disabled={connectionSuccess}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <Button onClick={handleTogglePassword} edge="end" disabled={connectionSuccess}>
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </Button>
                  </InputAdornment>
                )
              }}
            />
          </Grid>
        )}

        {/* Table/Query Toggle */}
        {!isSQLite && (
          <Grid item xs={12}>
            <Button
              variant="text"
              onClick={() => setConfig({ ...config, use_query: !config.use_query })}
              disabled={connectionSuccess}
              sx={{ mb: 1 }}
            >
              {config.use_query ? '← Use table instead' : 'Use custom SQL query →'}
            </Button>
          </Grid>
        )}

        {/* Table Name */}
        {!config.use_query && (
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Table Name"
              value={config.table}
              onChange={handleChange('table')}
              required={!config.use_query}
              helperText="Which table to analyze"
              disabled={connectionSuccess}
              error={validationError?.includes('Table')}
            />
          </Grid>
        )}

        {/* Custom Query */}
        {config.use_query && (
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Custom SQL Query"
              value={config.query}
              onChange={handleChange('query')}
              multiline
              rows={3}
              placeholder="SELECT * FROM sales WHERE date > '2024-01-01'"
              helperText={`Max ${MAX_QUERY_LENGTH} characters. Only SELECT queries allowed.`}
              disabled={connectionSuccess}
              error={validationError?.includes('Query')}
            />
          </Grid>
        )}

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
                disabled={testing || !config.database || (!config.table && !config.query)}
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
              ← Connect to a different database
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
                  <li>Read-only access recommended</li>
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

export default DatabaseConnectionForm;