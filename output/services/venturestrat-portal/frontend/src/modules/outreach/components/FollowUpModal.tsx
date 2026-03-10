/**
 * FollowUpModal — schedule a follow-up email sequence after sending.
 *
 * Features:
 *   - Vertical timeline showing each follow-up step
 *   - Editable delay (days) per step
 *   - Add / remove steps (max 5)
 *   - Body template textarea with {name} / {company} placeholder hints
 *   - Live preview of absolute send dates
 *   - "Schedule Follow-ups" and "Skip" actions
 */

import React, { useState, useCallback, useMemo } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import TextField from '@mui/material/TextField';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { Add, Close, DeleteOutline, Email, Schedule } from '@mui/icons-material';
import { format, addDays } from 'date-fns';

import { useScheduleFollowUps } from '../hooks/useFollowUps';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FollowUpStep {
  /** Internal key for React list rendering */
  key: number;
  delay_days: number;
}

export interface FollowUpModalProps {
  open: boolean;
  /** ID of the message that was just sent */
  messageId: string | null;
  /** ISO timestamp of when the original message was sent */
  sentAt?: string | null;
  /** The original subject line (used to build the follow-up subject) */
  originalSubject?: string;
  onClose: () => void;
  /** Called after the sequence is successfully scheduled */
  onScheduled?: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_DELAYS = [3, 5, 7];
const MAX_STEPS = 5;
const DEFAULT_BODY_TEMPLATE =
  'Hi {name},\n\nJust following up on my previous email. I wanted to make sure it didn\'t get lost in your inbox.\n\nWould love to connect and learn more about your perspective on this opportunity.\n\nBest,';
const DEFAULT_SUBJECT_PREFIX = 'Re: ';

// ---------------------------------------------------------------------------
// Sub-component: TimelineStep
// ---------------------------------------------------------------------------

interface TimelineStepProps {
  index: number;
  step: FollowUpStep;
  sentAt: Date | null;
  isLast: boolean;
  onDelayChange: (key: number, value: number) => void;
  onRemove: (key: number) => void;
  canRemove: boolean;
}

const TimelineStep: React.FC<TimelineStepProps> = ({
  index,
  step,
  sentAt,
  isLast,
  onDelayChange,
  onRemove,
  canRemove,
}) => {
  const sendDate = sentAt ? addDays(sentAt, step.delay_days) : null;

  return (
    <Box sx={{ display: 'flex', gap: 1.5, position: 'relative' }}>
      {/* Vertical timeline line */}
      {!isLast && (
        <Box
          sx={{
            position: 'absolute',
            left: 11,
            top: 24,
            width: 2,
            height: 'calc(100% + 8px)',
            bgcolor: '#e5e7eb',
          }}
        />
      )}

      {/* Timeline dot */}
      <Box
        sx={{
          width: 24,
          height: 24,
          borderRadius: '50%',
          bgcolor: step.delay_days > 0 ? '#1565c0' : '#455a64',
          border: '2px solid',
          borderColor: step.delay_days > 0 ? '#42a5f5' : '#546e7a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          mt: 0.5,
          zIndex: 1,
        }}
      >
        <Email sx={{ fontSize: 12, color: '#fff' }} />
      </Box>

      {/* Step content */}
      <Box
        sx={{
          flex: 1,
          mb: isLast ? 0 : 1,
          pb: isLast ? 0 : 1,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Typography
            variant="caption"
            sx={{ color: '#6b7280', fontWeight: 600, fontSize: '0.7rem' }}
          >
            FOLLOW-UP #{index + 1}
          </Typography>

          {sendDate && (
            <Typography
              variant="caption"
              sx={{
                color: '#42a5f5',
                fontSize: '0.7rem',
                bgcolor: 'rgba(66, 165, 245, 0.1)',
                px: 0.75,
                py: 0.25,
                borderRadius: 1,
              }}
            >
              {format(sendDate, 'MMM d, yyyy')}
            </Typography>
          )}

          <Box sx={{ flex: 1 }} />

          {canRemove && (
            <Tooltip title="Remove this follow-up">
              <IconButton
                size="small"
                onClick={() => onRemove(step.key)}
                sx={{ color: '#546e7a', '&:hover': { color: '#ef5350' } }}
              >
                <DeleteOutline fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextField
            type="number"
            size="small"
            value={step.delay_days}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              if (!isNaN(val) && val >= 1 && val <= 365) {
                onDelayChange(step.key, val);
              }
            }}
            inputProps={{ min: 1, max: 365, style: { textAlign: 'center', width: 48 } }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <Typography variant="caption" sx={{ color: '#6b7280' }}>
                    days after send
                  </Typography>
                </InputAdornment>
              ),
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                bgcolor: 'rgba(255,255,255,0.04)',
                '& fieldset': { borderColor: '#e5e7eb' },
                '&:hover fieldset': { borderColor: '#42a5f5' },
                '&.Mui-focused fieldset': { borderColor: '#42a5f5' },
              },
              '& .MuiInputBase-input': { color: '#e3f2fd', fontSize: '0.875rem' },
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

let nextKey = 100;

export const FollowUpModal: React.FC<FollowUpModalProps> = ({
  open,
  messageId,
  sentAt,
  originalSubject = '',
  onClose,
  onScheduled,
}) => {
  const [steps, setSteps] = useState<FollowUpStep[]>(() =>
    DEFAULT_DELAYS.map((d) => ({ key: nextKey++, delay_days: d })),
  );
  const [bodyTemplate, setBodyTemplate] = useState(DEFAULT_BODY_TEMPLATE);

  const { mutate: scheduleFollowUps, isPending } = useScheduleFollowUps();

  const parsedSentAt = useMemo(() => {
    if (!sentAt) return null;
    try {
      return new Date(sentAt);
    } catch {
      return null;
    }
  }, [sentAt]);

  // Build follow-up subject
  const followUpSubject = useMemo(() => {
    if (!originalSubject) return '';
    return originalSubject.startsWith(DEFAULT_SUBJECT_PREFIX)
      ? originalSubject
      : `${DEFAULT_SUBJECT_PREFIX}${originalSubject}`;
  }, [originalSubject]);

  const handleDelayChange = useCallback((key: number, value: number) => {
    setSteps((prev) =>
      prev.map((s) => (s.key === key ? { ...s, delay_days: value } : s)),
    );
  }, []);

  const handleRemove = useCallback((key: number) => {
    setSteps((prev) => prev.filter((s) => s.key !== key));
  }, []);

  const handleAdd = useCallback(() => {
    setSteps((prev) => {
      if (prev.length >= MAX_STEPS) return prev;
      const lastDelay = prev.length > 0 ? prev[prev.length - 1].delay_days : 0;
      return [...prev, { key: nextKey++, delay_days: lastDelay + 3 }];
    });
  }, []);

  const handleSchedule = useCallback(() => {
    if (!messageId) return;
    scheduleFollowUps(
      {
        messageId,
        data: {
          delays: steps.map((s) => s.delay_days),
          subject_prefix: DEFAULT_SUBJECT_PREFIX,
          body_template: bodyTemplate,
        },
      },
      {
        onSuccess: () => {
          onScheduled?.();
          onClose();
        },
      },
    );
  }, [messageId, steps, bodyTemplate, scheduleFollowUps, onScheduled, onClose]);

  const handleClose = useCallback(() => {
    if (!isPending) onClose();
  }, [isPending, onClose]);

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
          gap: 1,
          p: 2,
          borderBottom: '1px solid #e5e7eb',
        }}
      >
        <Schedule sx={{ color: '#42a5f5', fontSize: 20 }} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, color: '#e3f2fd', lineHeight: 1.2 }}>
            Schedule Follow-ups
          </Typography>
          {followUpSubject && (
            <Typography variant="caption" sx={{ color: '#6b7280' }}>
              {followUpSubject}
            </Typography>
          )}
        </Box>
        <IconButton size="small" onClick={handleClose} sx={{ color: '#6b7280' }}>
          <Close fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 2.5 }}>
        {/* Intro */}
        <Typography variant="body2" sx={{ color: '#6b7280', mb: 2, fontSize: '0.8rem' }}>
          Automatically send follow-up emails after your original message. Each follow-up
          will be sent the specified number of days after your email is sent.
        </Typography>

        {/* Timeline of steps */}
        <Box sx={{ mb: 2 }}>
          {steps.map((step, index) => (
            <TimelineStep
              key={step.key}
              index={index}
              step={step}
              sentAt={parsedSentAt}
              isLast={index === steps.length - 1}
              onDelayChange={handleDelayChange}
              onRemove={handleRemove}
              canRemove={steps.length > 1}
            />
          ))}
        </Box>

        {/* Add follow-up button */}
        {steps.length < MAX_STEPS && (
          <Button
            variant="text"
            size="small"
            startIcon={<Add />}
            onClick={handleAdd}
            sx={{
              color: '#42a5f5',
              textTransform: 'none',
              fontSize: '0.8rem',
              mb: 2,
              px: 0,
            }}
          >
            Add follow-up ({steps.length}/{MAX_STEPS})
          </Button>
        )}

        {/* Divider */}
        <Box sx={{ borderTop: '1px solid #e5e7eb', my: 2 }} />

        {/* Body template */}
        <Typography variant="caption" sx={{ color: '#6b7280', display: 'block', mb: 0.75 }}>
          Body template — use <code style={{ color: '#42a5f5' }}>{'{name}'}</code> and{' '}
          <code style={{ color: '#42a5f5' }}>{'{company}'}</code> as placeholders
        </Typography>
        <TextField
          multiline
          rows={5}
          fullWidth
          value={bodyTemplate}
          onChange={(e) => setBodyTemplate(e.target.value)}
          placeholder="Hi {name}, just following up..."
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: 'rgba(255,255,255,0.03)',
              '& fieldset': { borderColor: '#e5e7eb' },
              '&:hover fieldset': { borderColor: '#2a4a6f' },
              '&.Mui-focused fieldset': { borderColor: '#42a5f5' },
            },
            '& .MuiInputBase-input': {
              color: '#cfd8dc',
              fontSize: '0.8rem',
              lineHeight: 1.6,
            },
          }}
        />

        {/* Preview note */}
        {parsedSentAt && (
          <Typography variant="caption" sx={{ color: '#546e7a', display: 'block', mt: 1 }}>
            Previewing dates based on send time: {format(parsedSentAt, 'MMM d, yyyy h:mm a')}
          </Typography>
        )}
        {!parsedSentAt && (
          <Typography variant="caption" sx={{ color: '#546e7a', display: 'block', mt: 1 }}>
            Exact send dates will be calculated when the original email is delivered.
          </Typography>
        )}
      </DialogContent>

      <DialogActions
        sx={{
          p: 2,
          pt: 0,
          gap: 1,
          borderTop: '1px solid #e5e7eb',
        }}
      >
        <Button
          variant="text"
          size="small"
          onClick={handleClose}
          disabled={isPending}
          sx={{ textTransform: 'none', color: '#6b7280' }}
        >
          Skip
        </Button>

        <Box sx={{ flex: 1 }} />

        <Button
          variant="contained"
          size="small"
          startIcon={
            isPending ? <CircularProgress size={14} color="inherit" /> : <Schedule />
          }
          onClick={handleSchedule}
          disabled={isPending || !messageId || steps.length === 0}
          sx={{
            textTransform: 'none',
            bgcolor: '#1565c0',
            '&:hover': { bgcolor: '#1976d2' },
          }}
        >
          Schedule {steps.length} follow-up{steps.length !== 1 ? 's' : ''}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FollowUpModal;
