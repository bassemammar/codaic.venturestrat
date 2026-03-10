import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import Tooltip from '@mui/material/Tooltip';
import { CreditCard, Trash2, Star } from 'lucide-react';
import {
  getPaymentMethods,
  setDefaultPaymentMethod,
  removePaymentMethod,
  type PaymentMethod,
} from '../api/billingApi';
import AddPaymentMethodModal from './AddPaymentMethodModal';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Return a short brand display label and colour. */
function brandInfo(brand: string): { label: string; color: string } {
  switch (brand.toLowerCase()) {
    case 'visa':        return { label: 'Visa',       color: '#1A1F71' };
    case 'mastercard':  return { label: 'Mastercard', color: '#EB001B' };
    case 'amex':        return { label: 'Amex',       color: '#006FCF' };
    case 'discover':    return { label: 'Discover',   color: '#FF6600' };
    default:            return { label: brand.charAt(0).toUpperCase() + brand.slice(1), color: '#6b7280' };
  }
}

function formatExpiry(month: number, year: number): string {
  return `${String(month).padStart(2, '0')}/${String(year).slice(-2)}`;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PaymentMethodsCardProps {
  userId: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PM_QUERY_KEY = 'payment-methods';

const PaymentMethodsCard: React.FC<PaymentMethodsCardProps> = ({ userId }) => {
  const queryClient = useQueryClient();

  const [addOpen, setAddOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<PaymentMethod | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Fetch payment methods
  const { data: methods = [], isLoading } = useQuery<PaymentMethod[]>({
    queryKey: [PM_QUERY_KEY, userId],
    queryFn: () => getPaymentMethods(userId),
    enabled: !!userId,
    staleTime: 60_000,
  });

  // Set default mutation
  const setDefaultMutation = useMutation({
    mutationFn: (pmId: string) => setDefaultPaymentMethod(userId, pmId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PM_QUERY_KEY, userId] });
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(
        err?.response?.data?.detail || err?.message || 'Failed to update default payment method.',
      );
    },
  });

  // Remove mutation
  const removeMutation = useMutation({
    mutationFn: (pmId: string) => removePaymentMethod(pmId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PM_QUERY_KEY, userId] });
      setRemoveTarget(null);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(
        err?.response?.data?.detail || err?.message || 'Failed to remove payment method.',
      );
      setRemoveTarget(null);
    },
  });

  const handleAddSuccess = () => {
    queryClient.invalidateQueries({ queryKey: [PM_QUERY_KEY, userId] });
    setAddOpen(false);
  };

  const handleConfirmRemove = () => {
    if (!removeTarget) return;
    removeMutation.mutate(removeTarget.id);
  };

  return (
    <>
      <Paper
        sx={{
          bgcolor: '#ffffff',
          border: '1px solid rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            px: 3,
            py: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CreditCard size={18} color="#4f7df9" />
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Saved Cards
            </Typography>
          </Box>
          <Button
            size="small"
            variant="outlined"
            onClick={() => setAddOpen(true)}
            sx={{
              borderColor: '#e5e7eb',
              color: '#4f7df9',
              '&:hover': { borderColor: '#4f7df9', bgcolor: 'rgba(79,195,247,0.08)' },
            }}
          >
            + Add Card
          </Button>
        </Box>

        {/* Error */}
        {actionError && (
          <Alert severity="error" sx={{ mx: 3, mt: 2 }} onClose={() => setActionError(null)}>
            {actionError}
          </Alert>
        )}

        {/* Body */}
        <Box sx={{ px: 3, py: 2 }}>
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
              <CircularProgress size={24} />
            </Box>
          ) : methods.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <CreditCard size={36} color="#2a4a6a" style={{ marginBottom: 8 }} />
              <Typography variant="body2" sx={{ color: '#6b7280' }}>
                No payment methods saved.{' '}
                <Box
                  component="span"
                  sx={{ color: '#4f7df9', cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                  onClick={() => setAddOpen(true)}
                >
                  Add one
                </Box>{' '}
                to subscribe.
              </Typography>
            </Box>
          ) : (
            <Stack divider={<Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />}>
              {methods.map((pm, idx) => {
                const brand = brandInfo(pm.brand);
                const isSettingDefault = setDefaultMutation.isPending &&
                  setDefaultMutation.variables === pm.id;
                const isRemoving = removeMutation.isPending &&
                  removeMutation.variables === pm.id;

                return (
                  <Box
                    key={pm.id}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 2,
                      py: 1.5,
                    }}
                  >
                    {/* Brand badge */}
                    <Box
                      sx={{
                        minWidth: 56,
                        height: 36,
                        borderRadius: 1,
                        bgcolor: '#f9fafb',
                        border: '1px solid #e5e7eb',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 700,
                          fontSize: '0.7rem',
                          color: brand.color,
                          letterSpacing: 0,
                        }}
                      >
                        {brand.label}
                      </Typography>
                    </Box>

                    {/* Card info */}
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="body2" sx={{ color: '#374151', fontWeight: 500 }}>
                          •••• •••• •••• {pm.last4}
                        </Typography>
                        {pm.is_default && (
                          <Chip
                            label="Default"
                            size="small"
                            sx={{
                              bgcolor: 'rgba(79,195,247,0.12)',
                              color: '#4f7df9',
                              borderColor: 'rgba(79,195,247,0.3)',
                              border: '1px solid',
                              height: 18,
                              fontSize: '0.65rem',
                              fontWeight: 600,
                            }}
                          />
                        )}
                      </Box>
                      <Typography variant="caption" sx={{ color: '#6b7280' }}>
                        Expires {formatExpiry(pm.exp_month, pm.exp_year)}
                      </Typography>
                    </Box>

                    {/* Actions */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                      {!pm.is_default && (
                        <Tooltip title="Set as default">
                          <span>
                            <IconButton
                              size="small"
                              onClick={() => setDefaultMutation.mutate(pm.id)}
                              disabled={isSettingDefault || setDefaultMutation.isPending}
                              sx={{ color: '#6b7280', '&:hover': { color: '#4f7df9' } }}
                            >
                              {isSettingDefault ? (
                                <CircularProgress size={14} />
                              ) : (
                                <Star size={14} />
                              )}
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                      <Tooltip title="Remove card">
                        <span>
                          <IconButton
                            size="small"
                            onClick={() => setRemoveTarget(pm)}
                            disabled={isRemoving || removeMutation.isPending}
                            sx={{ color: '#6b7280', '&:hover': { color: '#ef5350' } }}
                          >
                            {isRemoving ? (
                              <CircularProgress size={14} />
                            ) : (
                              <Trash2 size={14} />
                            )}
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Box>
                  </Box>
                );
              })}
            </Stack>
          )}
        </Box>
      </Paper>

      {/* Add payment method modal */}
      <AddPaymentMethodModal
        open={addOpen}
        userId={userId}
        onClose={() => setAddOpen(false)}
        onSuccess={handleAddSuccess}
      />

      {/* Remove confirmation dialog */}
      <Dialog
        open={!!removeTarget}
        onClose={() => setRemoveTarget(null)}
        PaperProps={{
          sx: { bgcolor: '#ffffff', backgroundImage: 'none', border: '1px solid #e5e7eb' },
        }}
      >
        <DialogTitle>Remove Card</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: '#c0cad5' }}>
            Remove the{' '}
            <Box component="span" sx={{ fontWeight: 600, color: '#374151' }}>
              {removeTarget ? brandInfo(removeTarget.brand).label : ''} ending in{' '}
              {removeTarget?.last4}
            </Box>
            ? This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setRemoveTarget(null)}
            disabled={removeMutation.isPending}
            sx={{ color: '#6b7280' }}
          >
            Cancel
          </Button>
          <Button
            color="error"
            onClick={handleConfirmRemove}
            disabled={removeMutation.isPending}
          >
            {removeMutation.isPending ? 'Removing...' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default PaymentMethodsCard;
