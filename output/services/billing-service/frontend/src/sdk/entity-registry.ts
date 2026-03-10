// =============================================================================
// Entity Registry SDK — Metadata
// Generated: 2026-03-10T13:09:44.854672Z
// Entities: 3
// =============================================================================

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type FieldType =
  | 'string'
  | 'number'
  | 'decimal'
  | 'boolean'
  | 'date'
  | 'uuid'
  | 'json'
  | 'enum';

export interface FKConfig {
  endpoint: string;
  valueField: string;
  labelField: string;
  freeSolo?: boolean;
}

export interface EntityFieldMeta {
  name: string;
  label: string;
  type: FieldType;
  rawType: string;
  required: boolean;
  nullable: boolean;
  unique: boolean;
  isFK: boolean;
  isSystem: boolean;
  fk?: FKConfig;
  enumValues?: string[];
  description?: string;
  maxLength?: number;
  defaultValue?: unknown;
}

export interface EntityRelationshipMeta {
  name: string;
  type: string;
  targetEntity: string;
  foreignKey: string;
}

export interface EntityMeta {
  name: string;
  slug: string;
  pluralSlug: string;
  label: string;
  tableName: string;
  endpoint: string;
  description: string;
  fields: EntityFieldMeta[];
  relationships: EntityRelationshipMeta[];
  labelField: string;
  hasTimestamps: boolean;
  hasSoftDelete: boolean;
  formDisplay: string;
}

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

