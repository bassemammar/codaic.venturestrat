"""POST /email-accounts/{id}/watch — Register push notifications for an email account."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from outreach_service.application.services.email_account_service import EmailAccountService
from outreach_service.config import settings
from outreach_service.core.database import get_session
from outreach_service.providers import gmail, microsoft
from outreach_service.schemas.email_account import EmailAccountUpdate

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['EmailAccount'])


class WatchRequest(BaseModel):
  """Request body for registering a push notification watch."""
  pubsub_topic: str | None = Field(
    default=None,
    description='Google Cloud Pub/Sub topic for Gmail push notifications',
  )
  notification_url: str | None = Field(
    default=None,
    description='Webhook URL for Microsoft Graph notifications',
  )


class WatchResult(BaseModel):
  """Response after registering a watch."""
  email_account_id: str = Field(description='Email account ID')
  provider: str = Field(description='Email provider')
  watch_history_id: str | None = Field(
    default=None, description='Gmail history ID (Gmail only)'
  )
  expiration: str | None = Field(
    default=None, description='Watch expiration timestamp'
  )
  status: str = Field(description='Watch registration status')


@router.post(
  '/{id}/watch',
  response_model=WatchResult,
  summary='Register push notification watch',
  description=(
    'Registers a push notification watch on the email account\'s inbox. '
    'For Gmail, this calls the Gmail API watch endpoint. '
    'For Microsoft, this creates a Graph API subscription.'
  ),
  responses={
    200: {'description': 'Watch registered successfully'},
    400: {'description': 'Missing required configuration'},
    404: {'description': 'Email account not found'},
    501: {'description': 'Provider not supported for watching'},
  },
)
async def watch_email_account(
  id: UUID,
  body: WatchRequest,
  session=Depends(get_session),
) -> WatchResult:
  """Register a push notification watch for an email account."""
  service = EmailAccountService(session)

  account = await service.get_email_account(id)
  if not account:
    raise HTTPException(status_code=404, detail='Email account not found')

  if not account.is_active:
    raise HTTPException(status_code=400, detail='Email account is not active')

  if not account.access_token:
    raise HTTPException(
      status_code=400,
      detail='Email account has no access token — re-authenticate via OAuth',
    )

  provider = (account.provider or '').lower()

  try:
    if provider == 'gmail':
      topic = body.pubsub_topic
      if not topic:
        raise HTTPException(
          status_code=400,
          detail='pubsub_topic is required for Gmail watch registration',
        )

      result = await gmail.watch_inbox(
        access_token=account.access_token,
        topic_name=topic,
      )

      history_id = str(result.get('historyId', ''))
      expiration = result.get('expiration')

      # Store watch_history_id on the account
      update_data = EmailAccountUpdate(watch_history_id=history_id)
      await service.update_email_account(id, update_data)

      return WatchResult(
        email_account_id=str(id),
        provider=provider,
        watch_history_id=history_id,
        expiration=str(expiration) if expiration else None,
        status='active',
      )

    elif provider == 'microsoft':
      notification_url = body.notification_url
      if not notification_url:
        raise HTTPException(
          status_code=400,
          detail='notification_url is required for Microsoft watch registration',
        )

      result = await microsoft.create_subscription(
        access_token=account.access_token,
        notification_url=notification_url,
      )

      return WatchResult(
        email_account_id=str(id),
        provider=provider,
        watch_history_id=None,
        expiration=result.get('expirationDateTime'),
        status='active',
      )

    else:
      raise HTTPException(
        status_code=501,
        detail=f'Push notification watch is not supported for provider: {provider}',
      )

  except NotImplementedError as e:
    raise HTTPException(status_code=501, detail=str(e))
  except HTTPException:
    raise
  except Exception as e:
    logger.error(
      'watch_registration_failed',
      email_account_id=str(id),
      provider=provider,
      error=str(e),
    )
    raise HTTPException(
      status_code=502,
      detail=f'Failed to register watch via {provider}: {str(e)}',
    )
