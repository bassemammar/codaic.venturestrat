/**
 * OAuthCallbackPage — handles redirect from Google/Microsoft OAuth consent.
 *
 * Mounted at:
 *   /settings/oauth/google/callback
 *   /settings/oauth/microsoft/callback
 *
 * Flow:
 *   1. Extract `code` and `state` from URL search params
 *   2. POST to backend callback endpoint
 *   3. Show success message → redirect to /settings after 2 s
 *   4. Show error message if anything fails
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Button from '@mui/material/Button';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { exchangeGoogleCode, exchangeMicrosoftCode } from '../../outreach/api/outreachApi';

type Status = 'loading' | 'success' | 'error';

const OAuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState<Status>('loading');
  const [message, setMessage] = useState('Connecting your account…');
  const [email, setEmail] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    if (error) {
      setStatus('error');
      setMessage(`Authorization denied: ${error}`);
      return;
    }

    if (!code || !state) {
      setStatus('error');
      setMessage('Missing authorization code or state parameter.');
      return;
    }

    // Determine provider from the current path
    const isGoogle = location.pathname.includes('/google/');
    const isMicrosoft = location.pathname.includes('/microsoft/');

    async function exchangeCode() {
      try {
        let result;
        if (isGoogle) {
          result = await exchangeGoogleCode(code!, state!);
        } else if (isMicrosoft) {
          result = await exchangeMicrosoftCode(code!, state!);
        } else {
          throw new Error('Unknown OAuth provider in callback URL');
        }

        setEmail(result.email);
        setStatus('success');
        setMessage(`Successfully connected ${result.email}`);

        // Auto-redirect to settings after 2 seconds
        setTimeout(() => navigate('/settings', { replace: true }), 2000);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Connection failed';
        setStatus('error');
        setMessage(msg);
      }
    }

    exchangeCode();
  }, []); // run once on mount

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: '#071929',
        gap: 3,
        p: 4,
      }}
    >
      {status === 'loading' && (
        <>
          <CircularProgress size={48} sx={{ color: '#4f7df9' }} />
          <Typography variant="h6" sx={{ color: '#c8d8e8' }}>
            {message}
          </Typography>
        </>
      )}

      {status === 'success' && (
        <>
          <CheckCircleOutlineIcon sx={{ fontSize: 64, color: '#4caf50' }} />
          <Typography variant="h5" sx={{ color: '#e2edf8', fontWeight: 600 }}>
            Account Connected
          </Typography>
          <Typography variant="body1" sx={{ color: '#6b7280' }}>
            {email} has been connected successfully.
          </Typography>
          <Typography variant="body2" sx={{ color: '#6b7280' }}>
            Redirecting to settings…
          </Typography>
          <Button
            variant="contained"
            sx={{ bgcolor: '#4f7df9', color: '#f9fafb', fontWeight: 600 }}
            onClick={() => navigate('/settings', { replace: true })}
          >
            Go to Settings
          </Button>
        </>
      )}

      {status === 'error' && (
        <>
          <ErrorOutlineIcon sx={{ fontSize: 64, color: '#ef5350' }} />
          <Typography variant="h5" sx={{ color: '#e2edf8', fontWeight: 600 }}>
            Connection Failed
          </Typography>
          <Typography
            variant="body2"
            sx={{ color: '#6b7280', maxWidth: 480, textAlign: 'center' }}
          >
            {message}
          </Typography>
          <Button
            variant="outlined"
            sx={{ borderColor: 'rgba(255,255,255,0.2)', color: '#6b7280' }}
            onClick={() => navigate('/settings', { replace: true })}
          >
            Back to Settings
          </Button>
        </>
      )}
    </Box>
  );
};

export default OAuthCallbackPage;
