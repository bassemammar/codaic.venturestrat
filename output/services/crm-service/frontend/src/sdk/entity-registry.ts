// =============================================================================
// Entity Registry SDK — Metadata
// Generated: 2026-03-10T13:09:26.217926Z
// Entities: 5
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
  'Activity': {
    name: 'Activity',
    slug: 'activity',
    pluralSlug: 'activities',
    label: 'Activity',
    tableName: 'vs_activity',
    endpoint: '/api/v1/activities',
    description: "Outreach activity touchpoint on a shortlisted investor",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'shortlist_id',
        label: "Shortlist",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/shortlists',
          valueField: 'id',
          labelField: 'name',
        },
        description: "Parent shortlist record",
      },
      {
        name: 'activity_type',
        label: "Activity Type",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        enumValues: ["email_sent", "email_received", "note", "call", "meeting"],
        maxLength: 30,
      },
      {
        name: 'summary',
        label: "Summary",
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
        name: 'details',
        label: "Details",
        type: 'string',
        rawType: 'text',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'date',
        label: "Date",
        type: 'date',
        rawType: 'datetime',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "When the activity occurred",
      },
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
        description: "Auth user who performed the activity",
        maxLength: 100,
      },
      {
        name: 'reference_id',
        label: "Reference Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "External reference, e.g. message ID",
        maxLength: 100,
      },
    ],
    relationships: [
      {
        name: 'shortlist',
        type: 'many_to_one',
        targetEntity: 'Shortlist',
        foreignKey: 'shortlist_id',
      },
    ],
  },
  'PipelineStage': {
    name: 'PipelineStage',
    slug: 'pipeline-stage',
    pluralSlug: 'pipeline-stages',
    label: 'Pipeline Stage',
    tableName: 'vs_pipeline_stage',
    endpoint: '/api/v1/pipeline-stages',
    description: "CRM pipeline stage for investor shortlisting",
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
        description: "Stage display name",
        maxLength: 100,
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
        description: "Stage code for programmatic use",
        maxLength: 50,
      },
      {
        name: 'sequence',
        label: "Sequence",
        type: 'number',
        rawType: 'integer',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Display ordering",
      },
      {
        name: 'color',
        label: "Color",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Hex color for Kanban column",
        maxLength: 20,
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
  'Shortlist': {
    name: 'Shortlist',
    slug: 'shortlist',
    pluralSlug: 'shortlists',
    label: 'Shortlist',
    tableName: 'vs_shortlist',
    endpoint: '/api/v1/shortlists',
    description: "User\u0027s investor pipeline \u2014 tracks shortlisted investors with CRM status",
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
        description: "Auth user reference",
        maxLength: 100,
      },
      {
        name: 'investor_id',
        label: "Investor Id",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Cross-service reference to investor-service Investor",
      },
      {
        name: 'stage_id',
        label: "Stage",
        type: 'uuid',
        rawType: 'uuid',
        required: false,
        nullable: true,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/pipeline-stages',
          valueField: 'id',
          labelField: 'name',
        },
        description: "Pipeline stage reference",
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
        enumValues: ["target", "contacted", "interested", "closed"],
        description: "Current pipeline status",
        maxLength: 30,
        defaultValue: "target",
      },
      {
        name: 'notes',
        label: "Notes",
        type: 'string',
        rawType: 'text',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'added_at',
        label: "Added At",
        type: 'date',
        rawType: 'datetime',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "When investor was shortlisted",
      },
    ],
    relationships: [
      {
        name: 'stage',
        type: 'many_to_one',
        targetEntity: 'PipelineStage',
        foreignKey: 'stage_id',
      },
      {
        name: 'activities',
        type: 'one_to_many',
        targetEntity: 'Activity',
        foreignKey: 'shortlist_id',
      },
      {
        name: 'tags',
        type: 'one_to_many',
        targetEntity: 'ShortlistTag',
        foreignKey: 'shortlist_id',
      },
    ],
  },
  'ShortlistTag': {
    name: 'ShortlistTag',
    slug: 'shortlist-tag',
    pluralSlug: 'shortlist-tags',
    label: 'Shortlist Tag',
    tableName: 'vs_shortlist_tag',
    endpoint: '/api/v1/shortlist-tags',
    description: "Many-to-many junction between shortlists and tags",
    labelField: 'name',
    hasTimestamps: true,
    hasSoftDelete: false,
    formDisplay: 'modal',
    fields: [
      {
        name: 'shortlist_id',
        label: "Shortlist",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/shortlists',
          valueField: 'id',
          labelField: 'name',
        },
      },
      {
        name: 'tag_id',
        label: "Tag",
        type: 'uuid',
        rawType: 'uuid',
        required: true,
        nullable: false,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/tags',
          valueField: 'id',
          labelField: 'name',
        },
      },
    ],
    relationships: [
      {
        name: 'shortlist',
        type: 'many_to_one',
        targetEntity: 'Shortlist',
        foreignKey: 'shortlist_id',
      },
      {
        name: 'tag',
        type: 'many_to_one',
        targetEntity: 'Tag',
        foreignKey: 'tag_id',
      },
    ],
  },
  'Tag': {
    name: 'Tag',
    slug: 'tag',
    pluralSlug: 'tags',
    label: 'Tag',
    tableName: 'vs_tag',
    endpoint: '/api/v1/tags',
    description: "Tag for categorizing shortlisted investors",
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
        maxLength: 100,
      },
      {
        name: 'color',
        label: "Color",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Hex color code",
        maxLength: 20,
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
