// frontend/src/components/SimpleDatabaseConnection.js
import React, { useState, useCallback } from 'react';
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
  IconButton,
  InputAdornment,
  Divider,
  Link
} from '@mui/material';
import {
  Storage as DatabaseIcon,
  Refresh as RefreshIcon,
  Visibility,
  VisibilityOff,
  CheckCircle as CheckCircleIcon,
  CloudUpload as UploadIcon,
  TableChart as TableIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { testDatabaseConnection } from '../services/api';

const API_BASE_URL = 'http://localhost:8000/api/v1';
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

const SimpleDatabaseConnection = ({ onConnect, onClearResults }) => {
  const [dbType, setDbType] = useState('postgresql');
  // ✅ UPDATED: Empty config instead of pre-filled values
  const [config, setConfig] = useState({
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
    table: ''
  });
  
  // SQLite specific states
  const [sqliteFile, setSqliteFile] = useState(null);
  const [sqliteTables, setSqliteTables] = useState([]);
  const [selectedSqliteTable, setSelectedSqliteTable] = useState('');
  const [uploadingFile, setUploadingFile] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  
  const [showPassword, setShowPassword] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [connectionSuccess, setConnectionSuccess] = useState(false);
  const [tableError, setTableError] = useState(false);

  const isSQLite = dbType === 'sqlite';

  // Fetch tables from uploaded SQLite file
  const fetchSqliteTables = async (file) => {
    setUploadingFile(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const token = localStorage.getItem('token');
      
      const response = await axios.post(`${API_BASE_URL}/analysis/sqlite-tables`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      setSqliteTables(response.data.tables || []);
      if (response.data.tables && response.data.tables.length > 0) {
        setSelectedSqliteTable(response.data.tables[0]);
      }
      setTestResult({ success: true, message: `File uploaded: ${file.name}` });
    } catch (error) {
      console.error('Error fetching SQLite tables:', error);
      setTestResult({ success: false, message: error.response?.data?.detail || 'Failed to read SQLite file' });
      setSqliteFile(null);
      setSqliteTables([]);
      setSelectedSqliteTable('');
    } finally {
      setUploadingFile(false);
    }
  };

  // Drag and drop handlers for SQLite
  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (file.size > MAX_FILE_SIZE) {
      setTestResult({ success: false, message: `File too large. Maximum size is ${MAX_FILE_SIZE / (1024*1024)}MB` });
      return;
    }

    const fileExt = file.name.split('.').pop().toLowerCase();
    if (!['db', 'sqlite', 'sqlite3'].includes(fileExt)) {
      setTestResult({ success: false, message: 'Invalid file type. Please upload SQLite database files (.db, .sqlite, .sqlite3)' });
      return;
    }

    setSqliteFile(file);
    fetchSqliteTables(file);
    setTestResult(null);
    setConnectionSuccess(false);
    if (onClearResults) onClearResults();
  }, []);

  const { getRootProps, getInputProps, isDragActive: dropActive } = useDropzone({
    onDrop,
    accept: {
      'application/x-sqlite3': ['.db', '.sqlite', '.sqlite3']
    },
    maxSize: MAX_FILE_SIZE,
    maxFiles: 1,
    disabled: connectionSuccess,
    noClick: false,
    noKeyboard: false
  });

  const handleRemoveFile = () => {
    setSqliteFile(null);
    setSqliteTables([]);
    setSelectedSqliteTable('');
    setTestResult(null);
    setConnectionSuccess(false);
    if (onClearResults) onClearResults();
  };

  const handleChange = (field) => (event) => {
    setConfig({ ...config, [field]: event.target.value });
    setTestResult(null);
    setConnectionSuccess(false);
    if (field === 'table') {
      setTableError(false);
    }
    if (onClearResults) onClearResults();
  };

  const handleDbTypeChange = (event) => {
    const newType = event.target.value;
    setDbType(newType);
    // ✅ UPDATED: Clear config when switching database types
    setConfig({ 
      host: '',
      port: '',
      database: '',
      username: '',
      password: '',
      table: ''
    });
    // Reset SQLite state when switching away from SQLite
    if (newType !== 'sqlite') {
      setSqliteFile(null);
      setSqliteTables([]);
      setSelectedSqliteTable('');
    }
    setTableError(false);
    setTestResult(null);
    setConnectionSuccess(false);
    if (onClearResults) onClearResults();
  };

  const handleTableSelect = (event) => {
    setSelectedSqliteTable(event.target.value);
    setTableError(false);
    setTestResult(null);
  };

  const handleReset = () => {
    // ✅ UPDATED: Reset all form fields to empty
    setDbType('postgresql');
    setConfig({
      host: '',
      port: '',
      database: '',
      username: '',
      password: '',
      table: ''
    });
    setSqliteFile(null);
    setSqliteTables([]);
    setSelectedSqliteTable('');
    setShowPassword(false);
    setTestResult(null);
    setConnectionSuccess(false);
    setTableError(false);
    setTesting(false);
    if (onClearResults) onClearResults();
  };

  const handleTestConnection = async () => {
    if (isSQLite) {
      // SQLite validation
      if (!sqliteFile) {
        setTestResult({ success: false, message: 'Please upload a SQLite database file' });
        return;
      }
      if (!selectedSqliteTable) {
        setTableError(true);
        setTestResult({ success: false, message: 'Please select a table to analyze' });
        return;
      }
      
      setTesting(true);
      setTestResult(null);
      
      try {
        const formData = new FormData();
        formData.append('file', sqliteFile);
        formData.append('table', selectedSqliteTable);
        
        const token = localStorage.getItem('token');
        const response = await axios.post(`${API_BASE_URL}/analysis/test-sqlite-connection`, formData, {
          headers: { 
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.data && response.data.success !== false) {
          setTestResult({ success: true, message: response.data.message || '✅ Successfully connected!' });
          setConnectionSuccess(true);
          onConnect({
            db_type: 'sqlite',
            sqlite_file: sqliteFile,
            selected_sqlite_table: selectedSqliteTable
          }, true);
        } else {
          throw new Error(response.data?.message || 'Connection failed');
        }
      } catch (error) {
        let errorMessage = 'Connection failed';
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
          if (typeof errorMessage === 'object') {
            errorMessage = JSON.stringify(errorMessage);
          }
        } else if (error.message) {
          errorMessage = error.message;
        }
        setTestResult({ success: false, message: errorMessage });
        onConnect(config, false);
      } finally {
        setTesting(false);
      }
    } else {
      // PostgreSQL/MySQL validation
      if (!config.host || !config.database || !config.username) {
        setTestResult({ success: false, message: 'Please fill in host, database, and username' });
        return;
      }
      
      if (!config.table || config.table.trim() === '') {
        setTableError(true);
        setTestResult({ success: false, message: 'Please enter a table name to analyze' });
        return;
      }

      setTesting(true);
      setTestResult(null);
      setTableError(false);

      try {
        const testConfig = {
          db_type: dbType,
          host: config.host,
          port: config.port || (dbType === 'postgresql' ? '5432' : '3306'),
          database: config.database,
          username: config.username,
          password: config.password,
          table: config.table,
          use_query: false
        };

        const result = await testDatabaseConnection(testConfig);
        
        if (result.status === 'success') {
          setTestResult({ success: true, message: result.message });
          setConnectionSuccess(true);
          onConnect(testConfig, true);
        } else {
          setTestResult({ success: false, message: result.message || 'Connection failed' });
          onConnect(testConfig, false);
        }
      } catch (error) {
        const errorMsg = error.response?.data?.detail || 'Connection failed. Please check your credentials.';
        setTestResult({ success: false, message: errorMsg });
        onConnect(config, false);
      } finally {
        setTesting(false);
      }
    }
  };

  const getDefaultPortHint = () => dbType === 'postgresql' ? 'e.g., 5432' : 'e.g., 3306';

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <DatabaseIcon sx={{ mr: 1, color: '#1976d2' }} />
        <Typography variant="h6">
          Connect Your Database
        </Typography>
      </Box>

      <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
        Enter your database credentials or upload a SQLite file to start analyzing your data.
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <FormControl fullWidth disabled={connectionSuccess}>
            <InputLabel>Database Type</InputLabel>
            <Select
              value={dbType}
              label="Database Type"
              onChange={handleDbTypeChange}
            >
              <MenuItem value="postgresql">PostgreSQL</MenuItem>
              <MenuItem value="mysql">MySQL</MenuItem>
              <MenuItem value="sqlite">SQLite (Upload File)</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        {/* SQLite File Upload Section */}
        {isSQLite && (
          <>
            <Grid item xs={12}>
              <Box
                {...getRootProps()}
                sx={{
                  border: '2px dashed',
                  borderColor: dropActive ? '#1976d2' : (sqliteFile ? '#2e7d32' : '#ccc'),
                  borderRadius: 2,
                  p: 3,
                  textAlign: 'center',
                  cursor: 'pointer',
                  bgcolor: dropActive ? '#f0f7ff' : (sqliteFile ? '#f1f8e9' : '#fafafa'),
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    borderColor: sqliteFile ? '#2e7d32' : '#1976d2',
                    bgcolor: sqliteFile ? '#e8f5e9' : '#f5f5f5',
                  }
                }}
                onDragEnter={() => setDragActive(true)}
                onDragLeave={() => setDragActive(false)}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragActive(false);
                  const files = e.dataTransfer.files;
                  if (files && files[0]) {
                    onDrop([files[0]]);
                  }
                }}
              >
                <input {...getInputProps()} />
                {uploadingFile ? (
                  <CircularProgress size={48} sx={{ mb: 2 }} />
                ) : sqliteFile ? (
                  <CheckCircleIcon sx={{ fontSize: 48, color: '#2e7d32', mb: 2 }} />
                ) : (
                  <UploadIcon sx={{ fontSize: 48, color: '#1976d2', mb: 2 }} />
                )}
                <Typography variant="body1">
                  {dropActive ? 'Drop your SQLite file here' : 'Drag & drop your SQLite database file here'}
                </Typography>
                <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                  or click to browse
                </Typography>
                <Typography variant="caption" display="block" sx={{ mt: 1, color: '#666' }}>
                  Supported: .db, .sqlite, .sqlite3 (max {MAX_FILE_SIZE / (1024*1024)}MB)
                </Typography>
              </Box>
            </Grid>

            {sqliteFile && (
              <Grid item xs={12}>
                <Alert 
                  severity="success" 
                  icon={<CheckCircleIcon />}
                  action={
                    <Button color="inherit" size="small" onClick={handleRemoveFile}>
                      <DeleteIcon fontSize="small" />
                    </Button>
                  }
                >
                  File uploaded: <strong>{sqliteFile.name}</strong> ({(sqliteFile.size / 1024).toFixed(2)} KB)
                </Alert>
              </Grid>
            )}

            {sqliteTables.length > 0 && (
              <Grid item xs={12}>
                <FormControl fullWidth error={tableError}>
                  <InputLabel>Select Table</InputLabel>
                  <Select
                    value={selectedSqliteTable}
                    label="Select Table"
                    onChange={handleTableSelect}
                    disabled={connectionSuccess}
                    startAdornment={
                      <InputAdornment position="start">
                        <TableIcon />
                      </InputAdornment>
                    }
                  >
                    {sqliteTables.map((table) => (
                      <MenuItem key={table} value={table}>
                        {table}
                      </MenuItem>
                    ))}
                  </Select>
                  <Typography variant="caption" color="textSecondary" sx={{ mt: 1 }}>
                    Choose the table containing your business data
                  </Typography>
                </FormControl>
              </Grid>
            )}
          </>
        )}

        {/* PostgreSQL/MySQL Fields */}
        {!isSQLite && (
          <>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Host"
                value={config.host}
                onChange={handleChange('host')}
                placeholder="e.g., localhost or db.your-company.com"
                disabled={connectionSuccess}
                required
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Port"
                value={config.port}
                onChange={handleChange('port')}
                placeholder={getDefaultPortHint()}
                disabled={connectionSuccess}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Database Name"
                value={config.database}
                onChange={handleChange('database')}
                placeholder="e.g., sales_db"
                disabled={connectionSuccess}
                required
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Username"
                value={config.username}
                onChange={handleChange('username')}
                placeholder="e.g., postgres or root"
                disabled={connectionSuccess}
                required
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type={showPassword ? 'text' : 'password'}
                label="Password"
                value={config.password}
                onChange={handleChange('password')}
                placeholder="Enter your database password"
                disabled={connectionSuccess}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  )
                }}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Table Name"
                value={config.table}
                onChange={handleChange('table')}
                placeholder="e.g., sales, customers, orders"
                disabled={connectionSuccess}
                required
                error={tableError}
                helperText={tableError ? "Table name is required" : "Which table you want to analyze"}
              />
            </Grid>
          </>
        )}

        {testResult && (
          <Grid item xs={12}>
            <Alert severity={testResult.success ? 'success' : 'error'}>
              {testResult.message}
            </Alert>
          </Grid>
        )}

        {connectionSuccess && (
          <>
            <Grid item xs={12}>
              <Alert severity="success" icon={<CheckCircleIcon />}>
                ✅ Connected successfully! You can now ask questions about your data.
              </Alert>
            </Grid>
            
            {/* Connect to Different Database Button */}
            <Grid item xs={12} sx={{ textAlign: 'center', mt: 2 }}>
              <Link
                component="button"
                variant="body2"
                onClick={handleReset}
                sx={{ cursor: 'pointer', textDecoration: 'none' }}
              >
                ← Connect to a different database
              </Link>
            </Grid>
          </>
        )}

        {!connectionSuccess && (
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                onClick={handleTestConnection}
                disabled={testing || (isSQLite ? (!sqliteFile || !selectedSqliteTable) : (!config.host || !config.database || !config.username || !config.table))}
                startIcon={testing ? <CircularProgress size={20} /> : <RefreshIcon />}
              >
                {testing ? 'Testing...' : 'Test Connection'}
              </Button>
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default SimpleDatabaseConnection;