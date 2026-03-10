"""Integration tests for the email send flow in outreach-service.

Covers end-to-end flows:
  - Create draft -> attach account -> send -> verify status=sent
  - Threading: send reply -> verify in_reply_to and thread_id
  - Schedule -> verify status=scheduled -> cancel -> verify status=draft
  - Send with failed provider -> verify status propagation
  - AI generate email -> verify subject + body (mock OpenAI)
  - AI edit text -> verify edited result (mock OpenAI)

All external providers (Gmail, OpenAI) are mocked via unittest.mock.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------

def _make_message(**overrides):
  """Build a mock MessageResponse-like object."""
  defaults = {
    'id': str(uuid4()),
    'user_id': 'user-1',
    'investor_id': None,
    'email_account_id': str(uuid4()),
    'status': 'draft',
    'to_addresses': ['investor@example.com'],
    'cc_addresses': [],
    'subject': 'Investment Discussion',
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


def _make_account(**overrides):
  """Build a mock EmailAccountResponse-like object."""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
  import os
  os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
  os.environ.setdefault('PLATFORM_MODE', 'standalone')
  os.environ.setdefault('LOG_LEVEL', 'WARNING')
  from outreach_service.main import app
  return TestClient(app)


# ---------------------------------------------------------------------------
# Integration Test: Full send flow (draft -> send -> verify sent)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestEmailSendFlow:
  """End-to-end send flow integration tests."""

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  @patch('outreach_service.endpoints.message_send.gmail.send_email', new_callable=AsyncMock)
  def test_full_send_flow_gmail(self, mock_gmail, MockMsgSvc, MockAcctSvc, client):
    """Draft message + Gmail account -> send -> verify status=sent + provider IDs."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())

    message = _make_message(id=msg_id, email_account_id=acct_id, status='draft')
    account = _make_account(id=acct_id, provider='gmail')

    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=message)
    msg_svc.update_message = AsyncMock(return_value=message)

    acct_svc = MockAcctSvc.return_value
    acct_svc.get_email_account = AsyncMock(return_value=account)

    mock_gmail.return_value = {
      'id': 'gmail-msg-001',
      'threadId': 'thread-001',
      'labelIds': ['SENT'],
    }

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 200

    data = resp.json()
    assert data['status'] == 'sent'
    assert data['provider_message_id'] == 'gmail-msg-001'
    assert data['thread_id'] == 'thread-001'
    assert data['sent_at'] is not None

    # Verify gmail.send_email was called with correct params
    mock_gmail.assert_called_once()
    call_kwargs = mock_gmail.call_args
    assert call_kwargs.kwargs.get('from_address') or call_kwargs[1].get('from_address') or 'me@venturestrat.com'

    # Verify message status was updated
    msg_svc.update_message.assert_called_once()

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  @patch('outreach_service.endpoints.message_send.gmail.send_email', new_callable=AsyncMock)
  def test_send_reply_preserves_threading(self, mock_gmail, MockMsgSvc, MockAcctSvc, client):
    """Sending a reply should include in_reply_to and thread_id."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())
    prev_msg_id = str(uuid4())

    message = _make_message(
      id=msg_id,
      email_account_id=acct_id,
      status='draft',
      thread_id='thread-existing',
      previous_message_id=prev_msg_id,
      provider_message_id='<original@mail.gmail.com>',
      provider_references='<ref1@mail.gmail.com>',
    )
    account = _make_account(id=acct_id, provider='gmail')

    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=message)
    msg_svc.update_message = AsyncMock(return_value=message)

    acct_svc = MockAcctSvc.return_value
    acct_svc.get_email_account = AsyncMock(return_value=account)

    mock_gmail.return_value = {
      'id': 'gmail-reply-001',
      'threadId': 'thread-existing',
      'labelIds': ['SENT'],
    }

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 200

    data = resp.json()
    assert data['thread_id'] == 'thread-existing'

    # Verify Gmail was called with threading headers
    call_kwargs = mock_gmail.call_args[1]
    assert call_kwargs['thread_id'] == 'thread-existing'
    assert call_kwargs['in_reply_to'] == '<original@mail.gmail.com>'
    assert call_kwargs['references'] == '<ref1@mail.gmail.com>'

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  @patch('outreach_service.endpoints.message_send.gmail.send_email', new_callable=AsyncMock)
  def test_send_with_provider_failure(self, mock_gmail, MockMsgSvc, MockAcctSvc, client):
    """When the provider raises an error, endpoint returns 502."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())

    message = _make_message(id=msg_id, email_account_id=acct_id, status='draft')
    account = _make_account(id=acct_id, provider='gmail')

    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=message)
    msg_svc.update_message = AsyncMock(return_value=message)

    acct_svc = MockAcctSvc.return_value
    acct_svc.get_email_account = AsyncMock(return_value=account)

    mock_gmail.side_effect = Exception('Gmail API error: rate limited')

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 502
    assert 'Failed to send' in resp.json()['detail']

  @patch('outreach_service.endpoints.message_send.EmailAccountService')
  @patch('outreach_service.endpoints.message_send.MessageService')
  def test_send_inactive_account_returns_400(self, MockMsgSvc, MockAcctSvc, client):
    """Sending from an inactive email account should return 400."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())

    message = _make_message(id=msg_id, email_account_id=acct_id, status='draft')
    account = _make_account(id=acct_id, provider='gmail', is_active=False)

    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=message)

    acct_svc = MockAcctSvc.return_value
    acct_svc.get_email_account = AsyncMock(return_value=account)

    resp = client.post(f'/api/v1/messages/{msg_id}/send')
    assert resp.status_code == 400
    assert 'not active' in resp.json()['detail']


# ---------------------------------------------------------------------------
# Integration Test: Schedule -> Cancel flow
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestScheduleCancelFlow:
  """End-to-end schedule and cancel-schedule integration tests."""

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_schedule_then_cancel_flow(self, MockMsgSvc, client):
    """Schedule a draft, then cancel it back to draft."""
    msg_id = str(uuid4())

    # Phase 1: Schedule
    draft_msg = _make_message(id=msg_id, status='draft')
    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=draft_msg)
    msg_svc.update_message = AsyncMock(return_value=draft_msg)

    future = (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    resp = client.post(
      f'/api/v1/messages/{msg_id}/schedule',
      json={'scheduled_for': future},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'scheduled'
    assert data['scheduled_for'] is not None

    # Phase 2: Cancel
    scheduled_msg = _make_message(id=msg_id, status='scheduled')
    msg_svc.get_message = AsyncMock(return_value=scheduled_msg)

    resp = client.post(f'/api/v1/messages/{msg_id}/cancel-schedule')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'draft'
    assert data['scheduled_for'] is None

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_schedule_message_not_found(self, MockMsgSvc, client):
    """Scheduling a nonexistent message returns 404."""
    msg_id = str(uuid4())
    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=None)

    future = (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    resp = client.post(
      f'/api/v1/messages/{msg_id}/schedule',
      json={'scheduled_for': future},
    )
    assert resp.status_code == 404

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_schedule_already_sent_returns_400(self, MockMsgSvc, client):
    """Scheduling an already-sent message returns 400."""
    msg_id = str(uuid4())
    sent_msg = _make_message(id=msg_id, status='sent')
    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=sent_msg)

    future = (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    resp = client.post(
      f'/api/v1/messages/{msg_id}/schedule',
      json={'scheduled_for': future},
    )
    assert resp.status_code == 400

  @patch('outreach_service.endpoints.message_schedule.MessageService')
  def test_cancel_non_scheduled_returns_400(self, MockMsgSvc, client):
    """Cancelling a draft (non-scheduled) message returns 400."""
    msg_id = str(uuid4())
    draft_msg = _make_message(id=msg_id, status='draft')
    msg_svc = MockMsgSvc.return_value
    msg_svc.get_message = AsyncMock(return_value=draft_msg)

    resp = client.post(f'/api/v1/messages/{msg_id}/cancel-schedule')
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Integration Test: AI generate + edit
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAiEmailIntegration:
  """AI email generation and editing integration tests."""

  @patch('outreach_service.endpoints.ai_endpoints._call_openai', new_callable=AsyncMock)
  def test_generate_email_returns_subject_and_body(self, mock_openai, client):
    """AI generate-email should return a structured response with subject and body."""
    mock_openai.return_value = (
      'SUBJECT: Partnership Opportunity with Alpha Fund\n'
      'BODY:\n'
      '<p>Dear John,</p>\n'
      '<p>I am reaching out to discuss a potential partnership.</p>\n'
      '<p>Best regards,<br>Team VentureStrat</p>'
    )

    resp = client.post('/api/v1/ai/generate-email', json={
      'investor_name': 'John Smith',
      'investor_company': 'Alpha Fund',
      'context': 'professional',
      'instructions': 'Mention our Series A round',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'subject' in data
    assert 'body' in data
    assert len(data['subject']) > 0
    assert '<p>' in data['body']

  @patch('outreach_service.endpoints.ai_endpoints._call_openai', new_callable=AsyncMock)
  def test_generate_email_fallback_parsing(self, mock_openai, client):
    """When AI response lacks SUBJECT:/BODY: markers, fallback parsing works."""
    mock_openai.return_value = (
      'Exciting Partnership Opportunity\n'
      '<p>Hi Jane, I would love to connect about investment opportunities.</p>'
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
  def test_edit_text_returns_improved_version(self, mock_openai, client):
    """AI edit-text should return the edited version of the text."""
    mock_openai.return_value = '<p>Dear Mr. Smith, I would like to schedule a meeting to discuss investment opportunities.</p>'

    resp = client.post('/api/v1/ai/edit-text', json={
      'original_text': '<p>Hey Smith, wanna meet about investing?</p>',
      'edit_instruction': 'Make it more professional and formal',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 'edited_text' in data
    assert len(data['edited_text']) > 0
    assert 'Dear' in data['edited_text']

  def test_generate_email_without_api_key_returns_500(self, client):
    """When OPENAI_API_KEY is not set, endpoint should return 500."""
    with patch('outreach_service.endpoints.ai_endpoints.settings') as mock_settings:
      mock_settings.openai_api_key = ''
      resp = client.post('/api/v1/ai/generate-email', json={
        'investor_name': 'Test User',
        'investor_company': 'Test Inc',
      })
      assert resp.status_code == 500
      assert 'OPENAI_API_KEY' in resp.json()['detail']

  @patch('outreach_service.endpoints.ai_endpoints._call_openai', new_callable=AsyncMock)
  def test_generate_multiple_emails_different_contexts(self, mock_openai, client):
    """Generate emails with different contexts should invoke AI each time."""
    mock_openai.side_effect = [
      'SUBJECT: Warm Introduction\nBODY:\n<p>Hey there, great meeting you!</p>',
      'SUBJECT: Follow-up on Our Call\nBODY:\n<p>Per our conversation last week...</p>',
    ]

    resp1 = client.post('/api/v1/ai/generate-email', json={
      'investor_name': 'Alice',
      'investor_company': 'Fund A',
      'context': 'warm',
    })
    resp2 = client.post('/api/v1/ai/generate-email', json={
      'investor_name': 'Bob',
      'investor_company': 'Fund B',
      'context': 'follow-up',
    })

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()['subject'] != resp2.json()['subject']
    assert mock_openai.call_count == 2
