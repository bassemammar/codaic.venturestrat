/**
 * Outreach API Client
 *
 * Axios client for outreach-service custom endpoints:
 * - Message send / schedule / cancel-schedule
 * - AI email generation and editing
 * - CRUD wrappers for messages and email accounts
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import type {
  Message,
  MessageCreateRequest,
  MessageUpdateRequest,
  MessageFilterOptions,
  MessageListResponse,
} from '@outr/types/message.types';
import type {
  EmailAccount,
  EmailAccountListResponse,
} from '@outr/types/email_account.types';

// ---------------------------------------------------------------------------
// Custom Types for outreach endpoints
// ---------------------------------------------------------------------------

export interface SendMessageRequest {
  provider_override?: string;
}

export interface SendMessageResponse {
  status: string;
  provider_message_id?: string;
  thread_id?: string;
}

export interface ScheduleMessageRequest {
  scheduled_for: string; // ISO 8601
}

export interface ScheduleMessageResponse {
  status: string;
  scheduled_for: string;
  job_id?: string;
}

export interface AIGenerateEmailRequest {
  investor_name: string;
  company?: string;
  tone?: 'professional' | 'friendly' | 'casual';
  custom_instructions?: string;
  template_id?: string;
}

export interface AIGenerateEmailResponse {
  subject: string;
  body: string;
  tone_used: string;
}

export interface AIEditTextRequest {
  text: string;
  instruction: string;
}

export interface AIEditTextResponse {
  text: string;
}

// ---------------------------------------------------------------------------
// Axios Instance
// ---------------------------------------------------------------------------

function createOutreachClient(): AxiosInstance {
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
          '00000000-0000-0000-0000-000000000000';
        config.headers['X-Tenant-ID'] = tenantId;
      }

      return config;
    },
    (error) => Promise.reject(error),
  );

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

  return client;
}

const client = createOutreachClient();

// ---------------------------------------------------------------------------
// Messages CRUD
// ---------------------------------------------------------------------------

export async function fetchMessages(
  filters?: MessageFilterOptions,
): Promise<Message[]> {
  const res = await client.get<Message[] | MessageListResponse>(
    '/api/v1/messages/',
    { params: { ...filters, page_size: 200 } },
  );
  const data = res.data;
  if (Array.isArray(data)) return data;
  return (data as MessageListResponse).items ||
    (data as MessageListResponse).messages || [];
}

export async function fetchMessageById(id: string): Promise<Message> {
  const res = await client.get<Message>(`/api/v1/messages/${id}`);
  return res.data;
}

export async function createMessage(
  data: MessageCreateRequest,
): Promise<Message> {
  const res = await client.post<Message>('/api/v1/messages/', data);
  return res.data;
}

export async function updateMessage(
  id: string,
  data: MessageUpdateRequest,
): Promise<Message> {
  const res = await client.put<Message>(`/api/v1/messages/${id}`, data);
  return res.data;
}

export async function deleteMessage(id: string): Promise<void> {
  await client.delete(`/api/v1/messages/${id}`);
}

// ---------------------------------------------------------------------------
// Email Accounts
// ---------------------------------------------------------------------------

export async function fetchEmailAccounts(): Promise<EmailAccount[]> {
  const res = await client.get<EmailAccount[] | EmailAccountListResponse>(
    '/api/v1/email-accounts/',
    { params: { page_size: 200 } },
  );
  const data = res.data;
  if (Array.isArray(data)) return data;
  return (data as EmailAccountListResponse).items ||
    (data as EmailAccountListResponse).email_accounts || [];
}

// ---------------------------------------------------------------------------
// Draft convenience wrappers
// Thin wrappers over createMessage / updateMessage for semantic clarity
// in auto-save and draft-management contexts.
// ---------------------------------------------------------------------------

export async function createDraft(
  data: Omit<MessageCreateRequest, 'status'>,
): Promise<Message> {
  return createMessage({ ...data, status: 'draft' });
}

export async function updateDraft(
  messageId: string,
  data: MessageUpdateRequest,
): Promise<Message> {
  return updateMessage(messageId, { ...data, status: 'draft' });
}

// ---------------------------------------------------------------------------
// Send / Schedule / Cancel
// ---------------------------------------------------------------------------

export async function sendMessage(
  id: string,
  payload?: SendMessageRequest,
): Promise<SendMessageResponse> {
  const res = await client.post<SendMessageResponse>(
    `/api/v1/messages/${id}/send`,
    payload || {},
  );
  return res.data;
}

export async function scheduleMessage(
  id: string,
  payload: ScheduleMessageRequest,
): Promise<ScheduleMessageResponse> {
  const res = await client.post<ScheduleMessageResponse>(
    `/api/v1/messages/${id}/schedule`,
    payload,
  );
  return res.data;
}

export async function cancelSchedule(
  id: string,
): Promise<{ status: string }> {
  const res = await client.post<{ status: string }>(
    `/api/v1/messages/${id}/cancel-schedule`,
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// AI Endpoints
// ---------------------------------------------------------------------------

export async function aiGenerateEmail(
  payload: AIGenerateEmailRequest,
): Promise<AIGenerateEmailResponse> {
  const res = await client.post<AIGenerateEmailResponse>(
    '/api/v1/ai/generate-email',
    payload,
  );
  return res.data;
}

export async function aiEditText(
  payload: AIEditTextRequest,
): Promise<AIEditTextResponse> {
  const res = await client.post<AIEditTextResponse>(
    '/api/v1/ai/edit-text',
    payload,
  );
  return res.data;
}

// ---------------------------------------------------------------------------
// Attachments
// ---------------------------------------------------------------------------

export interface Attachment {
  id: string;
  message_id: string;
  filename: string;
  size: number;
  content_type: string;
  created_at: string;
}

export async function uploadAttachment(
  messageId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<Attachment> {
  const form = new FormData();
  form.append('file', file);

  const res = await client.post<Attachment>(
    `/api/v1/messages/${messageId}/attachments`,
    form,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress
        ? (evt) => {
            if (evt.total) {
              onProgress(Math.round((evt.loaded / evt.total) * 100));
            }
          }
        : undefined,
    },
  );
  return res.data;
}

export async function listAttachments(messageId: string): Promise<Attachment[]> {
  const res = await client.get<Attachment[]>(
    `/api/v1/messages/${messageId}/attachments`,
  );
  return res.data;
}

export async function downloadAttachment(
  attachmentId: string,
  filename: string,
): Promise<void> {
  const res = await client.get<Blob>(
    `/api/v1/attachments/${attachmentId}/download`,
    { responseType: 'blob' },
  );
  const url = URL.createObjectURL(res.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Follow-up Sequences
// ---------------------------------------------------------------------------

export interface FollowUp {
  id: string;
  message_id: string;
  sequence_number: number;
  delay_days: number;
  scheduled_at: string | null;
  status: 'scheduled' | 'sent' | 'canceled';
  subject: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface ScheduleFollowUpsRequest {
  delays: number[];
  subject_prefix?: string;
  body_template?: string;
}

export interface UpdateFollowUpRequest {
  delay_days?: number;
  subject?: string;
  body?: string;
  status?: 'scheduled' | 'sent' | 'canceled';
}

export async function scheduleFollowUps(
  messageId: string,
  data: ScheduleFollowUpsRequest,
): Promise<FollowUp[]> {
  const res = await client.post<FollowUp[]>(
    `/api/v1/messages/${messageId}/follow-ups`,
    data,
  );
  return res.data;
}

export async function getFollowUps(messageId: string): Promise<FollowUp[]> {
  const res = await client.get<FollowUp[]>(
    `/api/v1/messages/${messageId}/follow-ups`,
  );
  return res.data;
}

export async function cancelFollowUp(followUpId: string): Promise<FollowUp> {
  const res = await client.delete<FollowUp>(`/api/v1/follow-ups/${followUpId}`);
  return res.data;
}

export async function updateFollowUp(
  followUpId: string,
  data: UpdateFollowUpRequest,
): Promise<FollowUp> {
  const res = await client.put<FollowUp>(
    `/api/v1/follow-ups/${followUpId}`,
    data,
  );
  return res.data;
}

export async function removeAttachment(attachmentId: string): Promise<void> {
  await client.delete(`/api/v1/attachments/${attachmentId}`);
}

// ---------------------------------------------------------------------------
// OAuth — Connected Email Accounts
// ---------------------------------------------------------------------------

export interface ConnectedAccount {
  id: string;
  provider: 'gmail' | 'microsoft';
  email: string;
  connected_at: string;
  is_active: boolean;
}

export interface OAuthAuthorizeResponse {
  authorization_url: string;
}

export interface OAuthCallbackResponse {
  email: string;
  provider: string;
  connected_at: string;
  account_id: string;
}

export async function getGoogleAuthUrl(userId?: string): Promise<OAuthAuthorizeResponse> {
  const params = userId ? { user_id: userId } : {};
  const res = await client.get<OAuthAuthorizeResponse>('/api/v1/oauth/google/authorize', { params });
  return res.data;
}

export async function exchangeGoogleCode(
  code: string,
  state: string,
): Promise<OAuthCallbackResponse> {
  const res = await client.post<OAuthCallbackResponse>('/api/v1/oauth/google/callback', { code, state });
  return res.data;
}

export async function getMicrosoftAuthUrl(userId?: string): Promise<OAuthAuthorizeResponse> {
  const params = userId ? { user_id: userId } : {};
  const res = await client.get<OAuthAuthorizeResponse>('/api/v1/oauth/microsoft/authorize', { params });
  return res.data;
}

export async function exchangeMicrosoftCode(
  code: string,
  state: string,
): Promise<OAuthCallbackResponse> {
  const res = await client.post<OAuthCallbackResponse>('/api/v1/oauth/microsoft/callback', { code, state });
  return res.data;
}

export async function getConnectedAccounts(userId?: string): Promise<ConnectedAccount[]> {
  const params = userId ? { user_id: userId } : {};
  const res = await client.get<ConnectedAccount[]>('/api/v1/oauth/accounts', { params });
  return res.data;
}

export async function disconnectAccount(accountId: string): Promise<void> {
  await client.delete(`/api/v1/oauth/accounts/${accountId}`);
}
