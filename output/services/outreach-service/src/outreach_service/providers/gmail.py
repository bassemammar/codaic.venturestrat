"""Gmail API provider for sending emails and managing push notifications."""

import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'


async def refresh_access_token(
  refresh_token: str,
  client_id: str,
  client_secret: str,
) -> dict:
  """Refresh an OAuth2 access token using the refresh token.

  Args:
      refresh_token: OAuth2 refresh token.
      client_id: Google OAuth client ID.
      client_secret: Google OAuth client secret.

  Returns:
      Dict with access_token, expires_in, and optionally a new refresh_token.
  """
  async with httpx.AsyncClient() as client:
    resp = await client.post(
      GOOGLE_TOKEN_URL,
      data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
      },
    )
    resp.raise_for_status()
    return resp.json()


def _build_mime_message(
  from_address: str,
  to_addresses: list[str],
  cc_addresses: list[str],
  subject: str,
  body_html: str,
  in_reply_to: Optional[str] = None,
  references: Optional[str] = None,
) -> str:
  """Build a MIME message and return base64url-encoded raw bytes.

  Args:
      from_address: Sender email.
      to_addresses: List of recipient emails.
      cc_addresses: List of CC emails.
      subject: Email subject line.
      body_html: HTML body content.
      in_reply_to: Message-ID of the message being replied to.
      references: References header for threading.

  Returns:
      Base64url-encoded string of the MIME message.
  """
  msg = MIMEMultipart('alternative')
  msg['From'] = from_address
  msg['To'] = ', '.join(to_addresses)
  if cc_addresses:
    msg['Cc'] = ', '.join(cc_addresses)
  msg['Subject'] = subject

  if in_reply_to:
    msg['In-Reply-To'] = in_reply_to
  if references:
    msg['References'] = references

  msg.attach(MIMEText(body_html, 'html'))

  raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('ascii')
  return raw


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
  """Send an email via the Gmail API.

  Args:
      access_token: Valid OAuth2 access token.
      from_address: Sender email address.
      to_addresses: List of recipient email addresses.
      cc_addresses: List of CC email addresses.
      subject: Email subject.
      body_html: HTML email body.
      thread_id: Gmail thread ID for threading (optional).
      in_reply_to: Message-ID to reply to (optional).
      references: References header for threading (optional).

  Returns:
      Dict with id (message ID), threadId, and labelIds from Gmail API.

  Raises:
      httpx.HTTPStatusError: If the Gmail API returns an error.
  """
  raw = _build_mime_message(
    from_address=from_address,
    to_addresses=to_addresses,
    cc_addresses=cc_addresses,
    subject=subject,
    body_html=body_html,
    in_reply_to=in_reply_to,
    references=references,
  )

  payload: dict[str, Any] = {'raw': raw}
  if thread_id:
    payload['threadId'] = thread_id

  async with httpx.AsyncClient() as client:
    resp = await client.post(
      f'{GMAIL_API_BASE}/users/me/messages/send',
      headers={'Authorization': f'Bearer {access_token}'},
      json=payload,
    )
    resp.raise_for_status()
    result = resp.json()

  logger.info(
    'gmail_email_sent',
    message_id=result.get('id'),
    thread_id=result.get('threadId'),
  )
  return result


async def watch_inbox(
  access_token: str,
  topic_name: str,
  label_ids: Optional[list[str]] = None,
) -> dict:
  """Register a Gmail push notification watch on the user's inbox.

  Args:
      access_token: Valid OAuth2 access token.
      topic_name: Google Cloud Pub/Sub topic (e.g. projects/my-project/topics/gmail).
      label_ids: Labels to watch. Defaults to ['INBOX'].

  Returns:
      Dict with historyId and expiration from Gmail API.

  Raises:
      httpx.HTTPStatusError: If the Gmail API returns an error.
  """
  payload = {
    'topicName': topic_name,
    'labelIds': label_ids or ['INBOX'],
  }

  async with httpx.AsyncClient() as client:
    resp = await client.post(
      f'{GMAIL_API_BASE}/users/me/watch',
      headers={'Authorization': f'Bearer {access_token}'},
      json=payload,
    )
    resp.raise_for_status()
    result = resp.json()

  logger.info(
    'gmail_watch_registered',
    history_id=result.get('historyId'),
    expiration=result.get('expiration'),
  )
  return result


async def get_message(
  access_token: str,
  message_id: str,
  format: str = 'full',
) -> dict:
  """Fetch a single message from Gmail by its ID.

  Args:
      access_token: Valid OAuth2 access token.
      message_id: Gmail message ID.
      format: Response format (full, minimal, metadata, raw).

  Returns:
      Gmail message resource dict.

  Raises:
      httpx.HTTPStatusError: If the Gmail API returns an error.
  """
  async with httpx.AsyncClient() as client:
    resp = await client.get(
      f'{GMAIL_API_BASE}/users/me/messages/{message_id}',
      headers={'Authorization': f'Bearer {access_token}'},
      params={'format': format},
    )
    resp.raise_for_status()
    return resp.json()


async def list_history(
  access_token: str,
  start_history_id: str,
  label_id: str = 'INBOX',
) -> dict:
  """List history records since a given historyId.

  Used to process push notification callbacks — Gmail sends a historyId
  and we fetch what changed since then.

  Args:
      access_token: Valid OAuth2 access token.
      start_history_id: The historyId to start from.
      label_id: Filter by label.

  Returns:
      Dict with history records and nextPageToken.

  Raises:
      httpx.HTTPStatusError: If the Gmail API returns an error.
  """
  async with httpx.AsyncClient() as client:
    resp = await client.get(
      f'{GMAIL_API_BASE}/users/me/history',
      headers={'Authorization': f'Bearer {access_token}'},
      params={
        'startHistoryId': start_history_id,
        'labelId': label_id,
        'historyTypes': 'messageAdded',
      },
    )
    resp.raise_for_status()
    return resp.json()
