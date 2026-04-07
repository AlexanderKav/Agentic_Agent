// frontend/src/components/VerifyEmail.js
import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Container, Paper, Typography, Box, CircularProgress, Alert, Button } from '@mui/material';
import axios from 'axios';

// 🔥 Use environment variable
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setError('No verification token provided');
      setLoading(false);
      return;
    }

    const verifyEmail = async () => {
      try {
        // 🔥 FIXED: Use environment variable, not hardcoded localhost
        const response = await axios.get(`${API_BASE_URL}/auth/verify-email?token=${token}`);
        console.log('Verification response:', response.data);
        setSuccess(true);
      } catch (err) {
        console.error('Verification error:', err);
        setError(err.response?.data?.detail || 'Verification failed');
      } finally {
        setLoading(false);
      }
    };

    verifyEmail();
  }, [searchParams]);

  if (loading) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <CircularProgress />
          <Typography sx={{ mt: 2 }}>Verifying your email...</Typography>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper sx={{ p: 4 }}>
        {success ? (
          <Box textAlign="center">
            <Typography variant="h5" color="success.main" gutterBottom>
              ✓ Email Verified Successfully!
            </Typography>
            <Typography sx={{ mb: 3 }}>
              Your email has been verified. You can now access all features.
            </Typography>
            <Button variant="contained" onClick={() => navigate('/')}>
              Go to Dashboard
            </Button>
          </Box>
        ) : (
          <Box textAlign="center">
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
            <Button variant="contained" onClick={() => navigate('/')}>
              Back to Home
            </Button>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default VerifyEmail;