// =============================================================================
// Entity Registry SDK — API Client
// Generated: 2026-03-10T13:09:42.032621Z
// =============================================================================

import { getEntity, type EntityFieldMeta } from './entity-registry';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ListParams {
  page?: number;
  page_size?: number;
  search?: string;
  ordering?: string;
  [key: string]: unknown;
}

export interface ListResponse<T = Record<string, unknown>> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DropdownOption {
  value: string;
  label: string;
}

export interface ApiClientConfig {
  baseUrl?: string;
  getAccessToken?: () => string | null;
  getTenantId?: () => string | null;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

const DEFAULT_BASE_URL = typeof window !== 'undefined' ? window.location.origin : '';

/** Extract tenant_id from JWT stored in localStorage. */
function tenantFromJWT(): string | null {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.tenant || payload.tenant_id || null;
  } catch { return null; }
}

/** Default tenant: localStorage key → JWT claim → fallback zero UUID */
const DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000000';

class EntityApiClient {
  private baseUrl: string;
  private getAccessToken: () => string | null;
  private getTenantId: () => string | null;

  constructor(config?: ApiClientConfig) {
    this.baseUrl = config?.baseUrl ?? DEFAULT_BASE_URL;
    this.getAccessToken =
      config?.getAccessToken ??
      (() => {
        try { return localStorage.getItem('access_token'); } catch { return null; }
      });
    this.getTenantId =
      config?.getTenantId ??
      (() => {
        try {
          return localStorage.getItem('tenant_id')
            || tenantFromJWT()
            || DEFAULT_TENANT_ID;
        } catch { return DEFAULT_TENANT_ID; }
      });
  }

  // ---- Internal helpers ---------------------------------------------------

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    const token = this.getAccessToken();
    if (token) h['Authorization'] = `Bearer ${token}`;
    const tenant = this.getTenantId();
    if (tenant) h['X-Tenant-ID'] = tenant;
    return h;
  }

  private async request<T>(
    method: string,
    url: string,
    body?: unknown,
  ): Promise<T> {
    const res = await fetch(`${this.baseUrl}${url}`, {
      method,
      headers: this.headers(),
      body: body != null ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`${method} ${url} failed (${res.status}): ${text}`);
    }
    if (res.status === 204) return undefined as unknown as T;
    return res.json() as Promise<T>;
  }

  // ---- CRUD ---------------------------------------------------------------

  /** List records for an entity with optional filtering/pagination. */
  async list<T = Record<string, unknown>>(
    entityName: string,
    params?: ListParams,
  ): Promise<ListResponse<T>> {
    const meta = getEntity(entityName);
    const qs = params ? '?' + new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v != null)
        .map(([k, v]) => [k, String(v)]),
    ).toString() : '';
    const raw = await this.request<ListResponse<T> | T[]>('GET', `${meta.endpoint}${qs}`);
    // Backend may return a flat array or a paginated envelope — normalize
    if (Array.isArray(raw)) {
      return {
        items: raw,
        total: raw.length,
        page: params?.page ?? 1,
        page_size: params?.page_size ?? raw.length,
      };
    }
    // Handle envelope with different key names (results vs items)
    const envelope = raw as unknown as Record<string, unknown>;
    const items = (envelope.items ?? envelope.results ?? []) as T[];
    return {
      items,
      total: (envelope.total ?? envelope.count ?? items.length) as number,
      page: (envelope.page ?? params?.page ?? 1) as number,
      page_size: (envelope.page_size ?? params?.page_size ?? items.length) as number,
    };
  }

  /** Get a single record by ID. */
  async get<T = Record<string, unknown>>(
    entityName: string,
    id: string,
  ): Promise<T> {
    const meta = getEntity(entityName);
    return this.request<T>('GET', `${meta.endpoint}/${id}`);
  }

  /** Create a new record. */
  async create<T = Record<string, unknown>>(
    entityName: string,
    data: Record<string, unknown>,
  ): Promise<T> {
    const meta = getEntity(entityName);
    return this.request<T>('POST', meta.endpoint, data);
  }

  /** Update an existing record. */
  async update<T = Record<string, unknown>>(
    entityName: string,
    id: string,
    data: Record<string, unknown>,
  ): Promise<T> {
    const meta = getEntity(entityName);
    return this.request<T>('PUT', `${meta.endpoint}/${id}`, data);
  }

  /** Delete a record by ID. */
  async delete(entityName: string, id: string): Promise<void> {
    const meta = getEntity(entityName);
    await this.request<void>('DELETE', `${meta.endpoint}/${id}`);
  }

  /** Load dropdown options for a FK field. */
  async loadOptions(field: EntityFieldMeta): Promise<DropdownOption[]> {
    if (!field.fk) return [];
    const res = await this.request<{ items?: unknown[]; [k: string]: unknown }>(
      'GET',
      `${field.fk.endpoint}?page_size=200`,
    );
    const items: Record<string, unknown>[] = Array.isArray(res)
      ? res
      : (res.items ?? []) as Record<string, unknown>[];
    return items.map((item) => ({
      value: String(item[field.fk!.valueField] ?? ''),
      label: String(item[field.fk!.labelField] ?? item[field.fk!.valueField] ?? ''),
    }));
  }
}

/** Default singleton client instance. */
export const entityClient = new EntityApiClient();

export { EntityApiClient };
