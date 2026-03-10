"""Webhook endpoints for Gmail and Microsoft push notifications."""

import base64
import json
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from outreach_service.application.services.email_account_service import EmailAccountService
from outreach_service.application.services.message_service import MessageService
from outreach_service.providers import gmail as gmail_provider
from outreach_service.schemas.message import MessageCreate

logger = structlog.get_logger(__name__)

router = APIRouter(prefix='/webhooks', tags=['Webhooks'])


class GmailNotification(BaseModel):
  """Google Pub/Sub push notification payload."""
  message: dict = Field(description='Pub/Sub message with data and attributes')
  subscription: str = Field(description='Pub/Sub subscription name')


class WebhookResult(BaseModel):
  """Response to acknowledge webhook receipt."""
  status: str = Field(default='ok', description='Acknowledgement status')
  messages_processed: int = Field(
    default=0, description='Number of new messages created'
  )


def _decode_pubsub_data(data_b64: str) -> dict:
  """Decode base64 Pub/Sub message data.

  Gmail push notifications send base64-encoded JSON with:
  - emailAddress: the Gmail address
  - historyId: the latest history ID

  Args:
      data_b64: Base64-encoded data string.

  Returns:
      Decoded JSON dict.
  """
  decoded = base64.urlsafe_b64decode(data_b64.encode('ascii'))
  return json.loads(decoded)


def _extract_header(headers: list[dict], name: str) -> str | None:
  """Extract a header value from Gmail message headers.

  Args:
      headers: List of {'name': ..., 'value': ...} dicts.
      name: Header name (case-insensitive).

  Returns:
      Header value or None.
  """
  name_lower = name.lower()
  for h in headers:
    if h.get('name', '').lower() == name_lower:
      return h.get('value')
  return None


def _extract_body_html(payload: dict) -> str:
  """Extract HTML body from a Gmail message payload.

  Handles both simple and multipart MIME structures.

  Args:
      payload: Gmail message payload dict.

  Returns:
      HTML body string (or plain text fallback).
  """
  # Simple message
  if payload.get('mimeType') == 'text/html' and payload.get('body', {}).get('data'):
    return base64.urlsafe_b64decode(payload['body']['data'].encode('ascii')).decode('utf-8')

  # Multipart — look for text/html part
  for part in payload.get('parts', []):
    if part.get('mimeType') == 'text/html' and part.get('body', {}).get('data'):
      return base64.urlsafe_b64decode(part['body']['data'].encode('ascii')).decode('utf-8')

  # Fallback to text/plain
  if payload.get('mimeType') == 'text/plain' and payload.get('body', {}).get('data'):
    return base64.urlsafe_b64decode(payload['body']['data'].encode('ascii')).decode('utf-8')

  for part in payload.get('parts', []):
    if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
      return base64.urlsafe_b64decode(part['body']['data'].encode('ascii')).decode('utf-8')

  return ''


