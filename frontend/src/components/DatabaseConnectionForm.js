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
  Visibility,
  VisibilityOff
} from '@mui/icons-material';

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
  const [connectionSuccess, setConnectionSuccess] = useState(false);

  const handleChange = (field) => (event) => {
    setConfig({ ...config, [field]: event.target.value });
    if (connectionSuccess) {
      setConnectionSuccess(false);
      setTestResult(null);
    }
  };

  const handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    
    try {
      const result = await onTestConnection(config);
      setTestResult({ success: true, message: '✅ Successfully connected to database!' });
      setConnectionSuccess(true);
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
              helperText="Write your own SQL query"
              disabled={connectionSuccess}
            />
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

        {/* Help Section - Always visible when not connected */}
        {!connectionSuccess && (
          <Grid item xs={12}>
            <Box sx={{ mt: 3, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <HelpIcon sx={{ mr: 1, fontSize: 18 }} />
                Connection Examples:
              </Typography>
              <Typography variant="body2" component="div">
                <strong>PostgreSQL:</strong> postgresql://user:pass@localhost:5432/dbname<br />
                <strong>MySQL:</strong> mysql+pymysql://user:pass@localhost:3306/dbname<br />
                <strong>SQLite:</strong> sqlite:///path/to/database.db
              </Typography>
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default DatabaseConnectionForm;