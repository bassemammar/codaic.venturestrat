import React from 'react';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Grid from '@mui/material/Grid';
import { CheckCircle } from 'lucide-react';
import type { Plan } from '@bill/types/plan.types';
import type { BillingPeriod } from '../api/billingApi';

// ---------------------------------------------------------------------------
// Plan color mapping
// ---------------------------------------------------------------------------

const PLAN_COLORS: Record<string, string> = {
  free: '#78909c',
  starter: '#42a5f5',
  pro: '#4f7df9',
  scale: '#ab47bc',
};

function getPlanColor(code: string): string {
  return PLAN_COLORS[code.toLowerCase()] ?? '#4f7df9';
}

// ---------------------------------------------------------------------------
// Plan subtitles & CTA labels
// ---------------------------------------------------------------------------

const PLAN_SUBTITLES: Record<string, string> = {
  starter: 'Perfect for pre-seed founders',
  pro: 'Best for active fundraisers',
  scale: 'Best for aggressive fundraising campaigns',
};

const PLAN_CTA: Record<string, string> = {
  starter: 'Get Started',
  pro: 'Go Pro',
  scale: 'Go Scale',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatLimitLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\bper\b/g, '/')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatLimitValue(val: number | string | boolean): string {
  if (typeof val === 'boolean') return val ? 'Yes' : 'No';
  if (typeof val === 'number') {
    if (val < 0 || val >= 999999) return 'Unlimited';
    return val.toLocaleString();
  }
  return String(val);
}

function getButtonLabel(
  plan: Plan,
  currentPlanId: string | null,
  currentPrice: number,
): string {
  if (plan.id === currentPlanId) return 'Current Plan';
  if (!currentPlanId) {
    const code = plan.code.toLowerCase();
    return PLAN_CTA[code]
      ? `${PLAN_CTA[code]} \u2192`
      : 'Get Started \u2192';
  }
  if (plan.price_monthly > currentPrice) return 'Upgrade';
  return 'Downgrade';
}

// ---------------------------------------------------------------------------
// Price calculation
// ---------------------------------------------------------------------------

interface PriceInfo {
  /** The total amount charged for the period */
  periodPrice: number;
  /** The monthly equivalent (for "~$X/mo" display) */
  monthlyEquivalent: number;
  /** The label appended after the price (e.g. "/mth", "/quarter") */
  periodLabel: string;
  /** Discount badge text, or null if no discount */
  discountLabel: string | null;
}

function computePriceInfo(plan: Plan, period: BillingPeriod): PriceInfo {
  const monthly = Number(plan.price_monthly);

  if (monthly === 0) {
    return {
      periodPrice: 0,
      monthlyEquivalent: 0,
      periodLabel: '/mth',
      discountLabel: null,
    };
  }

  if (period === 'quarterly') {
    // Use plan's stored quarterly price if available, else compute
    const periodPrice =
      plan.price_quarterly != null
        ? Number(plan.price_quarterly)
        : monthly * 3 * 0.7;
    return {
      periodPrice,
      monthlyEquivalent: periodPrice / 3,
      periodLabel: '/quarter',
      discountLabel: 'Save 30%',
    };
  }

  if (period === 'annual') {
    // Use plan's stored annual price if available, else compute
    const periodPrice =
      plan.price_annually != null
        ? Number(plan.price_annually)
        : monthly * 12 * 0.5;
    return {
      periodPrice,
      monthlyEquivalent: periodPrice / 12,
      periodLabel: '/year',
      discountLabel: 'Save 50%',
    };
  }

  // monthly (default)
  return {
    periodPrice: monthly,
    monthlyEquivalent: monthly,
    periodLabel: '/mth',
    discountLabel: null,
  };
}

