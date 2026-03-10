# VentureStrat Scripts

Cutover and operational scripts for the VentureStrat platform migration.

## Prerequisites

```bash
pip install psycopg2-binary httpx
```

## Scripts

| Script | Purpose |
|--------|---------|
| `verify_migration.py` | Check row counts and FK integrity for all 18 entity tables |
| `smoke_test.py` | End-to-end test of login, search, shortlist, email, subscription |
| `perf_test_search.py` | Load 120K investors, benchmark search P50/P95/P99 latency |
| `configure_stripe.sh` | Stripe webhook setup (dev listener + production instructions) |
| `configure_oauth.md` | Google OAuth, Microsoft OAuth, and SendGrid setup steps |
| `user_communication.md` | Email template and FAQ for notifying users about the migration |

## Usage

```bash
# Verify migration data
python scripts/verify_migration.py
python scripts/verify_migration.py --expected-counts investor=120000,market=50

# Run smoke test
python scripts/smoke_test.py

# Run performance test
python scripts/perf_test_search.py --record-count 120000

# Start Stripe dev listener
./scripts/configure_stripe.sh --dev
```
