import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';

// Helper function to safely convert any value to string
const safeStringify = (value) => {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.map(v => safeStringify(v)).join(', ');
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

// Helper to convert snake_case to Title Case (not ALL CAPS)
const toTitleCase = (str) => {
  return str
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

class DynamicDataRenderer {
  // Track what has been rendered to avoid duplicates
  static renderedHashes = new Set();

  static clearCache() {
    this.renderedHashes.clear();
  }

  static getHash(content, type) {
    if (!content) return null;
    const str = typeof content === 'string' ? content : JSON.stringify(content);
    return `${type}_${str.substring(0, 100)}`;
  }

  static render(data, title = null) {
    this.clearCache();
    if (!data) return null;
    
    let contentToRender = data;
    
    if (data.insights && typeof data.insights === 'object') {
      contentToRender = data.insights;
    } else if (data.content && typeof data.content === 'object') {
      contentToRender = data.content;
    }
    
    if (contentToRender.human_readable_summary) {
      return this.renderHumanReadableSummary(contentToRender);
    }
    
    return this.renderObject(contentToRender);
  }

  static renderHumanReadableSummary(data) {
    const renderedItems = [];
    const renderedHashes = new Set();

    const isRendered = (content, type) => {
      const hash = this.getHash(content, type);
      if (renderedHashes.has(hash)) return true;
      if (hash) renderedHashes.add(hash);
      return false;
    };

    // 1. Human Readable Summary
    if (data.human_readable_summary && !isRendered(data.human_readable_summary, 'summary')) {
      renderedItems.push(
        <Paper key="summary" sx={{ mb: 3, p: 3, bgcolor: '#e3f2fd', borderLeft: '4px solid #1976d2' }}>
          <Typography variant="h6" sx={{ mb: 2, color: '#1976d2', display: 'flex', alignItems: 'center' }}>
            <AnalyticsIcon sx={{ mr: 1 }} />
            Analysis Summary
          </Typography>
          <Typography variant="body1" sx={{ lineHeight: 1.8, fontSize: '1.05rem' }}>
            {data.human_readable_summary}
          </Typography>
          {data.confidence_score && (
            <Typography variant="caption" sx={{ mt: 2, display: 'block', color: '#666' }}>
              Confidence score: {(data.confidence_score * 100).toFixed(0)}%
            </Typography>
          )}
        </Paper>
      );
    }

    // 2. Key Findings - Plain paragraph format
    if (data.supporting_insights?.key_findings && !isRendered(data.supporting_insights.key_findings, 'key_findings')) {
      const findings = data.supporting_insights.key_findings;
      if (Array.isArray(findings) && findings.length > 0) {
        renderedItems.push(
          <Paper key="key_findings" sx={{ mb: 2, p: 3, bgcolor: '#f5f5f5', borderLeft: '4px solid #ff9800' }}>
            <Typography variant="h6" sx={{ mb: 2, color: '#ff9800', display: 'flex', alignItems: 'center' }}>
              <TrendingUpIcon sx={{ mr: 1 }} />
              Key Findings
            </Typography>
            <Box sx={{ pl: 2 }}>
              {findings.map((finding, idx) => (
                <Typography key={idx} variant="body1" sx={{ mb: 1.5, lineHeight: 1.6 }}>
                  • {safeStringify(finding)}
                </Typography>
              ))}
            </Box>
          </Paper>
        );
      }
    }

    // 3. Key Metrics - Plain paragraph format with Title Case (not ALL CAPS)
    if (data.supporting_insights?.metrics && !isRendered(data.supporting_insights.metrics, 'metrics')) {
      const metrics = data.supporting_insights.metrics;
      if (Object.keys(metrics).length > 0) {
        // Format metrics as a single line of text
        const metricLines = [];
        for (const [key, value] of Object.entries(metrics)) {
          let displayValue = value;
          if (typeof value === 'number') {
            if (key.includes('margin')) {
              displayValue = `${(value * 100).toFixed(1)}%`;
            } else if (key.includes('revenue') || key.includes('profit') || key.includes('value')) {
              displayValue = `$${value.toLocaleString()}`;
            } else {
              displayValue = value.toLocaleString();
            }
          } else if (value === null || value === undefined) {
            displayValue = '—';
          }
          // ✅ Use Title Case instead of ALL CAPS
          const label = toTitleCase(key);
          metricLines.push(`• ${label}: ${displayValue}`);
        }
        
        renderedItems.push(
          <Paper key="metrics" sx={{ mb: 2, p: 3, bgcolor: '#f8f9fa', borderLeft: '4px solid #4caf50' }}>
            <Typography variant="h6" sx={{ mb: 2, color: '#4caf50', display: 'flex', alignItems: 'center' }}>
              <AttachMoneyIcon sx={{ mr: 1 }} />
              Key Metrics
            </Typography>
            <Box sx={{ pl: 2 }}>
              {metricLines.map((line, idx) => (
                <Typography key={idx} variant="body1" sx={{ mb: 1, lineHeight: 1.6 }}>
                  {line}
                </Typography>
              ))}
            </Box>
          </Paper>
        );
      }
    }

    // 4. Anomalies - Plain paragraph format
    if (data.anomalies?.identified && !isRendered(data.anomalies.identified, 'anomalies')) {
      const anomalies = data.anomalies.identified;
      if (Array.isArray(anomalies) && anomalies.length > 0) {
        renderedItems.push(
          <Paper key="anomalies" sx={{ mb: 2, p: 3, bgcolor: '#ffebee', borderLeft: '4px solid #f44336' }}>
            <Typography variant="h6" sx={{ mb: 2, color: '#f44336', display: 'flex', alignItems: 'center' }}>
              <ReportProblemIcon sx={{ mr: 1 }} />
              Detected Anomalies
            </Typography>
            <Box sx={{ pl: 2 }}>
              {anomalies.map((anomaly, idx) => (
                <Typography key={idx} variant="body1" sx={{ mb: 1.5, lineHeight: 1.6 }}>
                  • {safeStringify(anomaly)}
                </Typography>
              ))}
            </Box>
          </Paper>
        );
      }
    }

    // 5. Recommendations - Plain paragraph format
    if (data.recommended_metrics?.next_steps && !isRendered(data.recommended_metrics.next_steps, 'recommendations')) {
      const steps = data.recommended_metrics.next_steps;
      if (Array.isArray(steps) && steps.length > 0) {
        renderedItems.push(
          <Paper key="recommendations" sx={{ mb: 2, p: 3, bgcolor: '#e8f5e9', borderLeft: '4px solid #2e7d32' }}>
            <Typography variant="h6" sx={{ mb: 2, color: '#2e7d32', display: 'flex', alignItems: 'center' }}>
              <TipsAndUpdatesIcon sx={{ mr: 1 }} />
              Recommended Next Steps
            </Typography>
            <Box sx={{ pl: 2 }}>
              {steps.map((step, idx) => (
                <Typography key={idx} variant="body1" sx={{ mb: 1.5, lineHeight: 1.6 }}>
                  {idx + 1}. {safeStringify(step)}
                </Typography>
              ))}
            </Box>
          </Paper>
        );
      }
    }

    if (renderedItems.length > 0) {
      return <Box>{renderedItems}</Box>;
    }

    return this.renderObject(data);
  }

  static renderObject(data) {
    const hash = this.getHash(data, 'object');
    if (this.renderedHashes.has(hash)) return null;
    if (hash) this.renderedHashes.add(hash);

    if (data.human_readable_summary) {
      return this.renderHumanReadableSummary(data);
    }

    if (data.supporting_insights || data.anomalies || data.recommended_metrics) {
      return this.renderHumanReadableSummary(data);
    }

    const keys = Object.keys(data);
    
    // Product monthly trends
    if (keys.some(key => key.includes('_monthly_trend') && typeof data[key] === 'object')) {
      return this.renderSupportingInsights(data);
    }

    // Time series data
    if (keys.some(key => /^\d{4}-\d{2}/.test(key) || key.match(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i))) {
      return this.renderTimeSeries(data);
    }

    // Default: generic accordion
    return (
      <Accordion sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">Additional Details</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
            {Object.entries(data).map(([key, value]) => (
              <Box key={key} sx={{ mb: 1 }}>
                <Typography variant="subtitle2" color="primary">
                  {toTitleCase(key)}
                </Typography>
                <Typography variant="body2" sx={{ pl: 2 }}>
                  {typeof value === 'object' ? safeStringify(value) : safeStringify(value)}
                </Typography>
                <Divider sx={{ mt: 1 }} />
              </Box>
            ))}
          </Box>
        </AccordionDetails>
      </Accordion>
    );
  }

  static renderSupportingInsights(data) {
    const hash = this.getHash(data, 'supporting');
    if (this.renderedHashes.has(hash)) return null;
    if (hash) this.renderedHashes.add(hash);

    let summaryText = '';
    const products = [];
    
    for (const [key, monthlyData] of Object.entries(data)) {
      let productName = key.replace('_monthly_trend', '').replace(/_/g, ' ');
      productName = productName.split(' ').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
      ).join(' ');
      
      const months = Object.keys(monthlyData);
      const revenues = Object.values(monthlyData).filter(v => typeof v === 'number' && !isNaN(v));
      if (revenues.length === 0) continue;
      
      const totalRevenue = revenues.reduce((sum, val) => sum + val, 0);
      const avgRevenue = totalRevenue / revenues.length;
      const maxRevenue = Math.max(...revenues);
      const maxMonth = months[revenues.indexOf(maxRevenue)];
      const minRevenue = Math.min(...revenues);
      const minMonth = months[revenues.indexOf(minRevenue)];
      
      if (totalRevenue > 0 && !isNaN(totalRevenue)) {
        products.push({
          name: productName,
          totalRevenue,
          avgRevenue,
          maxRevenue,
          maxMonth,
          minRevenue,
          minMonth
        });
      }
    }
    
    if (products.length === 0) return null;
    
    products.sort((a, b) => b.totalRevenue - a.totalRevenue);
    
    summaryText = `Revenue by Product:\n`;
    for (const product of products) {
      summaryText += `• ${product.name} generated $${product.totalRevenue.toLocaleString()} total revenue, `;
      summaryText += `averaging $${Math.round(product.avgRevenue).toLocaleString()} per month. `;
      summaryText += `Peak month was ${product.maxMonth} at $${product.maxRevenue.toLocaleString()}, `;
      summaryText += `while the lowest was ${product.minMonth} at $${product.minRevenue.toLocaleString()}.\n`;
    }
    
    return (
      <Paper sx={{ mb: 2, p: 3, bgcolor: '#f5f5f5', borderLeft: '4px solid #1976d2' }}>
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {summaryText}
        </Typography>
      </Paper>
    );
  }

  static renderTimeSeries(data) {
    const entries = Object.entries(data);
    return (
      <TableContainer component={Paper} sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><strong>Period</strong></TableCell>
              <TableCell align="right"><strong>Value</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.map(([period, value]) => (
              <TableRow key={period}>
                <TableCell>{safeStringify(period)}</TableCell>
                <TableCell align="right">{typeof value === 'number' ? this.formatCurrency(value) : safeStringify(value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }

  static formatCurrency(value) {
    if (value === undefined || value === null || isNaN(value)) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
  }
}

export default DynamicDataRenderer;