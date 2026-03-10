import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test-utils';
import PlanCards from '../components/PlanCards';
import type { Plan } from '@bill/types/plan.types';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const plans: Plan[] = [
  {
    id: 'plan-free',
    name: 'Free',
    code: 'free',
    price_monthly: 0,
    price_quarterly: null,
    price_annually: null,
    limits: { ai_drafts_per_day: 3, emails_per_day: 5 },
    features: ['Basic search', '5 emails/day'],
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
    features: ['Full contact info', '500 emails/month'],
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
    features: ['Advanced filters', '2,000 emails/month', 'Priority support'],
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
    features: ['Unlimited everything', 'Custom integrations', 'Dedicated support'],
    usage_basis: 'monthly',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PlanCards', () => {
  const onSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders 3 paid plan cards (Free hidden)', () => {
    renderWithProviders(
      <PlanCards plans={plans} onSelect={onSelect} />,
    );

    expect(screen.queryByText('Free')).not.toBeInTheDocument();
    expect(screen.getByText('Starter')).toBeInTheDocument();
    expect(screen.getByText('Pro')).toBeInTheDocument();
    expect(screen.getByText('Scale')).toBeInTheDocument();
  });

  it('renders prices for paid plans', () => {
    renderWithProviders(
      <PlanCards plans={plans} onSelect={onSelect} />,
    );

    expect(screen.getByText('$29')).toBeInTheDocument();
    expect(screen.getByText('$79')).toBeInTheDocument();
    expect(screen.getByText('$199')).toBeInTheDocument();
  });

  it('shows "Current Plan" button (disabled) on current plan', () => {
    renderWithProviders(
      <PlanCards
        plans={plans}
        currentPlanId="plan-pro"
        currentPrice={79}
        onSelect={onSelect}
      />,
    );

    const currentPlanButton = screen.getByRole('button', { name: 'Current Plan' });
    expect(currentPlanButton).toBeInTheDocument();
    expect(currentPlanButton).toBeDisabled();
  });

  it('shows action buttons for non-current plans', () => {
    renderWithProviders(
      <PlanCards
        plans={plans}
        currentPlanId="plan-pro"
        currentPrice={79}
        onSelect={onSelect}
      />,
    );

    // Starter is cheaper -> "Downgrade"
    expect(screen.getByRole('button', { name: 'Downgrade' })).toBeInTheDocument();

    // Scale is more expensive -> "Upgrade"
    expect(screen.getByRole('button', { name: 'Upgrade' })).toBeInTheDocument();
  });

  it('shows "POPULAR" badge on Pro plan', () => {
    renderWithProviders(
      <PlanCards plans={plans} onSelect={onSelect} />,
    );

    expect(screen.getByText('POPULAR')).toBeInTheDocument();
  });

  it('calls onSelect with the correct plan when a button is clicked', async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <PlanCards plans={plans} onSelect={onSelect} />,
    );

    // Starter shows "Get Started →" when no current plan
    const getStartedButton = screen.getByRole('button', { name: /Get Started/ });
    await user.click(getStartedButton);

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'plan-starter', name: 'Starter' }),
      'monthly',
    );
  });

  it('shows custom CTA for each plan when no current plan', () => {
    renderWithProviders(
      <PlanCards plans={plans} onSelect={onSelect} />,
    );

    expect(screen.getByRole('button', { name: /Get Started/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Go Pro/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Go Scale/ })).toBeInTheDocument();
  });

  it('shows features for paid plans', () => {
    renderWithProviders(
      <PlanCards plans={plans} onSelect={onSelect} />,
    );

    // Free plan features hidden
    expect(screen.queryByText('Basic search')).not.toBeInTheDocument();
    // Paid plan features shown
    expect(screen.getByText('Full contact info')).toBeInTheDocument();
    expect(screen.getByText('Advanced filters')).toBeInTheDocument();
    expect(screen.getByText('Unlimited everything')).toBeInTheDocument();
  });

  it('disables all buttons when loading is true', () => {
    renderWithProviders(
      <PlanCards
        plans={plans}
        currentPlanId="plan-pro"
        currentPrice={79}
        onSelect={onSelect}
        loading={true}
      />,
    );

    const buttons = screen.getAllByRole('button');
    buttons.forEach((button) => {
      expect(button).toBeDisabled();
    });
  });
});
