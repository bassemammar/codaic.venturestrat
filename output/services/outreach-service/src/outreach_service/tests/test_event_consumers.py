"""Tests for event consumers (Wave 10).

Tests cover:
- EmailSendConsumer processes message correctly (mock Kafka, mock provider)
- EmailSendConsumer handles failure with DLQ routing
- LifecycleEmailConsumer finds pending emails
- LifecycleEmailConsumer skips when conditions met
- EventProducer publishes correctly
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_message_response(**overrides):
  """Build a mock MessageResponse-like object."""
  defaults = {
    'id': str(uuid4()),
    'user_id': 'user-1',
    'investor_id': str(uuid4()),
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


def _make_lifecycle_email(**overrides):
  """Build a mock LifecycleEmailResponse-like object."""
  defaults = {
    'id': str(uuid4()),
    'user_id': 'user-1',
    'template_code': 'welcome',
    'status': 'pending',
    'scheduled_for': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
    'sent_at': None,
    'skip_reason': None,
    'created_at': datetime.utcnow(),
    'updated_at': datetime.utcnow(),
  }
  defaults.update(overrides)
  return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# 10.4 — EmailSendConsumer
# ---------------------------------------------------------------------------

class TestEmailSendConsumer:
  """Tests for the Kafka email send consumer."""

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.email_send_consumer.event_producer')
  @patch('outreach_service.consumers.email_send_consumer.gmail.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.email_send_consumer.EmailAccountService')
  @patch('outreach_service.consumers.email_send_consumer.MessageService')
  async def test_handle_message_success(
    self, MockMsgService, MockAcctService, mock_gmail_send, mock_producer,
  ):
    """Consumer should send email and publish outreach.message.sent on success."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())

    message = _make_message_response(
      id=msg_id, email_account_id=acct_id, status='draft',
    )
    account = _make_account_response(id=acct_id, provider='gmail')

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=message)
    mock_msg_svc.update_message = AsyncMock(return_value=message)

    mock_acct_svc = MockAcctService.return_value
    mock_acct_svc.get_email_account = AsyncMock(return_value=account)

    mock_gmail_send.return_value = {
      'id': 'gmail-msg-123',
      'threadId': 'thread-abc',
    }
    mock_producer.publish_event = AsyncMock()

    from outreach_service.consumers.email_send_consumer import EmailSendConsumer
    consumer = EmailSendConsumer()

    event = {
      'data': {
        'message_id': msg_id,
        'tenant_id': '00000000-0000-0000-0000-000000000000',
      }
    }
    await consumer._handle_message(event)

    # Verify provider was called
    mock_gmail_send.assert_called_once()

    # Verify message was updated to sent
    mock_msg_svc.update_message.assert_called()
    update_call = mock_msg_svc.update_message.call_args
    assert update_call[0][1].status == 'sent'

    # Verify outreach.message.sent event was published
    mock_producer.publish_event.assert_called_once()
    call_args = mock_producer.publish_event.call_args
    assert call_args[0][0] == 'outreach.message.sent'
    assert call_args[0][1]['message_id'] == msg_id

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.email_send_consumer.event_producer')
  @patch('outreach_service.consumers.email_send_consumer.gmail.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.email_send_consumer.EmailAccountService')
  @patch('outreach_service.consumers.email_send_consumer.MessageService')
  async def test_handle_message_failure_routes_to_dlq(
    self, MockMsgService, MockAcctService, mock_gmail_send, mock_producer,
  ):
    """On permanent failure after retries, consumer should route to DLQ."""
    msg_id = str(uuid4())
    acct_id = str(uuid4())

    message = _make_message_response(
      id=msg_id, email_account_id=acct_id, status='draft',
    )
    account = _make_account_response(id=acct_id, provider='gmail')

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=message)
    mock_msg_svc.update_message = AsyncMock()

    mock_acct_svc = MockAcctService.return_value
    mock_acct_svc.get_email_account = AsyncMock(return_value=account)

    # Make send fail every time
    mock_gmail_send.side_effect = RuntimeError('SMTP connection refused')
    mock_producer.publish_event = AsyncMock()

    from outreach_service.consumers.email_send_consumer import EmailSendConsumer
    consumer = EmailSendConsumer()

    event = {
      'data': {
        'message_id': msg_id,
      }
    }

    # Patch sleep to avoid waiting during tests
    with patch('outreach_service.consumers.email_send_consumer.asyncio.sleep', new_callable=AsyncMock):
      await consumer._handle_message(event)

    # Provider was called MAX_RETRIES times
    assert mock_gmail_send.call_count == 3

    # DLQ event was published
    dlq_calls = [
      c for c in mock_producer.publish_event.call_args_list
      if c[0][0] == 'outreach.send_email.dlq'
    ]
    assert len(dlq_calls) == 1

    # Message status set to failed
    update_calls = mock_msg_svc.update_message.call_args_list
    assert any(c[0][1].status == 'failed' for c in update_calls)

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.email_send_consumer.event_producer')
  @patch('outreach_service.consumers.email_send_consumer.MessageService')
  async def test_handle_message_not_found(self, MockMsgService, mock_producer):
    """Consumer should handle missing message gracefully (routes to DLQ)."""
    msg_id = str(uuid4())

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.get_message = AsyncMock(return_value=None)
    mock_msg_svc.update_message = AsyncMock()
    mock_producer.publish_event = AsyncMock()

    from outreach_service.consumers.email_send_consumer import EmailSendConsumer
    consumer = EmailSendConsumer()

    event = {'data': {'message_id': msg_id}}

    with patch('outreach_service.consumers.email_send_consumer.asyncio.sleep', new_callable=AsyncMock):
      await consumer._handle_message(event)

    # Should route to DLQ after retries
    dlq_calls = [
      c for c in mock_producer.publish_event.call_args_list
      if c[0][0] == 'outreach.send_email.dlq'
    ]
    assert len(dlq_calls) == 1


