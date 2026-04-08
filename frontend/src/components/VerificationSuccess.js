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
  const { login } = useAuth();
  const [status, setStatus] = useState('verifying');
  const [message, setMessage] = useState('');
  const hasVerified = useRef(false);

  useEffect(() => {
    const verifyEmail = async () => {
      if (hasVerified.current) return;
      hasVerified.current = true;

      const token = searchParams.get('token');
      
      console.log('==========================================');
      console.log('🔍 VERIFICATION PAGE LOADED');
      console.log('📝 Token from URL:', token?.substring(0, 30) + '...');
      console.log('🌐 API_BASE_URL:', API_BASE_URL);
      console.log('==========================================');
      
      if (!token) {
        setStatus('error');
        setMessage('No verification token provided. Please check your email link.');
        return;
      }

      try {
        const response = await axios.get(`${API_BASE_URL}/auth/verify-email?token=${token}`);
        
        console.log('✅ Verification response:', response.data);
        
        const { access_token, user, message: responseMessage } = response.data;
        
        if (access_token && user) {
          console.log('🔐 Storing token and user info');
          
          // Store token
          localStorage.setItem('token', access_token);
          
          // Test if token works by making a test request
          try {
            const testResponse = await axios.get(`${API_BASE_URL}/auth/me`, {
              headers: { Authorization: `Bearer ${access_token}` }
            });
            console.log('✅ Token test successful:', testResponse.data);
            
            // Now login via auth context
            login(user, access_token);
            
            setStatus('success');
            setMessage(responseMessage || 'Email verified successfully! Redirecting to dashboard...');
            
            setTimeout(() => {
              navigate('/');
            }, 2000);
          } catch (testError) {
            console.error('❌ Token test failed:', testError);
            // Token might be invalid, but verification succeeded
            setStatus('success');
            setMessage(responseMessage || 'Email verified successfully! You can now log in manually.');
            setTimeout(() => {
              navigate('/login');
            }, 3000);
          }
        } else {
          setStatus('success');
          setMessage(responseMessage || 'Email verified successfully! You can now log in.');
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
        
      } catch (err) {
        console.error('❌ Verification error:', err);
        
        setStatus('error');
        
        if (err.response?.data?.detail === "Email already verified") {
          setStatus('success');
          setMessage('Email already verified! You can now log in.');
          setTimeout(() => {
            navigate('/login');
          }, 2000);
        } else if (err.response?.status === 400) {
          setMessage(err.response?.data?.detail || 'Invalid or expired verification token');
        } else if (err.response?.status === 404) {
          setMessage('User not found');
        } else {
          setMessage(err.response?.data?.detail || 'Verification failed. Please try again.');
        }
      }
    };

    verifyEmail();
  }, [searchParams, navigate, login]);

  // Rest of your component remains the same...
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
            <Button variant="outlined" onClick={() => navigate('/login')}>
              Go to Login
            </Button>
            <Button variant="contained" onClick={() => window.location.reload()}>
              Try Again
            </Button>
          </Box>
        </Paper>
      </Container>
    );
  }

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