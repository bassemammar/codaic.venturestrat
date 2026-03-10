// =============================================================================
// Entity Registry SDK — Metadata
// Generated: 2026-03-10T13:09:13.282660Z
// Entities: 6
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
  'Investor': {
    name: 'Investor',
    slug: 'investor',
    pluralSlug: 'investors',
    label: 'Investor',
    tableName: 'vs_investor',
    endpoint: '/api/v1/investors',
    description: "VC investor profile with contact info, location, stages, types, and social links",
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
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Full name of the investor",
        maxLength: 300,
      },
      {
        name: 'avatar',
        label: "Avatar",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "S3 signed URL for profile image",
        maxLength: 500,
      },
      {
        name: 'website',
        label: "Website",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        maxLength: 500,
      },
      {
        name: 'phone',
        label: "Phone",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        maxLength: 50,
      },
      {
        name: 'title',
        label: "Title",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Job title, e.g. Managing Partner",
        maxLength: 200,
      },
      {
        name: 'external_id',
        label: "External Id",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Original source ID from data import",
        maxLength: 100,
      },
      {
        name: 'city',
        label: "City",
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
        name: 'state',
        label: "State",
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
        name: 'country',
        label: "Country",
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
        name: 'company_name',
        label: "Company Name",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Fund or firm name",
        maxLength: 300,
      },
      {
        name: 'stages',
        label: "Stages",
        type: 'json',
        rawType: 'json',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Investment stages, e.g. [\"Seed\", \"Series A\"]",
        defaultValue: "[]",
      },
      {
        name: 'investor_types',
        label: "Investor Types",
        type: 'json',
        rawType: 'json',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Investor types, e.g. [\"Angel\", \"VC\"]",
        defaultValue: "[]",
      },
      {
        name: 'social_links',
        label: "Social Links",
        type: 'json',
        rawType: 'json',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Social media links: {linkedin, twitter, crunchbase}",
      },
      {
        name: 'pipelines',
        label: "Pipelines",
        type: 'json',
        rawType: 'json',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Deal pipeline data from source",
      },
      {
        name: 'founded_companies',
        label: "Founded Companies",
        type: 'json',
        rawType: 'json',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'country_priority',
        label: "Country Priority",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Sorting weight for country-based ordering",
        defaultValue: 2,
      },
      {
        name: 'source_data',
        label: "Source Data",
        type: 'json',
        rawType: 'json',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Raw import data from original source",
      },
    ],
    relationships: [
      {
        name: 'emails',
        type: 'one_to_many',
        targetEntity: 'InvestorEmail',
        foreignKey: 'investor_id',
      },
      {
        name: 'markets',
        type: 'one_to_many',
        targetEntity: 'InvestorMarket',
        foreignKey: 'investor_id',
      },
      {
        name: 'past_investments',
        type: 'one_to_many',
        targetEntity: 'InvestorPastInvestment',
        foreignKey: 'investor_id',
      },
    ],
  },
  'InvestorEmail': {
    name: 'InvestorEmail',
    slug: 'investor-email',
    pluralSlug: 'investor-emails',
    label: 'Investor Email',
    tableName: 'vs_investor_email',
    endpoint: '/api/v1/investor-emails',
    description: "Email addresses associated with an investor",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'investor_id',
        label: "Investor",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/investors',
          valueField: 'id',
          labelField: 'name',
        },
        description: "Reference to the investor",
      },
      {
        name: 'email',
        label: "Email",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        maxLength: 255,
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
        enumValues: ["valid", "invalid", "pending", "unknown"],
        description: "Email validation status",
        maxLength: 20,
        defaultValue: "valid",
      },
    ],
    relationships: [
      {
        name: 'investor',
        type: 'many_to_one',
        targetEntity: 'Investor',
        foreignKey: 'investor_id',
      },
    ],
  },
  'InvestorMarket': {
    name: 'InvestorMarket',
    slug: 'investor-market',
    pluralSlug: 'investor-markets',
    label: 'Investor Market',
    tableName: 'vs_investor_market',
    endpoint: '/api/v1/investor-markets',
    description: "Many-to-many junction between investors and markets",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'investor_id',
        label: "Investor",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/investors',
          valueField: 'id',
          labelField: 'name',
        },
      },
      {
        name: 'market_id',
        label: "Market",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/markets',
          valueField: 'id',
          labelField: 'name',
        },
      },
    ],
    relationships: [
      {
        name: 'investor',
        type: 'many_to_one',
        targetEntity: 'Investor',
        foreignKey: 'investor_id',
      },
      {
        name: 'market',
        type: 'many_to_one',
        targetEntity: 'Market',
        foreignKey: 'market_id',
      },
    ],
  },
  'InvestorPastInvestment': {
    name: 'InvestorPastInvestment',
    slug: 'investor-past-investment',
    pluralSlug: 'investor-past-investments',
    label: 'Investor Past Investment',
    tableName: 'vs_investor_past_investment',
    endpoint: '/api/v1/investor-past-investments',
    description: "Many-to-many junction between investors and their past investments",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'investor_id',
        label: "Investor",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/investors',
          valueField: 'id',
          labelField: 'name',
        },
      },
      {
        name: 'past_investment_id',
        label: "Past Investment",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/past-investments',
          valueField: 'id',
          labelField: 'name',
        },
      },
    ],
    relationships: [
      {
        name: 'investor',
        type: 'many_to_one',
        targetEntity: 'Investor',
        foreignKey: 'investor_id',
      },
      {
        name: 'past_investment',
        type: 'many_to_one',
        targetEntity: 'PastInvestment',
        foreignKey: 'past_investment_id',
      },
    ],
  },
  'Market': {
    name: 'Market',
    slug: 'market',
    pluralSlug: 'markets',
    label: 'Market',
    tableName: 'vs_market',
    endpoint: '/api/v1/markets',
    description: "Market sector or industry focus category",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'title',
        label: "Title",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: true,
        isFK: false,
        isSystem: false,
        description: "Market/sector name",
        maxLength: 255,
      },
      {
        name: 'is_country',
        label: "Is Country",
        type: 'boolean',
        rawType: 'boolean',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Whether this is a country-based market category",
        defaultValue: false,
      },
    ],
    relationships: [
    ],
  },
  'PastInvestment': {
    name: 'PastInvestment',
    slug: 'past-investment',
    pluralSlug: 'past-investments',
    label: 'Past Investment',
    tableName: 'vs_past_investment',
    endpoint: '/api/v1/past-investments',
    description: "Portfolio company that an investor has previously invested in",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'title',
        label: "Title",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: true,
        isFK: false,
        isSystem: false,
        description: "Company name",
        maxLength: 255,
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
