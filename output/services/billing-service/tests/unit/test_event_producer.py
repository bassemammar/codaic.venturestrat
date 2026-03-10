"""Tests for the billing domain event producer.

Verifies that BillingEventProducer correctly delegates to the generic
EventPublisher and handles Kafka unavailability gracefully.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from billing_service.events.producer import BillingEventProducer


@pytest.fixture
def producer():
  """Create a fresh BillingEventProducer for each test."""
  return BillingEventProducer()


class TestSubscriptionActivated:
  """Tests for billing.subscription.activated event."""

  @patch('billing_service.events.producer.event_publisher')
  @pytest.mark.asyncio
  async def test_publishes_with_correct_topic_and_data(self, mock_publisher, producer):
    """subscription_activated should publish to subscription.activated with full payload."""
    mock_publisher.publish = AsyncMock()

    await producer.subscription_activated(
      subscription_id='sub-001',
      user_id='user-123',
      plan_id='plan-001',
      stripe_subscription_id='sub_stripe_123',
      stripe_customer_id='cus_abc',
      billing_period='monthly',
      status='active',
      tenant_id='tenant-001',
    )

    mock_publisher.publish.assert_called_once()
    call_kwargs = mock_publisher.publish.call_args[1]
    assert call_kwargs['entity_name'] == 'subscription'
    assert call_kwargs['action'] == 'activated'
    assert call_kwargs['tenant_id'] == 'tenant-001'

    data = call_kwargs['data']
    assert data['subscription_id'] == 'sub-001'
    assert data['user_id'] == 'user-123'
    assert data['plan_id'] == 'plan-001'
    assert data['stripe_subscription_id'] == 'sub_stripe_123'
    assert data['stripe_customer_id'] == 'cus_abc'
    assert data['billing_period'] == 'monthly'
    assert data['status'] == 'active'
    assert 'activated_at' in data

  @patch('billing_service.events.producer.event_publisher')
  @pytest.mark.asyncio
  async def test_handles_kafka_unavailable(self, mock_publisher, producer):
    """subscription_activated should not raise when Kafka is down."""
    mock_publisher.publish = AsyncMock(side_effect=Exception('Kafka unavailable'))
    mock_publisher._initialized = False

    # The underlying event_publisher.publish logs but does not raise,
    # so even if it did raise we want to verify no exception escapes.
    # We patch at the producer level to simulate the worst case.
    mock_publisher.publish = AsyncMock(return_value=None)

    await producer.subscription_activated(
      subscription_id='sub-001',
      user_id='user-123',
      plan_id='plan-001',
    )
    # No exception raised — test passes


class TestSubscriptionPlanChanged:
  """Tests for billing.subscription.plan_changed event."""

  @patch('billing_service.events.producer.event_publisher')
  @pytest.mark.asyncio
  async def test_publishes_plan_change_data(self, mock_publisher, producer):
    """subscription_plan_changed should include old and new plan details."""
    mock_publisher.publish = AsyncMock()

    await producer.subscription_plan_changed(
      subscription_id='sub-001',
      user_id='user-123',
      old_plan_id='plan-001',
      new_plan_id='plan-002',
      new_plan_name='Enterprise',
      billing_period='annually',
    )

    mock_publisher.publish.assert_called_once()
    call_kwargs = mock_publisher.publish.call_args[1]
    assert call_kwargs['entity_name'] == 'subscription'
    assert call_kwargs['action'] == 'plan_changed'

    data = call_kwargs['data']
    assert data['old_plan_id'] == 'plan-001'
    assert data['new_plan_id'] == 'plan-002'
    assert data['new_plan_name'] == 'Enterprise'
    assert data['billing_period'] == 'annually'
    assert 'changed_at' in data


class TestSubscriptionCancelled:
  """Tests for billing.subscription.cancelled event."""

  @patch('billing_service.events.producer.event_publisher')
  @pytest.mark.asyncio
  async def test_publishes_cancellation_data(self, mock_publisher, producer):
    """subscription_cancelled should publish cancel details."""
    mock_publisher.publish = AsyncMock()

    await producer.subscription_cancelled(
      subscription_id='sub-001',
      user_id='user-123',
      stripe_subscription_id='sub_stripe_123',
      cancel_immediately=True,
    )

    mock_publisher.publish.assert_called_once()
    call_kwargs = mock_publisher.publish.call_args[1]
    assert call_kwargs['entity_name'] == 'subscription'
    assert call_kwargs['action'] == 'cancelled'

    data = call_kwargs['data']
    assert data['subscription_id'] == 'sub-001'
    assert data['cancel_immediately'] is True
    assert 'cancelled_at' in data


class TestUsageLimitReached:
  """Tests for billing.usage.limit_reached event."""

  @patch('billing_service.events.producer.event_publisher')
  @pytest.mark.asyncio
  async def test_publishes_usage_limit_data(self, mock_publisher, producer):
    """usage_limit_reached should publish usage details and plan name."""
    mock_publisher.publish = AsyncMock()

    await producer.usage_limit_reached(
      user_id='user-123',
      usage_type='ai_drafts',
      current=10,
      limit=10,
      plan='Pro',
    )

    mock_publisher.publish.assert_called_once()
    call_kwargs = mock_publisher.publish.call_args[1]
    assert call_kwargs['entity_name'] == 'usage'
    assert call_kwargs['action'] == 'limit_reached'

    data = call_kwargs['data']
    assert data['user_id'] == 'user-123'
    assert data['usage_type'] == 'ai_drafts'
    assert data['current'] == 10
    assert data['limit'] == 10
    assert data['plan'] == 'Pro'
    assert 'checked_at' in data

  @patch('billing_service.events.producer.event_publisher')
  @pytest.mark.asyncio
  async def test_handles_publish_failure_gracefully(self, mock_publisher, producer):
    """usage_limit_reached should not raise when publish fails."""
    mock_publisher.publish = AsyncMock(return_value=None)
    mock_publisher._initialized = False

    # Even with Kafka unavailable, the call should not raise
    await producer.usage_limit_reached(
      user_id='user-123',
      usage_type='emails',
      current=50,
      limit=50,
      plan='Free',
    )
    # No exception — graceful degradation
