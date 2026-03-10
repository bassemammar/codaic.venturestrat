"""Tests for custom outreach-service endpoints (Wave 8).

Tests cover:
- POST /messages/{id}/send (mock provider)
- POST /messages/{id}/schedule + cancel-schedule
- POST /ai/generate-email (mock OpenAI)
- POST /webhooks/gmail (mock notification payload)
"""

import base64
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_message_response(**overrides):
  """Build a mock MessageResponse-like object with defaults."""
  defaults = {
    'id': str(uuid4()),
    'user_id': 'user-1',
    'investor_id': None,
    'email_account_id': str(uuid4()),
    'status': 'draft',
    'to_addresses': ['investor@example.com'],
    'cc_addresses': [],
    'subject': 'Hello Investor',
    'from_address': 'me@venturestrat.com',
    'body': '<p>Hi there</p>',
    'attachments': [],
    'thread_id': None,
    'provider_message_id': None,
    'provider_references': None,
    'previous_message_id': None,
    'scheduled_for': None,
    'job_id': None,
    'created_at': datetime.utcnow(),
    'updated_at': datetime.utcnow(),
  }
  defaults.update(overrides)
  return MagicMock(**defaults)


def _make_account_response(**overrides):
  """Build a mock EmailAccountResponse-like object with defaults."""
  defaults = {
    'id': str(uuid4()),
    'user_id': 'user-1',
    'provider': 'gmail',
    'email_address': 'me@venturestrat.com',
    'access_token': 'ya29.fake-token',
    'refresh_token': 'fake-refresh',
    'token_expires_at': None,
    'watch_history_id': None,
    'is_active': True,
    'created_at': datetime.utcnow(),
    'updated_at': datetime.utcnow(),
  }
  defaults.update(overrides)
  return MagicMock(**defaults)


# We import app here so that patches apply before routes are resolved
@pytest.fixture
def client():
  """Create a TestClient for the FastAPI app."""
  from outreach_service.main import app
  return TestClient(app)


# ---------------------------------------------------------------------------
# 8.1 — POST /messages/{id}/send
# ---------------------------------------------------------------------------

class TestSendMessage:
  """Tests for the send message endpoint."""

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  @patch('outreach_service.endpoints.message_send.gmail.send_email', new_callable=AsyncMock)
  def test_send_gmail_success(self, mock_gmail_send, MockMsgService, MockAcctService, client):
    """Sending a draft via Gmail should update status to sent."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())

    message = _make_message_response(id=msg_id, email_account_id=acct_id, status='draft')
    account = _make_account_response(id=acct_id, provider='gmail')

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=message)
    mock_msg_svc.update_message = AsyncMock(return_value=message)

    mock_acct_svc = MockAcctService.return_value
    mock_acct_svc.get_email_account = AsyncMock(return_value=account)

    mock_gmail_send.return_value = {
      'id': 'gmail-msg-123',
      'threadId': 'thread-abc',
      'labelIds': ['SENT'],
    }

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 200

    data = resp.json()
    assert data['status'] == 'sent'
    assert data['provider_message_id'] == 'gmail-msg-123'
    assert data['thread_id'] == 'thread-abc'
    mock_gmail_send.assert_called_once()

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  def test_send_not_draft_returns_400(self, MockMsgService, MockAcctService, client):
    """Sending a message that is not in draft status should return 400."""
    msg_id = str(uuid4())
    message = _make_message_response(id=msg_id, status='sent')

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=message)

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 400
    assert 'not in draft status' in resp.json()['detail']

  @patch('outreach_service.endpoints.message_send.MessageService')
  def test_send_not_found_returns_404(self, MockMsgService, client):
    """Sending a nonexistent message should return 404."""
    msg_id = str(uuid4())

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=None)

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 404

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  def test_send_no_account_id_returns_400(self, MockMsgService, MockAcctService, client):
    """Sending a message with no email_account_id should return 400."""
    msg_id = str(uuid4())
    message = _make_message_response(id=msg_id, status='draft', email_account_id=None)

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=message)

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 400
    assert 'email_account_id' in resp.json()['detail']

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  def test_send_unsupported_provider_returns_400(self, MockMsgService, MockAcctService, client):
    """Sending via an unsupported provider should return 400."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())

    message = _make_message_response(id=msg_id, email_account_id=acct_id, status='draft')
    account = _make_account_response(id=acct_id, provider='yahoo')

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=message)
    mock_msg_svc.update_message = AsyncMock()

    mock_acct_svc = MockAcctService.return_value
    mock_acct_svc.get_email_account = AsyncMock(return_value=account)

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 400
    assert 'Unsupported' in resp.json()['detail']


# ---------------------------------------------------------------------------
# 8.2 — POST /messages/{id}/schedule + cancel-schedule
# ---------------------------------------------------------------------------

