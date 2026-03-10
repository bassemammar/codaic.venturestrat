#!/bin/bash
# Registry Service Startup Script
# Starts the converted BaseModel registry service

set -e

echo "=========================================="
echo "Starting Registry Service"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
VENTURESTRAT_SDK="/opt/anaconda3/Risk_final/oddo_mngr/sdk/venturestrat-models/src"
SERVICE_SRC="src"

# Set PYTHONPATH to include both service source and venturestrat SDK
export PYTHONPATH="${SERVICE_SRC}:${VENTURESTRAT_SDK}:${PYTHONPATH}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Service source: ${SERVICE_SRC}"
echo "  VentureStrat SDK: ${VENTURESTRAT_SDK}"
echo "  PYTHONPATH: ${PYTHONPATH}"
echo ""

# Check if dependencies are available
echo -e "${YELLOW}Checking dependencies...${NC}"

# Test venturestrat.models import
python3 -c "from venturestrat.models import BaseModel, fields; print('  ✅ venturestrat.models available')" || {
    echo -e "${RED}  ❌ venturestrat.models not found${NC}"
    echo "  Make sure VENTURESTRAT_SDK path is correct"
    exit 1
}

# Test service model imports
python3 << 'EOF' || {
    echo -e "${RED}  ❌ Service model imports failed${NC}"
    exit 1
}
# Import models to verify conversion is correct
from registry.models.pricer_registry import PricerRegistry
from registry.models.pricer_capability import PricerCapability
from registry.repositories.pricing_repository import PricingRepository
print('  ✅ Service models import successfully')
EOF

echo ""
echo -e "${YELLOW}Database Configuration:${NC}"
echo "  Database URL: ${DATABASE_URL:-postgresql://registry:registry@localhost:5432/registry}"
echo ""

# Check if PostgreSQL is needed
echo -e "${YELLOW}Note:${NC}"
echo "  - Service requires PostgreSQL database"
echo "  - Set DATABASE_URL environment variable if different from default"
echo "  - BaseModel will auto-create tables on first run"
echo ""

# Ask user if they want to proceed
echo -e "${YELLOW}Starting service on http://0.0.0.0:8080${NC}"
echo "Press Ctrl+C to stop"
echo ""

# Start the service
exec python3 -m registry.main
