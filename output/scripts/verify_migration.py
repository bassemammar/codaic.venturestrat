#!/usr/bin/env python3
"""
Data migration verification script for VentureStrat.

Connects to PostgreSQL, checks row counts for all 18 entity tables
in the venturestrat schema, verifies FK integrity, and prints a summary.

Usage:
  python scripts/verify_migration.py
  python scripts/verify_migration.py --host localhost --port 15436
  python scripts/verify_migration.py --expected-counts investor=120000,market=50
"""
import argparse
import sys

try:
  import psycopg2
except ImportError:
  print('\033[91mError: psycopg2 is required. Install with: pip install psycopg2-binary\033[0m')
  sys.exit(1)


# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

SCHEMA = 'venturestrat'

# All 18 domain entity tables in the venturestrat schema
ENTITY_TABLES = [
  # investor-service (6)
  'vs_investor',
  'vs_investor_email',
  'vs_investor_market',
  'vs_investor_past_investment',
  'vs_market',
  'vs_past_investment',
  # outreach-service (4)
  'vs_email_account',
  'vs_email_template',
  'vs_lifecycle_email',
  'vs_message',
  # crm-service (5)
  'vs_activity',
  'vs_pipeline_stage',
  'vs_shortlist',
  'vs_shortlist_tag',
  'vs_tag',
  # billing-service (3)
  'vs_plan',
  'vs_subscription',
  'vs_usage_record',
]

# Foreign key relationships: (child_table, fk_column, parent_table, parent_column)
FK_RELATIONSHIPS = [
  # investor-service
  ('vs_investor_email', 'investor_id', 'vs_investor', 'id'),
  ('vs_investor_market', 'investor_id', 'vs_investor', 'id'),
  ('vs_investor_market', 'market_id', 'vs_market', 'id'),
  ('vs_investor_past_investment', 'investor_id', 'vs_investor', 'id'),
  ('vs_investor_past_investment', 'past_investment_id', 'vs_past_investment', 'id'),
  # outreach-service
  ('vs_message', 'email_account_id', 'vs_email_account', 'id'),
  ('vs_message', 'previous_message_id', 'vs_message', 'id'),
  # crm-service
  ('vs_shortlist', 'stage_id', 'vs_pipeline_stage', 'id'),
  ('vs_activity', 'shortlist_id', 'vs_shortlist', 'id'),
  ('vs_shortlist_tag', 'shortlist_id', 'vs_shortlist', 'id'),
  ('vs_shortlist_tag', 'tag_id', 'vs_tag', 'id'),
  # billing-service
  ('vs_subscription', 'plan_id', 'vs_plan', 'id'),
]


def parse_expected_counts(raw: str) -> dict:
  """Parse 'investor=120000,market=50' into {'vs_investor': 120000, ...}."""
  counts = {}
  if not raw:
    return counts
  for pair in raw.split(','):
    pair = pair.strip()
    if '=' not in pair:
      continue
    name, count_str = pair.split('=', 1)
    name = name.strip()
    # Allow both 'investor' and 'vs_investor'
    if not name.startswith('vs_'):
      name = f'vs_{name}'
    counts[name] = int(count_str.strip())
  return counts


def get_connection(host, port, dbname, user, password):
  return psycopg2.connect(
    host=host,
    port=port,
    dbname=dbname,
    user=user,
    password=password,
  )


def check_row_counts(cur, expected_counts):
  """Check row counts for all entity tables. Returns (results, all_pass)."""
  results = []
  all_pass = True

  for table in ENTITY_TABLES:
    try:
      cur.execute(f'SELECT COUNT(*) FROM {SCHEMA}.{table}')
      actual = cur.fetchone()[0]
    except psycopg2.Error as e:
      results.append((table, '-', 'ERROR', False, str(e).strip().split('\n')[0]))
      all_pass = False
      cur.connection.rollback()
      continue

    expected = expected_counts.get(table)
    if expected is not None:
      ok = actual == expected
      status = 'OK' if ok else 'MISMATCH'
      if not ok:
        all_pass = False
      results.append((table, expected, actual, ok, status))
    else:
      # No expected count: just verify table is accessible and report count
      ok = actual >= 0
      results.append((table, '-', actual, ok, 'OK'))

  return results, all_pass


