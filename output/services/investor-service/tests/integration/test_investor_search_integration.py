"""Integration tests for investor search, filters, and live-preview.

Tests the full search pipeline end-to-end through the FastAPI app with
large datasets, combined filters, pagination boundaries, sorting, and
Redis cache behaviour.  All external dependencies (BaseModel ORM, Redis)
are mocked so the tests run without infrastructure.
"""

import json
from datetime import datetime
from math import ceil
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers — fake ORM objects
# ---------------------------------------------------------------------------

def _make_investor(
  name='Investor',
  company_name='Fund',
  city='New York',
  state='NY',
  country='USA',
  stages=None,
  investor_types=None,
  **overrides,
):
  obj = MagicMock()
  data = {
    'id': overrides.get('id', str(uuid4())),
    'name': name,
    'avatar': overrides.get('avatar'),
    'website': overrides.get('website'),
    'phone': overrides.get('phone'),
    'title': overrides.get('title'),
    'external_id': overrides.get('external_id', 'ext-1'),
    'city': city,
    'state': state,
    'country': country,
    'company_name': company_name,
    'stages': json.dumps(stages or ['Seed']),
    'investor_types': json.dumps(investor_types or ['Angel']),
    'social_links': None,
    'pipelines': None,
    'founded_companies': None,
    'country_priority': overrides.get('country_priority', 2),
    'source_data': None,
    'created_at': datetime(2024, 1, 1),
    'updated_at': datetime(2024, 1, 1),
  }
  data.update(overrides)
  obj.to_dict.return_value = data
  return obj


def _make_email(investor_id, email='test@example.com'):
  obj = MagicMock()
  obj.to_dict.return_value = {
    'id': str(uuid4()),
    'investor_id': investor_id,
    'email': email,
    'status': 'valid',
  }
  return obj


def _make_market(market_id=None, title='FinTech'):
  obj = MagicMock()
  obj.to_dict.return_value = {
    'id': market_id or str(uuid4()),
    'title': title,
    'is_country': False,
  }
  return obj


def _make_investor_market(investor_id, market_id):
  obj = MagicMock()
  obj.to_dict.return_value = {
    'id': str(uuid4()),
    'investor_id': investor_id,
    'market_id': market_id,
  }
  return obj


def _patch_repos(investors, emails, markets, investor_markets):
  """Build a FakeRepo class that returns the right data per model class."""

  class FakeRepo:
    def __init__(self, model, session=None):
      self.model = model

    async def get_all(self, skip=0, limit=999999):
      from investor_service.infrastructure.orm.investor import Investor
      from investor_service.infrastructure.orm.investor_email import InvestorEmail
      from investor_service.infrastructure.orm.investor_market import InvestorMarket
      from investor_service.infrastructure.orm.market import Market

      if self.model is Investor:
        return investors
      elif self.model is InvestorEmail:
        return emails
      elif self.model is Market:
        return markets
      elif self.model is InvestorMarket:
        return investor_markets
      return []

  return FakeRepo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def app():
  """Import the FastAPI app once."""
  import os
  os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
  os.environ.setdefault('PLATFORM_MODE', 'standalone')
  os.environ.setdefault('LOG_LEVEL', 'WARNING')
  from investor_service.main import app
  return app


@pytest.fixture
def client(app):
  return TestClient(app)


# ---------------------------------------------------------------------------
# Large dataset fixture (120 investors across 3 locations, 4 stages,
# 3 investor types, 2 markets)
# ---------------------------------------------------------------------------

MKT_FINTECH = str(uuid4())
MKT_HEALTH = str(uuid4())

STAGES_POOL = ['Pre-Seed', 'Seed', 'Series A', 'Series B']
TYPES_POOL = ['Angel', 'VC', 'PE']
CITIES = [
  ('San Francisco', 'CA', 'USA'),
  ('London', '', 'UK'),
  ('Berlin', '', 'Germany'),
]
MARKETS = [
  _make_market(MKT_FINTECH, 'FinTech'),
  _make_market(MKT_HEALTH, 'HealthTech'),
]


def _build_large_dataset():
  """Create 120 investors with deterministic attributes."""
  investors = []
  emails = []
  inv_markets = []

  for i in range(120):
    inv_id = str(uuid4())
    city, state, country = CITIES[i % len(CITIES)]
    stage = STAGES_POOL[i % len(STAGES_POOL)]
    inv_type = TYPES_POOL[i % len(TYPES_POOL)]

    investors.append(_make_investor(
      id=inv_id,
      name=f'Investor {i:03d}',
      company_name=f'Fund {i:03d}',
      city=city,
      state=state,
      country=country,
      stages=[stage],
      investor_types=[inv_type],
    ))
    emails.append(_make_email(inv_id, f'inv{i}@fund{i}.com'))

    # Assign markets: even investors -> FinTech, multiples of 3 -> HealthTech
    if i % 2 == 0:
      inv_markets.append(_make_investor_market(inv_id, MKT_FINTECH))
    if i % 3 == 0:
      inv_markets.append(_make_investor_market(inv_id, MKT_HEALTH))

  return investors, emails, inv_markets