# ---------------------------------------------------------------------------
# 10.5 — LifecycleEmailConsumer
# ---------------------------------------------------------------------------

class TestLifecycleEmailConsumer:
  """Tests for the lifecycle email polling consumer."""

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_poll_finds_pending_and_sends(
    self, MockLifecycleSvc, MockMsgService, mock_sendgrid_send,
  ):
    """Polling should find pending emails and send them via SendGrid."""
    record = _make_lifecycle_email(template_code='welcome')

    mock_lc_svc = MockLifecycleSvc.return_value
    mock_lc_svc.search_lifecycle_emails = AsyncMock(return_value=[record])
    mock_lc_svc.update_lifecycle_email = AsyncMock()

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.search_messages = AsyncMock(return_value=[])

    mock_sendgrid_send.return_value = {'message_id': 'sg-123'}

    from outreach_service.consumers.lifecycle_email_consumer import LifecycleEmailConsumer
    consumer = LifecycleEmailConsumer(poll_interval=60)

    await consumer._poll_and_process()

    # SendGrid was called
    mock_sendgrid_send.assert_called_once()

    # Record was updated to sent
    update_calls = mock_lc_svc.update_lifecycle_email.call_args_list
    assert len(update_calls) == 1
    update_data = update_calls[0][0][1]
    assert update_data.status == 'sent'
    assert update_data.sent_at is not None

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_poll_skips_when_user_replied(
    self, MockLifecycleSvc, MockMsgService, mock_sendgrid_send,
  ):
    """Lifecycle email should be skipped if user has already replied."""
    record = _make_lifecycle_email(template_code='onboarding_reminder')

    mock_lc_svc = MockLifecycleSvc.return_value
    mock_lc_svc.search_lifecycle_emails = AsyncMock(return_value=[record])
    mock_lc_svc.update_lifecycle_email = AsyncMock()

    # User has a replied message — should trigger skip
    replied_msg = _make_message_response(status='replied')
    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.search_messages = AsyncMock(return_value=[replied_msg])

    from outreach_service.consumers.lifecycle_email_consumer import LifecycleEmailConsumer
    consumer = LifecycleEmailConsumer(poll_interval=60)

    await consumer._poll_and_process()

    # SendGrid should NOT be called
    mock_sendgrid_send.assert_not_called()

    # Record should be updated to skipped
    update_calls = mock_lc_svc.update_lifecycle_email.call_args_list
    assert len(update_calls) == 1
    update_data = update_calls[0][0][1]
    assert update_data.status == 'skipped'
    assert update_data.skip_reason == 'user_already_replied'

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_poll_no_pending_is_noop(
    self, MockLifecycleSvc, MockMsgService, mock_sendgrid_send,
  ):
    """When there are no pending lifecycle emails, nothing happens."""
    mock_lc_svc = MockLifecycleSvc.return_value
    mock_lc_svc.search_lifecycle_emails = AsyncMock(return_value=[])

    from outreach_service.consumers.lifecycle_email_consumer import LifecycleEmailConsumer
    consumer = LifecycleEmailConsumer(poll_interval=60)

    await consumer._poll_and_process()

    mock_sendgrid_send.assert_not_called()

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_poll_unknown_template_fails(
    self, MockLifecycleSvc, MockMsgService, mock_sendgrid_send,
  ):
    """Unknown template_code should mark lifecycle email as failed."""
    record = _make_lifecycle_email(template_code='nonexistent_template')

    mock_lc_svc = MockLifecycleSvc.return_value
    mock_lc_svc.search_lifecycle_emails = AsyncMock(return_value=[record])
    mock_lc_svc.update_lifecycle_email = AsyncMock()

    mock_msg_svc = MockMsgService.return_value
    mock_msg_svc.search_messages = AsyncMock(return_value=[])

    from outreach_service.consumers.lifecycle_email_consumer import LifecycleEmailConsumer
    consumer = LifecycleEmailConsumer(poll_interval=60)

    await consumer._poll_and_process()

    mock_sendgrid_send.assert_not_called()

    update_calls = mock_lc_svc.update_lifecycle_email.call_args_list
    assert len(update_calls) == 1
    update_data = update_calls[0][0][1]
    assert update_data.status == 'failed'
    assert 'nonexistent_template' in (update_data.skip_reason or '')


