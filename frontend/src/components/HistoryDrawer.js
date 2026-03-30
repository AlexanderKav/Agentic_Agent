// frontend/src/components/HistoryDrawer.js
import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider,
  CircularProgress,
  Alert,
  Pagination,
  Chip
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { getAnalysisHistory, deleteAnalysis } from '../services/api';

const HistoryDrawer = ({ open, onClose, onLoadAnalysis }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const itemsPerPage = 10;

  const loadHistory = async (pageNum = 1) => {
    setLoading(true);
    setError(null);
    try {
      const offset = (pageNum - 1) * itemsPerPage;
      const response = await getAnalysisHistory(itemsPerPage, offset);
      
      console.log("History response:", response);
      
      // Handle both old and new response formats
      if (Array.isArray(response)) {
        // Old format: direct array
        setHistory(response);
        setTotalItems(response.length);
        setTotalPages(Math.ceil(response.length / itemsPerPage));
      } else if (response && response.items && Array.isArray(response.items)) {
        // New format: paginated object
        setHistory(response.items);
        setTotalItems(response.total || response.items.length);
        setTotalPages(Math.ceil((response.total || response.items.length) / itemsPerPage));
      } else {
        // Fallback
        setHistory([]);
        setTotalItems(0);
        setTotalPages(1);
      }
    } catch (err) {
      console.error("Failed to load history:", err);
      setError(err.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadHistory(page);
    }
  }, [open, page]);

  const handleDelete = async (id, event) => {
    event.stopPropagation();
    if (window.confirm('Are you sure you want to delete this analysis?')) {
      try {
        await deleteAnalysis(id);
        // Refresh current page
        loadHistory(page);
      } catch (err) {
        setError('Failed to delete analysis');
      }
    }
  };

  const handlePageChange = (event, newPage) => {
    setPage(newPage);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'file': return '📁';
      case 'database': return '🗄️';
      case 'google_sheets': return '📊';
      default: return '📄';
    }
  };

  return (
    <Drawer anchor="right" open={open} onClose={onClose}>
      <Box sx={{ width: 400, p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Analysis History
          {totalItems > 0 && (
            <Chip 
              label={`${totalItems} items`} 
              size="small" 
              sx={{ ml: 1 }}
            />
          )}
        </Typography>
        
        <Divider sx={{ mb: 2 }} />
        
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        )}
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {!loading && history.length === 0 && !error && (
          <Typography color="textSecondary" sx={{ textAlign: 'center', p: 3 }}>
            No analysis history yet. Upload a file or connect to a database to get started.
          </Typography>
        )}
        
        <List>
          {history.map((item) => (
            <ListItem
              key={item.id}
              button
              onClick={() => onLoadAnalysis(item.id)}
              sx={{
                border: '1px solid #e0e0e0',
                borderRadius: 1,
                mb: 1,
                '&:hover': { bgcolor: '#f5f5f5' }
              }}
            >
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <span>{getTypeIcon(item.type)}</span>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                      {item.question.length > 50 
                        ? item.question.substring(0, 50) + '...' 
                        : item.question}
                    </Typography>
                  </Box>
                }
                secondary={
                  <Box sx={{ mt: 0.5 }}>
                    <Typography variant="caption" color="textSecondary">
                      {formatDate(item.created_at)}
                    </Typography>
                    {item.summary_metrics && item.summary_metrics.total_revenue && (
                      <Chip 
                        label={`$${item.summary_metrics.total_revenue.toLocaleString()}`}
                        size="small"
                        sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
                      />
                    )}
                    {item.insight_count > 0 && (
                      <Chip 
                        label={`${item.insight_count} insights`}
                        size="small"
                        sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                }
              />
              <ListItemSecondaryAction>
                <IconButton 
                  edge="end" 
                  onClick={(e) => handleDelete(item.id, e)}
                  size="small"
                >
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
        
        {totalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <Pagination 
              count={totalPages} 
              page={page} 
              onChange={handlePageChange}
              color="primary"
              size="small"
            />
          </Box>
        )}
      </Box>
    </Drawer>
  );
};

export default HistoryDrawer;