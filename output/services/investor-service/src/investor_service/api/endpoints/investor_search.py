"""Investor Search, Filters, and Live Preview Endpoints.

Custom endpoints beyond generated CRUD for the investor discovery experience:
  - GET /api/v1/investors/search — paginated multi-filter search with sorting
  - GET /api/v1/investors/filters — distinct filter values for dropdowns
  - GET /api/v1/investors/live-preview — 6 random investors for landing page

Wave 7 of VentureStrat migration.
"""

import hashlib
import json
import random
from math import ceil
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel as PydanticBaseModel, Field

from investor_service.core.database import get_session
from investor_service.infrastructure.repositories.base_repository import BaseRepository
from investor_service.infrastructure.orm.investor import Investor
from investor_service.infrastructure.orm.investor_email import InvestorEmail
from investor_service.infrastructure.orm.investor_market import InvestorMarket
from investor_service.infrastructure.orm.market import Market
from investor_service.api.endpoints.investor_search_cache import redis_cache

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Investor Search'])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class InvestorSearchItem(PydanticBaseModel):
  """Single investor in search results."""
  id: str
  name: str
  avatar: Optional[str] = None
  website: Optional[str] = None
  phone: Optional[str] = None
  title: Optional[str] = None
  external_id: Optional[str] = None
  city: Optional[str] = None
  state: Optional[str] = None
  country: Optional[str] = None
  company_name: Optional[str] = None
  stages: Any = Field(default_factory=list)
  investor_types: Any = Field(default_factory=list)
  social_links: Optional[Any] = None
  country_priority: int = 2
  primary_email: Optional[str] = None
  market_names: List[str] = Field(default_factory=list)
  created_at: Optional[str] = None
  updated_at: Optional[str] = None


class InvestorSearchResponse(PydanticBaseModel):
  """Paginated search response."""
  items: List[InvestorSearchItem]
  total: int
  page: int
  page_size: int
  total_pages: int


class InvestorFiltersResponse(PydanticBaseModel):
  """Available filter values for dropdowns."""
  locations: List[str]
  stages: List[str]
  types: List[str]
  markets: List[Dict[str, str]]


class InvestorLivePreviewItem(PydanticBaseModel):
  """Lightweight investor for landing page preview."""
  id: str
  name: str
  company_name: Optional[str] = None
  city: Optional[str] = None
  country: Optional[str] = None
  stages: Any = Field(default_factory=list)
  avatar: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_json(val: Any) -> list:
  """Parse a JSON field that may be a string, list, or None."""
  if val is None:
    return []
  if isinstance(val, list):
    return val
  if isinstance(val, str):
    try:
      parsed = json.loads(val)
      return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
      return []
  return []


def _build_cache_key(prefix: str, params: dict) -> str:
  """Deterministic cache key from filter params."""
  raw = json.dumps(sorted(params.items()), default=str)
  digest = hashlib.md5(raw.encode()).hexdigest()
  return f'investor:{prefix}:{digest}'


def _location_string(obj: dict) -> Optional[str]:
  """Build 'City, State, Country' string from investor dict."""
  parts = [p for p in [obj.get('city'), obj.get('state'), obj.get('country')] if p]
  return ', '.join(parts) if parts else None


def _to_str(val: Any) -> Optional[str]:
  """Safely convert a value to string for datetime fields."""
  if val is None:
    return None
  return str(val)


async def _get_all_investors(repo: BaseRepository) -> list:
  """Fetch all investors (the BaseModel ORM doesn't support SQL-level joins,
  so we fetch in Python and join in memory)."""
  return await repo.get_all(skip=0, limit=999999)


async def _get_primary_emails() -> dict:
  """Return {investor_id: email} for the first email per investor."""
  email_repo = BaseRepository(InvestorEmail)
  all_emails = await email_repo.get_all(skip=0, limit=999999)
  result: dict = {}
  for e in all_emails:
    d = e.to_dict()
    inv_id = d.get('investor_id')
    if inv_id and inv_id not in result:
      result[inv_id] = d.get('email')
  return result


