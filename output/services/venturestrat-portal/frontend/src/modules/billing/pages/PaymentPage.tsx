import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import Paper from '@mui/material/Paper';
import { subscribe } from '../api/billingApi';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PaymentPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const planId = searchParams.get('plan_id');

  const [status, setStatus] = useState<'loading' | 'error' | 'redirecting'>('loading');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!planId) {
      setStatus('error');
      setErrorMsg('No plan selected. Please go back and choose a plan.');
      return;
    }

    let cancelled = false;

    async function createCheckout() {
      try {
        setStatus('loading');
        const result = await subscribe({
          plan_id: planId!,
          success_url: `${window.location.origin}/billing/success`,
          cancel_url: `${window.location.origin}/billing/subscription`,
        });

        if (cancelled) return;

        if (result.checkout_url) {
          setStatus('redirecting');
          window.location.href = result.checkout_url;
        } else {
          setStatus('error');
          setErrorMsg('No checkout URL returned. Please try again.');
        }
      } catch (err: any) {
        if (cancelled) return;
        setStatus('error');
        setErrorMsg(
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          'Failed to create checkout session.',
        );
      }
    }

    createCheckout();

    return () => {
      cancelled = true;
    };
  }, [planId]);

  const handleRetry = () => {
    setStatus('loading');
    setErrorMsg(null);
    // Re-trigger by navigating to same page
    navigate(`/billing/payment?plan_id=${planId}`, { replace: true });
    window.location.reload();
  };

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
        {status === 'loading' && (
          <>
            <CircularProgress size={40} sx={{ mb: 3, color: '#4f7df9' }} />
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              Creating checkout session...
            </Typography>
            <Typography variant="body2" sx={{ color: '#6b7280' }}>
              You will be redirected to Stripe to complete your payment.
            </Typography>
          </>
        )}

        {status === 'redirecting' && (
          <>
            <CircularProgress size={40} sx={{ mb: 3, color: '#4f7df9' }} />
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              Redirecting to Stripe...
            </Typography>
            <Typography variant="body2" sx={{ color: '#6b7280' }}>
              If you are not redirected automatically, please wait a moment.
            </Typography>
          </>
        )}

        {status === 'error' && (
          <>
            <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
              {errorMsg}
            </Alert>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button
                variant="outlined"
                onClick={() => navigate('/billing/subscription')}
              >
                Back to Plans
              </Button>
              {planId && (
                <Button
                  variant="contained"
                  onClick={handleRetry}
                  sx={{
                    bgcolor: '#4f7df9',
                    color: '#f9fafb',
                    '&:hover': { bgcolor: '#4f7df9', opacity: 0.9 },
                  }}
                >
                  Try Again
                </Button>
              )}
            </Box>
          </>
        )}
      </Paper>
    </Box>
  );
};

export default PaymentPage;