def check_fk_integrity(cur):
  """Check for orphaned FK references. Returns (results, all_pass)."""
  results = []
  all_pass = True

  for child_table, fk_col, parent_table, parent_col in FK_RELATIONSHIPS:
    # Find rows where FK is not null but parent row does not exist
    query = f"""
      SELECT COUNT(*) FROM {SCHEMA}.{child_table} c
      WHERE c.{fk_col} IS NOT NULL
        AND NOT EXISTS (
          SELECT 1 FROM {SCHEMA}.{parent_table} p
          WHERE p.{parent_col} = c.{fk_col}
        )
    """
    try:
      cur.execute(query)
      orphan_count = cur.fetchone()[0]
    except psycopg2.Error as e:
      results.append((child_table, fk_col, parent_table, 'ERROR', str(e).strip().split('\n')[0]))
      all_pass = False
      cur.connection.rollback()
      continue

    ok = orphan_count == 0
    if not ok:
      all_pass = False
    status = 'OK' if ok else f'{orphan_count} orphaned'
    results.append((child_table, fk_col, parent_table, status, ok))

  return results, all_pass


def print_row_count_table(results):
  print(f'\n{BOLD}{CYAN}=== Row Count Verification ==={RESET}\n')
  # Header
  print(f'  {"Entity Table":<32} {"Expected":>10} {"Actual":>10}   {"Status":<10}')
  print(f'  {"-" * 32} {"-" * 10} {"-" * 10}   {"-" * 10}')

  for row in results:
    table, expected, actual, ok, status = row
    color = GREEN if ok else RED
    print(f'  {table:<32} {str(expected):>10} {str(actual):>10}   {color}{status}{RESET}')


def print_fk_integrity_table(results):
  print(f'\n{BOLD}{CYAN}=== Foreign Key Integrity ==={RESET}\n')
  print(f'  {"Child Table":<30} {"FK Column":<22} {"Parent Table":<26} {"Status":<16}')
  print(f'  {"-" * 30} {"-" * 22} {"-" * 26} {"-" * 16}')

  for child, fk_col, parent, status, ok in results:
    color = GREEN if ok else RED
    print(f'  {child:<30} {fk_col:<22} {parent:<26} {color}{status}{RESET}')


def main():
  parser = argparse.ArgumentParser(description='Verify VentureStrat data migration')
  parser.add_argument('--host', default='localhost', help='PostgreSQL host (default: localhost)')
  parser.add_argument('--port', type=int, default=15436, help='PostgreSQL port (default: 15436)')
  parser.add_argument('--dbname', default='venturestrat', help='Database name (default: venturestrat)')
  parser.add_argument('--user', default='venturestrat', help='Database user (default: venturestrat)')
  parser.add_argument('--password', default='venturestrat_dev_password', help='Database password')
  parser.add_argument(
    '--expected-counts',
    default='',
    help='Expected row counts: investor=120000,market=50 (use table name without vs_ prefix)',
  )
  args = parser.parse_args()

  expected_counts = parse_expected_counts(args.expected_counts)

  print(f'\n{BOLD}VentureStrat Migration Verification{RESET}')
  print(f'  Host: {args.host}:{args.port}  DB: {args.dbname}  User: {args.user}')

  try:
    conn = get_connection(args.host, args.port, args.dbname, args.user, args.password)
  except psycopg2.Error as e:
    print(f'\n{RED}Connection failed: {e}{RESET}')
    sys.exit(1)

  cur = conn.cursor()
  all_pass = True

  # 1. Row counts
  row_results, rows_ok = check_row_counts(cur, expected_counts)
  print_row_count_table(row_results)
  if not rows_ok:
    all_pass = False

  # 2. FK integrity
  fk_results, fk_ok = check_fk_integrity(cur)
  print_fk_integrity_table(fk_results)
  if not fk_ok:
    all_pass = False

  # Summary
  total_rows = sum(r[2] for r in row_results if isinstance(r[2], int))
  print(f'\n{BOLD}Summary:{RESET}')
  print(f'  Tables checked: {len(ENTITY_TABLES)}')
  print(f'  Total rows:     {total_rows:,}')
  print(f'  FK checks:      {len(FK_RELATIONSHIPS)}')

  if all_pass:
    print(f'\n  {GREEN}{BOLD}ALL CHECKS PASSED{RESET}\n')
  else:
    print(f'\n  {RED}{BOLD}SOME CHECKS FAILED{RESET}\n')

  cur.close()
  conn.close()
  sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
  main()
