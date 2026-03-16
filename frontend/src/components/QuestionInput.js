import React, { useState } from 'react';
import { TextField, Button, Box, Paper, Typography } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AnalyticsIcon from '@mui/icons-material/Analytics';

const QuestionInput = ({ onSubmit, loading }) => {
  const [question, setQuestion] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Allow empty questions (for general overview)
    onSubmit(question);
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Ask a Question (Optional)
      </Typography>
      <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
        Leave empty for a general business overview
      </Typography>
      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="e.g., What were our top products? (optional)"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />
        <Button
          type="submit"
          variant="contained"
          disabled={loading}
          endIcon={question.trim() ? <SendIcon /> : <AnalyticsIcon />}
        >
          {question.trim() ? 'Analyze' : 'Overview'}
        </Button>
      </Box>
    </Paper>
  );
};

export default QuestionInput;