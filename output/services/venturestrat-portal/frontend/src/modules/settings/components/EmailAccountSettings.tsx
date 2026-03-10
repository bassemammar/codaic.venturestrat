/**
 * EmailAccountSettings — manage connected OAuth email accounts.
 *
 * Shows connected Gmail / Microsoft accounts.
 * Provides "Connect Gmail" and "Connect Microsoft" buttons that initiate
 * the OAuth flow by redirecting the user to the provider consent screen.
 */

import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { Mail, Trash2 } from 'lucide-react';
import {
  useConnectedAccounts,
  useDisconnectAccount,
  useGoogleConnect,
  useMicrosoftConnect,
} from '../../outreach/hooks/useEmailAccounts';

// ---------------------------------------------------------------------------
// Provider icons (inline SVG — no external image dependency)
// ---------------------------------------------------------------------------

function GmailIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6 18V8.4L12 12.6L18 8.4V18H6Z" fill="#EA4335" />
      <path d="M2 6V18H4V8.4L6 9.8V18H18V9.8L20 8.4V18H22V6L12 12.6L2 6Z" fill="#FBBC05" />
      <path d="M2 6L12 12.6L22 6H2Z" fill="#4285F4" />
      <path d="M2 6V18H6V8.4L2 6Z" fill="#34A853" />
      <path d="M22 6L18 8.4V18H22V6Z" fill="#EA4335" />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="10" height="10" fill="#F25022" />
      <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
      <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
      <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  userId?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const EmailAccountSettings: React.FC<Props> = ({ userId }) => {
  const { data: accounts = [], isLoading, error, refetch } = useConnectedAccounts(userId);
  const disconnectMutation = useDisconnectAccount();
  const googleConnect = useGoogleConnect(userId);
  const microsoftConnect = useMicrosoftConnect(userId);

  const handleDisconnect = async (accountId: string) => {
    try {
      await disconnectMutation.mutateAsync(accountId);
    } catch {
      // error shown via mutation state
    }
  };

  const isNotConfiguredError =
    error instanceof Error && error.message?.toLowerCase().includes('not configured');

  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
        Connected Email Accounts
      </Typography>
      <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
        Connect your email accounts to send outreach emails directly from VentureStrat.
      </Typography>

      {/* Error state */}
      {error && !isNotConfiguredError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => refetch()}>
          Failed to load connected accounts. The OAuth service may be unavailable.
        </Alert>
      )}

      {isNotConfiguredError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          OAuth credentials are not configured on the server. Contact your administrator to set up
          GOOGLE_CLIENT_ID / MICROSOFT_CLIENT_ID.
        </Alert>
      )}

      {/* Disconnect error */}
      {disconnectMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to disconnect account. Please try again.
        </Alert>
      )}

      {/* Loading */}
      {isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3, color: '#6b7280' }}>
          <CircularProgress size={16} color="inherit" />
          <Typography variant="body2">Loading connected accounts…</Typography>
        </Box>
      )}

      {/* Account list */}
      {!isLoading && accounts.length === 0 && !error && (
        <Box
          sx={{
            p: 4,
            textAlign: 'center',
            border: '1px dashed rgba(255,255,255,0.12)',
            borderRadius: 2,
            mb: 3,
          }}
        >
          <Mail size={32} color="#6b7280" style={{ marginBottom: 8 }} />
          <Typography variant="body2" sx={{ color: '#6b7280' }}>
            No email accounts connected yet.
          </Typography>
          <Typography variant="caption" sx={{ color: '#556677' }}>
            Connect Gmail or Microsoft below to start sending emails.
          </Typography>
        </Box>
      )}

      {!isLoading && accounts.length > 0 && (
        <Stack spacing={1.5} sx={{ mb: 3 }}>
          {accounts.map((acct) => (
            <Box
              key={acct.id}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                p: 2,
                border: `1px solid ${acct.provider === 'gmail' ? 'rgba(234,67,53,0.3)' : 'rgba(0,120,212,0.3)'}`,
                borderRadius: 1.5,
                bgcolor: 'rgba(255,255,255,0.03)',
                transition: 'border-color 0.2s',
                '&:hover': {
                  borderColor: acct.provider === 'gmail'
                    ? 'rgba(234,67,53,0.6)'
                    : 'rgba(0,120,212,0.6)',
                },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {acct.provider === 'gmail' ? <GmailIcon /> : <MicrosoftIcon />}
                </Box>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {acct.email}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#6b7280', textTransform: 'capitalize' }}>
                    {acct.provider === 'gmail' ? 'Gmail' : 'Microsoft'}
                    {' · Connected '}
                    {new Date(acct.connected_at).toLocaleDateString()}
                  </Typography>
                </Box>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={acct.is_active ? 'Active' : 'Inactive'}
                  size="small"
                  color={acct.is_active ? 'success' : 'default'}
                  variant="outlined"
                />
                <IconButton
                  size="small"
                  sx={{ color: '#ef5350', '&:hover': { bgcolor: 'rgba(239,83,80,0.08)' } }}
                  onClick={() => handleDisconnect(acct.id)}
                  disabled={disconnectMutation.isPending}
                  title="Disconnect account"
                >
                  <Trash2 size={16} />
                </IconButton>
              </Box>
            </Box>
          ))}
        </Stack>
      )}

      {/* Connect buttons */}
      <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Button
          variant="outlined"
          startIcon={<GmailIcon />}
          onClick={() => googleConnect.mutate()}
          disabled={googleConnect.isPending}
          sx={{
            borderColor: '#4285f4',
            color: '#4285f4',
            textTransform: 'none',
            fontWeight: 500,
            '&:hover': { borderColor: '#4285f4', bgcolor: 'rgba(66,133,244,0.08)' },
            '&:disabled': { borderColor: 'rgba(66,133,244,0.3)', color: 'rgba(66,133,244,0.4)' },
          }}
        >
          {googleConnect.isPending ? 'Redirecting…' : 'Connect Gmail'}
        </Button>

        <Button
          variant="outlined"
          startIcon={<MicrosoftIcon />}
          onClick={() => microsoftConnect.mutate()}
          disabled={microsoftConnect.isPending}
          sx={{
            borderColor: '#0078d4',
            color: '#0078d4',
            textTransform: 'none',
            fontWeight: 500,
            '&:hover': { borderColor: '#0078d4', bgcolor: 'rgba(0,120,212,0.08)' },
            '&:disabled': { borderColor: 'rgba(0,120,212,0.3)', color: 'rgba(0,120,212,0.4)' },
          }}
        >
          {microsoftConnect.isPending ? 'Redirecting…' : 'Connect Microsoft'}
        </Button>
      </Stack>
    </Box>
  );
};

export default EmailAccountSettings;
