import React, { useState, useEffect, useRef } from 'react';
import {
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CardMedia,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  IconButton
} from '@mui/material';
import ImageIcon from '@mui/icons-material/Image';
import BarChartIcon from '@mui/icons-material/BarChart';
import RefreshIcon from '@mui/icons-material/Refresh';

const ChartViewer = ({ charts }) => {
  const [loadingStates, setLoadingStates] = useState({});
  const [errorStates, setErrorStates] = useState({});
  const retryCounts = useRef({});
  const imageKeys = useRef({});

  if (!charts || Object.keys(charts).length === 0) return null;

  // Helper function to extract just the filename from any path
  const getFilename = (chartPath) => {
    if (!chartPath) return null;
    // Handle Windows paths (backslashes)
    if (chartPath.includes('\\')) {
      const parts = chartPath.split('\\');
      return parts[parts.length - 1];
    }
    // Handle Unix paths (forward slashes)
    if (chartPath.includes('/')) {
      const parts = chartPath.split('/');
      return parts[parts.length - 1];
    }
    return chartPath;
  };

  // Get the base URL for charts (detect environment)
  const getBaseUrl = () => {
    // Check if we're in production (Docker) or development
    // Use relative URL for production, absolute for local
    const isLocalhost = window.location.hostname === 'localhost' || 
                        window.location.hostname === '127.0.0.1';
    
    if (isLocalhost) {
      // Local development - use absolute URL with port
      return 'http://localhost:8000/api/v1/analysis/chart';
    } else {
      // Production/Docker - use relative URL
      return '/api/v1/analysis/chart';
    }
  };

  const getImageUrl = (chartPath) => {
    const filename = getFilename(chartPath);
    if (!filename) return '';
    
    const baseUrl = getBaseUrl();
    const key = imageKeys.current[chartPath] || 0;
    const url = `${baseUrl}/${encodeURIComponent(filename)}?key=${key}`;
    
    console.log(`📷 Loading chart: ${url} (from path: ${chartPath})`);
    return url;
  };

  const handleImageLoad = (chartPath) => {
    setLoadingStates(prev => ({ ...prev, [chartPath]: false }));
    setErrorStates(prev => ({ ...prev, [chartPath]: false }));
    console.log(`✅ Chart loaded: ${chartPath}`);
  };

  const handleImageError = (chartPath) => {
    const currentRetries = retryCounts.current[chartPath] || 0;
    
    console.log(`❌ Chart error: ${chartPath}, retry: ${currentRetries}`);
    
    if (currentRetries < 3) {
      retryCounts.current[chartPath] = currentRetries + 1;
      imageKeys.current[chartPath] = (imageKeys.current[chartPath] || 0) + 1;
      setLoadingStates(prev => ({ ...prev, [chartPath]: true }));
      setErrorStates(prev => ({ ...prev, [chartPath]: false }));
    } else {
      setErrorStates(prev => ({ ...prev, [chartPath]: true }));
      setLoadingStates(prev => ({ ...prev, [chartPath]: false }));
    }
  };

  const handleManualRetry = (chartPath) => {
    retryCounts.current[chartPath] = 0;
    imageKeys.current[chartPath] = (imageKeys.current[chartPath] || 0) + 1;
    setErrorStates(prev => ({ ...prev, [chartPath]: false }));
    setLoadingStates(prev => ({ ...prev, [chartPath]: true }));
    console.log(`🔄 Manual retry for: ${chartPath}`);
  };

  return (
    <Paper sx={{ p: 3, mt: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
        <BarChartIcon sx={{ mr: 1, color: '#1976d2' }} />
        📊 Generated Visualizations
      </Typography>
      
      <Grid container spacing={3}>
        {Object.entries(charts).map(([chartName, chartPath]) => {
          const filename = getFilename(chartPath);
          return (
            <Grid item xs={12} md={6} key={chartPath}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <ImageIcon sx={{ mr: 1, color: '#1976d2' }} />
                    <Typography variant="subtitle1">
                      {chartName.replace(/_/g, ' ').toUpperCase()}
                    </Typography>
                    <Chip 
                      size="small" 
                      label="PNG" 
                      color="primary" 
                      variant="outlined"
                      sx={{ ml: 'auto' }}
                    />
                  </Box>
                  
                  {/* Debug info - shows filename only, not full path */}
                  <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 1 }}>
                    File: {filename}
                  </Typography>
                  
                  {/* Loading state */}
                  {loadingStates[chartPath] && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                      <CircularProgress />
                    </Box>
                  )}
                  
                  {/* Error state */}
                  {errorStates[chartPath] && (
                    <Alert 
                      severity="error" 
                      sx={{ mb: 2 }}
                      action={
                        <IconButton
                          color="inherit"
                          size="small"
                          onClick={() => handleManualRetry(chartPath)}
                        >
                          <RefreshIcon />
                        </IconButton>
                      }
                    >
                      Failed to load chart. Click to retry.
                    </Alert>
                  )}
                  
                  {/* Chart Image */}
                  {!errorStates[chartPath] && (
                    <CardMedia
                      component="img"
                      image={getImageUrl(chartPath)}
                      alt={chartName}
                      sx={{
                        width: '100%',
                        height: 'auto',
                        maxHeight: 400,
                        objectFit: 'contain',
                        border: '1px solid #eee',
                        borderRadius: 1,
                        bgcolor: '#fafafa',
                        display: loadingStates[chartPath] ? 'none' : 'block'
                      }}
                      onLoad={() => handleImageLoad(chartPath)}
                      onError={() => handleImageError(chartPath)}
                    />
                  )}
                  
                  {/* Chart info - show just filename */}
                  <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                    Saved to: {filename}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Paper>
  );
};

export default ChartViewer;