LARGE_INVESTORS, LARGE_EMAILS, LARGE_INV_MARKETS = _build_large_dataset()


@pytest.fixture
def large_dataset():
  return LARGE_INVESTORS, LARGE_EMAILS, MARKETS, LARGE_INV_MARKETS


# ---------------------------------------------------------------------------
# Integration Tests — Search with large dataset
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestInvestorSearchIntegrationLargeDataset:
  """Search integration tests against a 120-investor dataset."""

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_search_returns_all_120(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={'page_size': 200})
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 120
    assert len(data['items']) == 120

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_filter_by_name(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={'name': 'Investor 00'})
    data = resp.json()
    # Should match 'Investor 000' through 'Investor 009' (10 investors)
    assert data['total'] == 10

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_filter_by_location(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={'location': 'London'})
    data = resp.json()
    # London investors: every 3rd starting at index 1 (1, 4, 7, ...) -> 40
    assert data['total'] == 40

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_filter_by_stages(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={'stages': 'Seed'})
    data = resp.json()
    # Seed is at index 1 in STAGES_POOL -> every 4th starting at 1
    assert data['total'] == 30

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_combined_name_location_stages(self, _redis, client, large_dataset):
    """Combine name + location + stages filters."""
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'name': 'Investor',
        'location': 'USA',
        'stages': 'Seed',
      })
    data = resp.json()
    # USA investors with Seed stage
    # USA = index 0, 3, 6, 9, ... (every 3rd) -> 40 total
    # Seed = index 1, 5, 9, 13, ... (every 4th)
    # Intersection: indices where i%3==0 AND i%4==1 -> i=1 mod 12 -> nope
    # Actually: USA = i%3==0 -> {0,3,6,9,...}, Seed = i%4==1 -> {1,5,9,13,...}
    # Intersection = i%3==0 AND i%4==1 -> i in {9,21,33,45,57,69,81,93,105,117} = 10
    assert data['total'] == 10

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_filter_by_market_ids(self, _redis, client, large_dataset):
    """Filter by HealthTech market."""
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'market_ids': MKT_HEALTH,
      })
    data = resp.json()
    # HealthTech: i%3==0 -> 40 investors
    assert data['total'] == 40

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_combined_market_and_stages(self, _redis, client, large_dataset):
    """Filter by FinTech market + Series A stage."""
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'market_ids': MKT_FINTECH,
        'stages': 'Series A',
      })
    data = resp.json()
    # FinTech: i%2==0 (60), Series A: i%4==2 (30)
    # Intersection: i%2==0 AND i%4==2 -> i%4==2 -> 30 investors
    assert data['total'] == 30


# ---------------------------------------------------------------------------
# Integration Tests — Pagination
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestInvestorSearchPagination:
  """Verify pagination correctness at boundaries."""

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_page_1_correct_count(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'page': 1, 'page_size': 25,
      })
    data = resp.json()
    assert data['total'] == 120
    assert len(data['items']) == 25
    assert data['page'] == 1
    assert data['page_size'] == 25
    assert data['total_pages'] == ceil(120 / 25)

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_last_page_partial(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      # 120 / 25 = 4.8 -> 5 pages, last page has 20 items
      resp = client.get('/api/v1/investors/search', params={
        'page': 5, 'page_size': 25,
      })
    data = resp.json()
    assert data['total'] == 120
    assert len(data['items']) == 120 - (4 * 25)  # 20

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_beyond_last_page_empty(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'page': 99, 'page_size': 25,
      })
    data = resp.json()
    assert data['total'] == 120
    assert len(data['items']) == 0

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_total_items_across_all_pages(self, _redis, client, large_dataset):
    """Sum items across all pages equals total."""
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    total_items = 0
    page = 1
    page_size = 30
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      while True:
        resp = client.get('/api/v1/investors/search', params={
          'page': page, 'page_size': page_size,
        })
        data = resp.json()
        items_on_page = len(data['items'])
        total_items += items_on_page
        if items_on_page < page_size:
          break
        page += 1
    assert total_items == 120


