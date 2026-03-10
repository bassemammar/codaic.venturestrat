"""Subscription Management Endpoints — subscribe, change-plan, cancel, usage.

Custom business logic endpoints beyond generated CRUD:
  - POST /subscriptions/subscribe — create Stripe checkout session
  - POST /subscriptions/change-plan — upgrade/downgrade plan
  - POST /subscriptions/cancel — cancel subscription
  - POST /subscriptions/validate-usage — check if action is allowed
  - POST /subscriptions/track-usage — increment usage counter
"""

from datetime import date, datetime
from typing import Optional

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from billing_service.config import settings
from billing_service.core.database import get_session
from billing_service.application.services.subscription_service import SubscriptionService
from billing_service.application.services.plan_service import PlanService
from billing_service.application.services.usage_record_service import UsageRecordService
from billing_service.schemas.subscription import SubscriptionUpdate
from billing_service.schemas.usage_record import UsageRecordCreate
from billing_service.events.producer import billing_events

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Subscription Management'])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SubscribeRequest(BaseModel):
  """Request body for creating a Stripe checkout session."""
  plan_id: Optional[str] = Field(None, description='Plan UUID')
  plan_code: Optional[str] = Field(None, description='Plan code (alternative to plan_id)')
  billing_period: str = Field(
    default='monthly',
    description='Billing period: monthly, quarterly, annually',
  )
  success_url: str = Field(
    default='http://localhost:5178/billing/success',
    description='URL to redirect after successful checkout',
  )
  cancel_url: str = Field(
    default='http://localhost:5178/billing/cancel',
    description='URL to redirect if user cancels checkout',
  )


class SubscribeResponse(BaseModel):
  """Response with Stripe checkout URL."""
  checkout_url: str
  session_id: str


class ChangePlanRequest(BaseModel):
  """Request body for changing subscription plan."""
  new_plan_id: Optional[str] = Field(None, description='New plan UUID')
  new_plan_code: Optional[str] = Field(None, description='New plan code (alternative)')
  billing_period: Optional[str] = Field(None, description='New billing period')


class ChangePlanResponse(BaseModel):
  """Response after plan change."""
  status: str
  message: str
  subscription_id: str


class CancelRequest(BaseModel):
  """Request body for subscription cancellation."""
  subscription_id: Optional[str] = Field(
    default=None,
    description='Subscription UUID to cancel. If omitted, cancels the caller\'s active subscription.',
  )
  cancel_at_period_end: bool = Field(
    default=True,
    description='If true (recommended), cancel at end of current period. If false, cancel immediately.',
  )


class CancelResponse(BaseModel):
  """Response after cancellation."""
  status: str
  message: str
  cancel_at_period_end: bool
  subscription: Optional[dict] = Field(default=None, description='Updated subscription record')


class ValidateUsageRequest(BaseModel):
  """Request body for usage validation."""
  user_id: str
  usage_type: str = Field(
    description='Usage type: ai_drafts, emails, investors, follow_ups',
  )


class ValidateUsageResponse(BaseModel):
  """Response for usage validation check."""
  allowed: bool
  current: int
  limit: int
  plan: str
  usage_type: str


class TrackUsageRequest(BaseModel):
  """Request body for tracking usage."""
  user_id: str
  usage_type: str = Field(
    description='Usage type: ai_drafts, emails, investors, follow_ups',
  )
  increment: int = Field(default=1, ge=1, description='Amount to increment')


class TrackUsageResponse(BaseModel):
  """Response after tracking usage."""
  user_id: str
  usage_type: str
  current: int
  date: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Maps usage_type to (daily counter field, monthly counter field, daily limit key, monthly limit key)
USAGE_TYPE_MAP = {
  'ai_drafts': ('ai_drafts_used', None, 'ai_drafts_per_day', None),
  'emails': ('emails_sent', 'monthly_emails_sent', 'emails_per_day', 'emails_per_month'),
  'investors': ('investors_added', 'monthly_investors_added', 'investors_per_day', 'investors_per_month'),
  'follow_ups': (None, 'monthly_follow_ups_sent', None, 'follow_ups_per_month'),
}


def _get_price_for_period(plan_data, billing_period: str):
  """Get the price field value for the given billing period."""
  period_price_map = {
    'monthly': 'price_monthly',
    'quarterly': 'price_quarterly',
    'annually': 'price_annually',
  }
  price_field = period_price_map.get(billing_period, 'price_monthly')
  price = getattr(plan_data, price_field, None) or getattr(plan_data, 'price_monthly', 0)
  return price


