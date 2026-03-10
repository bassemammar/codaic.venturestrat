# Multi-Tenant Migration Strategy

**Version:** 1.0.0
**Created:** 2026-01-08
**Wave:** 8 - Task 8.1: Design migration strategy

## Overview

This document outlines the comprehensive strategy for migrating the VentureStrat platform from single-tenant to multi-tenant architecture. The migration adds `tenant_id` fields to existing database tables while preserving data integrity and ensuring zero-downtime deployment.

## Migration Approach

### 1. **Phased Migration Strategy**

**Phase 1: Foundation (Current)**
- ✅ Add tenant table with system tenant
- ✅ Update registry service tables with tenant_id
- ✅ Migrate existing data to system tenant

**Phase 2: Service Integration (Future)**
- Add tenant middleware to all services
- Update service models to use tenant context
- Implement tenant-aware queries

**Phase 3: Frontend & Auth (Future)**
- Add tenant selection in Keycloak
- Update frontend for tenant isolation
- Implement tenant switching for platform admins

### 2. **Data Migration Principles**

1. **Backwards Compatibility:** All existing records assigned to system tenant
2. **Zero Data Loss:** All migrations are additive, no data deletion
3. **Referential Integrity:** Foreign key constraints ensure data consistency
4. **Performance:** Optimized indexes for tenant-scoped queries
5. **Rollback Safety:** All changes can be reverted if needed

### 3. **System Tenant Strategy**

The system tenant (`00000000-0000-0000-0000-000000000000`) serves as:
- Default tenant for all existing data
- Platform-level services and configurations
- Cross-tenant administrative operations
- Backwards compatibility layer

## Database Schema Changes

### Tables Modified

| Table | Change | Reason |
|-------|--------|---------|
| `service_registrations` | Add `tenant_id` | Service instances should be scoped to tenants |
| `service_health_events` | Add `tenant_id` | Health data isolation between tenants |
| `service_dependencies` | Add `tenant_id` | Dependency graphs per tenant |

### Indexes Added

```sql
-- Tenant filtering
idx_service_registrations_tenant_id
idx_service_health_events_tenant_id
idx_service_dependencies_tenant_id

-- Tenant-scoped queries
idx_service_registrations_tenant_service
idx_service_health_events_tenant_service

-- Performance optimization
idx_service_registrations_tenant_active_cover
idx_service_health_events_tenant_recent_cover
```

### Constraints Updated

```sql
-- Updated unique constraint to include tenant
service_dependencies_tenant_service_depends_unique(tenant_id, service_name, depends_on)

-- Foreign key constraints with RESTRICT on delete
fk_service_registrations_tenant
fk_service_health_events_tenant
fk_service_dependencies_tenant
```

## Migration Execution Plan

### Pre-Migration Checklist

1. **Backup Database**
   ```bash
   pg_dump registry_db > registry_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Verify System Tenant Exists**
   ```sql
   SELECT id, slug, name FROM tenants WHERE slug = 'system';
   ```

3. **Count Existing Records**
   ```sql
   SELECT
     (SELECT COUNT(*) FROM service_registrations) as reg_count,
     (SELECT COUNT(*) FROM service_health_events) as health_count,
     (SELECT COUNT(*) FROM service_dependencies) as dep_count;
   ```

### Migration Steps

1. **Execute Migration Script**
   ```bash
   psql -d registry_db -f migrations/003_add_tenant_isolation.sql
   ```

2. **Verify Migration Success**
   ```sql
   -- Check columns exist
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_name IN ('service_registrations', 'service_health_events', 'service_dependencies')
   AND column_name = 'tenant_id';

   -- Verify all records have system tenant
   SELECT COUNT(*) FROM service_registrations WHERE tenant_id = '00000000-0000-0000-0000-000000000000';
   ```

3. **Test Tenant Isolation**
   ```python
   # Create test tenant
   from registry.tenant_service import TenantService

   tenant = await TenantService().create_tenant(
       slug="test-migration",
       name="Test Migration Tenant"
   )

   # Verify isolation
   assert len(ServiceRegistration.search([("tenant_id", "=", tenant.id)])) == 0
   ```

### Post-Migration Validation

1. **Data Integrity**
   - All existing records assigned to system tenant ✓
   - Foreign key constraints active ✓
   - No orphaned records ✓

2. **Performance**
   - Query plans use tenant indexes ✓
   - No full table scans on tenant queries ✓
   - View performance maintained ✓

3. **Functionality**
   - Registry service operations work ✓
   - Health monitoring continues ✓
   - Dependency tracking functional ✓

## Rollback Strategy

If migration needs to be reverted:

```sql
BEGIN;

-- Remove tenant columns
ALTER TABLE service_registrations DROP COLUMN tenant_id;
ALTER TABLE service_health_events DROP COLUMN tenant_id;
ALTER TABLE service_dependencies DROP COLUMN tenant_id;

-- Restore original unique constraint
ALTER TABLE service_dependencies
ADD CONSTRAINT service_dependencies_service_name_depends_on_key
UNIQUE(service_name, depends_on);

-- Restore original views
DROP VIEW active_services;
DROP VIEW service_uptime_24h;

-- Restore from backup file: 001_initial_schema.sql (view definitions)

COMMIT;
```

## Impact Assessment

### Minimal Impact Areas

- **Existing Services:** Continue operating normally (system tenant)
- **Data Access:** No changes to existing service behavior
- **Performance:** Marginal overhead from additional columns
- **Storage:** ~16 bytes per record (UUID tenant_id)

### Benefits Gained

- **Multi-Tenant Ready:** Foundation for customer isolation
- **Security:** Tenant data separation at database level
- **Scalability:** Tenant-specific performance optimization
- **Compliance:** Support for data residency requirements

## Implementation Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Migration Script | 1 day | Database access |
| Testing & Validation | 2 days | Test environment |
| Production Deployment | 1 day | Maintenance window |
| Monitoring & Verification | 1 week | Production observability |

## Risk Mitigation

### High Risk: Data Corruption
- **Mitigation:** Full database backup before migration
- **Detection:** Post-migration data validation queries
- **Response:** Immediate rollback from backup

### Medium Risk: Performance Degradation
- **Mitigation:** Comprehensive indexing strategy
- **Detection:** Query performance monitoring
- **Response:** Additional index optimization

### Low Risk: Application Errors
- **Mitigation:** Backwards compatible changes only
- **Detection:** Application error monitoring
- **Response:** Service restart or rollback

## Monitoring & Alerting

### Key Metrics
- Migration execution time
- Record count before/after
- Foreign key constraint violations
- Query performance impact
- Service error rates during migration

### Alert Conditions
- Migration execution > 30 minutes
- Data count mismatches
- Constraint violation errors
- Query response time > 2x baseline

## Next Steps

1. **Service Updates:** Update registry service models to use tenant context
2. **Middleware Integration:** Add tenant middleware to registry service
3. **Testing:** Comprehensive testing with multiple tenants
4. **Documentation:** Update API documentation for tenant support
5. **Monitoring:** Add tenant-specific metrics and dashboards

## Conclusion

This migration strategy provides a safe, efficient path to multi-tenancy for the registry service. The phased approach ensures minimal risk while establishing the foundation for full platform multi-tenancy support.

The migration is designed to be:
- **Reversible:** Can be rolled back if issues arise
- **Zero-Downtime:** No service interruption required
- **Data-Safe:** No risk of data loss or corruption
- **Performance-Aware:** Optimized for tenant-scoped queries

Upon completion, the registry service will support full tenant isolation while maintaining backwards compatibility with existing deployments.