function formatPrice(amount: number): string {
  return amount.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PlanCardsProps {
  plans: Plan[];
  currentPlanId?: string | null;
  currentPrice?: number;
  billingPeriod?: BillingPeriod;
  onSelect: (plan: Plan, billingPeriod: BillingPeriod) => void;
  loading?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PlanCards: React.FC<PlanCardsProps> = ({
  plans,
  currentPlanId = null,
  currentPrice = 0,
  billingPeriod = 'monthly',
  onSelect,
  loading = false,
}) => {
  // Filter out free plans, then sort by price ascending
  const sortedPlans = [...plans]
    .filter((p) => p.code.toLowerCase() !== 'free' && Number(p.price_monthly) > 0)
    .sort((a, b) => a.price_monthly - b.price_monthly);

  return (
    <Grid
      container
      spacing={3}
      sx={{ justifyContent: 'center' }}
    >
      {sortedPlans.map((plan) => {
        const isCurrent = plan.id === currentPlanId;
        const color = getPlanColor(plan.code);
        const code = plan.code.toLowerCase();
        const isPopular = code === 'pro';
        const priceInfo = computePriceInfo(plan, billingPeriod);
        const subtitle = PLAN_SUBTITLES[code] ?? '';

        const features: string[] = Array.isArray(plan.features)
          ? plan.features
          : typeof plan.features === 'object' && plan.features !== null
            ? Object.entries(plan.features)
                .filter(([, v]) => v === true || typeof v === 'string')
                .map(([k, v]) => (typeof v === 'string' ? v : formatLimitLabel(k)))
            : [];

        const limits: Array<[string, string]> = plan.limits
          ? Object.entries(plan.limits).map(([k, v]) => [
              formatLimitLabel(k),
              formatLimitValue(v),
            ])
          : [];

        const buttonLabel = getButtonLabel(plan, currentPlanId, currentPrice);

        return (
          <Grid
            key={plan.id}
            size={{ xs: 12, sm: 6, md: 4 }}
          >
            <Card
              variant="outlined"
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                overflow: 'visible',
                borderColor: isPopular
                  ? '#4f7df9'
                  : isCurrent
                    ? color
                    : '#e0e0e0',
                borderWidth: isPopular ? 2 : 1,
                borderTopWidth: isPopular ? 4 : 1,
                borderTopColor: isPopular ? '#4f7df9' : undefined,
                bgcolor: '#fff',
                borderRadius: '12px',
                boxShadow: isPopular
                  ? '0 8px 32px rgba(79,195,247,0.18)'
                  : '0 2px 12px rgba(0,0,0,0.06)',
                transform: isPopular ? 'scale(1.03)' : 'none',
                transition: 'border-color 0.2s, transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  borderColor: color,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
                  transform: isPopular ? 'scale(1.04)' : 'translateY(-2px)',
                },
              }}
            >
              {/* POPULAR ribbon */}
              {isPopular && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: -1,
                    left: '50%',
                    transform: 'translateX(-50%) translateY(-50%)',
                    bgcolor: '#4f7df9',
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: '0.7rem',
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    px: 2.5,
                    py: 0.5,
                    borderRadius: '20px',
                    whiteSpace: 'nowrap',
                    zIndex: 1,
                  }}
                >
                  POPULAR
                </Box>
              )}

              <CardContent
                sx={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  p: 3,
                  pt: isPopular ? 4 : 3,
                }}
              >
                {/* Plan name */}
                <Typography
                  variant="h6"
                  sx={{ color: '#1a2b3c', fontWeight: 700, mb: 0.5 }}
                >
                  {plan.name}
                </Typography>

                {/* Plan subtitle */}
                {subtitle && (
                  <Typography
                    variant="body2"
                    sx={{ color: '#6b7a8d', mb: 2, fontSize: '0.85rem' }}
                  >
                    {subtitle}
                  </Typography>
                )}

                {/* Price display */}
                <Box sx={{ mb: billingPeriod === 'monthly' ? 2.5 : 1.5 }}>
                  <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
                    <Typography
                      component="span"
                      sx={{ fontSize: '2.5rem', fontWeight: 800, color: '#1a2b3c', lineHeight: 1 }}
                    >
                      ${formatPrice(priceInfo.periodPrice)}
                    </Typography>
                    <Typography
                      component="span"
                      sx={{ color: '#6b7280', fontSize: '0.95rem' }}
                    >
                      {priceInfo.periodLabel}
                    </Typography>
                  </Box>

                  {/* Monthly equivalent for quarterly/annual */}
                  {billingPeriod !== 'monthly' && (
                    <Typography
                      variant="caption"
                      sx={{ color: '#4caf50', display: 'block', mt: 0.5, fontWeight: 600 }}
                    >
                      ~${formatPrice(priceInfo.monthlyEquivalent)}/mth
                    </Typography>
                  )}

                  {/* Discount badge inline */}
                  {priceInfo.discountLabel && (
                    <Typography
                      variant="caption"
                      sx={{
                        display: 'inline-block',
                        mt: 0.5,
                        bgcolor: 'rgba(76,175,80,0.1)',
                        color: '#4caf50',
                        border: '1px solid rgba(76,175,80,0.3)',
                        borderRadius: '4px',
                        px: 1,
                        py: 0.25,
                        fontWeight: 600,
                        fontSize: '0.7rem',
                      }}
                    >
                      {priceInfo.discountLabel}
                    </Typography>
                  )}
                </Box>

                {/* Limits summary */}
                {limits.length > 0 && (
                  <Stack spacing={0.5} sx={{ mb: 2 }}>
                    {limits.map(([label, value]) => (
                      <Typography
                        key={label}
                        variant="body2"
                        sx={{ color: '#6b7a8d' }}
                      >
                        <Box
                          component="span"
                          sx={{ color: '#1a2b3c', fontWeight: 600 }}
                        >
                          {value}
                        </Box>{' '}
                        {label}
                      </Typography>
                    ))}
                  </Stack>
                )}

                {/* Feature list */}
                <Stack spacing={1} sx={{ flex: 1, mb: 3 }}>
                  {features.map((feat, idx) => (
                    <Box
                      key={idx}
                      sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}
                    >
                      <CheckCircle size={16} color="#4caf50" style={{ marginTop: 2, flexShrink: 0 }} />
                      <Typography
                        variant="body2"
                        sx={{ color: '#4a5568', lineHeight: 1.5 }}
                      >
                        {feat}
                      </Typography>
                    </Box>
                  ))}
                </Stack>

                <Button
                  variant={isCurrent ? 'outlined' : 'contained'}
                  fullWidth
                  disabled={isCurrent || loading}
                  onClick={() => onSelect(plan, billingPeriod)}
                  sx={{
                    mt: 'auto',
                    bgcolor: isCurrent ? 'transparent' : isPopular ? '#4f7df9' : color,
                    color: isCurrent ? color : '#fff',
                    borderColor: isCurrent ? color : undefined,
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    py: 1.25,
                    borderRadius: '8px',
                    textTransform: 'none',
                    '&:hover': {
                      bgcolor: isCurrent ? 'transparent' : isPopular ? '#29b6f6' : color,
                      opacity: 0.9,
                    },
                    '&.Mui-disabled': {
                      bgcolor: isCurrent ? 'transparent' : undefined,
                      color: isCurrent ? color : undefined,
                      borderColor: isCurrent ? color : undefined,
                      opacity: 0.7,
                    },
                  }}
                >
                  {buttonLabel}
                </Button>
              </CardContent>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
};

export default PlanCards;
