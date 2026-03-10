/**
 * FollowUpTimeline — compact timeline displayed below a sent email in view mode.
 *
 * Shows scheduled, sent, and canceled follow-ups with cancel/reschedule actions.
 */

import React, { useCallback } from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { CancelOutlined, CheckCircleOutline, Schedule } from '@mui/icons-material';
import { format } from 'date-fns';

import { useGetFollowUps, useCancelFollowUp } from '../hooks/useFollowUps';
import type { FollowUp } from '../api/outreachApi';

interface FollowUpTimelineProps {
  messageId: string;
}

const STATUS_COLORS: Record<FollowUp['status'], string> = {
  scheduled: '#ff9800',
  sent: '#4f7df9',
  canceled: '#546e7a',
};

const STATUS_ICONS: Record<FollowUp['status'], React.ReactNode> = {
  scheduled: <Schedule sx={{ fontSize: 12 }} />,
  sent: <CheckCircleOutline sx={{ fontSize: 12 }} />,
  canceled: <CancelOutlined sx={{ fontSize: 12 }} />,
};

export const FollowUpTimeline: React.FC<FollowUpTimelineProps> = ({ messageId }) => {
  const { data: followUps, isLoading } = useGetFollowUps(messageId);
  const { mutate: cancelFollowUp, isPending: isCanceling } = useCancelFollowUp();

  const handleCancel = useCallback(
    (followUpId: string) => {
      cancelFollowUp({ followUpId, messageId });
    },
    [cancelFollowUp, messageId],
  );

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1 }}>
        <CircularProgress size={12} />
        <Typography variant="caption" sx={{ color: '#546e7a' }}>
          Loading follow-ups…
        </Typography>
      </Box>
    );
  }

  if (!followUps || followUps.length === 0) return null;

  return (
    <Box
      sx={{
        px: 2,
        py: 1.5,
        borderTop: '1px solid #1a2e42',
        bgcolor: 'rgba(21, 101, 192, 0.04)',
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: '#546e7a',
          fontWeight: 600,
          fontSize: '0.68rem',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          display: 'block',
          mb: 1,
        }}
      >
        Follow-up Sequence
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
        {followUps.map((fu, index) => (
          <Box
            key={fu.id}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              position: 'relative',
            }}
          >
            {/* Connecting line */}
            {index < followUps.length - 1 && (
              <Box
                sx={{
                  position: 'absolute',
                  left: 9,
                  top: 20,
                  width: 2,
                  height: 'calc(100% + 4px)',
                  bgcolor: '#1a2e42',
                  zIndex: 0,
                }}
              />
            )}

            {/* Status dot */}
            <Box
              sx={{
                width: 20,
                height: 20,
                borderRadius: '50%',
                bgcolor: STATUS_COLORS[fu.status],
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                opacity: fu.status === 'canceled' ? 0.5 : 1,
                zIndex: 1,
                color: '#fff',
              }}
            >
              {STATUS_ICONS[fu.status]}
            </Box>

            {/* Content */}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                <Typography
                  variant="caption"
                  sx={{
                    color: fu.status === 'canceled' ? '#546e7a' : '#b0bec5',
                    fontSize: '0.75rem',
                    textDecoration: fu.status === 'canceled' ? 'line-through' : 'none',
                  }}
                >
                  Follow-up #{fu.sequence_number} — {fu.delay_days} day{fu.delay_days !== 1 ? 's' : ''} after send
                </Typography>

                {fu.scheduled_at && fu.status !== 'canceled' && (
                  <Chip
                    label={format(new Date(fu.scheduled_at), 'MMM d')}
                    size="small"
                    sx={{
                      height: 16,
                      fontSize: '0.65rem',
                      bgcolor: `${STATUS_COLORS[fu.status]}22`,
                      color: STATUS_COLORS[fu.status],
                      border: `1px solid ${STATUS_COLORS[fu.status]}44`,
                    }}
                  />
                )}
              </Box>
            </Box>

            {/* Cancel action */}
            {fu.status === 'scheduled' && (
              <Tooltip title="Cancel this follow-up">
                <IconButton
                  size="small"
                  onClick={() => handleCancel(fu.id)}
                  disabled={isCanceling}
                  sx={{
                    color: '#546e7a',
                    p: 0.5,
                    '&:hover': { color: '#ef5350' },
                  }}
                >
                  <CancelOutlined sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default FollowUpTimeline;
