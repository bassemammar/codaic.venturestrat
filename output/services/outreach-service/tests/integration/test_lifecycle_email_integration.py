"""Integration tests for the lifecycle email campaign consumer.

Tests the LifecycleEmailConsumer polling logic end-to-end:
  - Finds pending records with scheduled_for <= now
  - Evaluates skip conditions (user already replied)
  - Sends via SendGrid (mocked)
  - Handles send failures with status update
  - Processes multiple pending emails in order

The consumer is tested by invoking its internal methods directly rather
than running the full asyncio polling loop.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------

def _make_lifecycle_email(
  id=None,
  user_id='user-1',
  template_code='welcome',
  status='pending',
  scheduled_for=None,
  sent_at=None,
  skip_reason=None,
):
  """Build a mock lifecycle email record."""
  record = MagicMock()
  record.id = id or str(uuid4())
  record.user_id = user_id
  record.template_code = template_code
  record.status = status
  record.scheduled_for = scheduled_for or (datetime.utcnow() - timedelta(minutes=5))
  record.sent_at = sent_at
  record.skip_reason = skip_reason
  return record


def _make_message_response(
  id=None,
  user_id='user-1',
  status='replied',
):
  """Build a mock message response for skip condition checks."""
  msg = MagicMock()
  msg.id = id or str(uuid4())
  msg.user_id = user_id
  msg.status = status
  return msg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def consumer():
  """Create a fresh LifecycleEmailConsumer for each test."""
  import os
  os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
  os.environ.setdefault('PLATFORM_MODE', 'standalone')
  os.environ.setdefault('LOG_LEVEL', 'WARNING')
  from outreach_service.consumers.lifecycle_email_consumer import LifecycleEmailConsumer
  return LifecycleEmailConsumer(poll_interval=1)


# ---------------------------------------------------------------------------
# Integration Test: Consumer finds and processes pending records
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestLifecycleEmailConsumerProcessing:
  """Tests for _poll_and_process and _process_record methods."""

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_processes_pending_records(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """Consumer should find and process pending records."""
    record = _make_lifecycle_email(
      template_code='welcome',
      status='pending',
      scheduled_for=datetime.utcnow() - timedelta(minutes=1),
    )

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.search_lifecycle_emails = AsyncMock(return_value=[record])
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])  # No replies

    mock_sendgrid.return_value = {'message_id': 'sg-001'}

    await consumer._poll_and_process()

    # Verify it searched for pending records
    lifecycle_svc.search_lifecycle_emails.assert_called_once()

    # Verify it updated the record to 'sent'
    lifecycle_svc.update_lifecycle_email.assert_called()
    update_call = lifecycle_svc.update_lifecycle_email.call_args
    update_data = update_call[0][1]
    assert update_data.status == 'sent'
    assert update_data.sent_at is not None

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_no_pending_records(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """When no pending records exist, nothing should be processed."""
    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.search_lifecycle_emails = AsyncMock(return_value=[])

    await consumer._poll_and_process()

    lifecycle_svc.update_lifecycle_email.assert_not_called()
    mock_sendgrid.assert_not_called()


# ---------------------------------------------------------------------------
# Integration Test: Skip conditions
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestLifecycleEmailSkipConditions:
  """Tests for skip condition evaluation."""

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_skip_when_user_already_replied(
    self, MockLifecycleSvc, MockMsgSvc, consumer
  ):
    """If user has a 'replied' message, lifecycle email should be skipped."""
    record = _make_lifecycle_email(user_id='user-replied', template_code='onboarding_reminder')

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[
      _make_message_response(user_id='user-replied', status='replied'),
    ])

    await consumer._process_record(record, lifecycle_svc)

    # Verify record was updated to 'skipped'
    lifecycle_svc.update_lifecycle_email.assert_called_once()
    update_data = lifecycle_svc.update_lifecycle_email.call_args[0][1]
    assert update_data.status == 'skipped'
    assert update_data.skip_reason == 'user_already_replied'

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_no_skip_when_user_has_no_replies(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """If user has no replied messages, email should be sent normally."""
    record = _make_lifecycle_email(user_id='user-new', template_code='welcome')

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])  # No replies

    mock_sendgrid.return_value = {'message_id': 'sg-002'}

    await consumer._process_record(record, lifecycle_svc)

    # Should be marked as sent (not skipped)
    update_data = lifecycle_svc.update_lifecycle_email.call_args[0][1]
    assert update_data.status == 'sent'

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_skip_check_failure_proceeds_with_send(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """If skip check raises an exception, email should still be sent."""
    record = _make_lifecycle_email(user_id='user-err', template_code='welcome')

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(side_effect=Exception('DB connection failed'))

    mock_sendgrid.return_value = {'message_id': 'sg-003'}

    await consumer._process_record(record, lifecycle_svc)

    # Should still be sent (skip check error is swallowed)
    update_data = lifecycle_svc.update_lifecycle_email.call_args[0][1]
    assert update_data.status == 'sent'


# ---------------------------------------------------------------------------
# Integration Test: SendGrid send (mock httpx)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestLifecycleEmailSend:
  """Tests for the SendGrid send path."""

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_send_welcome_email(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """Welcome template should be resolved and sent via SendGrid."""
    record = _make_lifecycle_email(
      user_id='newuser@example.com',
      template_code='welcome',
    )

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])

    mock_sendgrid.return_value = {'message_id': 'sg-welcome-001'}

    await consumer._process_record(record, lifecycle_svc)

    # Verify SendGrid was called with correct params
    mock_sendgrid.assert_called_once()
    call_kwargs = mock_sendgrid.call_args[1]
    assert call_kwargs['to_addresses'] == ['newuser@example.com']
    assert call_kwargs['subject'] == 'Welcome to VentureStrat'
    assert '<p>' in call_kwargs['body_html']
    assert call_kwargs['from_address'] == 'noreply@venturestrat.com'

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_send_onboarding_reminder(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """Onboarding reminder template should be sent correctly."""
    record = _make_lifecycle_email(
      user_id='user@example.com',
      template_code='onboarding_reminder',
    )

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])

    mock_sendgrid.return_value = {'message_id': 'sg-onboard-001'}

    await consumer._process_record(record, lifecycle_svc)

    call_kwargs = mock_sendgrid.call_args[1]
    assert call_kwargs['subject'] == 'Complete your VentureStrat setup'

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_unknown_template_sets_failed(
    self, MockLifecycleSvc, MockMsgSvc, consumer
  ):
    """An unknown template_code should mark the record as failed."""
    record = _make_lifecycle_email(
      template_code='nonexistent_template',
    )

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])

    await consumer._process_record(record, lifecycle_svc)

    update_data = lifecycle_svc.update_lifecycle_email.call_args[0][1]
    assert update_data.status == 'failed'
    assert 'nonexistent_template' in update_data.skip_reason


# ---------------------------------------------------------------------------
# Integration Test: Send failure handling
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestLifecycleEmailFailure:
  """Tests for send failure and retry behaviour."""

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_send_failure_sets_failed_status(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """When SendGrid raises an error, record should be marked as failed."""
    record = _make_lifecycle_email(template_code='welcome')

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])

    mock_sendgrid.side_effect = Exception('SendGrid API error: 503')

    await consumer._process_record(record, lifecycle_svc)

    update_data = lifecycle_svc.update_lifecycle_email.call_args[0][1]
    assert update_data.status == 'failed'

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_send_not_implemented_sets_failed(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """SendGrid NotImplementedError should also mark as failed."""
    record = _make_lifecycle_email(template_code='welcome')

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])

    mock_sendgrid.side_effect = NotImplementedError('SendGrid not implemented')

    await consumer._process_record(record, lifecycle_svc)

    update_data = lifecycle_svc.update_lifecycle_email.call_args[0][1]
    assert update_data.status == 'failed'


# ---------------------------------------------------------------------------
# Integration Test: Multiple pending emails processed in order
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestLifecycleEmailBatchProcessing:
  """Tests for batch processing of multiple pending emails."""

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_processes_multiple_records_in_order(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """Multiple pending records should all be processed."""
    records = [
      _make_lifecycle_email(
        id=f'le-{i}',
        user_id=f'user-{i}@example.com',
        template_code='welcome',
        scheduled_for=datetime.utcnow() - timedelta(minutes=10 - i),
      )
      for i in range(5)
    ]

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.search_lifecycle_emails = AsyncMock(return_value=records)
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])

    mock_sendgrid.return_value = {'message_id': 'sg-batch'}

    await consumer._poll_and_process()

    # All 5 records should have been processed
    assert mock_sendgrid.call_count == 5
    assert lifecycle_svc.update_lifecycle_email.call_count == 5

    # Verify each was marked as sent
    for call in lifecycle_svc.update_lifecycle_email.call_args_list:
      update_data = call[0][1]
      assert update_data.status == 'sent'

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_mixed_success_and_failure(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """When some sends fail, others should still succeed."""
    records = [
      _make_lifecycle_email(id='le-ok-1', user_id='ok1@example.com', template_code='welcome'),
      _make_lifecycle_email(id='le-fail', user_id='fail@example.com', template_code='welcome'),
      _make_lifecycle_email(id='le-ok-2', user_id='ok2@example.com', template_code='welcome'),
    ]

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.search_lifecycle_emails = AsyncMock(return_value=records)
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value
    msg_svc.search_messages = AsyncMock(return_value=[])

    # Second call fails, others succeed
    mock_sendgrid.side_effect = [
      {'message_id': 'sg-ok-1'},
      Exception('API timeout'),
      {'message_id': 'sg-ok-2'},
    ]

    await consumer._poll_and_process()

    # All 3 records should have been attempted
    assert mock_sendgrid.call_count == 3
    assert lifecycle_svc.update_lifecycle_email.call_count == 3

    # Check statuses: sent, failed, sent
    statuses = [
      call[0][1].status
      for call in lifecycle_svc.update_lifecycle_email.call_args_list
    ]
    assert statuses == ['sent', 'failed', 'sent']

  @pytest.mark.asyncio
  @patch('outreach_service.consumers.lifecycle_email_consumer.sendgrid_provider.send_email', new_callable=AsyncMock)
  @patch('outreach_service.consumers.lifecycle_email_consumer.MessageService')
  @patch('outreach_service.consumers.lifecycle_email_consumer.LifecycleEmailService')
  async def test_mixed_skip_and_send(
    self, MockLifecycleSvc, MockMsgSvc, mock_sendgrid, consumer
  ):
    """Some records skipped (user replied), others sent."""
    records = [
      _make_lifecycle_email(id='le-skip', user_id='replied-user', template_code='welcome'),
      _make_lifecycle_email(id='le-send', user_id='new-user', template_code='welcome'),
    ]

    lifecycle_svc = MockLifecycleSvc.return_value
    lifecycle_svc.search_lifecycle_emails = AsyncMock(return_value=records)
    lifecycle_svc.update_lifecycle_email = AsyncMock()

    msg_svc = MockMsgSvc.return_value

    # First call: user has replied; second call: no replies
    async def search_messages_side_effect(domain=None, **kwargs):
      user_id = None
      for d in (domain or []):
        if d[0] == 'user_id':
          user_id = d[2]
      if user_id == 'replied-user':
        return [_make_message_response(user_id='replied-user', status='replied')]
      return []

    msg_svc.search_messages = AsyncMock(side_effect=search_messages_side_effect)
    mock_sendgrid.return_value = {'message_id': 'sg-sent'}

    await consumer._poll_and_process()

    # Two updates: skip + send
    assert lifecycle_svc.update_lifecycle_email.call_count == 2
    statuses = [
      call[0][1].status
      for call in lifecycle_svc.update_lifecycle_email.call_args_list
    ]
    assert statuses == ['skipped', 'sent']

    # SendGrid only called once (for the non-skipped record)
    assert mock_sendgrid.call_count == 1
