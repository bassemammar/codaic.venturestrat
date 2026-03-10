import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import { CheckCircle } from 'lucide-react';

const BillingSuccessPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '60vh',
        p: { xs: 2, md: 4 },
      }}
    >
      <Paper
        sx={{
          p: 5,
          bgcolor: '#ffffff',
          border: '1px solid rgba(255,255,255,0.08)',
          textAlign: 'center',
          maxWidth: 480,
          width: '100%',
        }}
      >
        <Box sx={{ mb: 3 }}>
          <CheckCircle size={56} color="#66bb6a" />
        </Box>
        <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
          Subscription Activated!
        </Typography>
        <Typography variant="body1" sx={{ color: '#6b7280', mb: 4 }}>
          Your payment was successful and your subscription is now active.
          You can start using all the features included in your plan.
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button
            variant="contained"
            onClick={() => navigate('/dashboard')}
            sx={{
              bgcolor: '#4f7df9',
              color: '#f9fafb',
              fontWeight: 600,
              '&:hover': { bgcolor: '#4f7df9', opacity: 0.9 },
            }}
          >
            Go to Dashboard
          </Button>
          <Button
            variant="outlined"
            onClick={() => navigate('/billing/subscription')}
            sx={{ borderColor: '#4f7df9', color: '#4f7df9' }}
          >
            View Subscription
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default BillingSuccessPage;
