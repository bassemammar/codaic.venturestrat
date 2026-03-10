// =============================================================================
// Entity Registry SDK — Zod Schemas
// Generated: 2026-03-10T13:09:42.032621Z
// Entities: 4
// =============================================================================

import { z } from 'zod';

// ---------------------------------------------------------------------------
// Per-entity Create schemas
// ---------------------------------------------------------------------------

// --- EmailAccount ---
export const EmailAccountCreateSchema = z.object({
  user_id: z.string().max(100),
  provider: z.enum(["gmail", "microsoft", "sendgrid"]),
  email_address: z.string().max(255),
  access_token: z.string().nullable().optional(),
  refresh_token: z.string().nullable().optional(),
  token_expires_at: z.string().nullable().optional(),
  watch_history_id: z.string().max(100).nullable().optional(),
  is_active: z.boolean(),
});

export type EmailAccountCreateInput = z.infer<typeof EmailAccountCreateSchema>;

export const EmailAccountUpdateSchema = EmailAccountCreateSchema.partial();
export type EmailAccountUpdateInput = z.infer<typeof EmailAccountUpdateSchema>;

// --- EmailTemplate ---
export const EmailTemplateCreateSchema = z.object({
  user_id: z.string().max(100).nullable().optional(),
  name: z.string().max(200),
  subject: z.string().max(500),
  body: z.string(),
  category: z.enum(["outreach", "follow_up", "lifecycle", "system"]),
  is_active: z.boolean(),
});

export type EmailTemplateCreateInput = z.infer<typeof EmailTemplateCreateSchema>;

export const EmailTemplateUpdateSchema = EmailTemplateCreateSchema.partial();
export type EmailTemplateUpdateInput = z.infer<typeof EmailTemplateUpdateSchema>;

// --- LifecycleEmail ---
export const LifecycleEmailCreateSchema = z.object({
  user_id: z.string().max(100),
  template_code: z.string().max(50),
  status: z.enum(["pending", "sent", "skipped", "cancelled"]),
  scheduled_for: z.string(),
  sent_at: z.string().nullable().optional(),
  skip_reason: z.string().max(200).nullable().optional(),
});

export type LifecycleEmailCreateInput = z.infer<typeof LifecycleEmailCreateSchema>;

export const LifecycleEmailUpdateSchema = LifecycleEmailCreateSchema.partial();
export type LifecycleEmailUpdateInput = z.infer<typeof LifecycleEmailUpdateSchema>;

// --- Message ---
export const MessageCreateSchema = z.object({
  user_id: z.string().max(100),
  investor_id: z.string().uuid().nullable().optional(),
  email_account_id: z.string().uuid().nullable().optional(),
  status: z.enum(["draft", "scheduled", "sending", "sent", "failed", "answered"]),
  to_addresses: z.record(z.unknown()),
  cc_addresses: z.record(z.unknown()),
  subject: z.string().max(500),
  from_address: z.string().max(255),
  body: z.string(),
  attachments: z.record(z.unknown()),
  thread_id: z.string().max(200).nullable().optional(),
  provider_message_id: z.string().max(500).nullable().optional(),
  provider_references: z.string().nullable().optional(),
  previous_message_id: z.string().uuid().nullable().optional(),
  scheduled_for: z.string().nullable().optional(),
  job_id: z.string().max(100).nullable().optional(),
});

export type MessageCreateInput = z.infer<typeof MessageCreateSchema>;

export const MessageUpdateSchema = MessageCreateSchema.partial();
export type MessageUpdateInput = z.infer<typeof MessageUpdateSchema>;

// ---------------------------------------------------------------------------
// Schema registry
// ---------------------------------------------------------------------------

export const ENTITY_SCHEMAS: Record<string, { create: z.ZodType; update: z.ZodType }> = {
  'EmailAccount': {
    create: EmailAccountCreateSchema,
    update: EmailAccountUpdateSchema,
  },
  'EmailTemplate': {
    create: EmailTemplateCreateSchema,
    update: EmailTemplateUpdateSchema,
  },
  'LifecycleEmail': {
    create: LifecycleEmailCreateSchema,
    update: LifecycleEmailUpdateSchema,
  },
  'Message': {
    create: MessageCreateSchema,
    update: MessageUpdateSchema,
  },
};

/** Get Zod create schema for an entity. Throws if not found. */
export function getCreateSchema(entityName: string): z.ZodType {
  const entry = ENTITY_SCHEMAS[entityName];
  if (!entry) throw new Error(`No schema for entity "${entityName}"`);
  return entry.create;
}

/** Get Zod update schema for an entity. Throws if not found. */
export function getUpdateSchema(entityName: string): z.ZodType {
  const entry = ENTITY_SCHEMAS[entityName];
  if (!entry) throw new Error(`No schema for entity "${entityName}"`);
  return entry.update;
}
