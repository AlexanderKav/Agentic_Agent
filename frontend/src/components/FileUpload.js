import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button, Typography, Box, Paper, Alert, CircularProgress } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import axios from 'axios';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const FileUpload = ({ onFileSelect, onClearResults }) => {
  const [fileError, setFileError] = useState(null);
  const [schemaError, setSchemaError] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isValid, setIsValid] = useState(false);

  const validateFileSchema = async (file) => {
    setIsValidating(true);
    setSchemaError(null);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const token = localStorage.getItem('token');
      
      const response = await axios.post(`${API_BASE_URL}/analysis/validate-schema`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        },
      });
      
      console.log('📥 Validation response:', response.data);
      
      if (response.data.valid) {
        console.log('✅ File is valid!');
        setIsValid(true);
        onFileSelect(file);
      } else {
        console.log('❌ Validation failed:', response.data.message);
        setSchemaError(response.data.message);
        setIsValid(false);
        onFileSelect(null);
      }
    } catch (error) {
      console.error('❌ Validation error:', error);
      
      let errorMessage = 'Schema validation failed';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map(err => err.msg || err.message).join(', ');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setSchemaError(errorMessage);
      setIsValid(false);
      onFileSelect(null);
    } finally {
      setIsValidating(false);
    }
  };

  const validateFile = async (file) => {
    // Clear previous errors
    setFileError(null);
    setSchemaError(null);
    setIsValid(false);

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      setFileError(`File too large. Maximum size is ${MAX_FILE_SIZE / (1024*1024)}MB. Your file is ${(file.size / (1024*1024)).toFixed(2)}MB.`);
      onFileSelect(null);
      return false;
    }
    
    // Check file type - removed SQLite extensions
    const fileExt = file.name.split('.').pop().toLowerCase();
    const validExtensions = ['csv', 'xlsx', 'xls'];
    
    if (!validExtensions.includes(fileExt)) {
      setFileError(`Invalid file type. Please upload CSV or Excel files only.`);
      onFileSelect(null);
      return false;
    }

    // Validate schema
    await validateFileSchema(file);
    return true;
  };

  const onDrop = useCallback(async (acceptedFiles, rejectedFiles) => {
    // Handle react-dropzone's built-in rejection
    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      if (rejection.errors[0].code === 'file-too-large') {
        setFileError(`File too large. Maximum size is ${MAX_FILE_SIZE / (1024*1024)}MB.`);
      } else {
        setFileError('Invalid file type. Please upload CSV or Excel files.');
      }
      onFileSelect(null);
      return;
    }
    
    // Validate the file
    if (acceptedFiles.length > 0) {
      await validateFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls', '.xlsx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    maxSize: MAX_FILE_SIZE,
    maxFiles: 1,
    noClick: true,
    noKeyboard: true
  });

  const handleClick = () => {
    setFileError(null);
    setSchemaError(null);
    setIsValid(false);
    if (onClearResults) {
      onClearResults();
    }
    open();
  };

  // Determine border color based on validation state
  const getBorderColor = () => {
    if (fileError || schemaError) return '#d32f2f'; // Red for errors
    if (isValid) return '#2e7d32'; // Green for valid
    if (isDragActive) return '#1976d2'; // Blue for drag active
    return '#ccc'; // Default gray
  };

  // Determine background color
  const getBgColor = () => {
    if (fileError || schemaError) return '#ffebee'; // Light red for errors
    if (isValid) return '#f1f8e9'; // Light green for valid
    if (isDragActive) return '#f0f7ff'; // Light blue for drag active
    return 'white';
  };

  return (
    <Paper sx={{ p: 4 }}>
      <Box
        {...getRootProps()}
        sx={{
          textAlign: 'center',
          cursor: 'pointer',
          bgcolor: getBgColor(),
          border: '2px dashed',
          borderColor: getBorderColor(),
          borderRadius: 2,
          p: 4,
          transition: 'all 0.3s ease',
          '&:hover': {
            borderColor: fileError || schemaError ? '#d32f2f' : (isValid ? '#2e7d32' : '#1976d2'),
            bgcolor: fileError || schemaError ? '#ffebee' : (isValid ? '#e8f5e9' : '#f5f5f5'),
          },
        }}
      >
        <input {...getInputProps()} />
        
        {/* Icon based on state */}
        {isValidating ? (
          <CircularProgress size={48} sx={{ mb: 2 }} />
        ) : isValid ? (
          <CheckCircleIcon sx={{ fontSize: 48, color: '#2e7d32', mb: 2 }} />
        ) : (
          <CloudUploadIcon 
            sx={{ 
              fontSize: 48, 
              color: fileError || schemaError ? '#d32f2f' : '#1976d2', 
              mb: 2 
            }} 
          />
        )}
        
        <Typography variant="h6">
          {isDragActive ? 'Drop your file here' : 'Drag & drop your file here'}
        </Typography>
        
        <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
          or click to browse
        </Typography>
        
        <Typography variant="caption" display="block" sx={{ mt: 1, color: '#666' }}>
          Supported formats: CSV, Excel (.xls, .xlsx)
        </Typography>
        
        <Typography variant="caption" display="block" sx={{ color: '#666' }}>
          Max size: {MAX_FILE_SIZE / (1024*1024)}MB
        </Typography>
        
        <Typography variant="caption" display="block" sx={{ color: '#666', mt: 1 }}>
          Required columns: <strong>date</strong> and <strong>revenue</strong>
        </Typography>
        
        <Button 
          variant="contained" 
          onClick={handleClick}
          sx={{ mt: 2 }}
          color={fileError || schemaError ? 'error' : (isValid ? 'success' : 'primary')}
          disabled={isValidating}
        >
          {isValidating ? 'Validating...' : 'Select File'}
        </Button>
      </Box>

      {/* File Size Error Alert */}
      {fileError && (
        <Alert 
          severity="error" 
          icon={<WarningIcon />}
          sx={{ mt: 2 }}
          onClose={() => setFileError(null)}
        >
          {fileError}
        </Alert>
      )}

      {/* Schema Error Alert */}
      {schemaError && (
        <Alert 
          severity="error" 
          icon={<WarningIcon />}
          sx={{ mt: 2 }}
          onClose={() => setSchemaError(null)}
        >
          <Typography variant="subtitle2" gutterBottom>
            Schema Validation Failed
          </Typography>
          <Typography variant="body2">
            {schemaError}
          </Typography>
          <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
            Your file must contain at least 'date' and 'revenue' columns.
          </Typography>
        </Alert>
      )}

      {/* Success Message */}
      {isValid && !schemaError && !fileError && (
        <Alert 
          severity="success" 
          icon={<CheckCircleIcon />}
          sx={{ mt: 2 }}
        >
          ✓ File validated successfully! Ready to analyze.
        </Alert>
      )}
    </Paper>
  );
};

export default FileUpload;