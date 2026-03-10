#!/bin/bash
# Registry Service - BaseModel Conversion Test Script
# Tests the converted BaseModel implementation

set -e  # Exit on error

echo "=========================================="
echo "Registry Service: BaseModel Conversion Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

echo "Phase 1: Syntax Validation"
echo "-------------------------------------------"

# Test 1: Python syntax check for all converted files
python3 << 'EOF'
import sys

files = [
    ('src/registry/models/pricer_registry.py', 'pricer_registry'),
    ('src/registry/models/pricer_capability.py', 'pricer_capability'),
    ('src/registry/models/tenant.py', 'tenant'),
    ('src/registry/models/tenant_pricing_config.py', 'tenant_pricing_config'),
    ('src/registry/models/tenant_quotas.py', 'tenant_quotas'),
    ('src/registry/repositories/pricing_repository.py', 'pricing_repository'),
]

all_ok = True
for file_path, name in files:
    try:
        with open(file_path) as f:
            compile(f.read(), name, 'exec')
    except SyntaxError as e:
        print(f'Syntax error in {name}: {e}', file=sys.stderr)
        all_ok = False

sys.exit(0 if all_ok else 1)
EOF

test_result $? "All converted files have valid Python syntax"

# Test 2: Check for SQLAlchemy imports (should be removed)
echo ""
echo "Phase 2: Import Validation"
echo "-------------------------------------------"

! grep -r "from sqlalchemy" src/registry/models/ > /dev/null 2>&1
test_result $? "Models: No SQLAlchemy imports found"

! grep -r "from sqlalchemy" src/registry/repositories/pricing_repository.py > /dev/null 2>&1
test_result $? "Repository: No SQLAlchemy imports found"

# Test 3: Check for BaseModel imports (should be present)
grep -q "from venturestrat.models import BaseModel, fields" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: Uses BaseModel"

grep -q "from venturestrat.models import BaseModel, fields" src/registry/models/pricer_capability.py
test_result $? "pricer_capability: Uses BaseModel"

grep -q "from venturestrat.models import BaseModel, fields" src/registry/models/tenant.py
test_result $? "tenant: Uses BaseModel"

# Test 4: Check for fields.* usage (BaseModel pattern)
grep -q "fields.String" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: Uses fields.String()"

grep -q "fields.Boolean" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: Uses fields.Boolean()"

grep -q "fields.Integer" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: Uses fields.Integer()"

# Test 5: Check repository uses BaseModel API
echo ""
echo "Phase 3: Repository API Validation"
echo "-------------------------------------------"

grep -q "\.search\(\[" src/registry/repositories/pricing_repository.py
test_result $? "Repository: Uses Model.search() API"

grep -q "\.create({" src/registry/repositories/pricing_repository.py
test_result $? "Repository: Uses Model.create() API"

grep -q "\.write({" src/registry/repositories/pricing_repository.py
test_result $? "Repository: Uses record.write() API"

grep -q "\.unlink\(\)" src/registry/repositories/pricing_repository.py
test_result $? "Repository: Uses record.unlink() API"

# Test 6: Check that SQLAlchemy patterns are removed
! grep -q "session.execute\|session.add\|session.commit\|session.rollback\|AsyncSession" src/registry/repositories/pricing_repository.py
test_result $? "Repository: No SQLAlchemy session operations"

! grep -q "select\(.*\)\.where" src/registry/repositories/pricing_repository.py
test_result $? "Repository: No SQLAlchemy select() queries"

# Test 7: Check model structure
echo ""
echo "Phase 4: Model Structure Validation"
echo "-------------------------------------------"

grep -q "_name = \"pricer_registry\"" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: Has _name attribute"

grep -q "_schema = \"public\"" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: Has _schema attribute"

grep -q "_no_tenant = True" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: Has _no_tenant flag"

# Test 8: Check for Column() removal (should not exist)
! grep -q "Column(" src/registry/models/pricer_registry.py
test_result $? "pricer_registry: No Column() definitions"

! grep -q "Column(" src/registry/models/pricer_capability.py
test_result $? "pricer_capability: No Column() definitions"

# Print summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start the service: python -m registry.main"
    echo "2. Test endpoints: curl http://localhost:8080/health/live"
    echo "3. Test pricer operations: See CONVERSION_COMPLETE.md"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo "Review the failures above and fix before proceeding."
    exit 1
fi
