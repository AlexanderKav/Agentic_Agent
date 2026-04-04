import React, { useState } from 'react';
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
  Collapse,
  IconButton,
  Tooltip
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ChartViewer from './ChartViewer';
import DynamicDataRenderer from './DynamicDataRenderer';

const ResultsDisplay = ({ results, userQuestion }) => {
  const [expandedWarnings, setExpandedWarnings] = useState(false);
  
  if (!results) return null;
  console.log("🎯 ResultsDisplay received:", results);

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
  
  // Extract charts
  const charts = analysisResults?.charts || results?.charts || null;
  
  // Determine if this is a general overview
  const isOverview = is_generic_overview || !userQuestion || userQuestion.trim() === '';
  
  // Parse insights - extract structured data
  let structuredData = null;
  
  // Helper to extract structured insights
  const extractStructuredData = (data) => {
    if (!data) return null;
    
    if (data.human_readable_summary || data.supporting_insights || data.anomalies || data.recommended_metrics) {
      return data;
    }
    
    if (data.answer && (data.supporting_insights || data.anomalies)) {
      return data;
    }
    
    if (data.insights && typeof data.insights === 'object') {
      return data.insights;
    }
    
    return null;
  };
  
  // Try to get structured data from various sources
  structuredData = extractStructuredData(insights);
  if (!structuredData && raw_insights) {
    structuredData = extractStructuredData(raw_insights);
  }
  
  // For the DynamicDataRenderer, we want to pass the ENTIRE structured object
  const hasStructuredResponse = structuredData !== null;
  
  // Extract answer for fallback only
  let answerText = '';
  if (structuredData?.answer && typeof structuredData.answer === 'string') {
    answerText = structuredData.answer;
  } else if (structuredData?.human_readable_summary && typeof structuredData.human_readable_summary === 'string') {
    answerText = structuredData.human_readable_summary;
  } else if (typeof insights === 'string') {
    answerText = insights;
  } else if (typeof raw_insights === 'string') {
    answerText = raw_insights;
  }

  // Process warnings
  const columnDropWarnings = [];
  const otherWarnings = [];
  
  if (warnings && warnings.length > 0) {
    warnings.forEach(warning => {
      if (warning.includes('columns not mapped') || 
          warning.includes('Columns not mapped') ||
          (warning.includes('Dropped') && warning.includes('unmapped columns'))) {
        columnDropWarnings.push(warning);
      } else {
        otherWarnings.push(warning);
      }
    });
  }

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
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
          {!isOverview && userQuestion && (
            <Typography variant="body1" color="textSecondary" sx={{ mt: 1 }}>
              Question: "{userQuestion}"
            </Typography>
          )}
        </Box>
      </Box>

      {/* Column Drop Warnings */}
      {columnDropWarnings.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Alert 
            severity="info" 
            icon={<VisibilityIcon />}
            action={
              <IconButton
                aria-label="expand"
                size="small"
                onClick={() => setExpandedWarnings(!expandedWarnings)}
              >
                {expandedWarnings ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            }
            sx={{ backgroundColor: '#e3f2fd' }}
          >
            <Typography variant="body2">
              <strong>📋 Column Notice:</strong> {columnDropWarnings.length} column(s) were not recognized
            </Typography>
          </Alert>
          
          <Collapse in={expandedWarnings}>
            <Box sx={{ mt: 1, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
              {columnDropWarnings.map((warning, idx) => (
                <Typography key={idx} variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem', mb: 0.5 }}>
                  • {warning}
                </Typography>
              ))}
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Other Warnings */}
      {otherWarnings.length > 0 && (
        <Box sx={{ mb: 2 }}>
          {otherWarnings.map((warning, idx) => (
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
              <Typography color="textSecondary" gutterBottom>Rows Processed</Typography>
              <Typography variant="h5">{data_summary?.rows?.toLocaleString() || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card variant="outlined">
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Columns</Typography>
              <Typography variant="h5">{data_summary?.columns?.length || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card variant="outlined">
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Execution Time</Typography>
              <Typography variant="h5">{execution_time?.toFixed(2)}s</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card variant="outlined">
            <CardContent>
              <Typography color="textSecondary" gutterBottom>Analysis Type</Typography>
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

      {/* Charts */}
      {charts && <ChartViewer charts={charts} />}

      {/* ✅ CORRECTED: Use the static render method, not as a component */}
      {hasStructuredResponse && (
        <Box sx={{ mt: 3 }}>
          {DynamicDataRenderer.render(structuredData)}
        </Box>
      )}

      {/* Fallback for simple string answers */}
      {!hasStructuredResponse && answerText && (
        <Box sx={{ 
          mt: 3, 
          p: 3, 
          bgcolor: isOverview ? '#f5f5f5' : '#e3f2fd',
          borderRadius: 2
        }}>
          <Typography variant="body1">{answerText}</Typography>
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