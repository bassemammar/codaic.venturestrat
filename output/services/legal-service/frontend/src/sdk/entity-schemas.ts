// =============================================================================
// Entity Registry SDK — Zod Schemas
// Generated: 2026-03-10T20:43:56.023466Z
// Entities: 10
// =============================================================================

import { z } from 'zod';

// ---------------------------------------------------------------------------
// Per-entity Create schemas
// ---------------------------------------------------------------------------

// --- ContactPerson ---
export const ContactPersonCreateSchema = z.object({
  user_id: z.string().max(100),
  legal_entity_id: z.string().uuid().nullable().optional(),
  full_name: z.string().max(100),
  email: z.string().max(255),
  role: z.enum(["founder", "employee", "investor", "advisor", "director", "counterparty"]),
  is_primary: z.boolean(),
  date_of_birth: z.string().nullable().optional(),
  residential_address_id: z.string().uuid().nullable().optional(),
});

export type ContactPersonCreateInput = z.infer<typeof ContactPersonCreateSchema>;

export const ContactPersonUpdateSchema = ContactPersonCreateSchema.partial();
export type ContactPersonUpdateInput = z.infer<typeof ContactPersonUpdateSchema>;

// --- DocumentParty ---
export const DocumentPartyCreateSchema = z.object({
  legal_document_id: z.string().uuid(),
  legal_entity_id: z.string().uuid(),
  signatory_id: z.string().uuid().nullable().optional(),
  party_role: z.enum(["party_a", "party_b", "disclosing", "receiving", "employer", "employee", "investor", "company"]),
  party_label: z.string().max(50).nullable().optional(),
});

export type DocumentPartyCreateInput = z.infer<typeof DocumentPartyCreateSchema>;

export const DocumentPartyUpdateSchema = DocumentPartyCreateSchema.partial();
export type DocumentPartyUpdateInput = z.infer<typeof DocumentPartyUpdateSchema>;

// --- DocumentTemplate ---
export const DocumentTemplateCreateSchema = z.object({
  name: z.string().max(100),
  document_type: z.enum(["mutual_nda", "one_way_nda", "founders_agreement", "employment_agreement", "safe_agreement", "certificate_of_incorporation", "master_services_agreement"]),
  jurisdiction: z.enum(["england_wales", "scotland", "delaware", "california", "difc", "ksa", "universal"]),
  version: z.string().max(20),
  description: z.string().nullable().optional(),
  template_content: z.string(),
  configuration_schema: z.record(z.unknown()).nullable().optional(),
  is_active: z.boolean(),
  clause_ids: z.record(z.unknown()).nullable().optional(),
});

export type DocumentTemplateCreateInput = z.infer<typeof DocumentTemplateCreateSchema>;

export const DocumentTemplateUpdateSchema = DocumentTemplateCreateSchema.partial();
export type DocumentTemplateUpdateInput = z.infer<typeof DocumentTemplateUpdateSchema>;

// --- EquityGrant ---
export const EquityGrantCreateSchema = z.object({
  legal_entity_id: z.string().uuid(),
  holder_person_id: z.string().uuid().nullable().optional(),
  holder_entity_id: z.string().uuid().nullable().optional(),
  holder_type: z.enum(["person", "entity"]),
  share_class: z.enum(["common", "preferred_seed", "preferred_a", "preferred_b", "preferred_c", "options"]),
  number_of_shares: z.number(),
  percentage: z.number(),
  valuation: z.number().nullable().optional(),
  issue_date: z.string(),
  source_document_id: z.string().uuid().nullable().optional(),
});

export type EquityGrantCreateInput = z.infer<typeof EquityGrantCreateSchema>;

export const EquityGrantUpdateSchema = EquityGrantCreateSchema.partial();
export type EquityGrantUpdateInput = z.infer<typeof EquityGrantUpdateSchema>;

// --- InvestmentTerm ---
export const InvestmentTermCreateSchema = z.object({
  legal_entity_id: z.string().uuid(),
  investor_person_id: z.string().uuid(),
  investor_id: z.string().uuid().nullable().optional(),
  investment_amount: z.number(),
  currency: z.enum(["GBP", "USD", "EUR", "AED", "SAR"]),
  valuation_cap: z.number().nullable().optional(),
  discount_percentage: z.number().nullable().optional(),
  investment_date: z.string(),
  pro_rata_rights: z.boolean(),
  source_document_id: z.string().uuid().nullable().optional(),
});

export type InvestmentTermCreateInput = z.infer<typeof InvestmentTermCreateSchema>;

export const InvestmentTermUpdateSchema = InvestmentTermCreateSchema.partial();
export type InvestmentTermUpdateInput = z.infer<typeof InvestmentTermUpdateSchema>;

// --- LegalAddress ---
export const LegalAddressCreateSchema = z.object({
  address_line_1: z.string().max(100),
  address_line_2: z.string().max(100).nullable().optional(),
  city: z.string().max(50),
  state_province: z.string().max(50).nullable().optional(),
  postal_code: z.string().max(20),
  country: z.string().max(2),
  jurisdiction: z.enum(["england_wales", "scotland", "northern_ireland", "delaware", "california", "new_york", "difc", "uae_mainland", "ksa", "egypt"]),
});