export const ENTITY_REGISTRY: Record<string, EntityMeta> = {
  'Plan': {
    name: 'Plan',
    slug: 'plan',
    pluralSlug: 'plans',
    label: 'Plan',
    tableName: 'vs_plan',
    endpoint: '/api/v1/plans',
    description: "Subscription plan tier definition",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'name',
        label: "Name",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: true,
        isFK: false,
        isSystem: false,
        maxLength: 50,
      },
      {
        name: 'code',
        label: "Code",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: true,
        isFK: false,
        isSystem: false,
        enumValues: ["free", "starter", "pro", "scale"],
        maxLength: 20,
      },
      {
        name: 'price_monthly',
        label: "Price Monthly",
        type: 'decimal',
        rawType: 'decimal',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: "0.00",
      },
      {
        name: 'price_quarterly',
        label: "Price Quarterly",
        type: 'decimal',
        rawType: 'decimal',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'price_annually',
        label: "Price Annually",
        type: 'decimal',
        rawType: 'decimal',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'limits',
        label: "Limits",
        type: 'json',
        rawType: 'json',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Usage limits: {ai_drafts_per_day, emails_per_day, emails_per_month, investors_per_day, investors_per_month, follow_ups_per_month}",
      },
      {
        name: 'features',
        label: "Features",
        type: 'json',
        rawType: 'json',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Feature flags: {show_full_contact_info, advanced_filters, priority_support, custom_integrations, can_download_csv}",
      },
      {
        name: 'usage_basis',
        label: "Usage Basis",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        enumValues: ["daily", "monthly"],
        description: "Whether limits are enforced daily (free) or monthly (paid)",
        maxLength: 10,
      },
      {
        name: 'is_active',
        label: "Is Active",
        type: 'boolean',
        rawType: 'boolean',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: true,
      },
    ],
    relationships: [
    ],
  },
  'Subscription': {
    name: 'Subscription',
    slug: 'subscription',
    pluralSlug: 'subscriptions',
    label: 'Subscription',
    tableName: 'vs_subscription',
    endpoint: '/api/v1/subscriptions',
    description: "User subscription linked to Stripe",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'user_id',
        label: "User Id",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: true,
        isFK: false,
        isSystem: false,
        description: "Auth user reference \u2014 one subscription per user",
        maxLength: 100,
      },
      {
        name: 'plan_id',
        label: "Plan",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/plans',
          valueField: 'id',
          labelField: 'name',
        },
      },
      {
        name: 'status',
        label: "Status",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        enumValues: ["trialing", "active", "past_due", "cancelled", "incomplete"],
        maxLength: 30,
        defaultValue: "trialing",
      },
      {
        name: 'stripe_customer_id',
        label: "Stripe Customer Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: true,
        isFK: false,
        isSystem: false,
        maxLength: 100,
      },
      {
        name: 'stripe_subscription_id',
        label: "Stripe Subscription Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: true,
        isFK: false,
        isSystem: false,
        maxLength: 100,
      },
      {
        name: 'stripe_payment_method_id',
        label: "Stripe Payment Method Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        maxLength: 100,
      },
      {
        name: 'billing_period',
        label: "Billing Period",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        enumValues: ["monthly", "quarterly", "annually"],
        maxLength: 20,
      },
      {
        name: 'current_period_end',
        label: "Current Period End",
        type: 'date',
        rawType: 'datetime',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'cancel_at_period_end',
        label: "Cancel At Period End",
        type: 'boolean',
        rawType: 'boolean',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: false,
      },
      {
        name: 'trial_ends_at',
        label: "Trial Ends At",
        type: 'date',
        rawType: 'datetime',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
    ],
    relationships: [
      {
        name: 'plan',
        type: 'many_to_one',
        targetEntity: 'Plan',
        foreignKey: 'plan_id',
      },
    ],
  },
  'UsageRecord': {
    name: 'UsageRecord',
    slug: 'usage-record',
    pluralSlug: 'usage-records',
    label: 'Usage Record',
    tableName: 'vs_usage_record',
    endpoint: '/api/v1/usage-records',
    description: "Daily usage tracking for subscription limit enforcement",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'user_id',
        label: "User Id",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        maxLength: 100,
      },
      {
        name: 'date',
        label: "Date",
        type: 'date',
        rawType: 'date',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Tracking date",
      },
      {
        name: 'month',
        label: "Month",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Month number (1-12)",
      },
      {
        name: 'year',
        label: "Year",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'ai_drafts_used',
        label: "Ai Drafts Used",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: 0,
      },
      {
        name: 'emails_sent',
        label: "Emails Sent",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: 0,
      },
      {
        name: 'investors_added',
        label: "Investors Added",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: 0,
      },
      {
        name: 'monthly_emails_sent',
        label: "Monthly Emails Sent",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: 0,
      },
      {
        name: 'monthly_investors_added',
        label: "Monthly Investors Added",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: 0,
      },
      {
        name: 'monthly_follow_ups_sent',
        label: "Monthly Follow Ups Sent",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: 0,
      },
    ],
    relationships: [
    ],
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Get entity metadata by name. Throws if not found. */
export function getEntity(name: string): EntityMeta {
  const meta = ENTITY_REGISTRY[name];
  if (!meta) {
    throw new Error(`Entity "${name}" not found in registry. Available: ${getAllEntityNames().join(', ')}`);
  }
  return meta;
}

/** Get entity metadata by name, returning undefined if not found. */
export function findEntity(name: string): EntityMeta | undefined {
  return ENTITY_REGISTRY[name];
}

/** Get all registered entity names. */
export function getAllEntityNames(): string[] {
  return Object.keys(ENTITY_REGISTRY);
}

/** Get fields suitable for a form (excludes system fields like id, timestamps). */
export function getEntityFieldsForForm(name: string): EntityFieldMeta[] {
  return getEntity(name).fields.filter((f) => !f.isSystem);
}

/** Get fields suitable for a table (excludes system + FK UUIDs + json/text). */
export function getEntityFieldsForTable(name: string): EntityFieldMeta[] {
  return getEntity(name).fields.filter(
    (f) => !f.isSystem && !f.isFK && f.type !== 'json',
  );
}

/** Get FK fields that need dropdown loading. */
export function getEntityFKFields(name: string): EntityFieldMeta[] {
  return getEntity(name).fields.filter((f) => f.fk != null);
}

/** Find entity by slug (singular or plural kebab-case). */
export function getEntityBySlug(slug: string): EntityMeta | undefined {
  return Object.values(ENTITY_REGISTRY).find(
    (e) => e.slug === slug || e.pluralSlug === slug,
  );
}
