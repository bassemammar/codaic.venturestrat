"""
OAuth2 endpoints for connecting Gmail and Microsoft email accounts.

GET  /api/v1/oauth/google/authorize      — generate Google OAuth2 authorization URL
POST /api/v1/oauth/google/callback       — exchange code for tokens, store account
GET  /api/v1/oauth/microsoft/authorize   — generate Microsoft OAuth2 authorization URL
POST /api/v1/oauth/microsoft/callback    — exchange code for tokens, store account
GET  /api/v1/oauth/accounts             — list connected email accounts for a user
DELETE /api/v1/oauth/accounts/{id}       — disconnect an email account
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from outreach_service.config import settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Google OAuth2 constants
# ---------------------------------------------------------------------------

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
GOOGLE_REVOKE_URL = 'https://oauth2.googleapis.com/revoke'

GOOGLE_SCOPES = [
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/userinfo.email',
]

# ---------------------------------------------------------------------------
# Microsoft OAuth2 constants
# ---------------------------------------------------------------------------

MICROSOFT_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
MICROSOFT_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
MICROSOFT_USERINFO_URL = 'https://graph.microsoft.com/v1.0/me'

MICROSOFT_SCOPES = [
  'https://graph.microsoft.com/Mail.Send',
  'https://graph.microsoft.com/Mail.Read',
  'openid',
  'email',
  'profile',
  'offline_access',
]

# ---------------------------------------------------------------------------
# In-memory account store (replace with DB in production)
# account_id -> account dict
# ---------------------------------------------------------------------------

_accounts: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AuthorizeResponse(BaseModel):
  authorization_url: str


class OAuthCallbackRequest(BaseModel):
  code: str
  state: str


class ConnectedAccountResponse(BaseModel):
  id: str
  provider: str
  email: str
  connected_at: str
  is_active: bool = True


class CallbackResponse(BaseModel):
  email: str
  provider: str
  connected_at: str
  account_id: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=['OAuth'])


# ---------------------------------------------------------------------------
# Helper: check credentials configured
# ---------------------------------------------------------------------------

def _assert_google_configured() -> None:
  if not settings.google_client_id or not settings.google_client_secret:
    raise HTTPException(
      status_code=503,
      detail='Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.',
    )


def _assert_microsoft_configured() -> None:
  if not settings.microsoft_client_id or not settings.microsoft_client_secret:
    raise HTTPException(
      status_code=503,
      detail='Microsoft OAuth credentials not configured. Set MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET.',
    )


# ---------------------------------------------------------------------------
# GET /oauth/google/authorize
# ---------------------------------------------------------------------------

@router.get(
  '/google/authorize',
  response_model=AuthorizeResponse,
  summary='Get Google OAuth2 authorization URL',
  description='Returns a URL to redirect the user to for Google OAuth2 consent.',
)
async def google_authorize(
  user_id: str = Query(default='anonymous', description='User ID for state/CSRF param'),
) -> AuthorizeResponse:
  """Generate a Google OAuth2 authorization URL."""
  _assert_google_configured()

  # Use user_id + random nonce as state for CSRF protection
  state = f'{user_id}:{secrets.token_urlsafe(16)}'

  params = {
    'client_id': settings.google_client_id,
    'redirect_uri': settings.google_redirect_uri,
    'response_type': 'code',
    'scope': ' '.join(GOOGLE_SCOPES),
    'state': state,
    'access_type': 'offline',
    'prompt': 'consent',
  }

  authorization_url = f'{GOOGLE_AUTH_URL}?{urlencode(params)}'

  logger.info('google_authorize_url_generated', user_id=user_id)
  return AuthorizeResponse(authorization_url=authorization_url)


# ---------------------------------------------------------------------------
# POST /oauth/google/callback
# ---------------------------------------------------------------------------

@router.post(
  '/google/callback',
  response_model=CallbackResponse,
  summary='Exchange Google authorization code for tokens',
  description='Exchanges the OAuth2 code for tokens and stores the connected account.',
)
async def google_callback(body: OAuthCallbackRequest) -> CallbackResponse:
  """Exchange a Google authorization code for access + refresh tokens."""
  _assert_google_configured()

  # Extract user_id from state (format: "user_id:nonce")
  state_parts = body.state.split(':', 1)
  user_id = state_parts[0] if state_parts else 'anonymous'

  # Exchange code for tokens
  try:
    async with httpx.AsyncClient() as client:
      token_resp = await client.post(
        GOOGLE_TOKEN_URL,
        data={
          'code': body.code,
          'client_id': settings.google_client_id,
          'client_secret': settings.google_client_secret,
          'redirect_uri': settings.google_redirect_uri,
          'grant_type': 'authorization_code',
        },
      )
      token_resp.raise_for_status()
      tokens = token_resp.json()
  except httpx.HTTPStatusError as e:
    logger.error('google_token_exchange_failed', status=e.response.status_code, detail=e.response.text)
    raise HTTPException(
      status_code=400,
      detail=f'Google token exchange failed: {e.response.text}',
    )

  access_token = tokens.get('access_token')
  refresh_token = tokens.get('refresh_token')
  expires_in = tokens.get('expires_in', 3600)

  if not access_token:
    raise HTTPException(status_code=400, detail='No access_token in Google response')

  # Fetch user email via userinfo API
  try:
    async with httpx.AsyncClient() as client:
      userinfo_resp = await client.get(
        GOOGLE_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
      )
      userinfo_resp.raise_for_status()
      userinfo = userinfo_resp.json()
  except httpx.HTTPStatusError as e:
    logger.error('google_userinfo_failed', status=e.response.status_code)
    raise HTTPException(
      status_code=400,
      detail='Failed to fetch Google user info',
    )

  email = userinfo.get('email', '')
  if not email:
    raise HTTPException(status_code=400, detail='No email in Google userinfo response')

  # Deactivate any existing Gmail account for this user+email
  for acct in _accounts.values():
    if acct['user_id'] == user_id and acct['provider'] == 'gmail' and acct['email'] == email:
      acct['is_active'] = False

  # Store account
  account_id = str(uuid.uuid4())
  connected_at = datetime.now(timezone.utc).isoformat()
  token_expires_at = (
    datetime.now(timezone.utc) + timedelta(seconds=expires_in)
  ).isoformat()

  _accounts[account_id] = {
    'id': account_id,
    'user_id': user_id,
    'provider': 'gmail',
    'email': email,
    'access_token': access_token,
    'refresh_token': refresh_token,
    'token_expires_at': token_expires_at,
    'connected_at': connected_at,
    'is_active': True,
  }

  logger.info('google_account_connected', account_id=account_id, email=email, user_id=user_id)

  return CallbackResponse(
    email=email,
    provider='gmail',
    connected_at=connected_at,
    account_id=account_id,
  )


# ---------------------------------------------------------------------------
# GET /oauth/microsoft/authorize
# ---------------------------------------------------------------------------

@router.get(
  '/microsoft/authorize',
  response_model=AuthorizeResponse,
  summary='Get Microsoft OAuth2 authorization URL',
  description='Returns a URL to redirect the user to for Microsoft OAuth2 consent.',
)
async def microsoft_authorize(
  user_id: str = Query(default='anonymous', description='User ID for state/CSRF param'),
) -> AuthorizeResponse:
  """Generate a Microsoft OAuth2 authorization URL."""
  _assert_microsoft_configured()

  state = f'{user_id}:{secrets.token_urlsafe(16)}'

  params = {
    'client_id': settings.microsoft_client_id,
    'redirect_uri': settings.microsoft_redirect_uri,
    'response_type': 'code',
    'scope': ' '.join(MICROSOFT_SCOPES),
    'state': state,
    'response_mode': 'query',
  }

  authorization_url = f'{MICROSOFT_AUTH_URL}?{urlencode(params)}'

  logger.info('microsoft_authorize_url_generated', user_id=user_id)
  return AuthorizeResponse(authorization_url=authorization_url)


# ---------------------------------------------------------------------------
# POST /oauth/microsoft/callback
# ---------------------------------------------------------------------------

@router.post(
  '/microsoft/callback',
  response_model=CallbackResponse,
  summary='Exchange Microsoft authorization code for tokens',
  description='Exchanges the OAuth2 code for tokens and stores the connected account.',
)
async def microsoft_callback(body: OAuthCallbackRequest) -> CallbackResponse:
  """Exchange a Microsoft authorization code for access + refresh tokens."""
  _assert_microsoft_configured()

  state_parts = body.state.split(':', 1)
  user_id = state_parts[0] if state_parts else 'anonymous'

  # Exchange code for tokens
  try:
    async with httpx.AsyncClient() as client:
      token_resp = await client.post(
        MICROSOFT_TOKEN_URL,
        data={
          'code': body.code,
          'client_id': settings.microsoft_client_id,
          'client_secret': settings.microsoft_client_secret,
          'redirect_uri': settings.microsoft_redirect_uri,
          'grant_type': 'authorization_code',
          'scope': ' '.join(MICROSOFT_SCOPES),
        },
      )
      token_resp.raise_for_status()
      tokens = token_resp.json()
  except httpx.HTTPStatusError as e:
    logger.error('microsoft_token_exchange_failed', status=e.response.status_code, detail=e.response.text)
    raise HTTPException(
      status_code=400,
      detail=f'Microsoft token exchange failed: {e.response.text}',
    )

  access_token = tokens.get('access_token')
  refresh_token = tokens.get('refresh_token')
  expires_in = tokens.get('expires_in', 3600)

  if not access_token:
    raise HTTPException(status_code=400, detail='No access_token in Microsoft response')

  # Fetch user email via Microsoft Graph
  try:
    async with httpx.AsyncClient() as client:
      userinfo_resp = await client.get(
        MICROSOFT_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
      )
      userinfo_resp.raise_for_status()
      userinfo = userinfo_resp.json()
  except httpx.HTTPStatusError as e:
    logger.error('microsoft_userinfo_failed', status=e.response.status_code)
    raise HTTPException(
      status_code=400,
      detail='Failed to fetch Microsoft user info',
    )

  email = userinfo.get('mail') or userinfo.get('userPrincipalName', '')
  if not email:
    raise HTTPException(status_code=400, detail='No email in Microsoft userinfo response')

  # Deactivate any existing Microsoft account for this user+email
  for acct in _accounts.values():
    if acct['user_id'] == user_id and acct['provider'] == 'microsoft' and acct['email'] == email:
      acct['is_active'] = False

  # Store account
  account_id = str(uuid.uuid4())
  connected_at = datetime.now(timezone.utc).isoformat()
  token_expires_at = (
    datetime.now(timezone.utc) + timedelta(seconds=expires_in)
  ).isoformat()

  _accounts[account_id] = {
    'id': account_id,
    'user_id': user_id,
    'provider': 'microsoft',
    'email': email,
    'access_token': access_token,
    'refresh_token': refresh_token,
    'token_expires_at': token_expires_at,
    'connected_at': connected_at,
    'is_active': True,
  }

  logger.info('microsoft_account_connected', account_id=account_id, email=email, user_id=user_id)

  return CallbackResponse(
    email=email,
    provider='microsoft',
    connected_at=connected_at,
    account_id=account_id,
  )


# ---------------------------------------------------------------------------
# GET /oauth/accounts
# ---------------------------------------------------------------------------

@router.get(
  '/accounts',
  response_model=list[ConnectedAccountResponse],
  summary='List connected email accounts',
  description='Returns all connected email accounts for a user.',
)
async def list_accounts(
  user_id: str = Query(default='anonymous', description='User ID to filter accounts'),
) -> list[ConnectedAccountResponse]:
  """List all connected email accounts for a given user."""
  results = [
    ConnectedAccountResponse(
      id=acct['id'],
      provider=acct['provider'],
      email=acct['email'],
      connected_at=acct['connected_at'],
      is_active=acct.get('is_active', True),
    )
    for acct in _accounts.values()
    if acct['user_id'] == user_id and acct.get('is_active', True)
  ]
  return sorted(results, key=lambda a: a.connected_at, reverse=True)


# ---------------------------------------------------------------------------
# DELETE /oauth/accounts/{account_id}
# ---------------------------------------------------------------------------

@router.delete(
  '/accounts/{account_id}',
  status_code=204,
  summary='Disconnect an email account',
  description='Revokes the OAuth token (if possible) and removes the account.',
)
async def disconnect_account(account_id: str) -> None:
  """Disconnect an email account and attempt to revoke its token."""
  acct = _accounts.get(account_id)
  if not acct:
    raise HTTPException(status_code=404, detail='Account not found')

  # Attempt token revocation for Gmail
  if acct['provider'] == 'gmail' and acct.get('access_token'):
    try:
      async with httpx.AsyncClient() as client:
        await client.post(
          GOOGLE_REVOKE_URL,
          params={'token': acct['access_token']},
        )
      logger.info('google_token_revoked', account_id=account_id)
    except Exception as e:
      # Revocation failure is non-fatal — we still remove locally
      logger.warning('google_token_revoke_failed', account_id=account_id, error=str(e))

  del _accounts[account_id]
  logger.info('account_disconnected', account_id=account_id, provider=acct['provider'])
