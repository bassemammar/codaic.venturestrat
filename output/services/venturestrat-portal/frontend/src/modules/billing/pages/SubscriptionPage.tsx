import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Divider from '@mui/material/Divider';
import Snackbar from '@mui/material/Snackbar';
import Stack from '@mui/material/Stack';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ReplayIcon from '@mui/icons-material/Replay';
import { CheckCircle, Shield, Lock } from 'lucide-react';
import type { Plan } from '@bill/types/plan.types';
import type { BillingPeriod } from '../api/billingApi';
import { useAuth } from '../../../auth/AuthProvider';
import { usePlans } from '../hooks/usePlans';
import { useSubscription } from '../hooks/useSubscription';
import { useUsage } from '../hooks/useUsage';
import { useSubscribe } from '../hooks/useSubscribe';
import PlanCards from '../components/PlanCards';
import UsageDashboard from '../components/UsageDashboard';
import PaymentMethodsCard from '../components/PaymentMethodsCard';
import CancelSubscriptionModal from '../components/CancelSubscriptionModal';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  active: 'success',
  trialing: 'info',
  canceling: 'warning',
  past_due: 'warning',
  canceled: 'error',
  unpaid: 'error',
};

function formatDate(iso: string | null): string {
  if (!iso) return '--';
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

// ---------------------------------------------------------------------------
// Billing period toggle options
// ---------------------------------------------------------------------------

interface PeriodOption {
  value: BillingPeriod;
  label: string;
  sublabel?: string;
}

const PERIOD_OPTIONS: PeriodOption[] = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly', sublabel: 'Save 30%' },
  { value: 'annual', label: 'Annually', sublabel: 'Save 50%' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const SubscriptionPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: plans = [], isLoading: plansLoading } = usePlans();
  const { data: subscription, isLoading: subLoading } = useSubscription();
  const { data: usageRecords = [] } = useUsage();
  const { cancel, changePlan } = useSubscribe();

  const [cancelOpen, setCancelOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly');

  const isLoading = plansLoading || subLoading;
  const currentPlan = subscription?.plan ?? null;
  const latestUsage = usageRecords.length > 0 ? usageRecords[0] : null;

  // Subscription is "canceling" if status is 'canceling' or cancel_at_period_end is set
  const isCanceling =
    subscription?.status === 'canceling' || subscription?.cancel_at_period_end === true;

  const handleBillingPeriodChange = (
    _: React.MouseEvent<HTMLElement>,
    newPeriod: BillingPeriod | null,
  ) => {
    // Prevent deselecting all -- always keep one selected
    if (newPeriod !== null) {
      setBillingPeriod(newPeriod);
    }
  };

  const handleSelectPlan = (plan: Plan, period: BillingPeriod) => {
    setError(null);

    if (subscription && (subscription.status === 'active' || subscription.status === 'trialing')) {
      // Change plan (upgrade/downgrade)
      changePlan.mutate(
        { new_plan_id: plan.id },
        {
          onError: (err) => {
            setError(err.message || 'Failed to change plan');
          },
        },
      );
    } else {
      // New subscription -- redirect to payment page with period
      navigate(`/billing/payment?plan_id=${plan.id}&billing_period=${period}`);
    }
  };

  const handleCancelConfirm = (cancelAtPeriodEnd: boolean) => {
    setError(null);
    cancel.mutate(
      {
        subscription_id: subscription?.id,
        cancel_at_period_end: cancelAtPeriodEnd,
      },
      {
        onSuccess: () => {
          setCancelOpen(false);
          setSuccessMsg(
            cancelAtPeriodEnd
              ? `Your subscription will end on ${formatDate(subscription?.current_period_end ?? null)}. You'll retain access until then.`
              : 'Your subscription has been cancelled.',
          );
        },
        onError: (err) => {
          setError(err.message || 'Failed to cancel subscription');
          setCancelOpen(false);
        },
      },
    );
  };

  const handleReactivate = () => {
    if (!subscription) return;
    setError(null);
    // Reactivate by re-applying the same plan, which clears the cancel flag
    changePlan.mutate(
      { new_plan_id: subscription.plan_id },
      {
        onSuccess: () => setSuccessMsg('Your subscription has been reactivated.'),
        onError: (err) => {
          setError(err.message || 'Failed to reactivate subscription');
        },
      },
    );
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: { xs: 2, md: 4 } }}>
      {/* Page breadcrumb */}
      <Typography variant="body2" sx={{ color: '#6b7280', mb: 1 }}>
        Home &gt; Subscription
      </Typography>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
        Subscription
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Canceling-state warning banner */}
      {isCanceling && subscription && (
        <Alert
          severity="warning"
          sx={{ mb: 3, bgcolor: 'rgba(237,108,2,0.1)', border: '1px solid rgba(237,108,2,0.3)' }}
          action={
            <Button
              size="small"
              startIcon={<ReplayIcon />}
              onClick={handleReactivate}
              disabled={changePlan.isPending}
              sx={{ color: '#ed6c02', whiteSpace: 'nowrap' }}
            >
              Reactivate
            </Button>
          }
        >
          Your{' '}
          <Box component="span" sx={{ fontWeight: 700 }}>
            {currentPlan?.name ?? 'subscription'}
          </Box>{' '}
          subscription will end on{' '}
          <Box component="span" sx={{ fontWeight: 700 }}>
            {formatDate(subscription.current_period_end)}
          </Box>
          . You'll retain access until then.
        </Alert>
      )}

      {/* Current subscription status */}
      <Paper
        sx={{
          p: 3,
          mb: 4,
          bgcolor: '#ffffff',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={3}
          sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
        >
          <Box>
            <Typography variant="overline" sx={{ color: '#6b7280' }}>
              Current Plan
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mt: 0.5 }}>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {currentPlan?.name ?? 'No active plan'}
              </Typography>
              {subscription && (
                <Chip
                  label={subscription.status}
                  size="small"
                  color={STATUS_COLORS[subscription.status] ?? 'default'}
                  variant="outlined"
                />
              )}
            </Box>
            {subscription?.current_period_end && (
              <Typography variant="body2" sx={{ color: '#6b7280', mt: 0.5 }}>
                {subscription.cancel_at_period_end
                  ? `Cancels on ${formatDate(subscription.current_period_end)}`
                  : `Renews on ${formatDate(subscription.current_period_end)}`}
              </Typography>
            )}
          </Box>

          {/* Only show cancel button when active/trialing and not already canceling */}
          {subscription &&
            (subscription.status === 'active' || subscription.status === 'trialing') &&
            !isCanceling && (
              <Button
                variant="text"
                size="small"
                onClick={() => setCancelOpen(true)}
                disabled={cancel.isPending}
                sx={{
                  color: '#6b7280',
                  fontSize: '0.75rem',
                  textDecoration: 'underline',
                  textDecorationColor: 'rgba(136,153,170,0.4)',
                  '&:hover': {
                    color: '#f44336',
                    textDecorationColor: '#f44336',
                    bgcolor: 'transparent',
                  },
                }}
              >
                Cancel subscription
              </Button>
            )}
        </Stack>
      </Paper>

      {/* Usage dashboard */}
      {currentPlan && (
        <>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Usage
          </Typography>
          <Box sx={{ mb: 4 }}>
            <UsageDashboard
              usage={latestUsage}
              limits={currentPlan.limits ?? {}}
            />
          </Box>
        </>
      )}

      <Divider sx={{ my: 4, borderColor: 'rgba(255,255,255,0.06)' }} />

      {/* Hero section */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography
          variant="h4"
          sx={{ fontWeight: 800, mb: 1.5, color: '#374151', fontSize: { xs: '1.5rem', md: '2rem' } }}
        >
          Unlock Full Access to Investors and Outreach Tools
        </Typography>
        <Typography
          variant="body1"
          sx={{ color: '#6b7280', maxWidth: 600, mx: 'auto', fontSize: '1rem', lineHeight: 1.6 }}
        >
          Choose a plan that matches your fundraising stage. Upgrade instantly &mdash; no interruptions.
        </Typography>
      </Box>

      {/* Billing period toggle - centered */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
        <ToggleButtonGroup
          value={billingPeriod}
          exclusive
          onChange={handleBillingPeriodChange}
          size="small"
          sx={{
            bgcolor: '#071828',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 2,
            p: 0.25,
            '& .MuiToggleButton-root': {
              border: 'none',
              borderRadius: '6px !important',
              px: 2.5,
              py: 0.75,
              color: '#6b7280',
              fontWeight: 500,
              fontSize: '0.85rem',
              textTransform: 'none',
              lineHeight: 1.3,
              transition: 'background-color 0.15s, color 0.15s',
              '&:hover': {
                bgcolor: 'rgba(79,195,247,0.08)',
                color: '#c0cad5',
              },
              '&.Mui-selected': {
                bgcolor: '#1565c0',
                color: '#fff',
                fontWeight: 600,
                '&:hover': {
                  bgcolor: '#1565c0',
                },
              },
            },
          }}
        >
          {PERIOD_OPTIONS.map((opt) => (
            <ToggleButton key={opt.value} value={opt.value}>
              <Box sx={{ textAlign: 'center' }}>
                <Box>{opt.label}</Box>
                {opt.sublabel && (
                  <Box
                    sx={{
                      fontSize: '0.68rem',
                      color: billingPeriod === opt.value ? 'rgba(255,255,255,0.85)' : '#66bb6a',
                      fontWeight: 600,
                    }}
                  >
                    {opt.sublabel}
                  </Box>
                )}
              </Box>
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      <PlanCards
        plans={plans}
        currentPlanId={currentPlan?.id ?? null}
        currentPrice={currentPlan?.price_monthly ?? 0}
        billingPeriod={billingPeriod}
        onSelect={handleSelectPlan}
        loading={changePlan.isPending}
      />

      {/* Free trial note */}
      <Typography
        variant="body2"
        sx={{ textAlign: 'center', color: '#6b7280', mt: 3, mb: 2, fontSize: '0.85rem' }}
      >
        All plans include a 3 day free trial
      </Typography>

      {/* Trust footer */}
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={3}
        sx={{
          justifyContent: 'center',
          alignItems: 'center',
          mt: 2,
          mb: 4,
          py: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CheckCircle size={16} color="#4caf50" />
          <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '0.85rem' }}>
            No hidden fees. Cancel anytime.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Shield size={16} color="#4caf50" />
          <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '0.85rem' }}>
            Secure checkout powered by Stripe
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Lock size={16} color="#4caf50" />
          <Typography variant="body2" sx={{ color: '#6b7280', fontSize: '0.85rem' }}>
            Your data stays private &mdash; always.
          </Typography>
        </Box>
      </Stack>

      {/* Payment methods */}
      <Divider sx={{ my: 4, borderColor: 'rgba(255,255,255,0.06)' }} />
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
        Payment Methods
      </Typography>
      {user?.id && (
        <Box sx={{ mb: 4 }}>
          <PaymentMethodsCard userId={user.id} />
        </Box>
      )}

      {/* Billing history placeholder */}
      <Divider sx={{ my: 4, borderColor: 'rgba(255,255,255,0.06)' }} />
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
        Billing History
      </Typography>
      <Paper
        sx={{
          p: 4,
          bgcolor: '#ffffff',
          border: '1px solid rgba(255,255,255,0.08)',
          textAlign: 'center',
        }}
      >
        <Typography variant="body2" sx={{ color: '#6b7280' }}>
          Billing history will be available soon.
        </Typography>
      </Paper>

      {/* Cancel subscription modal */}
      <CancelSubscriptionModal
        open={cancelOpen}
        planName={currentPlan?.name ?? 'your plan'}
        currentPeriodEnd={subscription?.current_period_end ?? null}
        isPending={cancel.isPending}
        onClose={() => setCancelOpen(false)}
        onConfirm={handleCancelConfirm}
      />

      {/* Success snackbar */}
      <Snackbar
        open={!!successMsg}
        autoHideDuration={6000}
        onClose={() => setSuccessMsg(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity="success"
          variant="filled"
          onClose={() => setSuccessMsg(null)}
          sx={{ width: '100%' }}
        >
          {successMsg}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SubscriptionPage;
