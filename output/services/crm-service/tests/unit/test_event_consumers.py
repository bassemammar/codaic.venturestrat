"""Tests for CRM event consumers (activity + shortlist status).

Tests cover:
- ActivityConsumer creates activity on outreach.message.sent
- ActivityConsumer skips when no shortlist found
- ShortlistStatusConsumer updates stage to interested on reply
- ShortlistStatusConsumer skips when already past interested
- ShortlistStatusConsumer creates reply_received activity
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins for ORM objects
# ---------------------------------------------------------------------------

def _make_shortlist(
  id=None,
  user_id='user-1',
  investor_id='inv-1',
  stage_id='stage-contacted',
  status='contacted',
):
  obj = MagicMock()
  obj.id = id or str(uuid.uuid4())
  obj.user_id = user_id
  obj.investor_id = investor_id
  obj.stage_id = stage_id
  obj.status = status
  return obj


def _make_stage(id=None, code='interested', name='Interested', sequence=3):
  obj = MagicMock()
  obj.id = id or str(uuid.uuid4())
  obj.code = code
  obj.name = name
  obj.sequence = sequence
  return obj


def _make_activity(id=None, shortlist_id='sl-1', activity_type='email_sent'):
  obj = MagicMock()
  obj.id = id or str(uuid.uuid4())
  obj.shortlist_id = shortlist_id
  obj.activity_type = activity_type
  obj.to_dict = MagicMock(return_value={
    'id': obj.id,
    'shortlist_id': shortlist_id,
    'activity_type': activity_type,
  })
  return obj


def _event(topic_suffix, data, tenant_id=None):
  """Build a minimal Kafka event payload."""
  evt = {
    'event_id': str(uuid.uuid4()),
    'event_type': f'Message{topic_suffix.title()}',
    'data': data,
    'timestamp': datetime.utcnow().isoformat(),
    'service': 'outreach-service',
  }
  if tenant_id:
    evt['tenant_id'] = tenant_id
  return evt


# ===========================================================================
# ActivityConsumer tests
# ===========================================================================

class TestActivityConsumer:
  """Tests for the ActivityConsumer (outreach.message.sent handler)."""

  @pytest.fixture(autouse=True)
  def _patch_repos(self):
    """Patch repositories and event publisher used by ActivityConsumer."""
    with (
      patch('crm_service.consumers.activity_consumer.ShortlistRepository') as sl_cls,
      patch('crm_service.consumers.activity_consumer.ActivityRepository') as act_cls,
      patch('crm_service.consumers.activity_consumer.event_publisher') as pub,
      patch('crm_service.consumers.activity_consumer.entity_operations_total') as metrics,
    ):
      self.shortlist_repo = AsyncMock()
      self.activity_repo = AsyncMock()
      sl_cls.return_value = self.shortlist_repo
      act_cls.return_value = self.activity_repo
      self.publisher = pub
      self.publisher.publish = AsyncMock()
      self.metrics = metrics

      from crm_service.consumers.activity_consumer import ActivityConsumer
      self.consumer = ActivityConsumer()
      yield

  @pytest.mark.asyncio
  async def test_creates_activity_on_message_sent(self):
    """Should create an Activity when a shortlist is found for the user+investor."""
    shortlist = _make_shortlist()
    self.shortlist_repo.search = AsyncMock(return_value=[shortlist])

    created_activity = _make_activity(shortlist_id=shortlist.id)
    self.activity_repo.create = AsyncMock(return_value=created_activity)

    event = _event('sent', {
      'investor_id': shortlist.investor_id,
      'user_id': shortlist.user_id,
      'subject': 'Intro meeting',
      'message_id': 'msg-123',
    })

    await self.consumer.handle_event('outreach.message.sent', event)

    # Verify shortlist lookup
    self.shortlist_repo.search.assert_awaited_once()
    call_args = self.shortlist_repo.search.call_args
    domain = call_args[0][0]
    assert ('user_id', '=', shortlist.user_id) in domain
    assert ('investor_id', '=', shortlist.investor_id) in domain

    # Verify activity creation
    self.activity_repo.create.assert_awaited_once()
    create_kwargs = self.activity_repo.create.call_args[1]
    assert create_kwargs['shortlist_id'] == shortlist.id
    assert create_kwargs['activity_type'] == 'email_sent'
    assert 'Intro meeting' in create_kwargs['summary']
    assert create_kwargs['user_id'] == shortlist.user_id
    assert create_kwargs['reference_id'] == 'msg-123'

    # Verify event published
    self.publisher.publish.assert_awaited_once()

  @pytest.mark.asyncio
  async def test_skips_when_no_shortlist_found(self):
    """Should skip activity creation when no shortlist matches the user+investor."""
    self.shortlist_repo.search = AsyncMock(return_value=[])

    event = _event('sent', {
      'investor_id': 'inv-unknown',
      'user_id': 'user-unknown',
      'subject': 'Hello',
    })

    await self.consumer.handle_event('outreach.message.sent', event)

    self.activity_repo.create.assert_not_awaited()
    self.publisher.publish.assert_not_awaited()

  @pytest.mark.asyncio
  async def test_skips_on_missing_fields(self):
    """Should skip when investor_id or user_id is missing from event data."""
    event = _event('sent', {'subject': 'Hello'})  # no investor_id / user_id

    await self.consumer.handle_event('outreach.message.sent', event)

    self.shortlist_repo.search.assert_not_awaited()
    self.activity_repo.create.assert_not_awaited()


# ===========================================================================
# ShortlistStatusConsumer tests
# ===========================================================================

class TestShortlistStatusConsumer:
  """Tests for the ShortlistStatusConsumer (outreach.message.replied handler)."""

  @pytest.fixture(autouse=True)
  def _patch_repos(self):
    """Patch repositories and event publisher used by ShortlistStatusConsumer."""
    with (
      patch('crm_service.consumers.shortlist_status_consumer.ShortlistRepository') as sl_cls,
      patch('crm_service.consumers.shortlist_status_consumer.ActivityRepository') as act_cls,
      patch('crm_service.consumers.shortlist_status_consumer.PipelineStageRepository') as ps_cls,
      patch('crm_service.consumers.shortlist_status_consumer.event_publisher') as pub,
      patch('crm_service.consumers.shortlist_status_consumer.entity_operations_total') as metrics,
    ):
      self.shortlist_repo = AsyncMock()
      self.activity_repo = AsyncMock()
      self.pipeline_stage_repo = AsyncMock()
      sl_cls.return_value = self.shortlist_repo
      act_cls.return_value = self.activity_repo
      ps_cls.return_value = self.pipeline_stage_repo
      self.publisher = pub
      self.publisher.publish = AsyncMock()
      self.metrics = metrics

      from crm_service.consumers.shortlist_status_consumer import ShortlistStatusConsumer
      self.consumer = ShortlistStatusConsumer()
      yield

  @pytest.mark.asyncio
  async def test_updates_stage_to_interested(self):
    """Should update shortlist stage to 'interested' when currently at a pre-interested stage."""
    contacted_stage = _make_stage(code='contacted', sequence=2)
    interested_stage = _make_stage(code='interested', sequence=3)
    shortlist = _make_shortlist(stage_id=contacted_stage.id, status='contacted')

    self.shortlist_repo.search = AsyncMock(return_value=[shortlist])
    self.shortlist_repo.update = AsyncMock(return_value=shortlist)
    self.pipeline_stage_repo.get_by_id = AsyncMock(return_value=contacted_stage)
    # When searching for 'interested' stage by code
    self.pipeline_stage_repo.search = AsyncMock(return_value=[interested_stage])

    created_activity = _make_activity(
      shortlist_id=shortlist.id, activity_type='reply_received'
    )
    self.activity_repo.create = AsyncMock(return_value=created_activity)

    event = _event('replied', {
      'investor_id': shortlist.investor_id,
      'user_id': shortlist.user_id,
      'investor_name': 'Acme Ventures',
      'message_id': 'msg-reply-1',
    })

    await self.consumer.handle_event('outreach.message.replied', event)

    # Verify stage was updated
    self.shortlist_repo.update.assert_awaited_once()
    assert shortlist.stage_id == interested_stage.id
    assert shortlist.status == 'interested'

    # Verify status_changed event published
    publish_calls = self.publisher.publish.call_args_list
    status_call = [c for c in publish_calls if c[1].get('action') == 'status_changed']
    assert len(status_call) == 1
    status_data = status_call[0][1]['data']
    assert status_data['new_stage'] == 'interested'
    assert status_data['old_stage'] == 'contacted'

  @pytest.mark.asyncio
  async def test_skips_update_when_already_past_interested(self):
    """Should NOT update stage when shortlist is already past 'interested'."""
    negotiating_stage = _make_stage(code='negotiating', sequence=5)
    shortlist = _make_shortlist(stage_id=negotiating_stage.id, status='negotiating')

    self.shortlist_repo.search = AsyncMock(return_value=[shortlist])
    self.pipeline_stage_repo.get_by_id = AsyncMock(return_value=negotiating_stage)

    created_activity = _make_activity(
      shortlist_id=shortlist.id, activity_type='reply_received'
    )
    self.activity_repo.create = AsyncMock(return_value=created_activity)

    event = _event('replied', {
      'investor_id': shortlist.investor_id,
      'user_id': shortlist.user_id,
      'investor_name': 'BigFund',
    })

    await self.consumer.handle_event('outreach.message.replied', event)

    # Stage should NOT have been updated
    self.shortlist_repo.update.assert_not_awaited()

    # Activity should still be created (reply_received)
    self.activity_repo.create.assert_awaited_once()
    create_kwargs = self.activity_repo.create.call_args[1]
    assert create_kwargs['activity_type'] == 'reply_received'

  @pytest.mark.asyncio
  async def test_creates_reply_received_activity(self):
    """Should always create a reply_received activity regardless of stage update."""
    contacted_stage = _make_stage(code='contacted', sequence=2)
    interested_stage = _make_stage(code='interested', sequence=3)
    shortlist = _make_shortlist(stage_id=contacted_stage.id, status='contacted')

    self.shortlist_repo.search = AsyncMock(return_value=[shortlist])
    self.shortlist_repo.update = AsyncMock(return_value=shortlist)
    self.pipeline_stage_repo.get_by_id = AsyncMock(return_value=contacted_stage)
    self.pipeline_stage_repo.search = AsyncMock(return_value=[interested_stage])

    created_activity = _make_activity(
      shortlist_id=shortlist.id, activity_type='reply_received'
    )
    self.activity_repo.create = AsyncMock(return_value=created_activity)

    event = _event('replied', {
      'investor_id': shortlist.investor_id,
      'user_id': shortlist.user_id,
      'investor_name': 'SeedCo',
      'message_id': 'msg-reply-2',
    })

    await self.consumer.handle_event('outreach.message.replied', event)

    self.activity_repo.create.assert_awaited_once()
    create_kwargs = self.activity_repo.create.call_args[1]
    assert create_kwargs['activity_type'] == 'reply_received'
    assert 'SeedCo' in create_kwargs['summary']
    assert create_kwargs['shortlist_id'] == shortlist.id
    assert create_kwargs['user_id'] == shortlist.user_id

  @pytest.mark.asyncio
  async def test_skips_when_no_shortlist_found(self):
    """Should skip entirely when no shortlist matches the user+investor."""
    self.shortlist_repo.search = AsyncMock(return_value=[])

    event = _event('replied', {
      'investor_id': 'inv-unknown',
      'user_id': 'user-unknown',
      'investor_name': 'Nobody',
    })

    await self.consumer.handle_event('outreach.message.replied', event)

    self.shortlist_repo.update.assert_not_awaited()
    self.activity_repo.create.assert_not_awaited()
    self.publisher.publish.assert_not_awaited()
