import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import type { Plan } from '@bill/types/plan.types';
import type { SubscriptionWithPlan } from '../api/billingApi';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockPlans: Plan[] = [
  {
    id: 'plan-free',
    name: 'Free',
    code: 'free',
    price_monthly: 0,
    price_quarterly: null,
    price_annually: null,
    limits: { ai_drafts_per_day: 3, emails_per_day: 5 },
    features: { show_full_contact_info: false },
    usage_basis: 'daily',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'plan-starter',
    name: 'Starter',
    code: 'starter',
    price_monthly: 29,
    price_quarterly: null,
    price_annually: null,
    limits: { ai_drafts_per_day: 20, emails_per_month: 500 },
    features: { show_full_contact_info: true },
    usage_basis: 'monthly',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'plan-pro',
    name: 'Pro',
    code: 'pro',
    price_monthly: 79,
    price_quarterly: null,
    price_annually: null,
    limits: { ai_drafts_per_day: 100, emails_per_month: 2000 },
    features: { show_full_contact_info: true, advanced_filters: true },
    usage_basis: 'monthly',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'plan-scale',
    name: 'Scale',
    code: 'scale',
    price_monthly: 199,
    price_quarterly: null,
    price_annually: null,
    limits: { ai_drafts_per_day: 999999, emails_per_month: 999999 },
    features: { show_full_contact_info: true, advanced_filters: true, priority_support: true },
    usage_basis: 'monthly',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const mockSubscription: SubscriptionWithPlan = {
  id: 'sub-1',
  user_id: 'user-1',
  plan_id: 'plan-pro',
  status: 'active',
  stripe_customer_id: null,
  stripe_subscription_id: null,
  stripe_payment_method_id: null,
  billing_period: 'monthly',
  current_period_end: '2026-04-10T00:00:00Z',
  cancel_at_period_end: false,
  trial_ends_at: null,
  created_at: '2026-03-10T00:00:00Z',
  updated_at: '2026-03-10T00:00:00Z',
  is_active: true,
  plan: mockPlans[2], // Pro plan
};

const mockCancelMutate = vi.fn();
const mockChangePlanMutate = vi.fn();

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../hooks/usePlans', () => ({
  usePlans: () => ({
    data: mockPlans,
    isLoading: false,
  }),
}));

vi.mock('../hooks/useSubscription', () => ({
  useSubscription: () => ({
    data: mockSubscription,
    isLoading: false,
  }),
}));

vi.mock('../hooks/useUsage', () => ({
  useUsage: () => ({
    data: [
      {
        id: 'usage-1',
        ai_drafts_used: 42,
        emails_sent: 15,
        monthly_emails_sent: 350,
        investors_added: 3,
        monthly_investors_added: 25,
        monthly_follow_ups_sent: 10,
      },
    ],
    isLoading: false,
  }),
}));

vi.mock('../hooks/useSubscribe', () => ({
  useSubscribe: () => ({
    cancel: {
      mutate: mockCancelMutate,
      isPending: false,
    },
    changePlan: {
      mutate: mockChangePlanMutate,
      isPending: false,
    },
    subscribe: {
      mutate: vi.fn(),
      isPending: false,
    },
  }),
}));

vi.mock('../../../auth/AuthProvider', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      role: 'admin',
      permissions: [],
    },
    isAuthenticated: true,
    loading: false,
    error: null,
  }),
}));

// Mock the navigate function
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ---------------------------------------------------------------------------
// Lazy import
// ---------------------------------------------------------------------------
let SubscriptionPage: React.FC;

beforeEach(async () => {
  vi.clearAllMocks();
  const mod = await import('../pages/SubscriptionPage');
  SubscriptionPage = mod.default;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SubscriptionPage', () => {
  it('renders current plan info', () => {
    renderWithProviders(<SubscriptionPage />);

    expect(screen.getByText('Subscription')).toBeInTheDocument();
    expect(screen.getAllByText('Pro').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('active').length).toBeGreaterThanOrEqual(1);
  });

  it('renders current plan name in the status section', () => {
    renderWithProviders(<SubscriptionPage />);

    // The "Current Plan" label and the plan name (may appear in both status + plan card)
    expect(screen.getAllByText('Current Plan').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Pro').length).toBeGreaterThanOrEqual(1);
  });

  it('shows usage section with labels', () => {
    renderWithProviders(<SubscriptionPage />);

    expect(screen.getByText('Usage')).toBeInTheDocument();
  });

  it('cancel button shows confirmation dialog', async () => {
    const user = userEvent.setup();

    renderWithProviders(<SubscriptionPage />);

    const cancelButton = screen.getByRole('button', { name: /cancel subscription/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });
  });

  it('confirm cancel calls cancel mutation', async () => {
    const user = userEvent.setup();

    renderWithProviders(<SubscriptionPage />);

    // Open the cancel dialog
    const cancelButton = screen.getByRole('button', { name: /cancel subscription/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.getByText(/confirm cancellation/i)).toBeInTheDocument();
    });

    // Click "Confirm Cancellation"
    const confirmButton = screen.getByRole('button', { name: /confirm cancellation/i });
    await user.click(confirmButton);

    expect(mockCancelMutate).toHaveBeenCalled();
  });

  it('shows keep subscription option in cancel dialog', async () => {
    const user = userEvent.setup();

    renderWithProviders(<SubscriptionPage />);

    const cancelButton = screen.getByRole('button', { name: /cancel subscription/i });
    await user.click(cancelButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /keep subscription/i })).toBeInTheDocument();
    });
  });

  it('renders the plan cards section', () => {
    renderWithProviders(<SubscriptionPage />);

    expect(screen.getByText(/Unlock Full Access/)).toBeInTheDocument();
  });

  it('shows renewal date', () => {
    renderWithProviders(<SubscriptionPage />);

    expect(screen.getByText(/renews on/i)).toBeInTheDocument();
  });
});
