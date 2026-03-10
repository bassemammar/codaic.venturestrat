#!/usr/bin/env python3
"""
Performance test for VentureStrat investor search.

Generates 120K synthetic investor records via bulk SQL insert,
runs investor search with various filter combinations,
measures P50/P95/P99 latency, and cleans up test data.

Usage:
  python scripts/perf_test_search.py
  python scripts/perf_test_search.py --host localhost --api-port 8059 --db-port 15436
  python scripts/perf_test_search.py --record-count 50000 --concurrency 20
"""
import argparse
import asyncio
import json
import random
import statistics
import string
import sys
import time
import uuid

try:
  import httpx
except ImportError:
  print('\033[91mError: httpx is required. Install with: pip install httpx\033[0m')
  sys.exit(1)

try:
  import psycopg2
except ImportError:
  print('\033[91mError: psycopg2 is required. Install with: pip install psycopg2-binary\033[0m')
  sys.exit(1)


# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

TENANT_ID = '00000000-0000-0000-0000-000000000000'

COUNTRIES = [
  'United States', 'United Kingdom', 'Germany', 'France', 'Canada',
  'Singapore', 'Israel', 'India', 'Japan', 'Australia',
  'Brazil', 'Sweden', 'Netherlands', 'Switzerland', 'South Korea',
]
STATES = [
  'California', 'New York', 'Texas', 'Massachusetts', 'Florida',
  'Washington', 'Illinois', 'Colorado', 'Georgia', 'Pennsylvania',
  None, None, None,
]
CITIES = [
  'San Francisco', 'New York', 'London', 'Berlin', 'Singapore',
  'Tel Aviv', 'Toronto', 'Mumbai', 'Tokyo', 'Sydney',
  'Palo Alto', 'Boston', 'Austin', 'Seattle', 'Chicago',
]
STAGES = ['Pre-Seed', 'Seed', 'Series A', 'Series B', 'Series C', 'Growth', 'Late Stage']
TYPES = ['Angel', 'VC', 'PE', 'Family Office', 'Corporate', 'Accelerator', 'Syndicate']
TITLES = [
  'Managing Partner', 'General Partner', 'Partner', 'Principal',
  'Associate', 'Venture Partner', 'Founding Partner', 'Investment Director',
]


def random_name():
  first = ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 8)))
  last = ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))
  return f'{first} {last}'


def random_company():
  suffixes = ['Capital', 'Ventures', 'Partners', 'Fund', 'Labs', 'Holdings', 'Investments', 'Group']
  name = ''.join(random.choices(string.ascii_uppercase, k=1)) + ''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 7)))
  return f'{name} {random.choice(suffixes)}'


def generate_investor_rows(count, batch_tag):
  """Generate investor row tuples for bulk insert."""
  rows = []
  for i in range(count):
    investor_id = str(uuid.uuid4())
    name = random_name()
    country = random.choice(COUNTRIES)
    state = random.choice(STATES)
    city = random.choice(CITIES)
    stages = json.dumps(random.sample(STAGES, k=random.randint(1, 3)))
    inv_types = json.dumps(random.sample(TYPES, k=random.randint(1, 2)))
    title = random.choice(TITLES)
    company = random_company()
    external_id = f'perf-{batch_tag}-{i}'
    priority = random.choice([1, 1, 2, 2, 2, 3])
    rows.append((
      investor_id, TENANT_ID, name, None, None, None,
      title, external_id, city, state, country,
      company, stages, inv_types, None, None, None,
      priority, None,
    ))
  return rows


def bulk_insert_investors(conn, rows):
  """Insert investor rows using executemany with a batch approach."""
  cur = conn.cursor()
  sql = """
    INSERT INTO venturestrat.vs_investor (
      id, tenant_id, name, avatar, website, phone,
      title, external_id, city, state, country,
      company_name, stages, investor_types, social_links, pipelines, founded_companies,
      country_priority, source_data
    ) VALUES (
      %s::uuid, %s::uuid, %s, %s, %s, %s,
      %s, %s, %s, %s, %s,
      %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
      %s, %s::jsonb
    )
  """
  batch_size = 5000
  for i in range(0, len(rows), batch_size):
    batch = rows[i:i + batch_size]
    cur.executemany(sql, batch)
    conn.commit()
    done = min(i + batch_size, len(rows))
    print(f'  Inserted {done:,} / {len(rows):,} rows', end='\r')
  print()
  cur.close()


