import axios from 'axios';
import type { Investor } from '@inve/types/investor.types';
import type { PaginationMeta } from '@inve/types/investor.types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface InvestorSearchParams {
  q?: string;
  location?: string[];
  stages?: string[];
  types?: string[];
  markets?: string[];
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface InvestorSearchResponse {
  items: Investor[];
  pagination: PaginationMeta;
}

export interface MarketOption {
  id: string;
  title: string;
}

export interface InvestorFilterValues {
  locations: string[];
  stages: string[];
  types: string[];
  markets: MarketOption[];
}

export interface InvestorLivePreviewResponse {
  items: Investor[];
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
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------

export async function searchInvestors(
  params: InvestorSearchParams,
): Promise<InvestorSearchResponse> {
  const cleanParams: Record<string, unknown> = {};

  if (params.q) cleanParams.q = params.q;
  if (params.page) cleanParams.page = params.page;
  if (params.page_size) cleanParams.page_size = params.page_size;
  if (params.sort_by) cleanParams.sort_by = params.sort_by;
  if (params.sort_order) cleanParams.sort_order = params.sort_order;

  if (params.location?.length) cleanParams.location = params.location.join(',');
  if (params.stages?.length) cleanParams.stages = params.stages.join(',');
  if (params.types?.length) cleanParams.types = params.types.join(',');
  if (params.markets?.length) cleanParams.market_ids = params.markets.join(',');

  const res = await client.get<InvestorSearchResponse>(
    '/api/v1/investors/search',
    { params: cleanParams },
  );
  return res.data;
}

export async function fetchInvestorFilters(): Promise<InvestorFilterValues> {
  const res = await client.get<InvestorFilterValues>(
    '/api/v1/investors/filters',
  );
  return res.data;
}

export async function fetchInvestorLivePreview(): Promise<Investor[]> {
  const res = await client.get<InvestorLivePreviewResponse>(
    '/api/v1/investors/live-preview',
  );
  return res.data.items ?? (res.data as unknown as Investor[]);
}

export async function fetchInvestorById(id: string): Promise<Investor> {
  const res = await client.get<Investor>(`/api/v1/investors/${id}`);
  return res.data;
}

export async function fetchInvestorEmails(
  investorId: string,
): Promise<Array<{ id: string; investor_id: string; email: string; status: string }>> {
  const res = await client.get('/api/v1/investor-emails/', {
    params: { investor_id: investorId, page_size: 200 },
  });
  const data = res.data;
  const items: Array<{ id: string; investor_id: string; email: string; status: string }> =
    Array.isArray(data) ? data : data.items ?? [];
  // Backend may not filter by investor_id — filter client-side
  return items.filter((e) => e.investor_id === investorId);
}

export async function fetchInvestorMarkets(
  investorId: string,
): Promise<Array<{ id: string; investor_id: string; market_id: string }>> {
  const res = await client.get('/api/v1/investor-markets/', {
    params: { investor_id: investorId, page_size: 200 },
  });
  const data = res.data;
  const items: Array<{ id: string; investor_id: string; market_id: string }> =
    Array.isArray(data) ? data : data.items ?? [];
  return items.filter((e) => e.investor_id === investorId);
}

export async function fetchInvestorPastInvestments(
  investorId: string,
): Promise<Array<{ id: string; investor_id: string; past_investment_id: string }>> {
  const res = await client.get('/api/v1/investor-past-investments/', {
    params: { investor_id: investorId, page_size: 200 },
  });
  const data = res.data;
  const items: Array<{ id: string; investor_id: string; past_investment_id: string }> =
    Array.isArray(data) ? data : data.items ?? [];
  return items.filter((e) => e.investor_id === investorId);
}

export async function fetchMarkets(): Promise<
  Array<{ id: string; title: string }>
> {
  const res = await client.get('/api/v1/markets/', {
    params: { page_size: 200 },
  });
  const data = res.data;
  return Array.isArray(data) ? data : data.items ?? [];
}

export async function fetchPastInvestments(): Promise<
  Array<{ id: string; title: string }>
> {
  const res = await client.get('/api/v1/past-investments/', {
    params: { page_size: 200 },
  });
  const data = res.data;
  return Array.isArray(data) ? data : data.items ?? [];
}

export async function fetchUserSubscription(
  userId: string,
): Promise<{
  id: string;
  plan_id: string;
  status: string;
  trial_ends_at?: string | null;
  plan?: { name: string; code: string; limits: Record<string, any>; features: Record<string, any> };
} | null> {
  try {
    const res = await client.get('/api/v1/subscriptions/', {
      params: { user_id: userId, page_size: 1 },
    });
    const data = res.data;
    const items = Array.isArray(data) ? data : data.items ?? [];
    const active = items.find(
      (s: any) => s.status === 'active' || s.status === 'trialing',
    );
    if (!active) return null;

    // Fetch the plan details
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
