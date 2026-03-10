-- tenant-header plugin schema
-- Configuration schema for the tenant-header plugin

local typedefs = require "kong.db.schema.typedefs"

return {
    name = "tenant-header",
    fields = {
        { consumer = typedefs.no_consumer },  -- Cannot be applied on consumers
        { protocols = typedefs.protocols_http },  -- Only HTTP protocols
        { config = {
            type = "record",
            fields = {
                -- Paths to exclude from tenant requirement (e.g., health checks)
                { exclude_paths = {
                    type = "array",
                    default = { "/health", "/metrics", "/status" },
                    elements = { type = "string" },
                    description = "Regex patterns for paths that don't require tenant_id"
                } },

                -- Add debug header with tenant_id in response
                { debug_header = {
                    type = "boolean",
                    default = false,
                    description = "Add X-Debug-Tenant-ID header to responses for debugging"
                } },

                -- Emit custom metrics for tenant usage
                { emit_metrics = {
                    type = "boolean",
                    default = true,
                    description = "Emit tenant-specific metrics for monitoring"
                } },

                -- Custom header name (in case X-Tenant-ID conflicts)
                { header_name = {
                    type = "string",
                    default = "X-Tenant-ID",
                    description = "Name of the header to set with tenant_id"
                } },

                -- Strict mode: fail if JWT plugin hasn't run first
                { strict_mode = {
                    type = "boolean",
                    default = true,
                    description = "Fail if JWT claims are not available (requires JWT plugin before this)"
                } },

                -- Log level for tenant operations
                { log_level = {
                    type = "string",
                    default = "info",
                    one_of = { "debug", "info", "warn", "error" },
                    description = "Log level for tenant-related messages"
                } }
            }
        } }
    }
}
