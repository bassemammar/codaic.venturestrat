import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Typography from '@mui/material/Typography';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface CancelSubscriptionModalProps {
  open: boolean;
  planName: string;
  currentPeriodEnd: string | null;
  isPending: boolean;
  onClose: () => void;
  onConfirm: (cancelAtPeriodEnd: boolean) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string | null): string {
  if (!iso) return 'the end of your billing period';
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const CancelSubscriptionModal: React.FC<CancelSubscriptionModalProps> = ({
  open,
  planName,
  currentPeriodEnd,
  isPending,
  onClose,
  onConfirm,
}) => {
  const [cancelMode, setCancelMode] = useState<'period_end' | 'immediate'>('period_end');

  const handleConfirm = () => {
    onConfirm(cancelMode === 'period_end');
  };

  const handleClose = () => {
    // Reset choice when closing so it defaults to safe option next time
    setCancelMode('period_end');
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#ffffff',
          backgroundImage: 'none',
          border: '1px solid #e5e7eb',
          borderRadius: 2,
        },
      }}
    >
      {/* Title */}
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          pb: 1,
          color: '#ffffff',
        }}
      >
        <WarningAmberIcon sx={{ color: '#f44336', fontSize: 24 }} />
        Cancel Subscription
      </DialogTitle>

      {/* Body */}
      <DialogContent>
        <Typography variant="body1" sx={{ color: '#c0cad5', mb: 3 }}>
          Are you sure you want to cancel your{' '}
          <Box component="span" sx={{ color: '#ffffff', fontWeight: 600 }}>
            {planName}
          </Box>{' '}
          subscription?
        </Typography>

        {/* Cancellation mode options */}
        <FormControl component="fieldset" sx={{ width: '100%' }}>
          <RadioGroup
            value={cancelMode}
            onChange={(e) => setCancelMode(e.target.value as 'period_end' | 'immediate')}
          >
            {/* Recommended — cancel at period end */}
            <Box
              sx={{
                border: '1px solid',
                borderColor: cancelMode === 'period_end' ? '#1565c0' : 'rgba(255,255,255,0.1)',
                borderRadius: 1.5,
                px: 2,
                py: 1.5,
                mb: 1.5,
                cursor: 'pointer',
                transition: 'border-color 0.15s',
                '&:hover': { borderColor: '#1565c0' },
              }}
              onClick={() => setCancelMode('period_end')}
            >
              <FormControlLabel
                value="period_end"
                control={<Radio sx={{ color: '#1565c0', '&.Mui-checked': { color: '#1976d2' } }} />}
                label={
                  <Box>
                    <Typography variant="body2" sx={{ color: '#ffffff', fontWeight: 600 }}>
                      Cancel at end of billing period{' '}
                      <Box
                        component="span"
                        sx={{
                          ml: 1,
                          px: 0.75,
                          py: 0.25,
                          bgcolor: 'rgba(25, 118, 210, 0.15)',
                          color: '#42a5f5',
                          borderRadius: 0.75,
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          verticalAlign: 'middle',
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                        }}
                      >
                        Recommended
                      </Box>
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      You keep full access until {formatDate(currentPeriodEnd)}, then your plan is
                      cancelled.
                    </Typography>
                  </Box>
                }
                sx={{ m: 0, alignItems: 'flex-start' }}
              />
            </Box>

            {/* Immediate cancellation */}
            <Box
              sx={{
                border: '1px solid',
                borderColor: cancelMode === 'immediate' ? '#c62828' : 'rgba(255,255,255,0.1)',
                borderRadius: 1.5,
                px: 2,
                py: 1.5,
                cursor: 'pointer',
                transition: 'border-color 0.15s',
                '&:hover': { borderColor: '#c62828' },
              }}
              onClick={() => setCancelMode('immediate')}
            >
              <FormControlLabel
                value="immediate"
                control={<Radio sx={{ color: '#c62828', '&.Mui-checked': { color: '#f44336' } }} />}
                label={
                  <Box>
                    <Typography variant="body2" sx={{ color: '#ffffff', fontWeight: 600 }}>
                      Cancel immediately
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      Your access ends right now. This action cannot be undone.
                    </Typography>
                  </Box>
                }
                sx={{ m: 0, alignItems: 'flex-start' }}
              />
            </Box>
          </RadioGroup>
        </FormControl>
      </DialogContent>

      {/* Actions */}
      <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
        <Button
          variant="outlined"
          onClick={handleClose}
          disabled={isPending}
          sx={{
            borderColor: 'rgba(255,255,255,0.2)',
            color: '#c0cad5',
            '&:hover': { borderColor: 'rgba(255,255,255,0.4)', bgcolor: 'rgba(255,255,255,0.05)' },
          }}
        >
          Keep Subscription
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={isPending}
          sx={{
            bgcolor: '#c62828',
            color: '#ffffff',
            '&:hover': { bgcolor: '#b71c1c' },
            '&:disabled': { bgcolor: 'rgba(198,40,40,0.4)', color: 'rgba(255,255,255,0.5)' },
          }}
        >
          {isPending ? 'Cancelling…' : 'Confirm Cancellation'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CancelSubscriptionModal;