# ---------------------------------------------------------------------------
# EventProducer
# ---------------------------------------------------------------------------

class TestEventProducer:
  """Tests for the Kafka event producer."""

  @pytest.mark.asyncio
  @patch('outreach_service.events.producer.AIOKafkaProducer')
  async def test_publish_event_sends_to_kafka(self, MockProducer):
    """publish_event should serialize and send via AIOKafkaProducer."""
    mock_instance = AsyncMock()
    MockProducer.return_value = mock_instance

    from outreach_service.events.producer import EventProducer
    producer = EventProducer()
    await producer.start()

    assert producer._started is True
    mock_instance.start.assert_called_once()

    await producer.publish_event(
      'outreach.message.sent',
      {'message_id': 'abc-123', 'user_id': 'user-1'},
      tenant_id='tenant-1',
    )

    mock_instance.send_and_wait.assert_called_once()
    call_args = mock_instance.send_and_wait.call_args
    # topic is positional arg [0][0], value is keyword arg [1]['value']
    assert call_args[0][0] == 'outreach.message.sent'
    event_value = call_args[1]['value']
    assert event_value['data']['message_id'] == 'abc-123'
    assert event_value['tenant_id'] == 'tenant-1'
    assert 'event_id' in event_value

    await producer.stop()
    mock_instance.stop.assert_called_once()

  @pytest.mark.asyncio
  async def test_publish_event_not_started_is_noop(self):
    """publish_event should warn and return if producer is not started."""
    from outreach_service.events.producer import EventProducer
    producer = EventProducer()

    # Should not raise
    await producer.publish_event('some.topic', {'key': 'value'})

  @pytest.mark.asyncio
  @patch('outreach_service.events.producer.AIOKafkaProducer')
  async def test_start_failure_does_not_crash(self, MockProducer):
    """If Kafka connection fails, start should log error but not crash."""
    mock_instance = AsyncMock()
    mock_instance.start.side_effect = ConnectionError('Kafka unreachable')
    MockProducer.return_value = mock_instance

    from outreach_service.events.producer import EventProducer
    producer = EventProducer()

    # Should not raise
    await producer.start()
    assert producer._started is False
