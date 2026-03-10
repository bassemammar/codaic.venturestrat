# Registry Service - Startup Guide

**Status**: ✅ BaseModel conversion complete | ⏳ Dependency installation needed

---

## Summary of Work Completed

### ✅ Phase 1: BaseModel Conversion (DONE)

**Models Converted** (5 files):
- ✅ pricer_registry.py
- ✅ pricer_capability.py
- ✅ tenant.py
- ✅ tenant_pricing_config.py
- ✅ tenant_quotas.py

**Repository Converted** (1 file):
- ✅ pricing_repository.py - Complete rewrite to use BaseModel API

### ✅ Phase 2: Bug Fixes (DONE)

**Fixed during testing**:
1. ✅ **fields.Json → fields.JSON** - Fixed in 3 files
   - Updated pricer_capability.py
   - Updated tenant.py
   - Updated tenant_pricing_config.py

2. ✅ **Python 3.9 Compatibility** - Fixed `UTC` import
   - Changed `from datetime import UTC` → `from datetime import timezone`
   - Changed `datetime.now(UTC)` → `datetime.now(timezone.utc)`
   - Fixed in tenant.py and tenant_quotas.py

**All models now import successfully!** ✅

---

## Remaining Steps to Start Service

### Step 1: Install Python Dependencies

The service needs these Python packages:

```bash
cd /opt/anaconda3/Risk_final/oddo_mngr/services/registry-service

# Install from pyproject.toml
pip install -e .

# Or manually install missing packages:
pip install python-consul fastapi uvicorn sqlalchemy asyncpg pydantic pydantic-settings
```

**Missing packages identified**:
- `consul` - Consul client (optional, for service discovery)
- Other packages in pyproject.toml

### Step 2: Setup Database

The service expects PostgreSQL:

```bash
# Default connection string:
DATABASE_URL="postgresql://registry:registry@localhost:5432/registry"

# Create database if needed:
createdb registry
```

**BaseModel behavior**:
- BaseModel (BaseModel ORM) typically auto-creates tables
- May need to run migrations if using Alembic

### Step 3: Configure Environment

Create `.env` file or export environment variables:

```bash
# Required
DATABASE_URL=postgresql://registry:registry@localhost:5432/registry

# Optional (service works without these)
CONSUL_HOST=localhost
CONSUL_PORT=8500
REDIS_HOST=localhost
REDIS_PORT=6379
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Step 4: Start the Service

**Option A: Using startup script**:
```bash
# Set venturestrat SDK path
export VENTURESTRAT_SDK="/opt/anaconda3/Risk_final/oddo_mngr/sdk/venturestrat-models/src"
export PYTHONPATH="src:${VENTURESTRAT_SDK}:${PYTHONPATH}"

# Start service
python3 -m registry.main
```

**Option B: Using uvicorn**:
```bash
export PYTHONPATH="src:/opt/anaconda3/Risk_final/oddo_mngr/sdk/venturestrat-models/src"
uvicorn registry.main:app --host 0.0.0.0 --port 8080
```

**Option C: Using Docker**:
```bash
docker-compose -f docker-compose.dev.yaml up registry-service
```

---

## Testing the Service

### 1. Health Check
```bash
# Liveness
curl http://localhost:8080/health/live

# Readiness
curl http://localhost:8080/health/ready
```

### 2. List Pricers (Should return empty array initially)
```bash
curl http://localhost:8080/api/v1/registry/pricers
```

### 3. Register a Pricer
```bash
curl -X POST http://localhost:8080/api/v1/registry/pricers \
  -H "Content-Type: application/json" \
  -d '{
    "pricer_id": "quantlib-v1.18",
    "name": "QuantLib",
    "version": "1.18.0",
    "description": "Open-source quantitative finance library",
    "health_check_url": "http://quantlib-service:8088/health",
    "pricing_url": "http://quantlib-service:8088/api/v1",
    "batch_supported": true,
    "max_batch_size": 10000
  }'
```

### 4. Get Pricer by ID
```bash
curl http://localhost:8080/api/v1/registry/pricers/quantlib-v1.18
```

---

## Troubleshooting

### Issue: "No module named 'consul'"
**Solution**: Install python-consul
```bash
pip install python-consul
```

### Issue: "No module named 'venturestrat'"
**Solution**: Add venturestrat-models SDK to PYTHONPATH
```bash
export PYTHONPATH="/opt/anaconda3/Risk_final/oddo_mngr/sdk/venturestrat-models/src:$PYTHONPATH"
```

### Issue: "Cannot import name 'UTC' from 'datetime'"
**Status**: ✅ FIXED - Already resolved in Phase 2

### Issue: "module 'venturestrat.models.fields' has no attribute 'Json'"
**Status**: ✅ FIXED - Changed to fields.JSON

### Issue: Database connection errors
**Solution**: Ensure PostgreSQL is running and DATABASE_URL is correct
```bash
# Test database connection
psql postgresql://registry:registry@localhost:5432/registry -c "SELECT 1"
```

### Issue: Import errors from registry.__init__.py
**Status**: Known issue - package __init__ imports optional dependencies
**Workaround**: Install all dependencies from pyproject.toml

---

## Files Modified

| File | Changes | Status |
|------|---------|--------|
| pricer_registry.py | SQLAlchemy → BaseModel | ✅ |
| pricer_capability.py | SQLAlchemy → BaseModel, fields.Json → fields.JSON | ✅ |
| tenant.py | SQLAlchemy → BaseModel, fields.Json → fields.JSON, UTC → timezone.utc | ✅ |
| tenant_pricing_config.py | SQLAlchemy → BaseModel, fields.Json → fields.JSON | ✅ |
| tenant_quotas.py | SQLAlchemy → BaseModel, UTC → timezone.utc | ✅ |
| pricing_repository.py | Complete rewrite to BaseModel API | ✅ |

---

## Next Actions

1. **Install Dependencies**
   ```bash
   pip install -e .
   ```

2. **Setup Database**
   ```bash
   createdb registry
   ```

3. **Start Service**
   ```bash
   export PYTHONPATH="src:/opt/anaconda3/Risk_final/oddo_mngr/sdk/venturestrat-models/src"
   python3 -m registry.main
   ```

4. **Test Endpoints**
   - See testing section above

---

## Summary

**✅ Conversion Complete**: All models and repository converted to BaseModel
**✅ Bugs Fixed**: fields.JSON and Python 3.9 compatibility
**✅ Imports Tested**: All models import successfully
**⏳ Dependencies**: Need to install packages from pyproject.toml
**⏳ Database**: Need PostgreSQL running
**⏳ Runtime Test**: Need to start service and verify

---

**The architectural mismatch is completely resolved. Service is ready for runtime testing once dependencies are installed.**
