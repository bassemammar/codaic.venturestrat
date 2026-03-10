// =============================================================================
// Entity Registry SDK — Zod Schemas
// Generated: 2026-03-10T13:09:44.854672Z
// Entities: 3
// =============================================================================

import { z } from 'zod';

// ---------------------------------------------------------------------------
// Per-entity Create schemas
// ---------------------------------------------------------------------------

// --- Plan ---
export const PlanCreateSchema = z.object({
  name: z.string().max(50),
  code: z.enum(["free", "starter", "pro", "scale"]),
  price_monthly: z.number(),
  price_quarterly: z.number().nullable().optional(),
  price_annually: z.number().nullable().optional(),
  limits: z.record(z.unknown()),
  features: z.record(z.unknown()),
  usage_basis: z.enum(["daily", "monthly"]),
  is_active: z.boolean(),
});

export type PlanCreateInput = z.infer<typeof PlanCreateSchema>;

export const PlanUpdateSchema = PlanCreateSchema.partial();
export type PlanUpdateInput = z.infer<typeof PlanUpdateSchema>;

// --- Subscription ---
export const SubscriptionCreateSchema = z.object({
  user_id: z.string().max(100),
  plan_id: z.string().uuid(),
  status: z.enum(["trialing", "active", "past_due", "cancelled", "incomplete"]),
  stripe_customer_id: z.string().max(100).nullable().optional(),
  stripe_subscription_id: z.string().max(100).nullable().optional(),
  stripe_payment_method_id: z.string().max(100).nullable().optional(),
  billing_period: z.enum(["monthly", "quarterly", "annually"]).nullable().optional(),
  current_period_end: z.string().nullable().optional(),
  cancel_at_period_end: z.boolean(),
  trial_ends_at: z.string().nullable().optional(),
});

export type SubscriptionCreateInput = z.infer<typeof SubscriptionCreateSchema>;

export const SubscriptionUpdateSchema = SubscriptionCreateSchema.partial();
export type SubscriptionUpdateInput = z.infer<typeof SubscriptionUpdateSchema>;

// --- UsageRecord ---
export const UsageRecordCreateSchema = z.object({
  user_id: z.string().max(100),
  date: z.string(),
  month: z.number(),
  year: z.number(),
  ai_drafts_used: z.number(),
  emails_sent: z.number(),
  investors_added: z.number(),
  monthly_emails_sent: z.number(),
  monthly_investors_added: z.number(),
  monthly_follow_ups_sent: z.number(),
});

export type UsageRecordCreateInput = z.infer<typeof UsageRecordCreateSchema>;

export const UsageRecordUpdateSchema = UsageRecordCreateSchema.partial();
export type UsageRecordUpdateInput = z.infer<typeof UsageRecordUpdateSchema>;

// ---------------------------------------------------------------------------
// Schema registry
// ---------------------------------------------------------------------------

export const ENTITY_SCHEMAS: Record<string, { create: z.ZodType; update: z.ZodType }> = {
  'Plan': {
    create: PlanCreateSchema,
    update: PlanUpdateSchema,
  },
  'Subscription': {
    create: SubscriptionCreateSchema,
    update: SubscriptionUpdateSchema,
  },
  'UsageRecord': {
    create: UsageRecordCreateSchema,
    update: UsageRecordUpdateSchema,
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
