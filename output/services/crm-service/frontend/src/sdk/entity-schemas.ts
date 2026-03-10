// =============================================================================
// Entity Registry SDK — Zod Schemas
// Generated: 2026-03-10T13:09:26.217926Z
// Entities: 5
// =============================================================================

import { z } from 'zod';

// ---------------------------------------------------------------------------
// Per-entity Create schemas
// ---------------------------------------------------------------------------

// --- Activity ---
export const ActivityCreateSchema = z.object({
  shortlist_id: z.string().uuid(),
  activity_type: z.enum(["email_sent", "email_received", "note", "call", "meeting"]),
  summary: z.string().max(500).nullable().optional(),
  details: z.string().nullable().optional(),
  date: z.string(),
  user_id: z.string().max(100),
  reference_id: z.string().max(100).nullable().optional(),
});

export type ActivityCreateInput = z.infer<typeof ActivityCreateSchema>;

export const ActivityUpdateSchema = ActivityCreateSchema.partial();
export type ActivityUpdateInput = z.infer<typeof ActivityUpdateSchema>;

// --- PipelineStage ---
export const PipelineStageCreateSchema = z.object({
  name: z.string().max(100),
  code: z.string().max(50),
  sequence: z.number(),
  color: z.string().max(20).nullable().optional(),
  is_active: z.boolean(),
});

export type PipelineStageCreateInput = z.infer<typeof PipelineStageCreateSchema>;

export const PipelineStageUpdateSchema = PipelineStageCreateSchema.partial();
export type PipelineStageUpdateInput = z.infer<typeof PipelineStageUpdateSchema>;

// --- Shortlist ---
export const ShortlistCreateSchema = z.object({
  user_id: z.string().max(100),
  investor_id: z.string().uuid(),
  stage_id: z.string().uuid().nullable().optional(),
  status: z.enum(["target", "contacted", "interested", "closed"]),
  notes: z.string().nullable().optional(),
  added_at: z.string(),
});

export type ShortlistCreateInput = z.infer<typeof ShortlistCreateSchema>;

export const ShortlistUpdateSchema = ShortlistCreateSchema.partial();
export type ShortlistUpdateInput = z.infer<typeof ShortlistUpdateSchema>;

// --- ShortlistTag ---
export const ShortlistTagCreateSchema = z.object({
  shortlist_id: z.string().uuid(),
  tag_id: z.string().uuid(),
});

export type ShortlistTagCreateInput = z.infer<typeof ShortlistTagCreateSchema>;

export const ShortlistTagUpdateSchema = ShortlistTagCreateSchema.partial();
export type ShortlistTagUpdateInput = z.infer<typeof ShortlistTagUpdateSchema>;

// --- Tag ---
export const TagCreateSchema = z.object({
  name: z.string().max(100),
  color: z.string().max(20).nullable().optional(),
});

export type TagCreateInput = z.infer<typeof TagCreateSchema>;

export const TagUpdateSchema = TagCreateSchema.partial();
export type TagUpdateInput = z.infer<typeof TagUpdateSchema>;

// ---------------------------------------------------------------------------
// Schema registry
// ---------------------------------------------------------------------------

export const ENTITY_SCHEMAS: Record<string, { create: z.ZodType; update: z.ZodType }> = {
  'Activity': {
    create: ActivityCreateSchema,
    update: ActivityUpdateSchema,
  },
  'PipelineStage': {
    create: PipelineStageCreateSchema,
    update: PipelineStageUpdateSchema,
  },
  'Shortlist': {
    create: ShortlistCreateSchema,
    update: ShortlistUpdateSchema,
  },
  'ShortlistTag': {
    create: ShortlistTagCreateSchema,
    update: ShortlistTagUpdateSchema,
  },
  'Tag': {
    create: TagCreateSchema,
    update: TagUpdateSchema,
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
