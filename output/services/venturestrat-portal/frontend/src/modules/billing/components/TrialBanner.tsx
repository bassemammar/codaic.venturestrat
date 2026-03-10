import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import { X, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useSubscriptionStatus } from '../../investor/hooks/useSubscriptionStatus';

const SESSION_DISMISS_KEY = 'trial_banner_dismissed';

interface TrialBannerProps {
  /** Called after the user dismisses the banner, so parent can update layout offsets */
  onDismiss?: () => void;
}

const TrialBanner: React.FC<TrialBannerProps> = ({ onDismiss }) => {
  const navigate = useNavigate();
  const { data: sub } = useSubscriptionStatus();
  const [dismissed, setDismissed] = useState<boolean>(
    () => sessionStorage.getItem(SESSION_DISMISS_KEY) === '1',
  );

  if (!sub?.isTrialing || dismissed) return null;

  const days = sub.daysRemaining ?? 0;
  const isUrgent = days <= 3;

  const handleDismiss = () => {
    sessionStorage.setItem(SESSION_DISMISS_KEY, '1');
    setDismissed(true);
    onDismiss?.();
  };

  const handleUpgrade = () => {
    navigate('/billing/subscription');
  };

  return (
    <Box
      sx={{
        height: 36,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        px: 2,
        gap: 1.5,
        bgcolor: isUrgent
          ? 'rgba(255, 152, 0, 0.15)'
          : 'rgba(30, 58, 95, 0.9)',
        borderBottom: `1px solid ${
          isUrgent ? 'rgba(255, 152, 0, 0.35)' : 'rgba(79, 195, 247, 0.18)'
        }`,
      }}
    >
      <Clock
        size={14}
        color={isUrgent ? '#ff9800' : '#4f7df9'}
        style={{ flexShrink: 0 }}
      />

      <Typography
        variant="caption"
        sx={{
          color: isUrgent ? '#ffb74d' : '#b0c4d8',
          fontWeight: 500,
          lineHeight: 1,
        }}
      >
        {days === 0
          ? 'Your free trial ends today'
          : `You have ${days} day${days === 1 ? '' : 's'} left in your free trial`}
      </Typography>

      <Button
        size="small"
        variant="contained"
        onClick={handleUpgrade}
        sx={{
          height: 22,
          px: 1.5,
          py: 0,
          minWidth: 0,
          textTransform: 'none',
          fontSize: '0.7rem',
          fontWeight: 600,
          lineHeight: 1,
          bgcolor: isUrgent ? '#ff9800' : '#4f7df9',
          color: '#f9fafb',
          '&:hover': {
            bgcolor: isUrgent ? '#ffa726' : '#81d4fa',
          },
        }}
      >
        Upgrade Now
      </Button>

      <IconButton
        size="small"
        onClick={handleDismiss}
        sx={{
          p: 0.25,
          ml: 0.5,
          color: isUrgent ? '#ff9800' : '#4f7df9',
          '&:hover': { bgcolor: 'rgba(255,255,255,0.06)' },
        }}
        aria-label="Dismiss trial banner"
      >
        <X size={13} />
      </IconButton>
    </Box>
  );
};

export default TrialBanner;
