import React from 'react';
import { Container, Paper, Typography, Box, Button, Alert } from '@mui/material';
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';  // Add this import

const VerificationPending = () => {
  const { user, logout } = useAuth();

  const handleResendEmail = async () => {
    try {
      await axios.post('http://localhost:8000/api/v1/auth/resend-verification', {
        email: user.email
      });
      alert('Verification email resent! Check your inbox.');
    } catch (error) {
      alert('Failed to resend email. Please try again later.');
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 8 }}>
      <Paper sx={{ p: 5, textAlign: 'center' }}>
        <MarkEmailReadIcon sx={{ fontSize: 80, color: '#1976d2', mb: 2 }} />
        
        <Typography variant="h4" gutterBottom>
          Verify Your Email
        </Typography>
        
        <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
          We've sent a verification email to:
        </Typography>
        
        <Typography variant="h6" sx={{ mb: 3, color: 'primary.main' }}>
          {user?.email}
        </Typography>
        
        <Alert severity="info" sx={{ mb: 4, textAlign: 'left' }}>
          Please check your inbox and click the verification link to activate your account.
          If you don't see the email, check your spam folder.
        </Alert>
        
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button 
            variant="outlined" 
            onClick={handleResendEmail}
          >
            Resend Email
          </Button>
          <Button 
            variant="contained" 
            onClick={logout}
          >
            Logout
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default VerificationPending;