async def _get_investor_market_map() -> dict:
  """Return {investor_id: [market_title, ...]}."""
  im_repo = BaseRepository(InvestorMarket)
  m_repo = BaseRepository(Market)

  all_im = await im_repo.get_all(skip=0, limit=999999)
  all_markets = await m_repo.get_all(skip=0, limit=999999)

  market_lookup = {}
  for m in all_markets:
    md = m.to_dict()
    market_lookup[md['id']] = md.get('title', '')

  result: dict = {}
  for im in all_im:
    imd = im.to_dict()
    inv_id = imd.get('investor_id')
    mkt_id = imd.get('market_id')
    if inv_id and mkt_id:
      result.setdefault(inv_id, []).append(market_lookup.get(mkt_id, ''))

  return result


# ---------------------------------------------------------------------------
# 7.1 — GET /investors/search
# ---------------------------------------------------------------------------

@router.get(
  '/search',
  response_model=InvestorSearchResponse,
  summary='Search investors',
  description='Paginated, multi-filter, multi-sort investor search.',
)
async def search_investors(
  request: Request,
  page: int = Query(default=1, ge=1, description='Page number (1-indexed)'),
  page_size: int = Query(default=20, ge=1, le=200, description='Results per page'),
  name: Optional[str] = Query(default=None, description='Name filter (case-insensitive contains)'),
  company: Optional[str] = Query(default=None, description='Company name filter (case-insensitive contains)'),
  location: Optional[str] = Query(default=None, description='City / state / country filter (case-insensitive contains)'),
  stages: Optional[str] = Query(default=None, description='Comma-separated stages to match (JSON array contains)'),
  types: Optional[str] = Query(default=None, description='Comma-separated investor types to match (JSON array contains)'),
  market_ids: Optional[str] = Query(default=None, description='Comma-separated market UUIDs'),
  sort_by: str = Query(default='name', description='Field to sort by'),
  sort_dir: str = Query(default='asc', description='Sort direction: asc or desc'),
  session=Depends(get_session),
) -> InvestorSearchResponse:
  # Build filter params dict for cache key
  filter_params = {
    'name': name, 'company': company, 'location': location,
    'stages': stages, 'types': types, 'market_ids': market_ids,
    'sort_by': sort_by, 'sort_dir': sort_dir,
  }
  count_cache_key = _build_cache_key('search_count', filter_params)

  # Fetch all data (BaseModel ORM doesn't support SQL-level joins)
  investor_repo = BaseRepository(Investor)
  all_investors = await _get_all_investors(investor_repo)
  primary_emails = await _get_primary_emails()
  market_map = await _get_investor_market_map()

  # Convert to dicts for filtering
  items = []
  for inv in all_investors:
    d = inv.to_dict()
    d['_primary_email'] = primary_emails.get(d['id'])
    d['_market_names'] = market_map.get(d['id'], [])
    items.append(d)

  # --- Apply filters ---

  if name:
    name_lower = name.lower()
    items = [i for i in items if name_lower in (i.get('name') or '').lower()]

  if company:
    company_lower = company.lower()
    items = [i for i in items if company_lower in (i.get('company_name') or '').lower()]

  if location:
    loc_lower = location.lower()
    items = [
      i for i in items
      if loc_lower in (i.get('city') or '').lower()
      or loc_lower in (i.get('state') or '').lower()
      or loc_lower in (i.get('country') or '').lower()
    ]

  if stages:
    wanted_stages = {s.strip().lower() for s in stages.split(',')}
    items = [
      i for i in items
      if wanted_stages & {s.lower() for s in _safe_json(i.get('stages'))}
    ]

  if types:
    wanted_types = {t.strip().lower() for t in types.split(',')}
    items = [
      i for i in items
      if wanted_types & {t.lower() for t in _safe_json(i.get('investor_types'))}
    ]

  if market_ids:
    wanted_market_ids = {m.strip() for m in market_ids.split(',')}
    # Investor must have at least one matching market
    im_repo = BaseRepository(InvestorMarket)
    all_im = await im_repo.get_all(skip=0, limit=999999)
    investor_ids_with_market = set()
    for im in all_im:
      imd = im.to_dict()
      if imd.get('market_id') in wanted_market_ids:
        investor_ids_with_market.add(imd.get('investor_id'))
    items = [i for i in items if i['id'] in investor_ids_with_market]

  # --- Sort ---
  reverse = sort_dir.lower() == 'desc'
  items.sort(key=lambda i: (i.get(sort_by) or '') if isinstance(i.get(sort_by), str) else i.get(sort_by, 0), reverse=reverse)

  total = len(items)

  # Try to cache total count
  await redis_cache.set(count_cache_key, str(total), ttl=300)

  # Paginate
  start = (page - 1) * page_size
  end = start + page_size
  page_items = items[start:end]

  # Build response items
  result_items = []
  for d in page_items:
    result_items.append(InvestorSearchItem(
      id=d['id'],
      name=d.get('name', ''),
      avatar=d.get('avatar'),
      website=d.get('website'),
      phone=d.get('phone'),
      title=d.get('title'),
      external_id=d.get('external_id'),
      city=d.get('city'),
      state=d.get('state'),
      country=d.get('country'),
      company_name=d.get('company_name'),
      stages=_safe_json(d.get('stages')),
      investor_types=_safe_json(d.get('investor_types')),
      social_links=d.get('social_links'),
      country_priority=d.get('country_priority', 2),
      primary_email=d.get('_primary_email'),
      market_names=d.get('_market_names', []),
      created_at=_to_str(d.get('created_at')),
      updated_at=_to_str(d.get('updated_at')),
    ))

  return InvestorSearchResponse(
    items=result_items,
    total=total,
    page=page,
    page_size=page_size,
    total_pages=ceil(total / page_size) if page_size else 0,
  )