async def _resolve_plan(plan_service: PlanService, plan_id: str = None, plan_code: str = None):
  """Resolve a plan by ID or code."""
  if plan_id:
    plan = await plan_service.get_plan(plan_id)
    if plan:
      return plan

  if plan_code:
    results = await plan_service.search_plans(
      domain=[('code', '=', plan_code)],
      skip=0,
      limit=1,
    )
    if results:
      return results[0]

  return None


async def _get_active_subscription(sub_service: SubscriptionService, user_id: str):
  """Get the active subscription for a user."""
  results = await sub_service.search_subscriptions(
    domain=[('user_id', '=', user_id)],
    skip=0,
    limit=1,
  )
  return results[0] if results else None


async def _get_or_create_usage_record(
  usage_service: UsageRecordService, user_id: str, today: date
):
  """Get today's usage record for user, or create one if it doesn't exist."""
  results = await usage_service.search_usage_records(
    domain=[
      ('user_id', '=', user_id),
      ('date', '=', str(today)),
    ],
    skip=0,
    limit=1,
  )
  if results:
    return results[0]

  # Create a new record for today
  create_data = UsageRecordCreate(
    user_id=user_id,
    date=today,
    month=today.month,
    year=today.year,
    ai_drafts_used=0,
    emails_sent=0,
    investors_added=0,
    monthly_emails_sent=0,
    monthly_investors_added=0,
    monthly_follow_ups_sent=0,
  )
  return await usage_service.create_usage_record(create_data)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
  '/subscribe',
  response_model=SubscribeResponse,
  status_code=status.HTTP_200_OK,
  summary='Create Stripe Checkout Session',
  description='Creates a Stripe checkout session and returns the URL for frontend redirect.',
)
async def subscribe(
  data: SubscribeRequest,
  request: Request,
  session: AsyncSession = Depends(get_session),
):
  """Create a Stripe checkout session for subscribing to a plan."""
  plan_service = PlanService(session)
  plan = await _resolve_plan(plan_service, data.plan_id, data.plan_code)
  if not plan:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail='Plan not found',
    )

  if not plan.is_active:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail='Plan is not active',
    )

  price = _get_price_for_period(plan, data.billing_period)

  # Extract user_id from request state (set by auth middleware) or metadata
  user_id = getattr(request.state, 'user_id', None) or ''

  if not settings.stripe_secret_key:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Stripe is not configured',
    )

  stripe.api_key = settings.stripe_secret_key

  try:
    checkout_session = stripe.checkout.Session.create(
      payment_method_types=['card'],
      line_items=[{
        'price_data': {
          'currency': 'usd',
          'product_data': {
            'name': plan.name,
            'description': f'{plan.name} — {data.billing_period}',
          },
          'unit_amount': int(float(price) * 100),  # Stripe uses cents
          'recurring': {
            'interval': {
              'monthly': 'month',
              'quarterly': 'month',
              'annually': 'year',
            }.get(data.billing_period, 'month'),
            'interval_count': 3 if data.billing_period == 'quarterly' else 1,
          },
        },
        'quantity': 1,
      }],
      mode='subscription',
      success_url=data.success_url + '?session_id={CHECKOUT_SESSION_ID}',
      cancel_url=data.cancel_url,
      metadata={
        'user_id': user_id,
        'plan_id': plan.id,
        'billing_period': data.billing_period,
      },
    )

    logger.info(
      'checkout_session_created',
      session_id=checkout_session.id,
      plan_id=plan.id,
      user_id=user_id,
    )

    return SubscribeResponse(
      checkout_url=checkout_session.url,
      session_id=checkout_session.id,
    )

  except stripe.error.StripeError as e:
    logger.error('stripe_checkout_failed', error=str(e))
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f'Stripe error: {str(e)}',
    )


