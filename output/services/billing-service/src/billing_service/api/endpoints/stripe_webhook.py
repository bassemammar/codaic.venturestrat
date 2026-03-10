"""Stripe Webhook Endpoint — receives and processes Stripe events.

Public endpoint (no auth) — Stripe sends webhooks directly.
Verifies signature using STRIPE_WEBHOOK_SECRET before processing.

Handled events:
  - checkout.session.completed -> create/activate Subscription
  - customer.subscription.updated -> update Subscription status/plan
  - customer.subscription.deleted -> cancel Subscription
  - invoice.payment_succeeded -> update current_period_end
  - invoice.payment_failed -> set status to past_due
"""

from datetime import datetime, timezone

import stripe
import structlog
from fastapi import APIRouter, HTTPException, Request, status

from billing_service.config import settings
from billing_service.application.services.subscription_service import SubscriptionService
from billing_service.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from billing_service.events.producer import billing_events
from billing_service.integrations.events import event_publisher

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Stripe Webhook'])


async def _find_subscription_by_stripe_id(
  service: SubscriptionService, stripe_subscription_id: str
):
  """Look up a Subscription by its stripe_subscription_id."""
  results = await service.search_subscriptions(
    domain=[('stripe_subscription_id', '=', stripe_subscription_id)],
    skip=0,
    limit=1,
  )
  return results[0] if results else None


async def _find_subscription_by_customer_id(
  service: SubscriptionService, stripe_customer_id: str
):
  """Look up a Subscription by its stripe_customer_id."""
  results = await service.search_subscriptions(
    domain=[('stripe_customer_id', '=', stripe_customer_id)],
    skip=0,
    limit=1,
  )
  return results[0] if results else None


async def _handle_checkout_session_completed(session_obj: dict, service: SubscriptionService):
  """Handle checkout.session.completed — create or activate subscription."""
  stripe_customer_id = session_obj.get('customer')
  stripe_subscription_id = session_obj.get('subscription')
  user_id = (session_obj.get('metadata') or {}).get('user_id', '')
  plan_id = (session_obj.get('metadata') or {}).get('plan_id', '')
  billing_period = (session_obj.get('metadata') or {}).get('billing_period', 'monthly')

  if not stripe_subscription_id:
    logger.warning('checkout_session_no_subscription', session_id=session_obj.get('id'))
    return

  # Check if subscription already exists
  existing = await _find_subscription_by_stripe_id(service, stripe_subscription_id)
  if existing:
    # Activate existing subscription
    update_data = SubscriptionUpdate(
      status='active',
      stripe_customer_id=stripe_customer_id,
    )
    await service.update_subscription(existing.id, update_data)
    logger.info(
      'subscription_activated',
      subscription_id=existing.id,
      stripe_subscription_id=stripe_subscription_id,
    )
    await billing_events.subscription_activated(
      subscription_id=existing.id,
      user_id=getattr(existing, 'user_id', ''),
      plan_id=getattr(existing, 'plan_id', ''),
      stripe_subscription_id=stripe_subscription_id,
      stripe_customer_id=stripe_customer_id or '',
      billing_period=getattr(existing, 'billing_period', '') or 'monthly',
      status='active',
    )
    return

  # Create new subscription
  create_data = SubscriptionCreate(
    user_id=user_id,
    plan_id=plan_id,
    status='active',
    stripe_customer_id=stripe_customer_id,
    stripe_subscription_id=stripe_subscription_id,
    billing_period=billing_period,
  )
  created = await service.create_subscription(create_data)
  logger.info(
    'subscription_created_from_checkout',
    subscription_id=created.id,
    stripe_subscription_id=stripe_subscription_id,
  )
  await billing_events.subscription_activated(
    subscription_id=created.id,
    user_id=user_id,
    plan_id=plan_id,
    stripe_subscription_id=stripe_subscription_id or '',
    stripe_customer_id=stripe_customer_id or '',
    billing_period=billing_period,
    status='active',
  )


async def _handle_subscription_updated(sub_obj: dict, service: SubscriptionService):
  """Handle customer.subscription.updated — update status/plan."""
  stripe_subscription_id = sub_obj.get('id', '')
  existing = await _find_subscription_by_stripe_id(service, stripe_subscription_id)
  if not existing:
    logger.warning(
      'subscription_not_found_for_update',
      stripe_subscription_id=stripe_subscription_id,
    )
    return

  new_status = sub_obj.get('status', existing.status)
  cancel_at_period_end = sub_obj.get('cancel_at_period_end', False)

  # Map Stripe status to our status values
  status_map = {
    'active': 'active',
    'past_due': 'past_due',
    'canceled': 'cancelled',
    'unpaid': 'past_due',
    'trialing': 'trialing',
    'incomplete': 'incomplete',
    'incomplete_expired': 'expired',
    'paused': 'paused',
  }
  mapped_status = status_map.get(new_status, new_status)

  update_data = SubscriptionUpdate(
    status=mapped_status,
    cancel_at_period_end=cancel_at_period_end,
  )

  # Update current_period_end if present
  current_period_end_ts = sub_obj.get('current_period_end')
  if current_period_end_ts:
    update_data.current_period_end = datetime.fromtimestamp(
      current_period_end_ts, tz=timezone.utc
    )

  await service.update_subscription(existing.id, update_data)
  logger.info(
    'subscription_updated_from_stripe',
    subscription_id=existing.id,
    new_status=mapped_status,
  )
  # Publish generic update event (covers status changes, period updates)
  await event_publisher.publish(
    entity_name='subscription',
    action='updated',
    data={
      'subscription_id': existing.id,
      'user_id': getattr(existing, 'user_id', ''),
      'new_status': mapped_status,
      'cancel_at_period_end': cancel_at_period_end,
      'stripe_subscription_id': stripe_subscription_id,
    },
  )