# ---------------------------------------------------------------------------
# Integration Tests — Sorting
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestInvestorSearchSorting:
  """Verify sort by different fields and directions."""

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_sort_by_name_asc(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'sort_by': 'name', 'sort_dir': 'asc', 'page_size': 200,
      })
    data = resp.json()
    names = [i['name'] for i in data['items']]
    assert names == sorted(names)

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_sort_by_name_desc(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'sort_by': 'name', 'sort_dir': 'desc', 'page_size': 200,
      })
    data = resp.json()
    names = [i['name'] for i in data['items']]
    assert names == sorted(names, reverse=True)

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_sort_by_company_name(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'sort_by': 'company_name', 'sort_dir': 'asc', 'page_size': 200,
      })
    data = resp.json()
    companies = [i['company_name'] for i in data['items']]
    assert companies == sorted(companies)

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_sort_by_city(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search', params={
        'sort_by': 'city', 'sort_dir': 'asc', 'page_size': 200,
      })
    data = resp.json()
    cities = [i['city'] for i in data['items']]
    assert cities == sorted(cities)


# ---------------------------------------------------------------------------
# Integration Tests — Redis cache behaviour
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestInvestorSearchRedisCache:
  """Verify Redis caching interactions."""

  def test_search_caches_total_count(self, client, large_dataset):
    """search endpoint tries to cache the total count in Redis."""
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()
    mock_redis.ping = AsyncMock()

    with patch(
      'investor_service.api.endpoints.investor_search_cache._get_redis',
      new_callable=AsyncMock,
      return_value=mock_redis,
    ), patch(
      'investor_service.api.endpoints.investor_search.BaseRepository',
      FakeRepo,
    ):
      resp = client.get('/api/v1/investors/search')
    assert resp.status_code == 200
    # Verify redis.set was called (cache the total count)
    mock_redis.set.assert_called()

  def test_filters_returns_from_cache(self, client, large_dataset):
    """When Redis has cached filters, they should be returned directly."""
    cached_data = json.dumps({
      'locations': ['Cached City'],
      'stages': ['Cached Stage'],
      'types': ['Cached Type'],
      'markets': [{'id': 'mkt-1', 'title': 'Cached Market'}],
    })

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=cached_data)
    mock_redis.set = AsyncMock()
    mock_redis.ping = AsyncMock()

    with patch(
      'investor_service.api.endpoints.investor_search_cache._get_redis',
      new_callable=AsyncMock,
      return_value=mock_redis,
    ):
      resp = client.get('/api/v1/investors/filters')
    assert resp.status_code == 200
    data = resp.json()
    assert data['locations'] == ['Cached City']
    assert data['stages'] == ['Cached Stage']

  def test_filters_cache_miss_fetches_data(self, client, large_dataset):
    """When Redis cache misses, data is fetched from repo and cached."""
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # Cache miss
    mock_redis.set = AsyncMock()
    mock_redis.ping = AsyncMock()

    with patch(
      'investor_service.api.endpoints.investor_search_cache._get_redis',
      new_callable=AsyncMock,
      return_value=mock_redis,
    ), patch(
      'investor_service.api.endpoints.investor_search.BaseRepository',
      FakeRepo,
    ):
      resp = client.get('/api/v1/investors/filters')
    assert resp.status_code == 200
    data = resp.json()
    # Should contain real data from the dataset
    assert 'USA' in data['locations']
    assert 'UK' in data['locations']
    # Redis set should have been called to cache the result
    mock_redis.set.assert_called()


# ---------------------------------------------------------------------------
# Integration Tests — Live Preview
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestInvestorLivePreviewIntegration:
  """Integration tests for the live preview endpoint."""

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_live_preview_returns_6_from_large_dataset(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/live-preview')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_live_preview_returns_different_results(self, _redis, client, large_dataset):
    """Multiple calls should return different random investors (with high probability)."""
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    results = []
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      for _ in range(5):
        resp = client.get('/api/v1/investors/live-preview')
        assert resp.status_code == 200
        ids = frozenset(item['id'] for item in resp.json())
        results.append(ids)
    # With 120 investors and 6 picks, 5 calls should produce at least 2
    # different sets (probability of all 5 identical is vanishingly small)
    unique_sets = set(results)
    assert len(unique_sets) >= 2

  @patch(
    'investor_service.api.endpoints.investor_search_cache._get_redis',
    new_callable=AsyncMock,
    return_value=None,
  )
  def test_live_preview_item_has_required_fields(self, _redis, client, large_dataset):
    investors, emails, markets, inv_markets = large_dataset
    FakeRepo = _patch_repos(investors, emails, markets, inv_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/live-preview')
    data = resp.json()
    for item in data:
      assert 'id' in item
      assert 'name' in item
      assert 'stages' in item
      assert isinstance(item['stages'], list)