@router.post(
  '/change-plan',
  response_model=ChangePlanResponse,
  summary='Change Subscription Plan',
  description='Upgrade or downgrade the current subscription plan.',
)
async def change_plan(
  data: ChangePlanRequest,
  request: Request,
  session: AsyncSession = Depends(get_session),
):
  """Change the plan for an existing subscription."""
  user_id = getattr(request.state, 'user_id', None) or ''
  if not user_id:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail='User ID required',
    )

  sub_service = SubscriptionService(session)
  plan_service = PlanService(session)

  subscription = await _get_active_subscription(sub_service, user_id)
  if not subscription:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail='No active subscription found',
    )

  new_plan = await _resolve_plan(plan_service, data.new_plan_id, data.new_plan_code)
  if not new_plan:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail='New plan not found',
    )

  if not new_plan.is_active:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail='New plan is not active',
    )

  # If the subscription has a Stripe subscription, update it there too
  if subscription.stripe_subscription_id and settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key
    try:
      stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
      stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        metadata={'plan_id': new_plan.id},
        proration_behavior='create_prorations',
      )
    except stripe.error.StripeError as e:
      logger.error('stripe_plan_change_failed', error=str(e))
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f'Stripe error: {str(e)}',
      )

  # Update local subscription record
  update_fields = {'plan_id': new_plan.id}
  if data.billing_period:
    update_fields['billing_period'] = data.billing_period

  update_data = SubscriptionUpdate(**update_fields)
  await sub_service.update_subscription(subscription.id, update_data)

  logger.info(
    'subscription_plan_changed',
    subscription_id=subscription.id,
    new_plan_id=new_plan.id,
    user_id=user_id,
  )

  return ChangePlanResponse(
    status='ok',
    message=f'Plan changed to {new_plan.name}',
    subscription_id=subscription.id,
  )


@router.post(
  '/cancel',
  response_model=CancelResponse,
  summary='Cancel Subscription',
  description='Cancel the current subscription (at period end or immediately).',
)
async def cancel_subscription(
  data: CancelRequest,
  request: Request,
  session: AsyncSession = Depends(get_session),
):
  """Cancel the user's subscription.

  If cancel_at_period_end=True (default/recommended), marks the subscription as
  'canceling' and it will expire naturally at current_period_end.
  If cancel_at_period_end=False, cancels immediately and sets status='canceled'.
  """
  user_id = getattr(request.state, 'user_id', None) or ''
  if not user_id:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail='User ID required',
    )

  sub_service = SubscriptionService(session)

  # Resolve subscription — by explicit ID or fall back to caller's active subscription
  if data.subscription_id:
    subscription = await sub_service.get_subscription(data.subscription_id)
    if not subscription:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='Subscription not found',
      )
    # Ensure the subscription belongs to the requesting user
    if subscription.user_id != user_id:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='Not authorized to cancel this subscription',
      )
  else:
    subscription = await _get_active_subscription(sub_service, user_id)
    if not subscription:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='No active subscription found',
      )

  # Cancel in Stripe if configured
  if subscription.stripe_subscription_id and settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key
    try:
      if data.cancel_at_period_end:
        stripe.Subscription.modify(
          subscription.stripe_subscription_id,
          cancel_at_period_end=True,
        )
      else:
        stripe.Subscription.cancel(subscription.stripe_subscription_id)
    except stripe.error.StripeError as e:
      logger.error('stripe_cancel_failed', error=str(e))
      raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f'Stripe error: {str(e)}',
      )

  # Update local record
  if data.cancel_at_period_end:
    # Mark as canceling — retains access until period end
    update_data = SubscriptionUpdate(
      status='canceling',
      cancel_at_period_end=True,
    )
    message = 'Subscription will cancel at end of billing period'
  else:
    # Cancel immediately
    update_data = SubscriptionUpdate(
      status='canceled',
      cancel_at_period_end=False,
    )
    message = 'Subscription cancelled immediately'

  updated = await sub_service.update_subscription(subscription.id, update_data)

  logger.info(
    'subscription_cancelled',
    subscription_id=subscription.id,
    cancel_at_period_end=data.cancel_at_period_end,
    user_id=user_id,
  )

  # Serialize updated subscription for response
  sub_dict = None
  if updated:
    try:
      sub_dict = {
        'id': str(updated.id),
        'user_id': str(updated.user_id),
        'plan_id': str(updated.plan_id),
        'status': updated.status,
        'cancel_at_period_end': updated.cancel_at_period_end,
        'current_period_end': updated.current_period_end.isoformat() if updated.current_period_end else None,
        'billing_period': updated.billing_period,
        'stripe_customer_id': updated.stripe_customer_id,
        'stripe_subscription_id': updated.stripe_subscription_id,
      }
    except Exception:
      pass

  return CancelResponse(
    status='ok',
    message=message,
    cancel_at_period_end=data.cancel_at_period_end,
    subscription=sub_dict,
  )


