"""SendGrid API provider for sending emails.

TODO: Implement full SendGrid integration.
Currently stubbed with the correct API structure.
"""

from typing import Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

SENDGRID_API_BASE = 'https://api.sendgrid.com/v3'


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
  api_key: Optional[str] = None,
) -> dict:
  """Send an email via SendGrid API.

  TODO: Implement full SendGrid send.

  For SendGrid, the api_key is used instead of access_token.
  The access_token parameter is kept for interface consistency.

  Args:
      access_token: Ignored for SendGrid (kept for interface consistency).
      from_address: Sender email address.
      to_addresses: List of recipient email addresses.
      cc_addresses: List of CC email addresses.
      subject: Email subject.
      body_html: HTML email body.
      thread_id: Not used by SendGrid (kept for interface consistency).
      in_reply_to: Message-ID to reply to (set as custom header).
      references: References header for threading (set as custom header).
      api_key: SendGrid API key (required).

  Returns:
      Dict with message_id from SendGrid.

  Raises:
      httpx.HTTPStatusError: If the SendGrid API returns an error.
      NotImplementedError: Until fully implemented.
  """
  payload = {
    'personalizations': [
      {
        'to': [{'email': addr} for addr in to_addresses],
        'cc': [{'email': addr} for addr in cc_addresses] if cc_addresses else [],
      }
    ],
    'from': {'email': from_address},
    'subject': subject,
    'content': [
      {
        'type': 'text/html',
        'value': body_html,
      }
    ],
  }

  headers_list = []
  if in_reply_to:
    headers_list.append({'In-Reply-To': in_reply_to})
  if references:
    headers_list.append({'References': references})
  if headers_list:
    payload['headers'] = {k: v for d in headers_list for k, v in d.items()}

  # TODO: Make the actual API call when SendGrid is configured
  # effective_key = api_key or access_token
  # async with httpx.AsyncClient() as client:
  #   resp = await client.post(
  #     f'{SENDGRID_API_BASE}/mail/send',
  #     headers={
  #       'Authorization': f'Bearer {effective_key}',
  #       'Content-Type': 'application/json',
  #     },
  #     json=payload,
  #   )
  #   resp.raise_for_status()
  #   message_id = resp.headers.get('X-Message-Id', '')
  #   return {'message_id': message_id}

  logger.warning('sendgrid_send_not_implemented', to=to_addresses)
  raise NotImplementedError(
    'SendGrid email sending is not yet implemented. '
    'Configure SENDGRID_API_KEY and uncomment the API call above.'
  )
