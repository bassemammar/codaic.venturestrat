"""POST /messages/{id}/send — Send an email via the sender's provider."""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from outreach_service.application.services.message_service import MessageService
from outreach_service.application.services.email_account_service import EmailAccountService
from outreach_service.config import settings
from outreach_service.core.database import get_session
from outreach_service.providers import gmail, microsoft, sendgrid
from outreach_service.schemas.message import MessageResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Messages'])


class SendResult(BaseModel):
  """Response after sending an email."""
  message_id: str = Field(description='Internal message ID')
  provider_message_id: str | None = Field(
    default=None, description='Provider-assigned message ID'
  )
  thread_id: str | None = Field(
    default=None, description='Provider thread/conversation ID'
  )
  status: str = Field(description='New message status (sent)')
  sent_at: str = Field(description='ISO timestamp when the email was sent')


@router.post(
  '/{id}/send',
  response_model=SendResult,
  summary='Send a draft message',
  description=(
    'Sends an email via the sender\'s email provider (Gmail, Microsoft, or SendGrid). '
    'The message must be in draft status and have an associated email_account_id.'
  ),
  responses={
    200: {'description': 'Email sent successfully'},
    400: {
      'description': 'Message not in sendable state',
      'content': {'application/json': {'example': {'detail': 'Message is not in draft status'}}},
    },
    404: {
      'description': 'Message or email account not found',
      'content': {'application/json': {'example': {'detail': 'Message not found'}}},
    },
  },
)
async def send_message(
  id: UUID,
  session=Depends(get_session),
) -> SendResult:
  """Send a draft message through the configured email provider."""
  msg_service = MessageService(session)
  acct_service = EmailAccountService(session)

  # Fetch message
  message = await msg_service.get_message(id)
  if not message:
    raise HTTPException(status_code=404, detail='Message not found')

  # Validate status
  if message.status != 'draft':
    raise HTTPException(
      status_code=400,
      detail=f'Message is not in draft status (current: {message.status})',
    )

  # Require email account
  if not message.email_account_id:
    raise HTTPException(
      status_code=400,
      detail='Message has no email_account_id — cannot determine provider',
    )

  # Fetch email account
  account = await acct_service.get_email_account(UUID(message.email_account_id))
  if not account:
    raise HTTPException(status_code=404, detail='Email account not found')

  if not account.is_active:
    raise HTTPException(status_code=400, detail='Email account is not active')

  # Parse addresses
  to_addrs = message.to_addresses if isinstance(message.to_addresses, list) else []
  cc_addrs = message.cc_addresses if isinstance(message.cc_addresses, list) else []

  # Determine in_reply_to / references for threading
  in_reply_to = message.provider_message_id if message.previous_message_id else None
  references = message.provider_references

  # Dispatch to provider
  provider = (account.provider or '').lower()
  provider_message_id = None
  provider_thread_id = message.thread_id

  try:
    if provider == 'gmail':
      # Refresh token if needed
      access_token = account.access_token
      if not access_token:
        raise HTTPException(
          status_code=400,
          detail='Email account has no access token — re-authenticate via OAuth',
        )

      result = await gmail.send_email(
        access_token=access_token,
        from_address=message.from_address,
        to_addresses=to_addrs,
        cc_addresses=cc_addrs,
        subject=message.subject,
        body_html=message.body,
        thread_id=message.thread_id,
        in_reply_to=in_reply_to,
        references=references,
      )
      provider_message_id = result.get('id')
      provider_thread_id = result.get('threadId', message.thread_id)

    elif provider == 'microsoft':
      access_token = account.access_token
      if not access_token:
        raise HTTPException(
          status_code=400,
          detail='Email account has no access token — re-authenticate via OAuth',
        )
      result = await microsoft.send_email(
        access_token=access_token,
        from_address=message.from_address,
        to_addresses=to_addrs,
        cc_addresses=cc_addrs,
        subject=message.subject,
        body_html=message.body,
        thread_id=message.thread_id,
        in_reply_to=in_reply_to,
        references=references,
      )
      provider_message_id = result.get('id')
      provider_thread_id = result.get('conversationId', message.thread_id)

    elif provider == 'sendgrid':
      result = await sendgrid.send_email(
        access_token=account.access_token or '',
        from_address=message.from_address,
        to_addresses=to_addrs,
        cc_addresses=cc_addrs,
        subject=message.subject,
        body_html=message.body,
        in_reply_to=in_reply_to,
        references=references,
        api_key=settings.sendgrid_api_key,
      )
      provider_message_id = result.get('message_id')

    else:
      raise HTTPException(
        status_code=400,
        detail=f'Unsupported email provider: {provider}',
      )

  except NotImplementedError as e:
    raise HTTPException(status_code=501, detail=str(e))
  except HTTPException:
    raise
  except Exception as e:
    logger.error('send_email_failed', message_id=str(id), provider=provider, error=str(e))
    raise HTTPException(
      status_code=502,
      detail=f'Failed to send email via {provider}: {str(e)}',
    )

  # Update message status
  sent_at = datetime.utcnow()
  from outreach_service.schemas.message import MessageUpdate

  update_data = MessageUpdate(
    status='sent',
    provider_message_id=provider_message_id,
    thread_id=provider_thread_id,
  )
  await msg_service.update_message(id, update_data)

  return SendResult(
    message_id=str(id),
    provider_message_id=provider_message_id,
    thread_id=provider_thread_id,
    status='sent',
    sent_at=sent_at.isoformat() + 'Z',
  )
