import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Divider,
  Box,
  Chip,
  Alert,
  Avatar,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ChartViewer from './ChartViewer';  // Add this import

const ResultsDisplay = ({ results, userQuestion }) => {
  if (!results) return null;

  const { insights, warnings, execution_time, data_summary, plan, is_generic_overview, results: analysisResults } = results;
  
  // Extract charts from analysisResults if they exist
  const charts = analysisResults?.charts || null;
  
  const isOverview = is_generic_overview || !userQuestion || userQuestion.trim() === '';

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header with Context */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Avatar sx={{ 
          bgcolor: isOverview ? '#2e7d32' : '#1976d2', 
          mr: 2,
          width: 56,
          height: 56
        }}>
          {isOverview ? <DashboardIcon /> : <QuestionAnswerIcon />}
        </Avatar>
        <Box>
          <Typography variant="h5">
            {isOverview ? '📊 Business Dashboard' : '🔍 Analysis Results'}
          </Typography>
          {!isOverview && (
            <Typography variant="body1" color="textSecondary" sx={{ mt: 1 }}>
              Question: "{userQuestion}"
            </Typography>
          )}
          {isOverview && (
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              Complete overview of your business performance
            </Typography>
          )}
        </Box>
      </Box>

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <Box sx={{ mb: 2 }}>
          {warnings.map((warning, idx) => (
            <Alert key={idx} severity="warning" icon={<WarningIcon />} sx={{ mb: 1 }}>
              {warning}
            </Alert>
          ))}
        </Box>
      )}

      {/* Quick Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <Card variant="outlined">
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Rows Processed
              </Typography>
              <Typography variant="h5">
                {data_summary?.rows?.toLocaleString() || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card variant="outlined">
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Columns
              </Typography>
              <Typography variant="h5">
                {data_summary?.columns?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card variant="outlined">
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Execution Time
              </Typography>
              <Typography variant="h5">
                {execution_time?.toFixed(2)}s
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card variant="outlined">
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Analysis Type
              </Typography>
              <Chip
                icon={isOverview ? <DashboardIcon /> : <QuestionAnswerIcon />}
                label={isOverview ? "Dashboard" : "Q&A"}
                color={isOverview ? "success" : "primary"}
                size="small"
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Divider sx={{ my: 2 }} />

      {/* Charts Section - Add this before the answer section */}
      {charts && <ChartViewer charts={charts} />}

      {/* Answer Section */}
      {insights?.answer && (
        <Box sx={{ 
          mt: 3, 
          mb: 3, 
          p: 3, 
          bgcolor: isOverview ? '#f5f5f5' : '#e3f2fd',
          borderRadius: 2,
          border: '1px solid',
          borderColor: isOverview ? '#ccc' : '#1976d2'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            {isOverview ? (
              <TrendingUpIcon sx={{ color: '#2e7d32', mr: 1 }} />
            ) : (
              <QuestionAnswerIcon sx={{ color: '#1976d2', mr: 1 }} />
            )}
            <Typography variant="subtitle1" fontWeight="bold">
              {isOverview ? 'Executive Summary' : 'Direct Answer'}
            </Typography>
          </Box>
          <Typography variant="body1">
            {typeof insights === 'string' ? insights : insights.answer}
          </Typography>
        </Box>
      )}

      {/* Human Readable Summary */}
      {insights?.human_readable_summary && (
        <Box sx={{ 
          mt: 3, 
          mb: 3, 
          p: 3, 
          bgcolor: '#f0f7ff', 
          borderRadius: 2,
          border: '1px solid #1976d2'
        }}>
          <Typography variant="h6" gutterBottom sx={{ color: '#1976d2', display: 'flex', alignItems: 'center' }}>
            <TipsAndUpdatesIcon sx={{ mr: 1 }} />
            📋 Detailed Analysis
          </Typography>
          <Typography variant="body1">
            {insights.human_readable_summary}
          </Typography>
        </Box>
      )}

      {/* Rest of your existing components... */}
      {/* Supporting Insights, Anomalies, Recommended Metrics sections */}

    </Paper>
  );
};

export default ResultsDisplay;