@router.post(
  '/validate-usage',
  response_model=ValidateUsageResponse,
  summary='Validate Usage',
  description='Check if a user is allowed to perform an action based on plan limits.',
)
async def validate_usage(
  data: ValidateUsageRequest,
  session: AsyncSession = Depends(get_session),
):
  """Validate whether a usage action is allowed for the user's plan.

  Looks up the user's active subscription, resolves the plan limits,
  and checks the current usage record for today.
  """
  if data.usage_type not in USAGE_TYPE_MAP:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f'Invalid usage_type. Allowed: {", ".join(USAGE_TYPE_MAP.keys())}',
    )

  sub_service = SubscriptionService(session)
  plan_service = PlanService(session)
  usage_service = UsageRecordService(session)

  subscription = await _get_active_subscription(sub_service, data.user_id)
  if not subscription:
    return ValidateUsageResponse(
      allowed=False, current=0, limit=0, plan='none', usage_type=data.usage_type,
    )

  plan = await plan_service.get_plan(subscription.plan_id)
  if not plan:
    return ValidateUsageResponse(
      allowed=False, current=0, limit=0, plan='unknown', usage_type=data.usage_type,
    )

  limits = plan.limits if isinstance(plan.limits, dict) else {}
  usage_basis = getattr(plan, 'usage_basis', 'daily')

  daily_field, monthly_field, daily_limit_key, monthly_limit_key = USAGE_TYPE_MAP[data.usage_type]

  # Determine which counter and limit to check based on usage_basis
  if usage_basis == 'monthly' and monthly_limit_key and monthly_field:
    limit_key = monthly_limit_key
    counter_field = monthly_field
  elif daily_limit_key and daily_field:
    limit_key = daily_limit_key
    counter_field = daily_field
  elif monthly_limit_key and monthly_field:
    limit_key = monthly_limit_key
    counter_field = monthly_field
  else:
    # No limit configured for this type
    return ValidateUsageResponse(
      allowed=True, current=0, limit=-1, plan=plan.name, usage_type=data.usage_type,
    )

  limit_value = limits.get(limit_key, -1)
  if limit_value == -1:
    # Unlimited
    return ValidateUsageResponse(
      allowed=True, current=0, limit=-1, plan=plan.name, usage_type=data.usage_type,
    )

  today = date.today()
  usage_record = await _get_or_create_usage_record(usage_service, data.user_id, today)

  current_value = getattr(usage_record, counter_field, 0) or 0
  allowed = current_value < limit_value

  if not allowed:
    await billing_events.usage_limit_reached(
      user_id=data.user_id,
      usage_type=data.usage_type,
      current=current_value,
      limit=limit_value,
      plan=plan.name,
    )

  return ValidateUsageResponse(
    allowed=allowed,
    current=current_value,
    limit=limit_value,
    plan=plan.name,
    usage_type=data.usage_type,
  )


@router.post(
  '/track-usage',
  response_model=TrackUsageResponse,
  summary='Track Usage',
  description='Increment a usage counter for the user for today.',
)
async def track_usage(
  data: TrackUsageRequest,
  session: AsyncSession = Depends(get_session),
):
  """Increment a usage counter for the user.

  Upserts a UsageRecord for today (user_id + date composite)
  and increments the appropriate counter field.
  """
  if data.usage_type not in USAGE_TYPE_MAP:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f'Invalid usage_type. Allowed: {", ".join(USAGE_TYPE_MAP.keys())}',
    )

  usage_service = UsageRecordService(session)
  today = date.today()
  usage_record = await _get_or_create_usage_record(usage_service, data.user_id, today)

  daily_field, monthly_field, _, _ = USAGE_TYPE_MAP[data.usage_type]

  # Increment the daily counter
  new_daily_value = 0
  if daily_field:
    current = getattr(usage_record, daily_field, 0) or 0
    new_daily_value = current + data.increment

  # Increment the monthly counter
  new_monthly_value = 0
  if monthly_field:
    current_monthly = getattr(usage_record, monthly_field, 0) or 0
    new_monthly_value = current_monthly + data.increment

  # Build update dict
  from billing_service.schemas.usage_record import UsageRecordUpdate
  update_fields = {}
  if daily_field:
    update_fields[daily_field] = new_daily_value
  if monthly_field:
    update_fields[monthly_field] = new_monthly_value

  if update_fields:
    update_data = UsageRecordUpdate(**update_fields)
    await usage_service.update_usage_record(usage_record.id, update_data)

  # Return the primary counter value
  primary_value = new_daily_value if daily_field else new_monthly_value

  logger.info(
    'usage_tracked',
    user_id=data.user_id,
    usage_type=data.usage_type,
    increment=data.increment,
    new_value=primary_value,
  )

  return TrackUsageResponse(
    user_id=data.user_id,
    usage_type=data.usage_type,
    current=primary_value,
    date=str(today),
  )
