# Registry Service: BaseModel Conversion Status

**Date**: 2026-02-04
**Status**: ✅ Models Converted | ⚠️ Repository Pending

---

## Summary

The registry-service had a **CRITICAL ARCHITECTURE MISMATCH**: models used SQLAlchemy `Column()` definitions with BaseModel `BaseModel` inheritance, causing all database queries to fail.

**Root Cause**: Mixing incompatible ORMs
- BaseModel expects: `PricerRegistry.search([])`, `record.create({})`
- SQLAlchemy expects: `session.execute(select(PricerRegistry))`
- Result: "Column expression... expected" errors

---

## ✅ COMPLETED: Model Conversion (5 files)

All models converted from hybrid SQLAlchemy/BaseModel to **pure BaseModel** following platform standard:

### 1. [pricer_registry.py](src/registry/models/pricer_registry.py)
**Before**:
```python
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime
pricer_id = Column(String(255), primary_key=True)
name = Column(String(255), nullable=False)
```

**After**:
```python
from venturestrat.models import BaseModel, fields
pricer_id: str = fields.String(size=255, required=True, primary_key=True)
name: str = fields.String(size=255, required=True)
```

### 2. [pricer_capability.py](src/registry/models/pricer_capability.py)
- Converted Column() to fields.*
- Changed JSONB to fields.Json()
- Removed SQLAlchemy relationship, added explicit foreign key

### 3. [tenant.py](src/registry/models/tenant.py)
- Converted all Column() definitions
- Kept all business logic methods (suspend, resume, delete, etc.)

### 4. [tenant_pricing_config.py](src/registry/models/tenant_pricing_config.py)
- Converted UUID/JSONB to BaseModel types
- Removed SQLAlchemy relationships
- Preserved all configuration methods

### 5. [tenant_quotas.py](src/registry/models/tenant_quotas.py)
- Simple model, clean conversion
- All quota methods preserved

---

## ⚠️ PENDING: Repository Conversion

**File**: [src/registry/repositories/pricing_repository.py](src/registry/repositories/pricing_repository.py) (475 lines)

### Current State (SQLAlchemy)
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def list_pricers(self):
    async with self._get_session() as session:
        result = await session.execute(select(PricerRegistry))
        return result.scalars().all()
```

### Target State (BaseModel)
```python
async def list_pricers(self):
    # BaseModel API (synchronous)
    pricers = PricerRegistry.search([])
    return pricers
```

### Conversion Patterns

| SQLAlchemy                | BaseModel API                    |
|---------------------------|----------------------------------|
| `session.get(Model, id)`  | `Model.browse(id)` or `Model.search([('id', '=', id)])` |
| `session.add(model)`      | `Model.create({...})`            |
| `session.execute(select(Model))` | `Model.search([])`        |
| `session.execute(select(Model).where(...))` | `Model.search([('field', '=', value)])` |
| `session.commit()`        | Auto-committed by BaseModel      |
| `model.field = value`     | `record.write({'field': value})` |

### Key Differences

1. **Async vs Sync**: BaseModel is synchronous (BaseModel ORM pattern)
2. **Session Management**: BaseModel handles automatically
3. **Query Syntax**: Domain filters `[('field', 'op', 'value')]` instead of SQLAlchemy expressions
4. **Commits**: BaseModel auto-commits, no explicit commit needed

---

## Next Steps

### 1. Convert Repository (Estimated: 1-2 hours)

**Pattern to follow**:
```python
# Remove SQLAlchemy imports
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession

# Update each method:
async def save_pricer(self, pricer_dict: dict) -> PricerRegistry:
    """Save using BaseModel.create() or write()."""
    # Check if exists
    existing = PricerRegistry.search([('pricer_id', '=', pricer_dict['pricer_id'])])
    if existing:
        existing[0].write(pricer_dict)
        return existing[0]
    else:
        return PricerRegistry.create(pricer_dict)
```

**Files to update**:
- `src/registry/repositories/pricing_repository.py`

**Methods to convert** (~20 methods):
- `save_pricer()`
- `get_pricer()`
- `list_pricers()`
- `find_pricers_by_capability()`
- `save_capability()`
- `list_capabilities()`
- `get_tenant_config()`
- `save_tenant_config()`
- etc.

### 2. Update Database Configuration

BaseModel may need different database setup than SQLAlchemy:
- Check `src/registry/database.py` or similar
- Ensure BaseModel is properly initialized with database connection
- May need to use `venturestrat` database infrastructure

### 3. Test

```bash
# Start registry service
cd services/registry-service
python -m registry.main

# Test basic queries
curl http://localhost:8XXX/api/v1/registry/pricers

# Test pricer registration
curl -X POST http://localhost:8XXX/api/v1/registry/pricers \
  -H "Content-Type: application/json" \
  -d '{"pricer_id": "quantlib-v1.18", ...}'
```

### 4. End-to-End Verification

```bash
# Test pricing orchestrator can query registry
curl http://localhost:8104/api/v1/registry/pricers

# Test pricing request works
curl -X POST http://localhost:8104/api/v1/pricing/price \
  -H "Content-Type: application/json" \
  -d '{"instrument_type": "swap", ...}'
```

---

## Platform Standard Confirmed

**VentureStrat uses BaseModel** as the ORM standard:

Evidence:
1. ✅ Codegen template: `codegen/templates/python/basemodel_orm.py.jinja2`
2. ✅ market-data-service: Uses `from venturestrat.models import BaseModel, fields`
3. ✅ reference-data-service: Uses `from venturestrat.models import BaseModel, fields`
4. ❌ registry-service (before fix): Hybrid BaseModel + SQLAlchemy (BROKEN)

---

## Risk Assessment

**Low Risk**: Models are now correct, repository conversion is mechanical
**Blast Radius**: 1 file (pricing_repository.py)
**Rollback**: Git commit after each step

---

## Questions for Platform Team

1. **BaseModel Async Support**: Does venturestrat.models.BaseModel support async queries, or are they synchronous?
2. **Database Setup**: What's the proper way to initialize BaseModel database connection?
3. **Migrations**: Do we need Alembic migrations, or does BaseModel handle schema automatically?
4. **Testing**: Are there existing tests for BaseModel repositories we can reference?

---

**Last Updated**: 2026-02-04
**Next Action**: Convert pricing_repository.py to use BaseModel API
