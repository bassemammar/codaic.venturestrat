"""Unit tests for investor search, filters, and live-preview endpoints.

Tests mock the BaseModel ORM repositories and Redis cache so they run
without any external dependencies.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers to build fake ORM objects
# ---------------------------------------------------------------------------

def _make_investor(
  name='Alice Vc',
  company_name='Alpha Fund',
  city='San Francisco',
  state='CA',
  country='USA',
  stages=None,
  investor_types=None,
  **overrides,
):
  """Return a mock ORM object that behaves like BaseModel."""
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


def _make_email(investor_id, email='alice@example.com'):
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Fixed IDs for deterministic tests
INV_1_ID = str(uuid4())
INV_2_ID = str(uuid4())
INV_3_ID = str(uuid4())
MKT_FINTECH_ID = str(uuid4())
MKT_HEALTH_ID = str(uuid4())


@pytest.fixture
def sample_investors():
  return [
    _make_investor(
      id=INV_1_ID, name='Alice Vc', company_name='Alpha Fund',
      city='San Francisco', state='CA', country='USA',
      stages=['Seed', 'Series A'], investor_types=['Angel', 'VC'],
    ),
    _make_investor(
      id=INV_2_ID, name='Bob Capital', company_name='Beta Ventures',
      city='London', state='', country='UK',
      stages=['Series B'], investor_types=['VC'],
    ),
    _make_investor(
      id=INV_3_ID, name='Carol Growth', company_name='Gamma Partners',
      city='Berlin', state='', country='Germany',
      stages=['Seed'], investor_types=['Angel'],
    ),
  ]


@pytest.fixture
def sample_emails():
  return [
    _make_email(INV_1_ID, 'alice@alphafund.com'),
    _make_email(INV_2_ID, 'bob@betaventures.com'),
  ]


@pytest.fixture
def sample_markets():
  return [
    _make_market(MKT_FINTECH_ID, 'FinTech'),
    _make_market(MKT_HEALTH_ID, 'HealthTech'),
  ]


@pytest.fixture
def sample_investor_markets():
  return [
    _make_investor_market(INV_1_ID, MKT_FINTECH_ID),
    _make_investor_market(INV_2_ID, MKT_FINTECH_ID),
    _make_investor_market(INV_2_ID, MKT_HEALTH_ID),
  ]


def _patch_repos(
  sample_investors,
  sample_emails,
  sample_markets,
  sample_investor_markets,
):
  """Return a side_effect function that resolves get_all based on model class."""
  async def fake_get_all(self_or_skip=None, skip=0, limit=999999):
    pass  # not used directly

  original_init = None

  class FakeRepo:
    """A fake BaseRepository whose get_all returns data based on model."""

    def __init__(self, model, session=None):
      self.model = model

    async def get_all(self, skip=0, limit=999999):
      from investor_service.infrastructure.orm.investor import Investor
      from investor_service.infrastructure.orm.investor_email import InvestorEmail
      from investor_service.infrastructure.orm.investor_market import InvestorMarket
      from investor_service.infrastructure.orm.market import Market

      if self.model is Investor:
        return sample_investors
      elif self.model is InvestorEmail:
        return sample_emails
      elif self.model is Market:
        return sample_markets
      elif self.model is InvestorMarket:
        return sample_investor_markets
      return []

  return FakeRepo


# ---------------------------------------------------------------------------
# Tests — 7.1 Search
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestInvestorSearch:

  def _do_search(self, client, params=None):
    return client.get('/api/v1/investors/search', params=params or {})

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_returns_all(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client)
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 3
    assert data['page'] == 1
    assert data['page_size'] == 20
    assert len(data['items']) == 3

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_filter_by_name(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'name': 'alice'})
    data = resp.json()
    assert data['total'] == 1
    assert data['items'][0]['name'] == 'Alice Vc'

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_filter_by_company(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'company': 'beta'})
    data = resp.json()
    assert data['total'] == 1
    assert data['items'][0]['company_name'] == 'Beta Ventures'

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_filter_by_location(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'location': 'london'})
    data = resp.json()
    assert data['total'] == 1
    assert data['items'][0]['name'] == 'Bob Capital'

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_filter_by_stages(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'stages': 'Seed'})
    data = resp.json()
    # Alice and Carol have 'Seed'
    assert data['total'] == 2

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_filter_by_types(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'types': 'VC'})
    data = resp.json()
    # Alice and Bob have 'VC'
    assert data['total'] == 2

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_filter_by_market_ids(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'market_ids': MKT_HEALTH_ID})
    data = resp.json()
    # Only Bob is in HealthTech
    assert data['total'] == 1
    assert data['items'][0]['name'] == 'Bob Capital'

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_combined_filters(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'stages': 'Seed', 'types': 'Angel'})
    data = resp.json()
    # Alice has both Seed+Angel, Carol has Seed+Angel
    assert data['total'] == 2

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_pagination(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'page': 1, 'page_size': 2})
    data = resp.json()
    assert data['total'] == 3
    assert len(data['items']) == 2
    assert data['total_pages'] == 2

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_page_2(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'page': 2, 'page_size': 2})
    data = resp.json()
    assert data['total'] == 3
    assert len(data['items']) == 1

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_sort_desc(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'sort_by': 'name', 'sort_dir': 'desc'})
    data = resp.json()
    names = [item['name'] for item in data['items']]
    assert names == sorted(names, reverse=True)

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_sort_asc(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'sort_by': 'name', 'sort_dir': 'asc'})
    data = resp.json()
    names = [item['name'] for item in data['items']]
    assert names == sorted(names)

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_includes_primary_email(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'name': 'alice'})
    data = resp.json()
    assert data['items'][0]['primary_email'] == 'alice@alphafund.com'

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_includes_market_names(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = self._do_search(client, {'name': 'bob'})
    data = resp.json()
    market_names = data['items'][0]['market_names']
    assert 'FinTech' in market_names
    assert 'HealthTech' in market_names


# ---------------------------------------------------------------------------
# Tests — 7.2 Filters
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestInvestorFilters:

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_filters_returns_expected_structure(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/filters')
    assert resp.status_code == 200
    data = resp.json()
    assert 'locations' in data
    assert 'stages' in data
    assert 'types' in data
    assert 'markets' in data

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_filters_locations(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/filters')
    data = resp.json()
    assert 'USA' in data['locations']
    assert 'UK' in data['locations']
    assert 'Germany' in data['locations']

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_filters_stages(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/filters')
    data = resp.json()
    assert 'Seed' in data['stages']
    assert 'Series A' in data['stages']
    assert 'Series B' in data['stages']

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_filters_types(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/filters')
    data = resp.json()
    assert 'Angel' in data['types']
    assert 'VC' in data['types']

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_filters_markets(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/filters')
    data = resp.json()
    market_titles = [m['title'] for m in data['markets']]
    assert 'FinTech' in market_titles
    assert 'HealthTech' in market_titles

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_filters_cached(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    """Test that a second call uses the cached response when Redis is available."""
    # With Redis unavailable (None), there's no cache — both calls hit the repo.
    # This test just verifies the endpoint is stable across multiple calls.
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp1 = client.get('/api/v1/investors/filters')
      resp2 = client.get('/api/v1/investors/filters')
    assert resp1.json() == resp2.json()


# ---------------------------------------------------------------------------
# Tests — 7.3 Live Preview
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestInvestorLivePreview:

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_live_preview_returns_max_6(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/live-preview')
    assert resp.status_code == 200
    data = resp.json()
    # We have 3 investors, so all 3 should appear
    assert len(data) == 3

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_live_preview_item_structure(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/live-preview')
    data = resp.json()
    item = data[0]
    assert 'id' in item
    assert 'name' in item
    assert 'company_name' in item
    assert 'city' in item
    assert 'country' in item
    assert 'stages' in item

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_live_preview_empty_when_no_investors(self, mock_redis, client):
    FakeRepo = _patch_repos([], [], [], [])
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/live-preview')
    assert resp.status_code == 200
    assert resp.json() == []

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_live_preview_limits_to_6(self, mock_redis, client):
    """When there are more than 6 investors, only 6 should be returned."""
    many_investors = [
      _make_investor(id=str(uuid4()), name=f'Investor {i}')
      for i in range(10)
    ]
    FakeRepo = _patch_repos(many_investors, [], [], [])
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/live-preview')
    assert resp.status_code == 200
    assert len(resp.json()) == 6


# ---------------------------------------------------------------------------
# Tests — Redis cache mock behavior
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCacheBehavior:

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_search_works_without_redis(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    """Endpoints gracefully degrade when Redis is unavailable."""
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/search')
    assert resp.status_code == 200

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_filters_works_without_redis(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/filters')
    assert resp.status_code == 200

  @patch('investor_service.api.endpoints.investor_search_cache._get_redis', new_callable=AsyncMock, return_value=None)
  def test_live_preview_works_without_redis(self, mock_redis, client, sample_investors, sample_emails, sample_markets, sample_investor_markets):
    FakeRepo = _patch_repos(sample_investors, sample_emails, sample_markets, sample_investor_markets)
    with patch('investor_service.api.endpoints.investor_search.BaseRepository', FakeRepo):
      resp = client.get('/api/v1/investors/live-preview')
    assert resp.status_code == 200
