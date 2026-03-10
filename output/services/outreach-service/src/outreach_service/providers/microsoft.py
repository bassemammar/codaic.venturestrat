"""Microsoft Graph API provider for sending emails and managing subscriptions.

TODO: Implement full Microsoft Graph integration.
Currently stubbed with the correct API structure.
"""

from typing import Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'


async def send_email(
  access_token: str,
  from_address: str,
  to_addresses: list[str],
  cc_addresses: list[str],
  subject: str,
  body_html: str,
  thread_id: Optional[str] = None,
  in_reply_to: Optional[str] = None,
  references: Optional[str] = None,
) -> dict:
  """Send an email via Microsoft Graph API.

  TODO: Implement full Microsoft Graph send.

  Args:
      access_token: Valid OAuth2 access token.
      from_address: Sender email address.
      to_addresses: List of recipient email addresses.
      cc_addresses: List of CC email addresses.
      subject: Email subject.
      body_html: HTML email body.
      thread_id: Conversation ID for threading (optional).
      in_reply_to: Message-ID to reply to (optional).
      references: References header for threading (optional).

  Returns:
      Dict with id and conversationId from Graph API.

  Raises:
      httpx.HTTPStatusError: If the Graph API returns an error.
  """
  # Build the Graph API message payload
  message_payload = {
    'message': {
      'subject': subject,
      'body': {
        'contentType': 'HTML',
        'content': body_html,
      },
      'toRecipients': [
        {'emailAddress': {'address': addr}} for addr in to_addresses
      ],
      'ccRecipients': [
        {'emailAddress': {'address': addr}} for addr in cc_addresses
      ],
    },
    'saveToSentItems': True,
  }

  if in_reply_to:
    message_payload['message']['internetMessageHeaders'] = [
      {'name': 'In-Reply-To', 'value': in_reply_to},
    ]
    if references:
      message_payload['message']['internetMessageHeaders'].append(
        {'name': 'References', 'value': references}
      )

  # TODO: Make the actual API call when Microsoft OAuth is configured
  # async with httpx.AsyncClient() as client:
  #   resp = await client.post(
  #     f'{GRAPH_API_BASE}/me/sendMail',
  #     headers={'Authorization': f'Bearer {access_token}'},
  #     json=message_payload,
  #   )
  #   resp.raise_for_status()

  logger.warning('microsoft_send_not_implemented', to=to_addresses)
  raise NotImplementedError(
    'Microsoft Graph email sending is not yet implemented. '
    'Configure Microsoft OAuth and uncomment the API call above.'
  )


async def create_subscription(
  access_token: str,
  notification_url: str,
  resource: str = 'me/mailFolders/inbox/messages',
  change_type: str = 'created',
  expiration_minutes: int = 4230,
) -> dict:
  """Create a Microsoft Graph subscription for inbox notifications.

  TODO: Implement full subscription creation.

  Args:
      access_token: Valid OAuth2 access token.
      notification_url: Webhook URL to receive notifications.
      resource: Graph resource to watch.
      change_type: Type of change to watch (created, updated, deleted).
      expiration_minutes: Subscription lifetime in minutes (max 4230 for mail).

  Returns:
      Dict with subscription id and expirationDateTime.

  Raises:
      httpx.HTTPStatusError: If the Graph API returns an error.
  """
  from datetime import datetime, timedelta, timezone

  expiration = (
    datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
  ).isoformat()

  payload = {
    'changeType': change_type,
    'notificationUrl': notification_url,
    'resource': resource,
    'expirationDateTime': expiration,
    'clientState': 'venturestrat-outreach',
  }

  # TODO: Make the actual API call when Microsoft OAuth is configured
  # async with httpx.AsyncClient() as client:
  #   resp = await client.post(
  #     f'{GRAPH_API_BASE}/subscriptions',
  #     headers={'Authorization': f'Bearer {access_token}'},
  #     json=payload,
  #   )
  #   resp.raise_for_status()
  #   return resp.json()

  logger.warning('microsoft_subscription_not_implemented')
  raise NotImplementedError(
    'Microsoft Graph subscription creation is not yet implemented. '
    'Configure Microsoft OAuth and uncomment the API call above.'
  )


async def get_message(
  access_token: str,
  message_id: str,
) -> dict:
  """Fetch a single message from Microsoft Graph by its ID.

  TODO: Implement full message fetch.

  Args:
      access_token: Valid OAuth2 access token.
      message_id: Microsoft message ID.

  Returns:
      Graph message resource dict.

  Raises:
      httpx.HTTPStatusError: If the Graph API returns an error.
  """
  # TODO: Make the actual API call
  # async with httpx.AsyncClient() as client:
  #   resp = await client.get(
  #     f'{GRAPH_API_BASE}/me/messages/{message_id}',
  #     headers={'Authorization': f'Bearer {access_token}'},
  #   )
  #   resp.raise_for_status()
  #   return resp.json()

  logger.warning('microsoft_get_message_not_implemented', message_id=message_id)
  raise NotImplementedError(
    'Microsoft Graph message fetch is not yet implemented.'
  )
