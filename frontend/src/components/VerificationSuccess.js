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
      console.log('📝 Token from URL:', token);
      console.log('🌐 API_BASE_URL:', API_BASE_URL);
      console.log('🔗 Full URL:', `${API_BASE_URL}/auth/verify-email?token=${token}`);
      console.log('==========================================');
      
      if (!token) {
        console.error('❌ No token found in URL');
        setStatus('error');
        setMessage('No verification token provided. Please check your email link.');
        return;
      }

      try {
        const response = await axios.get(`${API_BASE_URL}/auth/verify-email?token=${token}`);
        
        console.log('✅ Verification response:', response.data);
        console.log('   Status:', response.status);
        console.log('   Has access_token:', !!response.data?.access_token);
        console.log('   Has user:', !!response.data?.user);
        
        const { access_token, user, message: responseMessage } = response.data;
        
        if (access_token && user) {
          console.log('🔐 Logging user in:', user.username);
          login(user, access_token);
          
          setStatus('success');
          setMessage(responseMessage || 'Email verified successfully! Redirecting to dashboard...');
          
          setTimeout(() => {
            navigate('/');
          }, 2000);
        } else {
          console.log('⚠️ Verification succeeded but no auto-login token provided');
          setStatus('success');
          setMessage(responseMessage || 'Email verified successfully! You can now log in.');
          
          setTimeout(() => {
            navigate('/login');
          }, 3000);
        }
        
      } catch (err) {
        console.error('❌ Verification error:', err);
        console.error('   Status:', err.response?.status);
        console.error('   Data:', err.response?.data);
        console.error('   Message:', err.message);
        
        setStatus('error');
        
        // Handle different error cases
        if (err.response?.status === 200) {
          // This shouldn't happen, but if it does, treat as success
          setStatus('success');
          setMessage('Email verified successfully! You can now log in.');
          setTimeout(() => {
            navigate('/login');
          }, 2000);
        } else if (err.response?.data?.detail === "Email already verified") {
          setStatus('success');
          setMessage('Email already verified! You can now log in.');
          setTimeout(() => {
            navigate('/login');
          }, 2000);
        } else if (err.response?.status === 400) {
          setMessage(err.response?.data?.detail || 'Invalid or expired verification token. Please request a new one.');
        } else if (err.response?.status === 404) {
          setMessage('User not found. Please register again.');
        } else if (err.code === 'ERR_NETWORK') {
          setMessage('Network error. Please check your connection and try again.');
        } else {
          setMessage(err.response?.data?.detail || 'Verification failed. Please try again or request a new link.');
        }
      }
    };

    verifyEmail();
  }, [searchParams, navigate, login]);

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
              onClick={() => {
                // Resend verification email
                const email = localStorage.getItem('pendingVerificationEmail');
                if (email) {
                  // Call resend endpoint
                  axios.post(`${API_BASE_URL}/auth/resend-verification`, { email })
                    .then(() => alert('Verification email resent!'))
                    .catch(() => alert('Failed to resend email'));
                }
              }}
            >
              Resend Email
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