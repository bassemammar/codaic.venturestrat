// =============================================================================
// Entity Registry SDK — Zod Schemas
// Generated: 2026-03-10T13:09:13.282660Z
// Entities: 6
// =============================================================================

import { z } from 'zod';

// ---------------------------------------------------------------------------
// Per-entity Create schemas
// ---------------------------------------------------------------------------

// --- Investor ---
export const InvestorCreateSchema = z.object({
  name: z.string().max(300),
  avatar: z.string().max(500).nullable().optional(),
  website: z.string().max(500).nullable().optional(),
  phone: z.string().max(50).nullable().optional(),
  title: z.string().max(200).nullable().optional(),
  external_id: z.string().max(100),
  city: z.string().max(100).nullable().optional(),
  state: z.string().max(100).nullable().optional(),
  country: z.string().max(100).nullable().optional(),
  company_name: z.string().max(300).nullable().optional(),
  stages: z.record(z.unknown()),
  investor_types: z.record(z.unknown()),
  social_links: z.record(z.unknown()).nullable().optional(),
  pipelines: z.record(z.unknown()).nullable().optional(),
  founded_companies: z.record(z.unknown()).nullable().optional(),
  country_priority: z.number(),
  source_data: z.record(z.unknown()).nullable().optional(),
});

export type InvestorCreateInput = z.infer<typeof InvestorCreateSchema>;

export const InvestorUpdateSchema = InvestorCreateSchema.partial();
export type InvestorUpdateInput = z.infer<typeof InvestorUpdateSchema>;

// --- InvestorEmail ---
export const InvestorEmailCreateSchema = z.object({
  investor_id: z.string().uuid(),
  email: z.string().max(255),
  status: z.enum(["valid", "invalid", "pending", "unknown"]),
});

export type InvestorEmailCreateInput = z.infer<typeof InvestorEmailCreateSchema>;

export const InvestorEmailUpdateSchema = InvestorEmailCreateSchema.partial();
export type InvestorEmailUpdateInput = z.infer<typeof InvestorEmailUpdateSchema>;

// --- InvestorMarket ---
export const InvestorMarketCreateSchema = z.object({
  investor_id: z.string().uuid(),
  market_id: z.string().uuid(),
});

export type InvestorMarketCreateInput = z.infer<typeof InvestorMarketCreateSchema>;

export const InvestorMarketUpdateSchema = InvestorMarketCreateSchema.partial();
export type InvestorMarketUpdateInput = z.infer<typeof InvestorMarketUpdateSchema>;

// --- InvestorPastInvestment ---
export const InvestorPastInvestmentCreateSchema = z.object({
  investor_id: z.string().uuid(),
  past_investment_id: z.string().uuid(),
});

export type InvestorPastInvestmentCreateInput = z.infer<typeof InvestorPastInvestmentCreateSchema>;

export const InvestorPastInvestmentUpdateSchema = InvestorPastInvestmentCreateSchema.partial();
export type InvestorPastInvestmentUpdateInput = z.infer<typeof InvestorPastInvestmentUpdateSchema>;

// --- Market ---
export const MarketCreateSchema = z.object({
  title: z.string().max(255),
  is_country: z.boolean(),
});

export type MarketCreateInput = z.infer<typeof MarketCreateSchema>;

export const MarketUpdateSchema = MarketCreateSchema.partial();
export type MarketUpdateInput = z.infer<typeof MarketUpdateSchema>;

// --- PastInvestment ---
export const PastInvestmentCreateSchema = z.object({
  title: z.string().max(255),
});

export type PastInvestmentCreateInput = z.infer<typeof PastInvestmentCreateSchema>;

export const PastInvestmentUpdateSchema = PastInvestmentCreateSchema.partial();
export type PastInvestmentUpdateInput = z.infer<typeof PastInvestmentUpdateSchema>;

// ---------------------------------------------------------------------------
// Schema registry
// ---------------------------------------------------------------------------

export const ENTITY_SCHEMAS: Record<string, { create: z.ZodType; update: z.ZodType }> = {
  'Investor': {
    create: InvestorCreateSchema,
    update: InvestorUpdateSchema,
  },
  'InvestorEmail': {
    create: InvestorEmailCreateSchema,
    update: InvestorEmailUpdateSchema,
  },
  'InvestorMarket': {
    create: InvestorMarketCreateSchema,
    update: InvestorMarketUpdateSchema,
  },
  'InvestorPastInvestment': {
    create: InvestorPastInvestmentCreateSchema,
    update: InvestorPastInvestmentUpdateSchema,
  },
  'Market': {
    create: MarketCreateSchema,
    update: MarketUpdateSchema,
  },
  'PastInvestment': {
    create: PastInvestmentCreateSchema,
    update: PastInvestmentUpdateSchema,
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