def cleanup_test_data(conn, batch_tag):
  """Remove test investors by external_id prefix."""
  cur = conn.cursor()
  cur.execute(
    "DELETE FROM venturestrat.vs_investor WHERE external_id LIKE %s",
    (f'perf-{batch_tag}-%',),
  )
  deleted = cur.rowcount
  conn.commit()
  cur.close()
  return deleted


def get_auth_token(base_url, username, password):
  """Login and get JWT token."""
  resp = httpx.post(
    f'{base_url}/api/v1/auth/login',
    json={
      'username': username,
      'password': password,
      'tenant_id': TENANT_ID,
    },
    timeout=10.0,
  )
  resp.raise_for_status()
  return resp.json()['access_token']


# Search filter combinations to test
SEARCH_SCENARIOS = [
  {'name': 'No filters (page 1)', 'params': {'page': 1, 'page_size': 25}},
  {'name': 'Filter by country', 'params': {'country': 'United States', 'page_size': 25}},
  {'name': 'Filter by country + state', 'params': {'country': 'United States', 'state': 'California', 'page_size': 25}},
  {'name': 'Filter by city', 'params': {'city': 'San Francisco', 'page_size': 25}},
  {'name': 'Large page (100)', 'params': {'page_size': 100}},
  {'name': 'Name search', 'params': {'search': 'partner', 'page_size': 25}},
]


async def run_search(client, url, headers, params, iterations):
  """Run a search scenario multiple times and collect latencies."""
  latencies = []
  for _ in range(iterations):
    start = time.monotonic()
    try:
      resp = await client.get(url, headers=headers, params=params, timeout=10.0)
      elapsed = (time.monotonic() - start) * 1000  # ms
      if resp.status_code == 200:
        latencies.append(elapsed)
      else:
        latencies.append(elapsed)
    except httpx.HTTPError:
      latencies.append(float('inf'))
  return latencies


async def run_perf_tests(api_base, auth_base, token, concurrency, iterations):
  """Run all search scenarios with concurrency."""
  headers = {
    'Authorization': f'Bearer {token}',
    'X-Tenant-ID': TENANT_ID,
  }
  search_url = f'{api_base}/api/v1/investors'

  results = []

  async with httpx.AsyncClient() as client:
    for scenario in SEARCH_SCENARIOS:
      # Run concurrent requests
      tasks = []
      for _ in range(concurrency):
        tasks.append(run_search(client, search_url, headers, scenario['params'], iterations))

      all_latencies_nested = await asyncio.gather(*tasks)
      all_latencies = []
      for lat_list in all_latencies_nested:
        all_latencies.extend(lat_list)

      # Filter out infinite (failed) requests
      valid = [l for l in all_latencies if l != float('inf')]
      failed = len(all_latencies) - len(valid)

      if valid:
        valid.sort()
        p50 = statistics.median(valid)
        p95 = valid[int(len(valid) * 0.95)] if len(valid) >= 20 else max(valid)
        p99 = valid[int(len(valid) * 0.99)] if len(valid) >= 100 else max(valid)
        avg = statistics.mean(valid)
      else:
        p50 = p95 = p99 = avg = float('inf')

      results.append({
        'name': scenario['name'],
        'total': len(all_latencies),
        'failed': failed,
        'p50': p50,
        'p95': p95,
        'p99': p99,
        'avg': avg,
      })

  return results


def print_results(results, target_p95):
  print(f'\n{BOLD}{CYAN}=== Search Performance Results ==={RESET}\n')
  print(f'  {"Scenario":<30} {"Reqs":>6} {"Fail":>6} {"P50 ms":>10} {"P95 ms":>10} {"P99 ms":>10} {"Avg ms":>10} {"Status":>8}')
  print(f'  {"-" * 30} {"-" * 6} {"-" * 6} {"-" * 10} {"-" * 10} {"-" * 10} {"-" * 10} {"-" * 8}')

  all_pass = True
  for r in results:
    ok = r['p95'] <= target_p95 and r['failed'] == 0
    if not ok:
      all_pass = False
    color = GREEN if ok else RED
    status = 'PASS' if ok else 'FAIL'
    print(
      f'  {r["name"]:<30} {r["total"]:>6} {r["failed"]:>6} '
      f'{r["p50"]:>10.1f} {r["p95"]:>10.1f} {r["p99"]:>10.1f} {r["avg"]:>10.1f} '
      f'{color}{status}{RESET}'
    )

  print(f'\n  Target P95: {YELLOW}<{target_p95}ms{RESET}')
  if all_pass:
    print(f'  {GREEN}{BOLD}ALL SCENARIOS PASSED{RESET}\n')
  else:
    print(f'  {RED}{BOLD}SOME SCENARIOS FAILED{RESET}\n')

  return all_pass


