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
import ChartViewer from './ChartViewer';

const ResultsDisplay = ({ results, userQuestion }) => {
  if (!results) return null;
  console.log("🎯 ResultsDisplay received:", results);
  console.log("🎯 User question:", userQuestion);

  // Extract all possible fields
  const { 
    insights, 
    warnings, 
    execution_time, 
    data_summary, 
    plan, 
    is_generic_overview,
    results: analysisResults,
    raw_insights
  } = results;
  
  // Extract charts from analysisResults if they exist
  const charts = analysisResults?.charts || results?.charts || null;
  
  // Determine if this is a general overview
  const isOverview = is_generic_overview || !userQuestion || userQuestion.trim() === '';
  
  // Parse insights - it could be a string or an object
  let answerText = '';
  let summaryText = '';
  let supportingInsights = {};
  let anomalies = {};
  let recommendedMetrics = {};
  
  if (typeof insights === 'string') {
    // If insights is a string, use it as the answer
    answerText = insights;
    summaryText = insights;
  } else if (insights && typeof insights === 'object') {
    // If insights is an object, extract its fields
    answerText = insights.answer || insights.human_readable_summary || '';
    summaryText = insights.human_readable_summary || insights.answer || '';
    supportingInsights = insights.supporting_insights || {};
    anomalies = insights.anomalies || {};
    recommendedMetrics = insights.recommended_metrics || {};
  }
  
  // Also check raw_insights if insights is empty
  if ((!answerText || answerText === '') && raw_insights) {
    if (typeof raw_insights === 'object') {
      answerText = raw_insights.answer || raw_insights.human_readable_summary || '';
      summaryText = raw_insights.human_readable_summary || raw_insights.answer || '';
      supportingInsights = raw_insights.supporting_insights || {};
      anomalies = raw_insights.anomalies || {};
      recommendedMetrics = raw_insights.recommended_metrics || {};
    }
  }

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

      {/* Charts Section */}
      {charts && <ChartViewer charts={charts} />}

      {/* Answer Section */}
      {answerText && (
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
            {answerText}
          </Typography>
        </Box>
      )}

      {/* Human Readable Summary (if different from answer) */}
      {summaryText && summaryText !== answerText && (
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
            {summaryText}
          </Typography>
        </Box>
      )}

      {/* Supporting Insights */}
      {Object.keys(supportingInsights).length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <AnalyticsIcon sx={{ mr: 1, color: '#1976d2' }} />
            Supporting Insights
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, bgcolor: '#fafafa' }}>
            <pre style={{ margin: 0, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(supportingInsights, null, 2)}
            </pre>
          </Paper>
        </Box>
      )}

      {/* Anomalies */}
      {Object.keys(anomalies).length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ color: '#d32f2f', display: 'flex', alignItems: 'center' }}>
            <ReportProblemIcon sx={{ mr: 1 }} />
            ⚠️ Anomalies Detected
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, bgcolor: '#fff4f4' }}>
            <pre style={{ margin: 0, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(anomalies, null, 2)}
            </pre>
          </Paper>
        </Box>
      )}

      {/* Recommended Metrics */}
      {Object.keys(recommendedMetrics).length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ color: '#2e7d32', display: 'flex', alignItems: 'center' }}>
            <TipsAndUpdatesIcon sx={{ mr: 1 }} />
            📊 Recommended Next Steps
          </Typography>
          <Grid container spacing={2}>
            {Object.entries(recommendedMetrics).map(([key, value]) => (
              <Grid item xs={12} md={6} key={key}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent>
                    <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                      {key.replace(/_/g, ' ').toUpperCase()}
                    </Typography>
                    <Typography variant="body2">
                      {value}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Tools Used */}
      {plan?.plan && plan.plan.length > 0 && (
        <Box sx={{ mt: 3, pt: 2, borderTop: '1px dashed #ccc' }}>
          <Typography variant="caption" color="textSecondary">
            Analysis performed using: {plan.plan.join(' → ')}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default ResultsDisplay;