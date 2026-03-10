# Product Decisions Log

> Last Updated: TBD
> Version: 1.0.0

## DEC-001: Platform Foundation

**Status:** Accepted
**Category:** Architecture

### Decision

VentureStrat is built as a PlayformOS-derived platform using FastAPI, React+TypeScript+MUI, PostgreSQL, and Docker Compose.

### Rationale

PlayformOS provides production-proven patterns for multi-tenancy, RBAC, codegen, dashboards, and observability. Building on this foundation eliminates months of infrastructure work.

### Consequences

**Positive:**
- Full-stack CRUD, auth, multi-tenancy from day one
- Codegen from YAML entity definitions
- Dashboard framework with 10 widget types
- Consistent patterns across the stack

**Negative:**
- Must follow PlayformOS conventions
- SDK dependency on platform core packages

---

## DEC-002: Multi-Tenancy Mode

**Status:** Accepted
**Category:** Architecture

### Decision

VentureStrat uses row_level tenant isolation with X-Tenant-ID header propagation.

### Rationale

Row-level isolation is simpler to operate (single schema) and sufficient for most multi-tenant applications. Tenant context is set via middleware on every request.

---

*Add new decisions below as architectural choices are made.*
