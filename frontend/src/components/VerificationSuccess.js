import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Container, Paper, Typography, Box, CircularProgress, Alert, Button } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const VerificationSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setVerifiedUser } = useAuth();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');
  const hasVerified = useRef(false); // Prevent double verification

  useEffect(() => {
    const verifyEmail = async () => {
      // Prevent double execution (React Strict Mode)
      if (hasVerified.current) return;
      hasVerified.current = true;

      const token = searchParams.get('token');
      
      if (!token) {
        setStatus('error');
        setMessage('No verification token provided');
        return;
      }

      try {
        console.log('🔍 Verifying email with token:', token);
        
        // Call backend verification endpoint
        const response = await axios.get(`${API_BASE_URL}/auth/verify-email?token=${token}`);
        
        console.log('✅ Verification response:', response.data);
        
        // Get the returned data
        const { access_token, user, message } = response.data;
        
        if (access_token && user) {
          // Store token and update auth context
          localStorage.setItem('token', access_token);
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          // Manually set user in auth context
          setVerifiedUser(user);
          
          setStatus('success');
          setMessage(message || 'Email verified successfully!');
          
          // Redirect to dashboard after 2 seconds
          setTimeout(() => {
            navigate('/');
          }, 2000);
        } else {
          setStatus('success');
          setMessage(message || 'Email verified successfully! You can now log in.');
          
          // Redirect to login after 3 seconds
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
        
      } catch (err) {
        console.error('❌ Verification error:', err);
        setStatus('error');
        
        // Handle different error types
        if (err.response?.status === 400) {
          setMessage(err.response?.data?.detail || 'Invalid or expired verification token');
        } else if (err.response?.status === 404) {
          setMessage('User not found');
        } else {
          setMessage(err.response?.data?.detail || 'Verification failed. Please try again.');
        }
      }
    };

    verifyEmail();
  }, [searchParams, navigate, setVerifiedUser]); // Added setVerifiedUser to dependencies

  if (status === 'verifying') {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Paper sx={{ p: 5, textAlign: 'center' }}>
          <CircularProgress size={60} sx={{ mb: 3 }} />
          <Typography variant="h5" gutterBottom>
            Verifying Your Email...
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Please wait while we verify your email address.
          </Typography>
        </Paper>
      </Container>
    );
  }

  if (status === 'error') {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Paper sx={{ p: 5, textAlign: 'center' }}>
          <ErrorIcon sx={{ fontSize: 80, color: '#f44336', mb: 2 }} />
          <Typography variant="h5" gutterBottom color="error">
            Verification Failed
          </Typography>
          <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
            {message}
          </Alert>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button 
              variant="outlined" 
              onClick={() => navigate('/login')}
            >
              Go to Login
            </Button>
            <Button 
              variant="contained" 
              onClick={() => window.location.reload()}
            >
              Try Again
            </Button>
          </Box>
        </Paper>
      </Container>
    );
  }

  // Success state
  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper sx={{ p: 5, textAlign: 'center' }}>
        <CheckCircleIcon sx={{ fontSize: 80, color: '#4caf50', mb: 2 }} />
        
        <Typography variant="h4" gutterBottom>
          Email Verified!
        </Typography>
        
        <Alert severity="success" sx={{ mb: 3, textAlign: 'left' }}>
          {message}
        </Alert>
        
        <Typography variant="body1" sx={{ mb: 4, color: 'text.secondary' }}>
          {message.includes('log in') 
            ? 'You can now log in with your credentials.'
            : 'You are being redirected to the dashboard...'}
        </Typography>
        
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2 }}>
          <CircularProgress size={24} />
          <Typography variant="body2" color="textSecondary">
            Redirecting...
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
};

export default VerificationSuccess;