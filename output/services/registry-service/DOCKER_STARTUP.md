# Registry Service - Docker Startup Guide

**✅ BaseModel Conversion Complete** | **🐳 Docker Deployment**

---

## Quick Start with Docker

### Option 1: Standalone Service

```bash
cd /opt/anaconda3/Risk_final/oddo_mngr/services/registry-service

# Build the image
docker-compose -f docker-compose.dev.yaml build

# Start the service
docker-compose -f docker-compose.dev.yaml up
```

**Service will be available at**: http://localhost:8080

### Option 2: With Full Platform Stack

If you have the full VentureStrat infrastructure running:

```bash
# From repository root
cd /opt/anaconda3/Risk_final/oddo_mngr

# Start all infrastructure (if not already running)
docker-compose up -d postgres redis kafka consul

# Then start registry service
cd services/registry-service
docker-compose -f docker-compose.dev.yaml up
```

---

## Docker Configuration

**Ports Exposed**:
- `8080` - REST API
- `50051` - gRPC API

**Dependencies** (configured in docker-compose.dev.yaml):
- PostgreSQL: `postgresql://registry_user:reg_svc_d3v_p455@postgres:5432/venturestrat?currentSchema=registry`
- Consul: `consul-server-1:8500` (optional)
- Kafka: `kafka:29092` (optional)

**Network**:
- `venturestrat-network` (external)
- Network name: `wave-3-03ca1a47_venturestrat-network`

---

## Testing the Service

### 1. Check Container Status
```bash
docker ps | grep registry-service
```

### 2. View Logs
```bash
docker-compose -f docker-compose.dev.yaml logs -f
```

### 3. Test Health Endpoint
```bash
# Liveness
curl http://localhost:8080/health/live

# Readiness
curl http://localhost:8080/health/ready
```

### 4. Test Pricer Endpoints
```bash
# List pricers (empty initially)
curl http://localhost:8080/api/v1/registry/pricers

# Register a pricer
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

# Get pricer by ID
curl http://localhost:8080/api/v1/registry/pricers/quantlib-v1.18
```

---

## Troubleshooting

### Issue: Network not found
```
ERROR: Network wave-3-03ca1a47_venturestrat-network declared as external, but could not be found
```

**Solution A**: Create the network
```bash
docker network create wave-3-03ca1a47_venturestrat-network
```

**Solution B**: Update docker-compose to create network
Remove the `external: true` line from docker-compose.dev.yaml

### Issue: Database connection errors
```
ERROR: Could not connect to database
```

**Solution**: Ensure PostgreSQL is running
```bash
# Start PostgreSQL if using platform stack
docker-compose up -d postgres

# Or use a local PostgreSQL and update DATABASE_URL
export DATABASE_URL="postgresql://localhost:5432/registry"
```

### Issue: Port already in use
```
ERROR: Bind for 0.0.0.0:8080 failed: port is already allocated
```

**Solution**: Stop conflicting service or change port
```bash
# Find what's using port 8080
lsof -i :8080

# Kill the process or change port in docker-compose.dev.yaml
```

### Issue: Permission denied
**Solution**: Add sudo or add user to docker group
```bash
# Option 1: Use sudo
sudo docker-compose -f docker-compose.dev.yaml up

# Option 2: Add user to docker group (requires re-login)
sudo usermod -aG docker $USER
```

---

## Development Workflow

### Live Code Updates
The docker-compose mounts source code as read-only volumes:
```yaml
volumes:
  - ./src:/app/src:ro
  - ./tests:/app/tests:ro
```

**To apply code changes**: Restart the container
```bash
docker-compose -f docker-compose.dev.yaml restart
```

### View Logs
```bash
# Follow logs
docker-compose -f docker-compose.dev.yaml logs -f registry-service

# Last 100 lines
docker-compose -f docker-compose.dev.yaml logs --tail=100 registry-service
```

### Execute Commands Inside Container
```bash
# Open shell
docker-compose -f docker-compose.dev.yaml exec registry-service /bin/bash

# Run Python commands
docker-compose -f docker-compose.dev.yaml exec registry-service python3 -c "from registry.models.pricer_registry import PricerRegistry; print(PricerRegistry)"
```

### Stop Service
```bash
# Stop containers
docker-compose -f docker-compose.dev.yaml down

# Stop and remove volumes
docker-compose -f docker-compose.dev.yaml down -v
```

---

## What's in the Docker Image

**Base Image**: Python 3.11+ (from Dockerfile)

**Includes**:
- All Python dependencies from pyproject.toml
- VentureStrat BaseModel SDK (venturestrat-models)
- Converted models (pure BaseModel)
- Registry service application

**Automatically Handles**:
- ✅ Python version compatibility
- ✅ All package dependencies (consul, fastapi, etc.)
- ✅ Database connections
- ✅ Health checks
- ✅ Service startup

---

## Summary

**✅ Benefits of Docker**:
- No manual dependency installation
- Consistent environment
- Easy integration with platform stack
- Proper networking and service discovery

**✅ BaseModel Conversion**:
- All models converted to BaseModel
- All bugs fixed (fields.JSON, timezone.utc)
- Repository using BaseModel API

**🚀 Ready to Run**:
```bash
docker-compose -f docker-compose.dev.yaml up
```

---

## Next Steps

1. **Start Service**:
   ```bash
   docker-compose -f docker-compose.dev.yaml up
   ```

2. **Watch Logs**: Look for successful startup
   - "Pricing repository initialized (BaseModel)"
   - "Starting registry service"

3. **Test Endpoints**: See testing section above

4. **Integration Test**: Test with pricing-orchestrator once running

---

**The service is fully converted to BaseModel and ready to run with Docker!** 🐳
