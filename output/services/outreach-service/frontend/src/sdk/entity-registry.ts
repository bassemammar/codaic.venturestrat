// =============================================================================
// Entity Registry SDK — Metadata
// Generated: 2026-03-10T13:09:42.032621Z
// Entities: 4
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
  'EmailAccount': {
    name: 'EmailAccount',
    slug: 'email-account',
    pluralSlug: 'email-accounts',
    label: 'Email Account',
    tableName: 'vs_email_account',
    endpoint: '/api/v1/email-accounts',
    description: "OAuth email account for sending via Gmail, Microsoft, or SendGrid",
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
        name: 'provider',
        label: "Provider",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        enumValues: ["gmail", "microsoft", "sendgrid"],
        maxLength: 30,
      },
      {
        name: 'email_address',
        label: "Email Address",
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
        name: 'access_token',
        label: "Access Token",
        type: 'string',
        rawType: 'text',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Encrypted OAuth access token",
      },
      {
        name: 'refresh_token',
        label: "Refresh Token",
        type: 'string',
        rawType: 'text',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Encrypted OAuth refresh token",
      },
      {
        name: 'token_expires_at',
        label: "Token Expires At",
        type: 'date',
        rawType: 'datetime',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'watch_history_id',
        label: "Watch History Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Gmail push notification history ID",
        maxLength: 100,
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
  'EmailTemplate': {
    name: 'EmailTemplate',
    slug: 'email-template',
    pluralSlug: 'email-templates',
    label: 'Email Template',
    tableName: 'vs_email_template',
    endpoint: '/api/v1/email-templates',
    description: "Reusable email template for outreach and lifecycle emails",
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
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Owner user ID, null for system templates",
        maxLength: 100,
      },
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
        maxLength: 200,
      },
      {
        name: 'subject',
        label: "Subject",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        maxLength: 500,
      },
      {
        name: 'body',
        label: "Body",
        type: 'string',
        rawType: 'text',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "HTML template body",
      },
      {
        name: 'category',
        label: "Category",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        enumValues: ["outreach", "follow_up", "lifecycle", "system"],
        maxLength: 50,
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
  'LifecycleEmail': {
    name: 'LifecycleEmail',
    slug: 'lifecycle-email',
    pluralSlug: 'lifecycle-emails',
    label: 'Lifecycle Email',
    tableName: 'vs_lifecycle_email',
    endpoint: '/api/v1/lifecycle-emails',
    description: "Tracks drip campaign email execution per user",
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
        name: 'template_code',
        label: "Template Code",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Lifecycle template identifier: welcome, onboarding_reminder, gmail_reminder, etc.",
        maxLength: 50,
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
        enumValues: ["pending", "sent", "skipped", "cancelled"],
        maxLength: 20,
        defaultValue: "pending",
      },
      {
        name: 'scheduled_for',
        label: "Scheduled For",
        type: 'date',
        rawType: 'datetime',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "When this lifecycle email should be sent",
      },
      {
        name: 'sent_at',
        label: "Sent At",
        type: 'date',
        rawType: 'datetime',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
      },
      {
        name: 'skip_reason',
        label: "Skip Reason",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Why this email was skipped",
        maxLength: 200,
      },
    ],
    relationships: [
    ],
  },
  'Message': {
    name: 'Message',
    slug: 'message',
    pluralSlug: 'messages',
    label: 'Message',
    tableName: 'vs_message',
    endpoint: '/api/v1/messages',
    description: "Email message \u2014 draft, scheduled, sent, or received reply",
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
        name: 'investor_id',
        label: "Investor Id",
        type: 'uuid',
        rawType: 'uuid',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Cross-service reference to investor-service Investor",
      },
      {
        name: 'email_account_id',
        label: "Email Account",
        type: 'uuid',
        rawType: 'uuid',
        required: false,
        nullable: true,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/email-accounts',
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
        enumValues: ["draft", "scheduled", "sending", "sent", "failed", "answered"],
        maxLength: 20,
        defaultValue: "draft",
      },
      {
        name: 'to_addresses',
        label: "To Addresses",
        type: 'json',
        rawType: 'json',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Recipient email addresses array",
      },
      {
        name: 'cc_addresses',
        label: "Cc Addresses",
        type: 'json',
        rawType: 'json',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        defaultValue: "[]",
      },
      {
        name: 'subject',
        label: "Subject",
        type: 'string',
        rawType: 'string',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        maxLength: 500,
      },
      {
        name: 'from_address',
        label: "From Address",
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
        name: 'body',
        label: "Body",
        type: 'string',
        rawType: 'text',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "HTML email body",
      },
      {
        name: 'attachments',
        label: "Attachments",
        type: 'json',
        rawType: 'json',
        required: true,
        nullable: false,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Array of {key, name, size, type} for S3 attachments",
        defaultValue: "[]",
      },
      {
        name: 'thread_id',
        label: "Thread Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Gmail thread ID for conversation threading",
        maxLength: 200,
      },
      {
        name: 'provider_message_id',
        label: "Provider Message Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Message-ID header from email provider",
        maxLength: 500,
      },
      {
        name: 'provider_references',
        label: "Provider References",
        type: 'string',
        rawType: 'text',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "References header for email threading",
      },
      {
        name: 'previous_message_id',
        label: "Previous Message",
        type: 'uuid',
        rawType: 'uuid',
        required: false,
        nullable: true,
        unique: false,
        isFK: true,
        isSystem: false,
        fk: {
          endpoint: '/api/v1/messages',
          valueField: 'id',
          labelField: 'name',
        },
        description: "Self-referential FK for reply threading",
      },
      {
        name: 'scheduled_for',
        label: "Scheduled For",
        type: 'date',
        rawType: 'datetime',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "When to send if scheduled",
      },
      {
        name: 'job_id',
        label: "Job Id",
        type: 'string',
        rawType: 'string',
        required: false,
        nullable: true,
        unique: false,
        isFK: false,
        isSystem: false,
        description: "Kafka event reference for scheduled sends",
        maxLength: 100,
      },
    ],
    relationships: [
      {
        name: 'email_account',
        type: 'many_to_one',
        targetEntity: 'EmailAccount',
        foreignKey: 'email_account_id',
      },
      {
        name: 'previous_message',
        type: 'many_to_one',
        targetEntity: 'Message',
        foreignKey: 'previous_message_id',
      },
      {
        name: 'replies',
        type: 'one_to_many',
        targetEntity: 'Message',
        foreignKey: 'previous_message_id',
      },
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
