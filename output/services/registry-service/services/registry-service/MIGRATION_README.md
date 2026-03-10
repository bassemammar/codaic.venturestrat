# Registry Service Migration Testing

This document describes the comprehensive testing approach for Task 8.3: Test migration on sample data.

## Overview

The migration testing validates that the multi-tenant isolation migration works correctly with realistic production-like data, ensuring:

- Data integrity is preserved during migration
- All existing records are correctly assigned to the system tenant
- Foreign key constraints are properly enforced
- Tenant-aware views function correctly
- Migration can be safely rolled back if needed

## Test Files Created

### 1. `tests/test_migration_sample_data.py`
Comprehensive pytest-based test suite that creates realistic sample data and tests the full migration process.

**Features:**
- Realistic financial services microservices data
- Complex health event patterns simulating a week of monitoring
- Service dependency graphs representing real system architecture
- Comprehensive verification of migration results

**Key Test Cases:**
- `test_migration_with_realistic_data()`: Full migration workflow test
- `test_migration_rollback_with_sample_data()`: Rollback functionality test
- `test_foreign_key_constraint_with_sample_data()`: Constraint enforcement test

### 2. `scripts/test_migration_sample_data.py`
Standalone script for running migration tests with sample data in real database environments.

**Usage:**
```bash
python scripts/test_migration_sample_data.py --connection-url postgresql://user:pass@localhost/db
python scripts/test_migration_sample_data.py --connection-url postgresql://user:pass@localhost/db --verbose
python scripts/test_migration_sample_data.py --connection-url postgresql://user:pass@localhost/db --cleanup-only
```

**Features:**
- Comprehensive sample data generation
- Real database testing
- Automatic cleanup
- Detailed logging and reporting

### 3. `scripts/demo_migration_test.py`
Demonstration script that shows the migration testing process without requiring a real database.

**Usage:**
```bash
python scripts/demo_migration_test.py
```

## Sample Data Structure

The tests use realistic sample data representing a financial services platform:

### Service Registrations (8 instances)
- **pricing-service**: 3 instances (mixed versions)
- **trading-service**: 2 instances
- **risk-service**: 2 instances
- **reference-data-service**: 1 instance
- **market-data-service**: 2 instances (mixed versions)
- **auth-service**: 2 instances
- **notification-service**: 1 instance
- **reporting-service**: 2 instances

### Health Events (400+ events)
- Realistic health patterns over 7 days
- Different stability patterns per service type:
  - Core services (pricing, trading): High stability (90%+ healthy)
  - Market data: More volatile (75% healthy, periodic warnings/critical)
  - Auth services: Extremely stable (98%+ healthy)

### Service Dependencies (18 dependencies)
- Realistic dependency graph:
  - Trading depends on pricing, risk, auth, reference data
  - Pricing depends on market data, reference data, auth
  - Risk depends on pricing, market data, reference data, auth
  - And more...

## Migration Test Process

### Phase 1: Setup Test Environment
1. Create clean database tables (pre-migration schema)
2. Generate comprehensive sample data
3. Verify initial state

### Phase 2: Pre-Migration Validation
1. Validate tenant table exists
2. Verify system tenant exists
3. Check no existing tenant columns
4. Confirm database connectivity

### Phase 3: Execute Migration
1. Run the actual migration SQL (`003_add_tenant_isolation.sql`)
2. Measure execution time
3. Capture detailed statistics

### Phase 4: Post-Migration Verification
1. **Data Integrity Checks:**
   - Verify record counts unchanged
   - Confirm all records assigned to system tenant
   - Check foreign key constraints work

2. **Schema Verification:**
   - Verify tenant_id columns added to all tables
   - Check indexes created correctly
   - Validate constraints are in place

3. **Functional Testing:**
   - Test tenant-aware views
   - Verify foreign key enforcement
   - Test valid/invalid tenant insertions

### Phase 5: Rollback Testing
1. Test migration rollback functionality
2. Verify data preserved after rollback
3. Check original schema restored

## Key Verification Points

