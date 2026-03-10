import axios from 'axios';
import type { Plan } from '@bill/types/plan.types';
import type { Subscription } from '@bill/types/subscription.types';
import type { UsageRecord } from '@bill/types/usage_record.types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type BillingPeriod = 'monthly' | 'quarterly' | 'annual';

export interface SubscribeRequest {
  plan_id: string;
  billing_period?: BillingPeriod;
  success_url?: string;
  cancel_url?: string;
}

export interface SubscribeResponse {
  checkout_url: string;
  session_id?: string;
}

export interface ChangePlanRequest {
  new_plan_id: string;
}

export interface ChangePlanResponse {
  subscription: Subscription;
  message: string;
}

export interface CancelRequest {
  subscription_id?: string;
  cancel_at_period_end: boolean;
}

export interface CancelResponse {
  status: string;
  message: string;
  cancel_at_period_end: boolean;
  subscription?: Subscription;
}

export interface ValidateUsageRequest {
  action: string;
  count?: number;
}

export interface ValidateUsageResponse {
  allowed: boolean;
  current: number;
  limit: number;
  message?: string;
}

export interface TrackUsageRequest {
  action: string;
  count?: number;
}

export interface TrackUsageResponse {
  usage_record: UsageRecord;
  message: string;
}

export interface SubscriptionWithPlan extends Subscription {
  plan?: Plan;
}

export interface PaymentMethod {
  id: string;
  brand: string;   // visa, mastercard, amex, etc.
  last4: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
}

// ---------------------------------------------------------------------------
// API Client
// ---------------------------------------------------------------------------

const client = axios.create({
  headers: { 'Content-Type': 'application/json' },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const tenantId =
    localStorage.getItem('tenant_id') ||
    '00000000-0000-0000-0000-000000000000';
  if (config.headers) {
    config.headers['X-Tenant-ID'] = tenantId;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('token_expiry');
      if (
        typeof window !== 'undefined' &&
        !window.location.pathname.startsWith('/login')
      ) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

// ---------------------------------------------------------------------------
// Plans
// ---------------------------------------------------------------------------

export async function fetchPlans(): Promise<Plan[]> {
  const res = await client.get('/api/v1/plans/', {
    params: { page_size: 200 },
  });
  const data = res.data;
  return Array.isArray(data) ? data : data.items ?? data.plans ?? [];
}

// ---------------------------------------------------------------------------
// Subscription
// ---------------------------------------------------------------------------

export async function fetchUserSubscription(
  userId: string,
): Promise<SubscriptionWithPlan | null> {
  try {
    const res = await client.get('/api/v1/subscriptions/', {
      params: { user_id: userId, page_size: 1 },
    });
    const data = res.data;
    const items = Array.isArray(data) ? data : data.items ?? [];
    const active = items.find(
      (s: Subscription) =>
        s.status === 'active' ||
        s.status === 'trialing' ||
        s.status === 'canceling',
    );
    if (!active) return null;

    try {
      const planRes = await client.get(`/api/v1/plans/${active.plan_id}`);
      return { ...active, plan: planRes.data };
    } catch {
      return active;
    }
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Custom billing endpoints
// ---------------------------------------------------------------------------

export async function subscribe(
  data: SubscribeRequest,
): Promise<SubscribeResponse> {
  const res = await client.post<SubscribeResponse>(
    '/api/v1/subscriptions/subscribe',
    data,
  );
  return res.data;
}

export async function changePlan(
  data: ChangePlanRequest,
): Promise<ChangePlanResponse> {
  const res = await client.post<ChangePlanResponse>(
    '/api/v1/subscriptions/change-plan',
    data,
  );
  return res.data;
}

export async function cancelSubscription(
  data: CancelRequest,
): Promise<CancelResponse> {
  const res = await client.post<CancelResponse>(
    '/api/v1/subscriptions/cancel',
    data,
  );
  return res.data;
}

export async function validateUsage(
  data: ValidateUsageRequest,
): Promise<ValidateUsageResponse> {
  const res = await client.post<ValidateUsageResponse>(
    '/api/v1/subscriptions/validate-usage',
    data,
  );
  return res.data;
}

export async function trackUsage(
  data: TrackUsageRequest,
): Promise<TrackUsageResponse> {
  const res = await client.post<TrackUsageResponse>(
    '/api/v1/subscriptions/track-usage',
    data,
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Usage records
// ---------------------------------------------------------------------------

export async function fetchUsageRecords(
  userId: string,
): Promise<UsageRecord[]> {
  const res = await client.get('/api/v1/usage-records/', {
    params: { user_id: userId, page_size: 200, sort_by: 'date', sort_order: 'desc' },
  });
  const data = res.data;
  return Array.isArray(data) ? data : data.items ?? data.usage_records ?? [];
}

// ---------------------------------------------------------------------------
// Payment methods
// ---------------------------------------------------------------------------

export async function getPaymentMethods(userId: string): Promise<PaymentMethod[]> {
  try {
    const res = await client.get<PaymentMethod[]>('/api/v1/payment-methods/', {
      params: { user_id: userId },
    });
    return Array.isArray(res.data) ? res.data : [];
  } catch {
    return [];
  }
}

export async function createSetupIntent(
  userId: string,
): Promise<{ client_secret: string }> {
  const res = await client.post<{ client_secret: string }>(
    '/api/v1/payment-methods/setup-intent',
    { user_id: userId },
  );
  return res.data;
}

export async function setDefaultPaymentMethod(
  userId: string,
  paymentMethodId: string,
): Promise<{ status: string; message: string }> {
  const res = await client.post('/api/v1/payment-methods/default', {
    user_id: userId,
    payment_method_id: paymentMethodId,
  });
  return res.data;
}

export async function removePaymentMethod(
  paymentMethodId: string,
): Promise<{ status: string; message: string }> {
  const res = await client.delete(`/api/v1/payment-methods/${paymentMethodId}`);
  return res.data;
}
