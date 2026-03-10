#!/usr/bin/env python3
"""
End-to-end smoke test for VentureStrat.

Tests the full user journey across all services:
  1. Login (auth-service)
  2. Search investors (investor-service)
  3. Create shortlist entry (crm-service)
  4. Create draft email (outreach-service)
  5. Check subscription (billing-service)
  6. Validate usage (billing-service)

Usage:
  python scripts/smoke_test.py
  python scripts/smoke_test.py --host localhost --auth-port 8106
"""
import argparse
import asyncio
import json
import sys
import time
import uuid

try:
  import httpx
except ImportError:
  print('\033[91mError: httpx is required. Install with: pip install httpx\033[0m')
  sys.exit(1)


# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'

TENANT_ID = '00000000-0000-0000-0000-000000000000'


class SmokeTestRunner:
  def __init__(self, host, auth_port, investor_port, crm_port, outreach_port, billing_port,
               username, password):
    self.host = host
    self.auth_url = f'http://{host}:{auth_port}'
    self.investor_url = f'http://{host}:{investor_port}'
    self.crm_url = f'http://{host}:{crm_port}'
    self.outreach_url = f'http://{host}:{outreach_port}'
    self.billing_url = f'http://{host}:{billing_port}'
    self.username = username
    self.password = password
    self.token = None
    self.results = []
    # Track IDs for cleanup
    self.created_shortlist_id = None
    self.created_message_id = None

  def headers(self):
    h = {'X-Tenant-ID': TENANT_ID}
    if self.token:
      h['Authorization'] = f'Bearer {self.token}'
    return h

  async def run_step(self, name, coro):
    """Run a test step and record pass/fail."""
    start = time.monotonic()
    try:
      result = await coro
      elapsed = (time.monotonic() - start) * 1000
      self.results.append({
        'name': name,
        'passed': True,
        'elapsed_ms': elapsed,
        'detail': result,
      })
      print(f'  {GREEN}PASS{RESET}  {name} {DIM}({elapsed:.0f}ms){RESET}')
      return result
    except Exception as e:
      elapsed = (time.monotonic() - start) * 1000
      error_msg = str(e)
      self.results.append({
        'name': name,
        'passed': False,
        'elapsed_ms': elapsed,
        'detail': error_msg,
      })
      print(f'  {RED}FAIL{RESET}  {name} {DIM}({elapsed:.0f}ms){RESET}')
      print(f'        {RED}{error_msg}{RESET}')
      return None

  async def step_1_login(self):
    """Login and get JWT token."""
    async with httpx.AsyncClient() as client:
      resp = await client.post(
        f'{self.auth_url}/api/v1/auth/login',
        json={
          'username': self.username,
          'password': self.password,
          'tenant_id': TENANT_ID,
        },
        timeout=10.0,
      )
      if resp.status_code != 200:
        raise Exception(f'Login returned {resp.status_code}: {resp.text[:200]}')
      data = resp.json()
      self.token = data.get('access_token')
      if not self.token:
        raise Exception(f'No access_token in response: {list(data.keys())}')
      return f'token={self.token[:20]}...'

  async def step_2_search_investors(self):
    """Search investors with basic query."""
    async with httpx.AsyncClient() as client:
      resp = await client.get(
        f'{self.investor_url}/api/v1/investors',
        headers=self.headers(),
        params={'page_size': 5},
        timeout=10.0,
      )
      if resp.status_code != 200:
        raise Exception(f'Search returned {resp.status_code}: {resp.text[:200]}')
      data = resp.json()
      # Handle both paginated and list responses
      if isinstance(data, dict):
        items = data.get('items', data.get('data', []))
        total = data.get('total', len(items))
      elif isinstance(data, list):
        items = data
        total = len(items)
      else:
        items = []
        total = 0
      return f'total={total}, returned={len(items)}'

  async def step_3_create_shortlist(self):
    """Create a shortlist entry for the first investor found."""
    # First, get an investor ID
    async with httpx.AsyncClient() as client:
      resp = await client.get(
        f'{self.investor_url}/api/v1/investors',
        headers=self.headers(),
        params={'page_size': 1},
        timeout=10.0,
      )
      if resp.status_code != 200:
        raise Exception(f'Failed to fetch investors: {resp.status_code}')
      data = resp.json()
      if isinstance(data, dict):
        items = data.get('items', data.get('data', []))
      elif isinstance(data, list):
        items = data
      else:
        items = []
      if not items:
        raise Exception('No investors found to shortlist')
      investor_id = items[0].get('id')
      if not investor_id:
        raise Exception(f'Investor has no id field: {list(items[0].keys())}')

      # Create shortlist
      resp = await client.post(
        f'{self.crm_url}/api/v1/shortlists',
        headers=self.headers(),
        json={
          'user_id': self.username,
          'investor_id': investor_id,
          'status': 'target',
          'notes': 'Smoke test entry',
          'added_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        },
        timeout=10.0,
      )
      if resp.status_code not in (200, 201):
        raise Exception(f'Create shortlist returned {resp.status_code}: {resp.text[:200]}')
      shortlist = resp.json()
      self.created_shortlist_id = shortlist.get('id')
      return f'shortlist_id={self.created_shortlist_id}'

  async def step_4_create_draft_email(self):
    """Create a draft email message."""
    async with httpx.AsyncClient() as client:
      resp = await client.post(
        f'{self.outreach_url}/api/v1/messages',
        headers=self.headers(),
        json={
          'user_id': self.username,
          'status': 'draft',
          'to_addresses': ['test@example.com'],
          'cc_addresses': [],
          'subject': 'Smoke test email',
          'from_address': 'admin@venturestrat.test',
          'body': '<p>This is a smoke test draft email.</p>',
          'attachments': [],
        },
        timeout=10.0,
      )
      if resp.status_code not in (200, 201):
        raise Exception(f'Create message returned {resp.status_code}: {resp.text[:200]}')
      message = resp.json()
      self.created_message_id = message.get('id')
      return f'message_id={self.created_message_id}, status={message.get("status")}'

  async def step_5_check_subscription(self):
    """Check subscription status."""
    async with httpx.AsyncClient() as client:
      resp = await client.get(
        f'{self.billing_url}/api/v1/subscriptions',
        headers=self.headers(),
        params={'page_size': 1},
        timeout=10.0,
      )
      if resp.status_code != 200:
        raise Exception(f'Check subscription returned {resp.status_code}: {resp.text[:200]}')
      data = resp.json()
      if isinstance(data, dict):
        items = data.get('items', data.get('data', []))
      elif isinstance(data, list):
        items = data
      else:
        items = []
      if items:
        sub = items[0]
        return f'subscription status={sub.get("status")}, plan_id={sub.get("plan_id")}'
      return 'no subscriptions found (OK for new install)'

  async def step_6_validate_usage(self):
    """Validate usage endpoint responds correctly."""
    async with httpx.AsyncClient() as client:
      resp = await client.post(
        f'{self.billing_url}/api/v1/subscriptions/validate-usage',
        headers=self.headers(),
        json={
          'user_id': self.username,
          'action': 'email_send',
        },
        timeout=10.0,
      )
      # Accept 200 (allowed), 402 (limit reached), or 404 (no subscription)
      if resp.status_code in (200, 201):
        data = resp.json()
        return f'usage validation: allowed={data.get("allowed", True)}'
      elif resp.status_code == 402:
        return 'usage validation: limit reached (expected for free tier)'
      elif resp.status_code == 404:
        return 'usage validation: no subscription found (OK for new install)'
      else:
        raise Exception(f'Validate usage returned {resp.status_code}: {resp.text[:200]}')

  async def cleanup(self):
    """Remove test data created during smoke test."""
    async with httpx.AsyncClient() as client:
      if self.created_message_id:
        try:
          await client.delete(
            f'{self.outreach_url}/api/v1/messages/{self.created_message_id}',
            headers=self.headers(),
            timeout=5.0,
          )
        except Exception:
          pass

      if self.created_shortlist_id:
        try:
          await client.delete(
            f'{self.crm_url}/api/v1/shortlists/{self.created_shortlist_id}',
            headers=self.headers(),
            timeout=5.0,
          )
        except Exception:
          pass

  async def run_all(self):
    """Run all smoke test steps."""
    print(f'\n{BOLD}VentureStrat Smoke Test{RESET}')
    print(f'  Auth:     {self.auth_url}')
    print(f'  Investor: {self.investor_url}')
    print(f'  CRM:      {self.crm_url}')
    print(f'  Outreach: {self.outreach_url}')
    print(f'  Billing:  {self.billing_url}')
    print()

    # Step 1: Login
    await self.run_step('1. Login (POST /api/v1/auth/login)', self.step_1_login())
    if not self.token:
      print(f'\n  {RED}Cannot continue without auth token{RESET}')
      return

    # Steps 2-6
    await self.run_step('2. Search investors (GET /api/v1/investors)', self.step_2_search_investors())
    await self.run_step('3. Create shortlist (POST /api/v1/shortlists)', self.step_3_create_shortlist())
    await self.run_step('4. Create draft email (POST /api/v1/messages)', self.step_4_create_draft_email())
    await self.run_step('5. Check subscription (GET /api/v1/subscriptions)', self.step_5_check_subscription())
    await self.run_step('6. Validate usage (POST /api/v1/subscriptions/validate-usage)', self.step_6_validate_usage())

    # Cleanup
    print(f'\n{DIM}Cleaning up test data...{RESET}')
    await self.cleanup()

    # Summary
    passed = sum(1 for r in self.results if r['passed'])
    total = len(self.results)
    print(f'\n{BOLD}Results: {passed}/{total} steps passed{RESET}')

    if passed == total:
      print(f'{GREEN}{BOLD}ALL SMOKE TESTS PASSED{RESET}\n')
    else:
      failed_steps = [r['name'] for r in self.results if not r['passed']]
      print(f'{RED}{BOLD}FAILED STEPS:{RESET}')
      for name in failed_steps:
        print(f'  {RED}- {name}{RESET}')
      print()

    return passed == total


def main():
  parser = argparse.ArgumentParser(description='VentureStrat end-to-end smoke test')
  parser.add_argument('--host', default='localhost', help='Service host (default: localhost)')
  parser.add_argument('--auth-port', type=int, default=8106, help='Auth service port (default: 8106)')
  parser.add_argument('--investor-port', type=int, default=8059, help='Investor service port (default: 8059)')
  parser.add_argument('--crm-port', type=int, default=8062, help='CRM service port (default: 8062)')
  parser.add_argument('--outreach-port', type=int, default=8061, help='Outreach service port (default: 8061)')
  parser.add_argument('--billing-port', type=int, default=8063, help='Billing service port (default: 8063)')
  parser.add_argument('--username', default='admin', help='Auth username (default: admin)')
  parser.add_argument('--password', default='Admin123!@#', help='Auth password')
  args = parser.parse_args()

  runner = SmokeTestRunner(
    host=args.host,
    auth_port=args.auth_port,
    investor_port=args.investor_port,
    crm_port=args.crm_port,
    outreach_port=args.outreach_port,
    billing_port=args.billing_port,
    username=args.username,
    password=args.password,
  )

  all_pass = asyncio.run(runner.run_all())
  sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
  main()