def main():
  parser = argparse.ArgumentParser(description='VentureStrat investor search performance test')
  parser.add_argument('--host', default='localhost', help='Service host (default: localhost)')
  parser.add_argument('--api-port', type=int, default=8059, help='Investor service port (default: 8059)')
  parser.add_argument('--auth-port', type=int, default=8106, help='Auth service port (default: 8106)')
  parser.add_argument('--db-host', default='localhost', help='PostgreSQL host (default: localhost)')
  parser.add_argument('--db-port', type=int, default=15436, help='PostgreSQL port (default: 15436)')
  parser.add_argument('--db-name', default='venturestrat', help='Database name')
  parser.add_argument('--db-user', default='venturestrat', help='Database user')
  parser.add_argument('--db-password', default='venturestrat_dev_password', help='Database password')
  parser.add_argument('--record-count', type=int, default=120000, help='Number of test investors (default: 120000)')
  parser.add_argument('--concurrency', type=int, default=10, help='Concurrent requests per scenario (default: 10)')
  parser.add_argument('--iterations', type=int, default=10, help='Iterations per concurrent worker (default: 10)')
  parser.add_argument('--target-p95', type=float, default=500.0, help='Target P95 latency in ms (default: 500)')
  parser.add_argument('--username', default='admin', help='Auth username')
  parser.add_argument('--password', default='Admin123!@#', help='Auth password')
  parser.add_argument('--skip-cleanup', action='store_true', help='Skip test data cleanup')
  args = parser.parse_args()

  api_base = f'http://{args.host}:{args.api_port}'
  auth_base = f'http://{args.host}:{args.auth_port}'
  batch_tag = uuid.uuid4().hex[:8]

  print(f'\n{BOLD}VentureStrat Search Performance Test{RESET}')
  print(f'  API: {api_base}  Auth: {auth_base}  DB: {args.db_host}:{args.db_port}')
  print(f'  Records: {args.record_count:,}  Concurrency: {args.concurrency}  Iterations: {args.iterations}')
  print(f'  Batch tag: {batch_tag}')

  # 1. Connect to DB
  print(f'\n{CYAN}Connecting to database...{RESET}')
  try:
    conn = psycopg2.connect(
      host=args.db_host,
      port=args.db_port,
      dbname=args.db_name,
      user=args.db_user,
      password=args.db_password,
    )
  except psycopg2.Error as e:
    print(f'{RED}DB connection failed: {e}{RESET}')
    sys.exit(1)

  # 2. Generate and insert test data
  print(f'{CYAN}Generating {args.record_count:,} synthetic investors...{RESET}')
  rows = generate_investor_rows(args.record_count, batch_tag)

  print(f'{CYAN}Bulk inserting into venturestrat.vs_investor...{RESET}')
  t0 = time.monotonic()
  bulk_insert_investors(conn, rows)
  insert_time = time.monotonic() - t0
  print(f'  Insert completed in {insert_time:.1f}s ({args.record_count / insert_time:,.0f} rows/s)')

  # 3. Get auth token
  print(f'\n{CYAN}Authenticating...{RESET}')
  try:
    token = get_auth_token(auth_base, args.username, args.password)
    print(f'  {GREEN}Authenticated{RESET}')
  except Exception as e:
    print(f'  {RED}Auth failed: {e}{RESET}')
    if not args.skip_cleanup:
      cleanup_test_data(conn, batch_tag)
    conn.close()
    sys.exit(1)

  # 4. Run performance tests
  print(f'\n{CYAN}Running search performance tests...{RESET}')
  results = asyncio.run(run_perf_tests(api_base, auth_base, token, args.concurrency, args.iterations))
  all_pass = print_results(results, args.target_p95)

  # 5. Cleanup
  if not args.skip_cleanup:
    print(f'{CYAN}Cleaning up test data...{RESET}')
    deleted = cleanup_test_data(conn, batch_tag)
    print(f'  Deleted {deleted:,} test rows')
  else:
    print(f'{YELLOW}Skipping cleanup (--skip-cleanup). Batch tag: {batch_tag}{RESET}')

  conn.close()
  sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
  main()
