import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Chip from '@mui/material/Chip';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, TrendingUp } from 'lucide-react';

// Simple map of next-tier recommendations by current plan code
const UPGRADE_MAP: Record<string, { label: string; description: string }> = {
  free: { label: 'Starter', description: 'Unlock more investor views and contact exports.' },
  starter: { label: 'Pro', description: 'Get unlimited investor views and priority support.' },
  pro: { label: 'Scale', description: 'Unlock enterprise features and dedicated support.' },
};

interface SubscriptionLimitModalProps {
  open: boolean;
  onClose: () => void;
  limitType: string;
  current: number;
  limit: number;
  planName: string;
  planCode?: string | null;
}

const SubscriptionLimitModal: React.FC<SubscriptionLimitModalProps> = ({
  open,
  onClose,
  limitType,
  current,
  limit,
  planName,
  planCode,
}) => {
  const navigate = useNavigate();
  const progress = limit > 0 ? Math.min((current / limit) * 100, 100) : 100;

  const friendlyLimitName = limitType
    .replace(/_/g, ' ')
    .replace(/\bper\b/g, '/')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const upgrade = planCode ? UPGRADE_MAP[planCode.toLowerCase()] : null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            bgcolor: '#ffffff',
            border: '1px solid rgba(255, 152, 0, 0.3)',
            borderRadius: 2,
          },
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          color: '#374151',
          pb: 1,
        }}
      >
        <AlertTriangle size={22} color="#ff9800" />
        Plan Limit Reached
      </DialogTitle>

      <DialogContent>
        <Typography variant="body2" sx={{ color: '#6b7280', mb: 2 }}>
          You have reached the{' '}
          <strong style={{ color: '#374151' }}>{friendlyLimitName}</strong> limit on
          your <strong style={{ color: '#4f7df9' }}>{planName}</strong> plan.
        </Typography>

        {/* Usage bar */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#6b7280' }}>
              Usage
            </Typography>
            <Typography variant="caption" sx={{ color: '#374151', fontWeight: 600 }}>
              {current.toLocaleString()} / {limit.toLocaleString()}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: 'rgba(79, 195, 247, 0.1)',
              '& .MuiLinearProgress-bar': {
                bgcolor: progress >= 100 ? '#f44336' : '#ff9800',
                borderRadius: 4,
              },
            }}
          />
          <Typography variant="caption" sx={{ color: '#6b7d8e', mt: 0.5, display: 'block' }}>
            You've used {current.toLocaleString()} of your {limit.toLocaleString()}{' '}
            {friendlyLimitName.toLowerCase()} allowance.
          </Typography>
        </Box>

        {/* Upgrade recommendation */}
        {upgrade && (
          <Box
            sx={{
              p: 1.5,
              borderRadius: 1.5,
              bgcolor: 'rgba(79, 195, 247, 0.06)',
              border: '1px solid rgba(79, 195, 247, 0.14)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1.25,
            }}
          >
            <TrendingUp size={16} color="#4f7df9" style={{ marginTop: 2, flexShrink: 0 }} />
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
                <Typography variant="caption" sx={{ color: '#374151', fontWeight: 600 }}>
                  Upgrade to {upgrade.label}
                </Typography>
                <Chip
                  label="Recommended"
                  size="small"
                  sx={{
                    height: 16,
                    fontSize: '0.6rem',
                    bgcolor: 'rgba(79, 195, 247, 0.15)',
                    color: '#4f7df9',
                    '& .MuiChip-label': { px: 0.75 },
                  }}
                />
              </Box>
              <Typography variant="caption" sx={{ color: '#6b7280' }}>
                {upgrade.description}
              </Typography>
            </Box>
          </Box>
        )}

        {!upgrade && (
          <Typography variant="body2" sx={{ color: '#6b7280' }}>
            Upgrade your plan to increase your limits and unlock more features.
          </Typography>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2, gap: 1 }}>
        <Button
          onClick={onClose}
          sx={{ color: '#6b7280', textTransform: 'none' }}
        >
          Close
        </Button>
        <Button
          variant="contained"
          onClick={() => {
            onClose();
            navigate('/billing/subscription');
          }}
          sx={{
            textTransform: 'none',
            bgcolor: '#4f7df9',
            color: '#f9fafb',
            fontWeight: 600,
            '&:hover': { bgcolor: '#81d4fa' },
          }}
        >
          Upgrade Plan
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SubscriptionLimitModal;