class TestScheduleMessage:
  """Tests for schedule and cancel-schedule endpoints."""

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_schedule_success(self, MockMsgService, client):
    """Scheduling a draft message should set status to scheduled."""
    msg_id = str(uuid4())
    message = _make_message_response(id=msg_id, status='draft')

    mock_svc = MockMsgService.return_value
    mock_svc.get_message = AsyncMock(return_value=message)
    mock_svc.update_message = AsyncMock(return_value=message)

    future = (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    resp = client.post(
      f'/api/v1/messages/{msg_id}/schedule',
      json={'scheduled_for': future},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'scheduled'
    assert data['scheduled_for'] is not None

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_schedule_not_draft_returns_400(self, MockMsgService, client):
    """Scheduling a non-draft message should return 400."""
    msg_id = str(uuid4())
    message = _make_message_response(id=msg_id, status='sent')

    mock_svc = MockMsgService.return_value
    mock_svc.get_message = AsyncMock(return_value=message)

    future = (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    resp = client.post(
      f'/api/v1/messages/{msg_id}/schedule',
      json={'scheduled_for': future},
    )
    assert resp.status_code == 400

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_schedule_past_date_returns_400(self, MockMsgService, client):
    """Scheduling for a past date should return 400."""
    msg_id = str(uuid4())
    message = _make_message_response(id=msg_id, status='draft')

    mock_svc = MockMsgService.return_value
    mock_svc.get_message = AsyncMock(return_value=message)

    past = (datetime.utcnow() - timedelta(hours=2)).isoformat() + 'Z'
    resp = client.post(
      f'/api/v1/messages/{msg_id}/schedule',
      json={'scheduled_for': past},
    )
    assert resp.status_code == 400
    assert 'future' in resp.json()['detail']

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_cancel_schedule_success(self, MockMsgService, client):
    """Cancelling a scheduled message should revert to draft."""
    msg_id = str(uuid4())
    message = _make_message_response(id=msg_id, status='scheduled')

    mock_svc = MockMsgService.return_value
    mock_svc.get_message = AsyncMock(return_value=message)
    mock_svc.update_message = AsyncMock(return_value=message)

    resp = client.post(f'/api/v1/messages/{msg_id}/cancel-schedule')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'draft'
    assert data['scheduled_for'] is None

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_cancel_schedule_not_scheduled_returns_400(self, MockMsgService, client):
    """Cancelling a non-scheduled message should return 400."""
    msg_id = str(uuid4())
    message = _make_message_response(id=msg_id, status='draft')

    mock_svc = MockMsgService.return_value
    mock_svc.get_message = AsyncMock(return_value=message)

    resp = client.post(f'/api/v1/messages/{msg_id}/cancel-schedule')
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 8.3 + 8.4 — POST /ai/generate-email + /ai/edit-text
# ---------------------------------------------------------------------------

class TestAiEndpoints:
  """Tests for AI email generation and text editing."""

  @patch('outreach_service.endpoints.ai_endpoints._call_openai', new_callable=AsyncMock)
  def test_generate_email_success(self, mock_openai, client):
    """Generate email should parse subject and body from AI response."""
    mock_openai.return_value = (
      'SUBJECT: Investment Opportunity Discussion\n'
      'BODY:\n<p>Dear John,</p>\n<p>I wanted to reach out about...</p>'
    )

    resp = client.post('/api/v1/ai/generate-email', json={
      'investor_name': 'John Smith',
      'investor_company': 'Acme Ventures',
      'context': 'professional',
      'instructions': 'Mention our Series A',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'Investment Opportunity' in data['subject']
    assert '<p>' in data['body']

  @patch('outreach_service.endpoints.ai_endpoints._call_openai', new_callable=AsyncMock)
  def test_generate_email_fallback_parsing(self, mock_openai, client):
    """When AI response lacks SUBJECT:/BODY: markers, use fallback parsing."""
    mock_openai.return_value = (
      'Re: Partnership Discussion\n'
      '<p>Hi Jane, I would love to connect about...</p>'
    )

    resp = client.post('/api/v1/ai/generate-email', json={
      'investor_name': 'Jane Doe',
      'investor_company': 'VC Corp',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['subject'] != ''
    assert data['body'] != ''

  @patch('outreach_service.endpoints.ai_endpoints._call_openai', new_callable=AsyncMock)
  def test_edit_text_success(self, mock_openai, client):
    """Edit text should return the AI-edited version."""
    mock_openai.return_value = '<p>Hi John, excited to discuss our fund.</p>'

    resp = client.post('/api/v1/ai/edit-text', json={
      'original_text': '<p>Hey John, I want to talk about our fund thing.</p>',
      'edit_instruction': 'Make it more professional',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'excited' in data['edited_text']

  def test_generate_email_no_api_key(self, client):
    """Generate email without API key configured should return 500."""
    with patch('outreach_service.endpoints.ai_endpoints.settings') as mock_settings:
      mock_settings.openai_api_key = ''
      resp = client.post('/api/v1/ai/generate-email', json={
        'investor_name': 'Test',
        'investor_company': 'Test Co',
      })
      assert resp.status_code == 500
      assert 'OPENAI_API_KEY' in resp.json()['detail']


# ---------------------------------------------------------------------------
# 8.6 — POST /webhooks/gmail
# ---------------------------------------------------------------------------

class TestGmailWebhook:
  """Tests for the Gmail webhook endpoint."""

  @patch('outreach_service.endpoints.webhooks.MessageService')
  @patch('outreach_service.endpoints.webhooks.EmailAccountService')
  @patch('outreach_service.endpoints.webhooks.gmail_provider.list_history', new_callable=AsyncMock)
  @patch('outreach_service.endpoints.webhooks.gmail_provider.get_message', new_callable=AsyncMock)
  def test_gmail_webhook_creates_inbound_message(
    self, mock_get_msg, mock_list_history, MockAcctService, MockMsgService, client
  ):
    """A Gmail push notification should create an inbound message."""
    email = 'me@venturestrat.com'
    acct = _make_account_response(
      email_address=email,
      provider='gmail',
      watch_history_id='100',
    )

    mock_acct_svc = MockAcctService.return_value
    mock_acct_svc.search_email_accounts = AsyncMock(return_value=[acct])
    mock_acct_svc.update_email_account = AsyncMock()

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.search_messages = AsyncMock(return_value=[])
    mock_msg_svc.create_message = AsyncMock()

    # Mock Gmail history with one new message
    mock_list_history.return_value = {
      'history': [
        {
          'messagesAdded': [
            {'message': {'id': 'gmail-new-1'}}
          ]
        }
      ]
    }

    # Mock the full Gmail message
    mock_get_msg.return_value = {
      'id': 'gmail-new-1',
      'threadId': 'thread-xyz',
      'payload': {
        'headers': [
          {'name': 'From', 'value': 'investor@example.com'},
          {'name': 'To', 'value': email},
          {'name': 'Subject', 'value': 'Re: Our Meeting'},
          {'name': 'Message-ID', 'value': '<abc@mail.gmail.com>'},
        ],
        'mimeType': 'text/html',
        'body': {
          'data': base64.urlsafe_b64encode(b'<p>Thanks for the info</p>').decode(),
        },
      },
    }

    # Build the Pub/Sub notification
    pubsub_data = base64.urlsafe_b64encode(
      json.dumps({'emailAddress': email, 'historyId': '200'}).encode()
    ).decode()

    resp = client.post('/api/v1/webhooks/gmail', json={
      'message': {'data': pubsub_data},
      'subscription': 'projects/my-project/subscriptions/gmail-push',
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'ok'
    assert data['messages_processed'] == 1
    mock_msg_svc.create_message.assert_called_once()

  def test_gmail_webhook_empty_data(self, client):
    """A webhook with empty data should return ok with 0 processed."""
    resp = client.post('/api/v1/webhooks/gmail', json={
      'message': {'data': ''},
      'subscription': 'projects/my-project/subscriptions/gmail-push',
    })
    assert resp.status_code == 200
    assert resp.json()['messages_processed'] == 0

  @patch('outreach_service.endpoints.webhooks.EmailAccountService')
  def test_gmail_webhook_unknown_account(self, MockAcctService, client):
    """A webhook for an unknown email should return ok with 0 processed."""
    mock_acct_svc = MockAcctService.return_value
    mock_acct_svc.search_email_accounts = AsyncMock(return_value=[])

    pubsub_data = base64.urlsafe_b64encode(
      json.dumps({'emailAddress': 'unknown@example.com', 'historyId': '100'}).encode()
    ).decode()

    resp = client.post('/api/v1/webhooks/gmail', json={
      'message': {'data': pubsub_data},
      'subscription': 'projects/my-project/subscriptions/gmail-push',
    })
    assert resp.status_code == 200
    assert resp.json()['messages_processed'] == 0


# ---------------------------------------------------------------------------
# 8.7 — POST /webhooks/microsoft
# ---------------------------------------------------------------------------

class TestMicrosoftWebhook:
  """Tests for the Microsoft webhook endpoint."""

  def test_microsoft_webhook_validation(self, client):
    """Microsoft validation request should echo validationToken."""
    token = 'validation-token-12345'
    resp = client.post(
      f'/api/v1/webhooks/microsoft?validationToken={token}',
    )
    assert resp.status_code == 200
    assert resp.text == token

  def test_microsoft_webhook_notification(self, client):
    """Microsoft change notification should return ok."""
    resp = client.post('/api/v1/webhooks/microsoft', json={
      'value': [
        {
          'resource': 'me/messages/abc123',
          'changeType': 'created',
          'clientState': 'venturestrat-outreach',
        }
      ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'ok'