### 1. Data Preservation
```sql
-- Before migration
SELECT COUNT(*) FROM service_registrations; -- e.g., 8

-- After migration
SELECT COUNT(*) FROM service_registrations; -- Still 8
SELECT COUNT(*) FROM service_registrations
WHERE tenant_id = '00000000-0000-0000-0000-000000000000'; -- All 8
```

### 2. Foreign Key Enforcement
```sql
-- This should work (system tenant)
INSERT INTO service_registrations (..., tenant_id)
VALUES (..., '00000000-0000-0000-0000-000000000000');

-- This should fail (invalid tenant)
INSERT INTO service_registrations (..., tenant_id)
VALUES (..., '11111111-1111-1111-1111-111111111111');
```

### 3. View Functionality
```sql
-- Tenant-aware active services view
SELECT tenant_id, service_name, instance_count
FROM active_services
WHERE tenant_id = '00000000-0000-0000-0000-000000000000';
```

## Running the Tests

### Option 1: Full Test Suite with Real Database
Requires PostgreSQL with appropriate test database:

```bash
# Setup test database first
createdb test_registry_migration_sample

# Run comprehensive test
cd services/registry-service
python scripts/test_migration_sample_data.py \
  --connection-url postgresql://user:pass@localhost/test_registry_migration_sample
```

### Option 2: Demo Mode (No Database Required)
For demonstration and validation of test logic:

```bash
cd services/registry-service
python scripts/demo_migration_test.py
```

### Option 3: Pytest Integration
For CI/CD integration (requires test database setup):

```bash
cd services/registry-service
python -m pytest tests/test_migration_sample_data.py -v
```

## Expected Results

### Successful Migration Test Output:
```
🧪 Registry Migration Sample Data Test Demo
==================================================

📊 Initial Sample Data:
  Service Registrations: 8
  Health Events: 400+
  Dependencies: 18

--- Step 1: Pre-migration Validation ---
✅ Tenant table exists
✅ System tenant exists
✅ No existing tenant columns
✅ Database connectivity OK

--- Step 2: Migration Execution ---
📝 Adding tenant_id columns...
🔗 Adding foreign key constraints...
📚 Creating indexes...
👀 Updating views...
✅ Migration completed in 1.23 seconds

--- Step 3: Post-migration Verification ---
🔢 Record Count Verification:
  service_registrations: 8 → 8 (8 system) ✅
  service_health_events: 400+ → 400+ (400+ system) ✅
  service_dependencies: 18 → 18 (18 system) ✅

--- Step 4: Tenant Functionality Test ---
✅ All existing records assigned to system tenant
✅ Foreign key constraints working
✅ Tenant-aware views operational
✅ Data integrity preserved

🎉 Migration test completed successfully!
```

## Testing Scenarios Covered

### 1. Production-Like Data Volume
- Multiple services with realistic instance counts
- Thousands of health events over time
- Complex dependency relationships

### 2. Mixed Version Scenarios
- Services with different versions deployed
- Health events showing version upgrade patterns
- Dependency constraints with version requirements

### 3. Real-World Service Patterns
- Financial services microservice architecture
- Realistic health event patterns (mostly healthy with occasional issues)
- Service dependency graph matching real system designs

### 4. Error Conditions
- Foreign key constraint violations
- Invalid tenant ID handling
- Migration rollback scenarios

## Integration with CI/CD

The migration tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Test Migration with Sample Data
  run: |
    # Setup test database
    docker run -d --name postgres-test \
      -e POSTGRES_DB=test_migration \
      -e POSTGRES_USER=test_user \
      -e POSTGRES_PASSWORD=test_pass \
      -p 5432:5432 postgres:15

    # Wait for database
    sleep 10

    # Run migration test
    cd services/registry-service
    python scripts/test_migration_sample_data.py \
      --connection-url postgresql://test_user:test_pass@localhost/test_migration
```

## Conclusion

This comprehensive testing approach ensures the multi-tenant migration works correctly with realistic production data, covering:

- **Data Safety**: All existing data is preserved and correctly migrated
- **Functional Correctness**: Tenant isolation works as designed
- **Performance**: Migration completes in reasonable time with production-scale data
- **Rollback Safety**: Migration can be safely reversed if needed

The tests provide confidence that the migration can be safely applied to production systems with existing registry data.