async def _handle_subscription_deleted(sub_obj: dict, service: SubscriptionService):
  """Handle customer.subscription.deleted — set status to cancelled."""
  stripe_subscription_id = sub_obj.get('id', '')
  existing = await _find_subscription_by_stripe_id(service, stripe_subscription_id)
  if not existing:
    logger.warning(
      'subscription_not_found_for_deletion',
      stripe_subscription_id=stripe_subscription_id,
    )
    return

  update_data = SubscriptionUpdate(status='cancelled')
  await service.update_subscription(existing.id, update_data)
  logger.info(
    'subscription_cancelled_from_stripe',
    subscription_id=existing.id,
  )
  await billing_events.subscription_cancelled(
    subscription_id=existing.id,
    user_id=getattr(existing, 'user_id', ''),
    stripe_subscription_id=stripe_subscription_id,
    cancel_immediately=True,
  )


async def _handle_invoice_payment_succeeded(invoice_obj: dict, service: SubscriptionService):
  """Handle invoice.payment_succeeded — update current_period_end."""
  stripe_subscription_id = invoice_obj.get('subscription')
  if not stripe_subscription_id:
    return

  existing = await _find_subscription_by_stripe_id(service, stripe_subscription_id)
  if not existing:
    logger.warning(
      'subscription_not_found_for_invoice',
      stripe_subscription_id=stripe_subscription_id,
    )
    return

  # Get the subscription period end from the invoice lines
  lines = invoice_obj.get('lines', {}).get('data', [])
  period_end = None
  for line in lines:
    period = line.get('period', {})
    end_ts = period.get('end')
    if end_ts:
      period_end = datetime.fromtimestamp(end_ts, tz=timezone.utc)
      break

  update_fields = {'status': 'active'}
  if period_end:
    update_fields['current_period_end'] = period_end

  update_data = SubscriptionUpdate(**update_fields)
  await service.update_subscription(existing.id, update_data)
  logger.info(
    'subscription_payment_succeeded',
    subscription_id=existing.id,
  )


async def _handle_invoice_payment_failed(invoice_obj: dict, service: SubscriptionService):
  """Handle invoice.payment_failed — set status to past_due."""
  stripe_subscription_id = invoice_obj.get('subscription')
  if not stripe_subscription_id:
    return

  existing = await _find_subscription_by_stripe_id(service, stripe_subscription_id)
  if not existing:
    logger.warning(
      'subscription_not_found_for_failed_invoice',
      stripe_subscription_id=stripe_subscription_id,
    )
    return

  update_data = SubscriptionUpdate(status='past_due')
  await service.update_subscription(existing.id, update_data)
  logger.info(
    'subscription_payment_failed',
    subscription_id=existing.id,
  )


@router.post(
  '/stripe/webhook',
  status_code=status.HTTP_200_OK,
  summary='Stripe Webhook',
  description='Receives Stripe webhook events. Public endpoint — no auth required.',
  responses={
    200: {'description': 'Event processed'},
    400: {'description': 'Invalid payload or signature'},
  },
)
async def stripe_webhook(request: Request):
  """Process incoming Stripe webhook events.

  Reads raw body for signature verification, then dispatches
  to the appropriate handler based on event type.
  """
  payload = await request.body()
  sig_header = request.headers.get('stripe-signature', '')

  if not settings.stripe_webhook_secret:
    logger.error('stripe_webhook_secret_not_configured')
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Webhook secret not configured',
    )

  try:
    event = stripe.Webhook.construct_event(
      payload, sig_header, settings.stripe_webhook_secret
    )
  except ValueError:
    logger.warning('stripe_webhook_invalid_payload')
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail='Invalid payload',
    )
  except stripe.error.SignatureVerificationError:
    logger.warning('stripe_webhook_invalid_signature')
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail='Invalid signature',
    )

  event_type = event.get('type', '')
  event_data = event.get('data', {}).get('object', {})

  logger.info('stripe_webhook_received', event_type=event_type, event_id=event.get('id'))

  service = SubscriptionService()

  handlers = {
    'checkout.session.completed': _handle_checkout_session_completed,
    'customer.subscription.updated': _handle_subscription_updated,
    'customer.subscription.deleted': _handle_subscription_deleted,
    'invoice.payment_succeeded': _handle_invoice_payment_succeeded,
    'invoice.payment_failed': _handle_invoice_payment_failed,
  }

  handler = handlers.get(event_type)
  if handler:
    try:
      await handler(event_data, service)
    except Exception as e:
      logger.error(
        'stripe_webhook_handler_failed',
        event_type=event_type,
        error=str(e),
      )
      # Return 200 to prevent Stripe retries for application errors
      # Log the error for investigation
      return {'status': 'error', 'message': str(e)}
  else:
    logger.debug('stripe_webhook_unhandled_event', event_type=event_type)

  return {'status': 'ok'}
