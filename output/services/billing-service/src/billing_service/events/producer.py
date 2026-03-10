"""Domain-specific event publisher for billing events.

Thin async wrapper that delegates to the generic EventPublisher in
integrations/events.py. Each method corresponds to a domain event
declared in manifest.yaml under provides.events.

All publish calls are fire-and-forget — failures are logged but never
raise, so webhook/endpoint latency is not affected by Kafka availability.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog

from billing_service.integrations.events import event_publisher

logger = structlog.get_logger(__name__)


class BillingEventProducer:
  """Publishes billing domain events to Kafka.

  Uses the global event_publisher (AIOKafkaProducer) that is initialised
  during application startup in main.py.  If the producer is not
  connected (e.g. Kafka unavailable in dev) every call gracefully no-ops.
  """

  # ------------------------------------------------------------------
  # billing.subscription.activated
  # ------------------------------------------------------------------
  async def subscription_activated(
    self,
    *,
    subscription_id: str,
    user_id: str,
    plan_id: str,
    stripe_subscription_id: str = '',
    stripe_customer_id: str = '',
    billing_period: str = 'monthly',
    status: str = 'active',
    tenant_id: Optional[str] = None,
  ) -> None:
    """Emit billing.subscription.activated after checkout completes."""
    await event_publisher.publish(
      entity_name='subscription',
      action='activated',
      data={
        'subscription_id': subscription_id,
        'user_id': user_id,
        'plan_id': plan_id,
        'stripe_subscription_id': stripe_subscription_id,
        'stripe_customer_id': stripe_customer_id,
        'billing_period': billing_period,
        'status': status,
        'activated_at': datetime.now(timezone.utc).isoformat(),
      },
      tenant_id=tenant_id,
    )

  # ------------------------------------------------------------------
  # billing.subscription.plan_changed
  # ------------------------------------------------------------------
  async def subscription_plan_changed(
    self,
    *,
    subscription_id: str,
    user_id: str,
    old_plan_id: str,
    new_plan_id: str,
    new_plan_name: str,
    billing_period: str = '',
    tenant_id: Optional[str] = None,
  ) -> None:
    """Emit billing.subscription.plan_changed after upgrade/downgrade."""
    await event_publisher.publish(
      entity_name='subscription',
      action='plan_changed',
      data={
        'subscription_id': subscription_id,
        'user_id': user_id,
        'old_plan_id': old_plan_id,
        'new_plan_id': new_plan_id,
        'new_plan_name': new_plan_name,
        'billing_period': billing_period,
        'changed_at': datetime.now(timezone.utc).isoformat(),
      },
      tenant_id=tenant_id,
    )

  # ------------------------------------------------------------------
  # billing.subscription.cancelled
  # ------------------------------------------------------------------
  async def subscription_cancelled(
    self,
    *,
    subscription_id: str,
    user_id: str = '',
    stripe_subscription_id: str = '',
    cancel_immediately: bool = False,
    tenant_id: Optional[str] = None,
  ) -> None:
    """Emit billing.subscription.cancelled after cancellation."""
    await event_publisher.publish(
      entity_name='subscription',
      action='cancelled',
      data={
        'subscription_id': subscription_id,
        'user_id': user_id,
        'stripe_subscription_id': stripe_subscription_id,
        'cancel_immediately': cancel_immediately,
        'cancelled_at': datetime.now(timezone.utc).isoformat(),
      },
      tenant_id=tenant_id,
    )

  # ------------------------------------------------------------------
  # billing.usage.limit_reached
  # ------------------------------------------------------------------
  async def usage_limit_reached(
    self,
    *,
    user_id: str,
    usage_type: str,
    current: int,
    limit: int,
    plan: str,
    tenant_id: Optional[str] = None,
  ) -> None:
    """Emit billing.usage.limit_reached when a user hits their cap."""
    await event_publisher.publish(
      entity_name='usage',
      action='limit_reached',
      data={
        'user_id': user_id,
        'usage_type': usage_type,
        'current': current,
        'limit': limit,
        'plan': plan,
        'checked_at': datetime.now(timezone.utc).isoformat(),
      },
      tenant_id=tenant_id,
    )


# Global singleton — import and use directly
billing_events = BillingEventProducer()
