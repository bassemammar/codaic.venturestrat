import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import type { PipelineStage } from '@crm/types/pipeline_stage.types';
import type {
  Shortlist,
  ShortlistCreateRequest,
  ShortlistUpdateRequest,
  ShortlistListResponse,
} from '@crm/types/shortlist.types';
import type {
  Activity,
  ActivityCreateRequest,
  ActivityListResponse,
} from '@crm/types/activity.types';
import type { Tag, TagListResponse } from '@crm/types/tag.types';
import type {
  ShortlistTag,
  ShortlistTagCreateRequest,
  ShortlistTagListResponse,
} from '@crm/types/shortlist_tag.types';
import type { PipelineStageListResponse } from '@crm/types/pipeline_stage.types';

/**
 * Enriched shortlist with denormalized stage + investor info for Kanban rendering
 */
export interface KanbanShortlist extends Shortlist {
  stage_name?: string;
  stage_color?: string;
  stage_sequence?: number;
  investor_name?: string;
  investor_company?: string;
  investor_location?: string;
  investor_email?: string;
  last_activity_summary?: string;
  last_activity_date?: string;
  tags: Array<{ id: string; name: string; color: string | null }>;
  days_in_stage: number;
}

const TENANT_ID =
  (typeof localStorage !== 'undefined' && localStorage.getItem('tenant_id')) ||
  '00000000-0000-0000-0000-000000000000';

function createCrmClient(): AxiosInstance {
  const client = axios.create({
    headers: { 'Content-Type': 'application/json' },
  });

  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token =
        typeof localStorage !== 'undefined'
          ? localStorage.getItem('access_token')
          : null;
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      if (config.headers) {
        const tenantId =
          (typeof localStorage !== 'undefined' && localStorage.getItem('tenant_id')) ||
          TENANT_ID;
        config.headers['X-Tenant-ID'] = tenantId;
      }
      return config;
    },
    (error) => Promise.reject(error),
  );

  return client;
}

const crmClient = createCrmClient();

function extractItems<T>(data: unknown, fallbackKey?: string): T[] {
  if (Array.isArray(data)) return data as T[];
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>;
    if (Array.isArray(obj.items)) return obj.items as T[];
    if (fallbackKey && Array.isArray(obj[fallbackKey])) {
      return obj[fallbackKey] as T[];
    }
  }
  return [];
}

export const crmApi = {
  /**
   * Fetch all pipeline stages (active only, sorted by sequence)
   */
  async getPipelineStages(): Promise<PipelineStage[]> {
    const res = await crmClient.get<PipelineStage[] | PipelineStageListResponse>(
      '/api/v1/pipeline-stages/',
      { params: { page_size: 200, is_active: true, sort_by: 'sequence', sort_order: 'asc' } },
    );
    return extractItems(res.data, 'pipeline_stages');
  },

  /**
   * Fetch all shortlists for the current user
   */
  async getShortlists(userId?: string): Promise<Shortlist[]> {
    const params: Record<string, unknown> = { page_size: 200 };
    if (userId) params.user_id = userId;
    const res = await crmClient.get<Shortlist[] | ShortlistListResponse>(
      '/api/v1/shortlists/',
      { params },
    );
    return extractItems(res.data, 'shortlists');
  },

  /**
   * Create a new shortlist entry (add investor to CRM pipeline)
   */
  async createShortlist(data: ShortlistCreateRequest): Promise<Shortlist> {
    const res = await crmClient.post<Shortlist>('/api/v1/shortlists/', data);
    return res.data;
  },

  /**
   * Update a shortlist (partial update via PUT)
   */
  async updateShortlist(id: string, data: ShortlistUpdateRequest): Promise<Shortlist> {
    const res = await crmClient.put<Shortlist>(`/api/v1/shortlists/${id}`, data);
    return res.data;
  },

  /**
   * Fetch activities for a specific shortlist
   */
  async getActivities(shortlistId: string): Promise<Activity[]> {
    const res = await crmClient.get<Activity[] | ActivityListResponse>(
      '/api/v1/activities/',
      { params: { shortlist_id: shortlistId, page_size: 200, sort_by: 'date', sort_order: 'desc' } },
    );
    return extractItems(res.data, 'activities');
  },

  /**
   * Create a new activity
   */
  async createActivity(data: ActivityCreateRequest): Promise<Activity> {
    const res = await crmClient.post<Activity>('/api/v1/activities/', data);
    return res.data;
  },

  /**
   * Fetch all tags
   */
  async getTags(): Promise<Tag[]> {
    const res = await crmClient.get<Tag[] | TagListResponse>(
      '/api/v1/tags/',
      { params: { page_size: 200, is_active: true } },
    );
    return extractItems(res.data, 'tags');
  },

  /**
   * Fetch shortlist_tags for a specific shortlist
   */
  async getShortlistTags(shortlistId: string): Promise<ShortlistTag[]> {
    const res = await crmClient.get<ShortlistTag[] | ShortlistTagListResponse>(
      '/api/v1/shortlist-tags/',
      { params: { shortlist_id: shortlistId, page_size: 200 } },
    );
    return extractItems(res.data, 'shortlist_tags');
  },

  /**
   * Add a tag to a shortlist
   */
  async addShortlistTag(data: ShortlistTagCreateRequest): Promise<ShortlistTag> {
    const res = await crmClient.post<ShortlistTag>('/api/v1/shortlist-tags/', data);
    return res.data;
  },

  /**
   * Remove a shortlist tag
   */
  async removeShortlistTag(id: string): Promise<void> {
    await crmClient.delete(`/api/v1/shortlist-tags/${id}`);
  },
};

export default crmApi;
