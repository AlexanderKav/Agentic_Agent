import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CardMedia,
  Grid,
  Chip
} from '@mui/material';
import ImageIcon from '@mui/icons-material/Image';
import BarChartIcon from '@mui/icons-material/BarChart';

const ChartViewer = ({ charts }) => {
  if (!charts || Object.keys(charts).length === 0) return null;

  return (
    <Paper sx={{ p: 3, mt: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
        <BarChartIcon sx={{ mr: 1, color: '#1976d2' }} />
        📊 Generated Visualizations
      </Typography>
      
      <Grid container spacing={3}>
        {Object.entries(charts).map(([chartName, chartPath]) => (
          <Grid item xs={12} md={6} key={chartName}>
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
                
                {/* Chart Image */}
                <CardMedia
                  component="img"
                  image={`http://localhost:8000/api/v1/analysis/chart/${encodeURIComponent(chartPath.split('\\').pop())}`}
                  alt={chartName}
                  sx={{
                    width: '100%',
                    height: 'auto',
                    maxHeight: 400,
                    objectFit: 'contain',
                    border: '1px solid #eee',
                    borderRadius: 1,
                    bgcolor: '#fafafa'
                  }}
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = 'https://via.placeholder.com/400x300?text=Chart+Image+Not+Found';
                  }}
                />
                
                {/* Chart info */}
                <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                  Saved to: {chartPath}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Paper>
  );
};

export default ChartViewer;