export type LegalAddressCreateInput = z.infer<typeof LegalAddressCreateSchema>;

export const LegalAddressUpdateSchema = LegalAddressCreateSchema.partial();
export type LegalAddressUpdateInput = z.infer<typeof LegalAddressUpdateSchema>;

// --- LegalDocument ---
export const LegalDocumentCreateSchema = z.object({
  user_id: z.string().max(100),
  template_id: z.string().uuid().nullable().optional(),
  investor_id: z.string().uuid().nullable().optional(),
  document_type: z.enum(["mutual_nda", "one_way_nda", "founders_agreement", "employment_agreement", "safe_agreement", "certificate_of_incorporation", "master_services_agreement"]),
  title: z.string().max(255),
  status: z.enum(["draft", "generated", "reviewed", "signed", "archived"]),
  configuration: z.record(z.unknown()),
  content_markdown: z.string().nullable().optional(),
  content_html: z.string().nullable().optional(),
  file_path_docx: z.string().max(500).nullable().optional(),
  file_path_pdf: z.string().max(500).nullable().optional(),
  version: z.number(),
  generated_at: z.string().nullable().optional(),
});

export type LegalDocumentCreateInput = z.infer<typeof LegalDocumentCreateSchema>;

export const LegalDocumentUpdateSchema = LegalDocumentCreateSchema.partial();
export type LegalDocumentUpdateInput = z.infer<typeof LegalDocumentUpdateSchema>;

// --- LegalEntity ---
export const LegalEntityCreateSchema = z.object({
  user_id: z.string().max(100),
  legal_name: z.string().max(200),
  jurisdiction: z.enum(["england_wales", "scotland", "northern_ireland", "delaware", "california", "new_york", "difc", "uae_mainland", "ksa", "egypt"]),
  registration_number: z.string().max(50),
  incorporation_date: z.string().nullable().optional(),
  authorized_shares: z.number().nullable().optional(),
  par_value: z.number().nullable().optional(),
  registered_address_id: z.string().uuid().nullable().optional(),
});

export type LegalEntityCreateInput = z.infer<typeof LegalEntityCreateSchema>;

export const LegalEntityUpdateSchema = LegalEntityCreateSchema.partial();
export type LegalEntityUpdateInput = z.infer<typeof LegalEntityUpdateSchema>;

// --- TemplateClause ---
export const TemplateClauseCreateSchema = z.object({
  name: z.string().max(100),
  category: z.enum(["purpose", "data_protection", "duration", "confidentiality_survival", "permitted_recipients", "return_destruction", "ai_ml_restrictions", "dispute_resolution", "non_solicitation", "governing_law", "additional"]),
  description: z.string().nullable().optional(),
  variants: z.record(z.unknown()),
  default_variant: z.string().max(10),
  applicable_document_types: z.record(z.unknown()),
  sort_order: z.number(),
  is_required: z.boolean(),
});

export type TemplateClauseCreateInput = z.infer<typeof TemplateClauseCreateSchema>;

export const TemplateClauseUpdateSchema = TemplateClauseCreateSchema.partial();
export type TemplateClauseUpdateInput = z.infer<typeof TemplateClauseUpdateSchema>;

// --- VestingSchedule ---
export const VestingScheduleCreateSchema = z.object({
  equity_grant_id: z.string().uuid(),
  total_period_months: z.number(),
  cliff_months: z.number(),
  start_date: z.string(),
  acceleration_trigger: z.enum(["none", "single_trigger", "double_trigger"]),
});

export type VestingScheduleCreateInput = z.infer<typeof VestingScheduleCreateSchema>;

export const VestingScheduleUpdateSchema = VestingScheduleCreateSchema.partial();
export type VestingScheduleUpdateInput = z.infer<typeof VestingScheduleUpdateSchema>;

// ---------------------------------------------------------------------------
// Schema registry
// ---------------------------------------------------------------------------

export const ENTITY_SCHEMAS: Record<string, { create: z.ZodType; update: z.ZodType }> = {
  'ContactPerson': {
    create: ContactPersonCreateSchema,
    update: ContactPersonUpdateSchema,
  },
  'DocumentParty': {
    create: DocumentPartyCreateSchema,
    update: DocumentPartyUpdateSchema,
  },
  'DocumentTemplate': {
    create: DocumentTemplateCreateSchema,
    update: DocumentTemplateUpdateSchema,
  },
  'EquityGrant': {
    create: EquityGrantCreateSchema,
    update: EquityGrantUpdateSchema,
  },
  'InvestmentTerm': {
    create: InvestmentTermCreateSchema,
    update: InvestmentTermUpdateSchema,
  },
  'LegalAddress': {
    create: LegalAddressCreateSchema,
    update: LegalAddressUpdateSchema,
  },
  'LegalDocument': {
    create: LegalDocumentCreateSchema,
    update: LegalDocumentUpdateSchema,
  },
  'LegalEntity': {
    create: LegalEntityCreateSchema,
    update: LegalEntityUpdateSchema,
  },
  'TemplateClause': {
    create: TemplateClauseCreateSchema,
    update: TemplateClauseUpdateSchema,
  },
  'VestingSchedule': {
    create: VestingScheduleCreateSchema,
    update: VestingScheduleUpdateSchema,
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