# ---------------------------------------------------------------------------
# 7.2 — GET /investors/filters
# ---------------------------------------------------------------------------

@router.get(
  '/filters',
  response_model=InvestorFiltersResponse,
  summary='Get filter options',
  description='Returns distinct values for search filter dropdowns.',
)
async def get_filters(
  request: Request,
  session=Depends(get_session),
) -> InvestorFiltersResponse:
  cache_key = 'investor:filters:all'
  cached = await redis_cache.get(cache_key)
  if cached:
    try:
      return InvestorFiltersResponse(**json.loads(cached))
    except Exception:
      pass

  investor_repo = BaseRepository(Investor)
  all_investors = await _get_all_investors(investor_repo)

  locations_set: set = set()
  stages_set: set = set()
  types_set: set = set()

  for inv in all_investors:
    d = inv.to_dict()
    loc = _location_string(d)
    if loc:
      locations_set.add(loc)
    # Also add individual country values
    if d.get('country'):
      locations_set.add(d['country'])

    for s in _safe_json(d.get('stages')):
      if s:
        stages_set.add(s)

    for t in _safe_json(d.get('investor_types')):
      if t:
        types_set.add(t)

  # Markets from Market table
  m_repo = BaseRepository(Market)
  all_markets = await m_repo.get_all(skip=0, limit=999999)
  markets_list = [
    {'id': m.to_dict()['id'], 'title': m.to_dict().get('title', '')}
    for m in all_markets
  ]
  markets_list.sort(key=lambda m: m['title'])

  result = InvestorFiltersResponse(
    locations=sorted(locations_set),
    stages=sorted(stages_set),
    types=sorted(types_set),
    markets=markets_list,
  )

  await redis_cache.set(cache_key, result.model_dump_json(), ttl=900)

  return result


# ---------------------------------------------------------------------------
# 7.3 — GET /investors/live-preview
# ---------------------------------------------------------------------------

@router.get(
  '/live-preview',
  response_model=List[InvestorLivePreviewItem],
  summary='Live preview investors',
  description='Returns 6 random investors for landing page preview. Public endpoint.',
)
async def live_preview(
  session=Depends(get_session),
) -> List[InvestorLivePreviewItem]:
  cache_key = 'investor:live_preview'
  cached = await redis_cache.get(cache_key)
  if cached:
    try:
      parsed = json.loads(cached)
      return [InvestorLivePreviewItem(**item) for item in parsed]
    except Exception:
      pass

  investor_repo = BaseRepository(Investor)
  all_investors = await _get_all_investors(investor_repo)

  # Pick 6 random (or all if fewer than 6)
  sample_size = min(6, len(all_investors))
  if sample_size == 0:
    return []

  chosen = random.sample(all_investors, sample_size)

  result = []
  for inv in chosen:
    d = inv.to_dict()
    result.append(InvestorLivePreviewItem(
      id=d['id'],
      name=d.get('name', ''),
      company_name=d.get('company_name'),
      city=d.get('city'),
      country=d.get('country'),
      stages=_safe_json(d.get('stages')),
      avatar=d.get('avatar'),
    ))

  # Cache for 1 minute
  await redis_cache.set(
    cache_key,
    json.dumps([item.model_dump() for item in result]),
    ttl=60,
  )

  return result
