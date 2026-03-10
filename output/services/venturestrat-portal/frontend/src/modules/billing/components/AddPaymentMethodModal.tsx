import React, { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { createSetupIntent } from '../api/billingApi';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AddPaymentMethodModalProps {
  open: boolean;
  userId: string;
  onClose: () => void;
  onSuccess: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCardNumber(value: string): string {
  // Keep only digits, group in sets of 4
  const digits = value.replace(/\D/g, '').slice(0, 16);
  return digits.replace(/(.{4})/g, '$1 ').trim();
}

function formatExpiry(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 4);
  if (digits.length > 2) {
    return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  }
  return digits;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const AddPaymentMethodModal: React.FC<AddPaymentMethodModalProps> = ({
  open,
  userId,
  onClose,
  onSuccess,
}) => {
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [cardHolder, setCardHolder] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    if (submitting) return;
    setCardNumber('');
    setExpiry('');
    setCvc('');
    setCardHolder('');
    setError(null);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Basic validation
    const rawDigits = cardNumber.replace(/\s/g, '');
    if (rawDigits.length < 13) {
      setError('Please enter a valid card number.');
      return;
    }
    if (expiry.length < 5) {
      setError('Please enter a valid expiry date (MM/YY).');
      return;
    }
    if (cvc.length < 3) {
      setError('Please enter a valid CVC.');
      return;
    }
    if (!cardHolder.trim()) {
      setError('Please enter the cardholder name.');
      return;
    }

    setSubmitting(true);
    try {
      const { client_secret } = await createSetupIntent(userId);

      // If we got a mock secret, Stripe is not configured — show notice and close
      if (client_secret.startsWith('seti_mock_')) {
        setError(
          'Payment processing will be configured during deployment. ' +
          'Your card information has not been saved.',
        );
        setSubmitting(false);
        return;
      }

      // With real Stripe keys, use Stripe.js to confirm the SetupIntent.
      // Stripe.js is loaded lazily — if not present, show a helpful message.
      const stripeJs = (window as any).Stripe;
      if (!stripeJs) {
        setError(
          'Stripe.js is not loaded. Please ensure Stripe is configured and ' +
          'the publishable key is set.',
        );
        setSubmitting(false);
        return;
      }

      const [expMonth, expYear] = expiry.split('/');
      const stripe = stripeJs(
        (window as any).__STRIPE_PUBLISHABLE_KEY__ || '',
      );

      const { error: stripeError } = await stripe.confirmCardSetup(
        client_secret,
        {
          payment_method: {
            card: {
              number: rawDigits,
              exp_month: parseInt(expMonth, 10),
              exp_year: parseInt(`20${expYear}`, 10),
              cvc,
            },
            billing_details: { name: cardHolder },
          },
        },
      );

      if (stripeError) {
        setError(stripeError.message ?? 'Failed to add card.');
        setSubmitting(false);
        return;
      }

      onSuccess();
      handleClose();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to add payment method.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#ffffff',
          backgroundImage: 'none',
          border: '1px solid #e5e7eb',
        },
      }}
    >
      <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>
        Add Payment Method
      </DialogTitle>

      <form onSubmit={handleSubmit}>
        <DialogContent sx={{ pt: 1 }}>
          <Alert
            severity="info"
            variant="outlined"
            sx={{ mb: 2, fontSize: '0.8rem', borderColor: '#e5e7eb', color: '#6b7280' }}
          >
            Payment processing will be configured during deployment. Card data
            is only stored by Stripe — never on our servers.
          </Alert>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Stack spacing={2}>
            <TextField
              label="Cardholder Name"
              value={cardHolder}
              onChange={(e) => setCardHolder(e.target.value)}
              placeholder="Jane Smith"
              fullWidth
              autoComplete="cc-name"
              inputProps={{ maxLength: 60 }}
              sx={fieldSx}
            />

            <TextField
              label="Card Number"
              value={cardNumber}
              onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
              placeholder="4242 4242 4242 4242"
              fullWidth
              autoComplete="cc-number"
              inputProps={{ inputMode: 'numeric', maxLength: 19 }}
              sx={fieldSx}
            />

            <Stack direction="row" spacing={2}>
              <TextField
                label="Expiry (MM/YY)"
                value={expiry}
                onChange={(e) => setExpiry(formatExpiry(e.target.value))}
                placeholder="12/27"
                autoComplete="cc-exp"
                inputProps={{ inputMode: 'numeric', maxLength: 5 }}
                sx={{ ...fieldSx, flex: 1 }}
              />
              <TextField
                label="CVC"
                value={cvc}
                onChange={(e) => setCvc(e.target.value.replace(/\D/g, '').slice(0, 4))}
                placeholder="123"
                autoComplete="cc-csc"
                inputProps={{ inputMode: 'numeric', maxLength: 4 }}
                sx={{ ...fieldSx, flex: 1 }}
              />
            </Stack>
          </Stack>

          <Typography variant="caption" sx={{ color: '#6b7280', mt: 1.5, display: 'block' }}>
            Your card information is encrypted and processed securely by Stripe.
          </Typography>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
          <Button
            onClick={handleClose}
            disabled={submitting}
            sx={{ color: '#6b7280' }}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={submitting}
            sx={{
              bgcolor: '#4f7df9',
              color: '#f9fafb',
              fontWeight: 600,
              '&:hover': { bgcolor: '#4f7df9', opacity: 0.9 },
              '&.Mui-disabled': { opacity: 0.5 },
            }}
          >
            {submitting ? (
              <>
                <CircularProgress size={14} sx={{ mr: 1, color: '#f9fafb' }} />
                Saving...
              </>
            ) : (
              'Add Card'
            )}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

// ---------------------------------------------------------------------------
// Shared field styling
// ---------------------------------------------------------------------------

const fieldSx = {
  '& .MuiOutlinedInput-root': {
    color: '#374151',
    '& fieldset': { borderColor: '#e5e7eb' },
    '&:hover fieldset': { borderColor: '#4f7df9' },
    '&.Mui-focused fieldset': { borderColor: '#4f7df9' },
  },
  '& .MuiInputLabel-root': { color: '#6b7280' },
  '& .MuiInputLabel-root.Mui-focused': { color: '#4f7df9' },
};

export default AddPaymentMethodModal;