@router.post(
  '/gmail',
  response_model=WebhookResult,
  summary='Receive Gmail push notifications',
  description=(
    'Receives Gmail push notifications from Google Pub/Sub. '
    'Decodes the notification, fetches new messages via Gmail API, '
    'and creates inbound Message records for detected replies.'
  ),
  responses={
    200: {'description': 'Notification processed'},
    400: {'description': 'Invalid notification payload'},
  },
)
async def gmail_webhook(notification: GmailNotification) -> WebhookResult:
  """Process a Gmail push notification callback."""
  try:
    # Decode the Pub/Sub data
    data_b64 = notification.message.get('data', '')
    if not data_b64:
      logger.warning('gmail_webhook_empty_data')
      return WebhookResult(status='ok', messages_processed=0)

    payload = _decode_pubsub_data(data_b64)
    email_address = payload.get('emailAddress', '')
    history_id = str(payload.get('historyId', ''))

    logger.info(
      'gmail_webhook_received',
      email=email_address,
      history_id=history_id,
    )

    if not email_address:
      return WebhookResult(status='ok', messages_processed=0)

    # Look up the email account
    acct_service = EmailAccountService()
    accounts = await acct_service.search_email_accounts(
      domain=[('email_address', '=', email_address), ('provider', '=', 'gmail')],
    )

    if not accounts:
      logger.warning('gmail_webhook_unknown_account', email=email_address)
      return WebhookResult(status='ok', messages_processed=0)

    account = accounts[0]
    if not account.access_token:
      logger.warning('gmail_webhook_no_token', email=email_address)
      return WebhookResult(status='ok', messages_processed=0)

    # Fetch history since last known history ID
    start_history = account.watch_history_id or history_id
    try:
      history_data = await gmail_provider.list_history(
        access_token=account.access_token,
        start_history_id=start_history,
      )
    except Exception as e:
      logger.error('gmail_history_fetch_failed', error=str(e))
      return WebhookResult(status='ok', messages_processed=0)

    # Process new messages from history
    messages_processed = 0
    msg_service = MessageService()

    for record in history_data.get('history', []):
      for added in record.get('messagesAdded', []):
        gmail_msg_id = added.get('message', {}).get('id')
        if not gmail_msg_id:
          continue

        try:
          gmail_msg = await gmail_provider.get_message(
            access_token=account.access_token,
            message_id=gmail_msg_id,
          )

          headers = gmail_msg.get('payload', {}).get('headers', [])
          thread_id = gmail_msg.get('threadId')
          from_addr = _extract_header(headers, 'From') or ''
          to_addr = _extract_header(headers, 'To') or ''
          subject = _extract_header(headers, 'Subject') or ''
          message_id_header = _extract_header(headers, 'Message-ID')
          in_reply_to = _extract_header(headers, 'In-Reply-To')
          references_header = _extract_header(headers, 'References')
          body_html = _extract_body_html(gmail_msg.get('payload', {}))

          # Detect if this is a reply to an existing thread
          # by matching thread_id against our stored messages
          previous_message_id = None
          if thread_id:
            existing = await msg_service.search_messages(
              domain=[('thread_id', '=', thread_id)],
              skip=0,
              limit=1,
            )
            if existing:
              previous_message_id = existing[0].id

          # Create inbound message record
          create_data = MessageCreate(
            user_id=account.user_id,
            email_account_id=account.id,
            status='received',
            to_addresses=[to_addr] if to_addr else [],
            cc_addresses=[],
            subject=subject,
            from_address=from_addr,
            body=body_html,
            thread_id=thread_id,
            provider_message_id=message_id_header,
            provider_references=references_header,
            previous_message_id=previous_message_id,
          )

          await msg_service.create_message(create_data)
          messages_processed += 1

          logger.info(
            'gmail_inbound_message_created',
            gmail_msg_id=gmail_msg_id,
            thread_id=thread_id,
            is_reply=previous_message_id is not None,
          )

        except Exception as e:
          logger.error(
            'gmail_message_processing_failed',
            gmail_msg_id=gmail_msg_id,
            error=str(e),
          )

    # Update watch_history_id on the account
    from outreach_service.schemas.email_account import EmailAccountUpdate
    from uuid import UUID

    update_data = EmailAccountUpdate(watch_history_id=history_id)
    await acct_service.update_email_account(UUID(account.id), update_data)

    return WebhookResult(status='ok', messages_processed=messages_processed)

  except Exception as e:
    logger.error('gmail_webhook_error', error=str(e))
    # Always return 200 to Pub/Sub to prevent retries on processing errors
    return WebhookResult(status='error', messages_processed=0)


@router.post(
  '/microsoft',
  summary='Receive Microsoft Graph webhook notifications',
  description=(
    'Receives Microsoft Graph webhook notifications for new emails. '
    'Handles both validation requests (with validationToken) and '
    'change notifications.'
  ),
  responses={
    200: {'description': 'Notification processed or validation token returned'},
  },
)
async def microsoft_webhook(request: Request) -> Any:
  """Process a Microsoft Graph webhook notification.

  Microsoft Graph webhooks have two modes:
  1. Validation: GET/POST with validationToken query param — must echo it back.
  2. Notification: POST with JSON body containing change notifications.

  TODO: Implement full notification processing when Microsoft OAuth is configured.
  """
  # Handle validation request
  validation_token = request.query_params.get('validationToken')
  if validation_token:
    logger.info('microsoft_webhook_validation', token=validation_token[:20] + '...')
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=validation_token, status_code=200)

  # Process change notification
  try:
    body = await request.json()
    notifications = body.get('value', [])

    logger.info(
      'microsoft_webhook_received',
      notification_count=len(notifications),
    )

    for notification in notifications:
      resource = notification.get('resource', '')
      change_type = notification.get('changeType', '')
      client_state = notification.get('clientState', '')

      # Verify client state matches what we set during subscription
      if client_state != 'venturestrat-outreach':
        logger.warning(
          'microsoft_webhook_invalid_state',
          client_state=client_state,
        )
        continue

      logger.info(
        'microsoft_webhook_notification',
        resource=resource,
        change_type=change_type,
      )

      # TODO: Fetch the actual message from Microsoft Graph API
      # and create an inbound Message record (similar to Gmail webhook)
      # This requires:
      # 1. Looking up the email account from the notification
      # 2. Calling microsoft.get_message() to fetch the full message
      # 3. Creating a Message record with status='received'

    return WebhookResult(status='ok', messages_processed=0)

  except Exception as e:
    logger.error('microsoft_webhook_error', error=str(e))
    return WebhookResult(status='error', messages_processed=0)
