import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button, Typography, Box, Paper } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

const FileUpload = ({ onFileSelect }) => {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls', '.xlsx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.oasis.opendocument.spreadsheet': ['.ods']
    },
    maxFiles: 1,
  });

  return (
    <Paper
      {...getRootProps()}
      sx={{
        p: 4,
        textAlign: 'center',
        cursor: 'pointer',
        bgcolor: isDragActive ? '#f0f7ff' : 'white',
        border: '2px dashed',
        borderColor: isDragActive ? '#1976d2' : '#ccc',
        '&:hover': {
          borderColor: '#1976d2',
          bgcolor: '#f5f5f5',
        },
      }}
    >
      <input {...getInputProps()} />
      <CloudUploadIcon sx={{ fontSize: 48, color: '#1976d2', mb: 2 }} />
      <Typography variant="h6">
        {isDragActive ? 'Drop your file here' : 'Drag & drop your file here'}
      </Typography>
      <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
        or click to browse
      </Typography>
      <Typography variant="caption" display="block" sx={{ mt: 1, color: '#666' }}>
        Supported formats: CSV, Excel (.xls, .xlsx)
      </Typography>
      <Button variant="contained" sx={{ mt: 2 }}>
        Select File
      </Button>
    </Paper>
  );
};

export default FileUpload;