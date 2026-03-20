import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Box,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  IconButton,
  Divider,
  Chip,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import HistoryIcon from '@mui/icons-material/History';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import StorageIcon from '@mui/icons-material/Storage';
import GoogleIcon from '@mui/icons-material/Google';
import SearchIcon from '@mui/icons-material/Search';
import { getAnalysisHistory } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const HistoryDrawer = ({ open, onClose, onLoadAnalysis }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const { user } = useAuth();

  useEffect(() => {
    if (open && user) {
      loadHistory();
    }
  }, [open, user]);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAnalysisHistory();
      setHistory(data);
    } catch (err) {
      setError('Failed to load history');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'file':
        return <InsertDriveFileIcon color="primary" />;
      case 'database':
        return <StorageIcon color="success" />;
      case 'google_sheets':
        return <GoogleIcon color="error" />;
      default:
        return <HistoryIcon />;
    }
  };

  const getTypeLabel = (type) => {
    switch (type) {
      case 'file': return 'File Upload';
      case 'database': return 'Database';
      case 'google_sheets': return 'Google Sheets';
      default: return type;
    }
  };

  const filteredHistory = history.filter(item => 
    item.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
    getTypeLabel(item.type).toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 400 } } }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6">Analysis History</Typography>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </Box>
      
      <Divider />
      
      <Box sx={{ p: 2 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search history..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            )
          }}
        />
      </Box>
      
      <Divider />
      
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        )}
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {!loading && !error && filteredHistory.length === 0 && (
          <Typography color="textSecondary" align="center" sx={{ my: 4 }}>
            {history.length === 0 ? 'No analysis history yet' : 'No matches found'}
          </Typography>
        )}
        
        <List>
          {filteredHistory.map((item) => (
            <ListItem key={item.id} disablePadding sx={{ mb: 1 }}>
              <ListItemButton
                onClick={() => onLoadAnalysis(item.id)}
                sx={{
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  p: 2
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', mb: 1 }}>
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {getIcon(item.type)}
                  </ListItemIcon>
                  <ListItemText 
                    primary={item.question || 'General Overview'}
                    secondary={formatDate(item.created_at)}
                    primaryTypographyProps={{
                      sx: { fontWeight: 'medium', fontSize: '0.95rem' }
                    }}
                    secondaryTypographyProps={{
                      sx: { fontSize: '0.8rem' }
                    }}
                  />
                </Box>
                
                <Box sx={{ display: 'flex', gap: 1, ml: 5 }}>
                  <Chip 
                    label={getTypeLabel(item.type)} 
                    size="small" 
                    variant="outlined"
                    sx={{ fontSize: '0.7rem' }}
                  />
                  {item.data_source?.rows && (
                    <Chip 
                      label={`${item.data_source.rows} rows`} 
                      size="small" 
                      variant="outlined"
                      sx={{ fontSize: '0.7rem' }}
                    />
                  )}
                </Box>
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    </Drawer>
  );
};

export default HistoryDrawer;