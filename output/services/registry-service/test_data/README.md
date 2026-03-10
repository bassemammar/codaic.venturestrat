# Pricing Infrastructure Test Data

This directory contains comprehensive test data for validating the multi-tenant pricing infrastructure as specified in the [pricing infrastructure spec](../../.agent-os/specs/2026-01-10-pricing-infrastructure/spec.md).

## Overview

The test data supports the following validation scenarios as specified in the spec:

### Multi-Tenant Configuration Validation

**3 Test Tenants Created:**

1. **Tenant A (`11111111-1111-1111-1111-111111111111`)** - QuantLib Custom Curves
   - Default pricer: `quantlib-v1.18`
   - Fallback pricer: `treasury-v2.3`
   - Max batch size: 1,000 instruments
   - Features: batch_pricing, dual_pricing, greeks, duration
   - Custom Hull-White model parameters

2. **Tenant B (`22222222-2222-2222-2222-222222222222`)** - Treasury Custom Params
   - Default pricer: `treasury-v2.3`
   - Fallback pricer: `quantlib-v1.18`
   - Max batch size: 5,000 instruments
   - Features: batch_pricing, monte_carlo, pde, path_dependent
   - Custom SABR and HJM model parameters

3. **Tenant C (`33333333-3333-3333-3333-333333333333`)** - QuantLib Different Curves
   - Default pricer: `quantlib-v1.18`
   - Fallback pricer: None (for testing failure scenarios)
   - Max batch size: 500 instruments
   - Features: batch_pricing, greeks, duration, convexity
   - Custom Vasicek model parameters

## Test Data Structure

```
services/registry-service/test_data/
├── README.md                    # This file
├── curves/                      # Test yield curves
│   ├── tenant_a_usd_sofr.json  # Custom curves for Tenant A
│   ├── tenant_b_usd_sofr.json  # Custom curves for Tenant B
│   ├── tenant_c_usd_sofr.json  # Custom curves for Tenant C
│   ├── eur_euribor.json        # EUR curves
│   └── gbp_sonia.json          # GBP curves
├── instruments/                 # Test instruments for pricing
│   ├── usd_5y_vanilla_swap.json
│   ├── eur_10y_vanilla_swap.json
│   ├── usd_treasury_5y.json
│   ├── eur_corporate_bond_3y.json
│   ├── usd_swaption_5y_into_5y.json
│   ├── eur_cap_floor_3y.json
│   ├── eurusd_forward_1y.json
│   └── gbpusd_option_6m.json
└── portfolios/                  # Test portfolios for batch pricing
    ├── small_portfolio_100.json   # 100 instruments
    ├── medium_portfolio_500.json  # 500 instruments
    ├── large_portfolio_1000.json  # 1,000 instruments
    └── stress_portfolio_2500.json # 2,500 instruments
```

## Validation Scenarios Enabled

### 1. Multi-Tenant Routing Validation

Submit identical swap pricing request with different tenant JWTs:
- Tenant A JWT → QuantLib pricer with Tenant A custom curves
- Tenant B JWT → Treasury pricer with Tenant B custom parameters
- Tenant C JWT → QuantLib pricer with Tenant C conservative curves

**Expected Result:** Different NPV results based on tenant-specific curves/configs

### 2. Batch Pricing Performance Validation

Test batch pricing with tenant-specific limits:
- Tenant A: Max 1,000 instruments → should complete in <10 seconds
- Tenant B: Max 5,000 instruments → should handle larger batches
- Tenant C: Max 500 instruments → should reject batches >500

**Expected Result:** Performance validation per spec requirements

### 3. Capability-Based Routing Validation

Submit requests without specifying pricer:
- Swaption + Black-76 model → routes to QuantLib
- Complex Monte Carlo → routes to Treasury
- Basic swap → routes to tenant's default pricer

**Expected Result:** Orchestrator selects appropriate pricer based on capabilities

### 4. Fallback Pricer Validation

Test pricer unavailability scenarios:
- Stop QuantLib → Tenants A,B fallback to Treasury/QuantLib
- Stop Treasury → Tenant B falls back to QuantLib
- Stop QuantLib → Tenant C fails (no fallback configured)

**Expected Result:** Proper fallback behavior per tenant configuration

## Usage

### Database Setup

The test tenants are created by database migration:

```bash
# Apply the test data migration
venturestrat migrate --target registry-service --version 006
```

### File-Based Test Data

Create test data files using the CLI seeder:

```bash
# Create all test data
venturestrat seed pricing-test-data

# Create specific data types
venturestrat seed pricing-test-data --data-type curves
venturestrat seed pricing-test-data --data-type instruments
venturestrat seed pricing-test-data --data-type portfolios

# Preview what would be created
venturestrat seed pricing-test-data --dry-run --verbose
```

### Test Execution

Use the test data for integration testing:

```python
# Load test tenant configurations
tenant_a_id = "11111111-1111-1111-1111-111111111111"
tenant_b_id = "22222222-2222-2222-2222-222222222222"
tenant_c_id = "33333333-3333-3333-3333-333333333333"

# Load test curves
with open("test_data/curves/tenant_a_usd_sofr.json") as f:
    tenant_a_curve = json.load(f)

# Load test instruments
with open("test_data/instruments/usd_5y_vanilla_swap.json") as f:
    test_swap = json.load(f)

# Load test portfolios
with open("test_data/portfolios/large_portfolio_1000.json") as f:
    batch_test_portfolio = json.load(f)
```

## Expected Deliverable Validation

This test data enables validation of all core platform requirements:

### ✅ Multi-Tenant Routing Validated
- 3 tenants with different configurations created
- Submit identical requests with different tenant JWTs
- Verify different results based on tenant-specific curves/configs

### ✅ Batch Pricing Performance
- Portfolios with 100-2500 instruments created
- Price portfolio of 1000 swaps via `/api/v1/pricing/price_batch`
- Validate completion in <10 seconds (vs 100+ seconds sequential)

### ✅ Capability-Based Routing
- Test instruments requiring different models/features
- Submit without specifying pricer
- Verify orchestrator routes to capable pricer

### ✅ Service Independence
- Test tenants use different pricer configurations
- No dependencies on d2c platform data
- All test data self-contained in VentureStrat

## Implementation Notes

- **Database Records:** Test tenants created by migration `006_add_pricing_test_data.sql`
- **File Data:** Test curves/instruments/portfolios created by CLI seeder
- **Idempotent:** Can be run multiple times safely
- **Isolated:** Test data clearly marked and separated from production data
- **Comprehensive:** Covers all major instrument types and scenarios

This test data provides the foundation for validating the complete pricing infrastructure migration as specified in Phase 0 deliverables.