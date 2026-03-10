"""Payment Method Management Endpoints.

  - GET  /api/v1/payment-methods/         — list saved payment methods for a user
  - POST /api/v1/payment-methods/setup-intent — create Stripe SetupIntent for adding a card
  - POST /api/v1/payment-methods/default  — set a payment method as default
  - DELETE /api/v1/payment-methods/{pm_id} — detach a payment method
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from billing_service.config import settings
from billing_service.core.database import get_session
from billing_service.application.services.subscription_service import SubscriptionService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Payment Methods'])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class PaymentMethodCard(BaseModel):
  id: str
  brand: str          # visa, mastercard, amex, etc.
  last4: str
  exp_month: int
  exp_year: int
  is_default: bool


class SetupIntentRequest(BaseModel):
  user_id: str


class SetupIntentResponse(BaseModel):
  client_secret: str


class SetDefaultRequest(BaseModel):
  user_id: str
  payment_method_id: str


class SetDefaultResponse(BaseModel):
  status: str
  message: str


class DetachResponse(BaseModel):
  status: str
  message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_stripe_customer_id(
  sub_service: SubscriptionService,
  user_id: str,
) -> Optional[str]:
  """Retrieve the Stripe customer ID from the user's active subscription."""
  results = await sub_service.search_subscriptions(
    domain=[('user_id', '=', user_id)],
    skip=0,
    limit=10,
  )
  for sub in results:
    if getattr(sub, 'stripe_customer_id', None):
      return sub.stripe_customer_id
  return None


async def _get_or_create_stripe_customer(
  sub_service: SubscriptionService,
  user_id: str,
) -> Optional[str]:
  """Get existing Stripe customer ID or create a new customer."""
  import stripe

  customer_id = await _get_stripe_customer_id(sub_service, user_id)
  if customer_id:
    return customer_id

  # Create a new Stripe customer for this user
  try:
    customer = stripe.Customer.create(metadata={'user_id': user_id})
    return customer.id
  except stripe.error.StripeError as e:
    logger.error('stripe_customer_create_failed', error=str(e), user_id=user_id)
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
  '/',
  response_model=List[PaymentMethodCard],
  summary='List Payment Methods',
  description='List saved payment methods for the authenticated user.',
)
async def list_payment_methods(
  user_id: str,
  request: Request,
  session: AsyncSession = Depends(get_session),
):
  """Return all saved card payment methods for the user's Stripe customer."""
  if not settings.stripe_secret_key:
    logger.warning('stripe_not_configured_for_payment_methods')
    return []

  import stripe
  stripe.api_key = settings.stripe_secret_key

  sub_service = SubscriptionService(session)
  customer_id = await _get_stripe_customer_id(sub_service, user_id)
  if not customer_id:
    return []

  try:
    # Retrieve the customer to find the default payment method
    customer = stripe.Customer.retrieve(customer_id)
    default_pm_id = (
      (customer.get('invoice_settings') or {}).get('default_payment_method')
      or customer.get('default_source')
    )

    payment_methods = stripe.PaymentMethod.list(
      customer=customer_id,
      type='card',
    )

    result = []
    for pm in payment_methods.get('data', []):
      card = pm.get('card', {})
      result.append(
        PaymentMethodCard(
          id=pm['id'],
          brand=card.get('brand', 'unknown'),
          last4=card.get('last4', '****'),
          exp_month=card.get('exp_month', 0),
          exp_year=card.get('exp_year', 0),
          is_default=(pm['id'] == default_pm_id),
        )
      )

    return result

  except stripe.error.StripeError as e:
    logger.error('stripe_list_payment_methods_failed', error=str(e), user_id=user_id)
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f'Stripe error: {str(e)}',
    )


@router.post(
  '/setup-intent',
  response_model=SetupIntentResponse,
  summary='Create Setup Intent',
  description='Create a Stripe SetupIntent for securely adding a new payment method.',
)
async def create_setup_intent(
  data: SetupIntentRequest,
  request: Request,
  session: AsyncSession = Depends(get_session),
):
  """Create a SetupIntent so the frontend can collect card details via Stripe Elements."""
  if not settings.stripe_secret_key:
    # Return a mock client secret so the UI can still render
    logger.warning('stripe_not_configured_returning_mock_setup_intent')
    return SetupIntentResponse(
      client_secret='seti_mock_not_configured_secret_test'
    )

  import stripe
  stripe.api_key = settings.stripe_secret_key

  sub_service = SubscriptionService(session)
  customer_id = await _get_or_create_stripe_customer(sub_service, data.user_id)
  if not customer_id:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail='Could not create or retrieve Stripe customer',
    )

  try:
    setup_intent = stripe.SetupIntent.create(
      customer=customer_id,
      payment_method_types=['card'],
      metadata={'user_id': data.user_id},
    )
    return SetupIntentResponse(client_secret=setup_intent.client_secret)

  except stripe.error.StripeError as e:
    logger.error('stripe_setup_intent_failed', error=str(e), user_id=data.user_id)
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f'Stripe error: {str(e)}',
    )


@router.post(
  '/default',
  response_model=SetDefaultResponse,
  summary='Set Default Payment Method',
  description='Set a payment method as the default for future invoices.',
)
async def set_default_payment_method(
  data: SetDefaultRequest,
  request: Request,
  session: AsyncSession = Depends(get_session),
):
  """Update the customer's default invoice payment method in Stripe."""
  if not settings.stripe_secret_key:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail='Stripe is not configured',
    )

  import stripe
  stripe.api_key = settings.stripe_secret_key

  sub_service = SubscriptionService(session)
  customer_id = await _get_stripe_customer_id(sub_service, data.user_id)
  if not customer_id:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail='No Stripe customer found for this user',
    )

  try:
    stripe.Customer.modify(
      customer_id,
      invoice_settings={'default_payment_method': data.payment_method_id},
    )
    logger.info(
      'default_payment_method_set',
      user_id=data.user_id,
      payment_method_id=data.payment_method_id,
    )
    return SetDefaultResponse(
      status='ok',
      message='Default payment method updated',
    )

  except stripe.error.StripeError as e:
    logger.error('stripe_set_default_failed', error=str(e))
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f'Stripe error: {str(e)}',
    )


@router.delete(
  '/{payment_method_id}',
  response_model=DetachResponse,
  summary='Remove Payment Method',
  description='Detach a payment method from the customer, removing it from saved cards.',
)
async def remove_payment_method(
  payment_method_id: str,
  request: Request,
):
  """Detach the given payment method from its Stripe customer."""
  if not settings.stripe_secret_key:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail='Stripe is not configured',
    )

  import stripe
  stripe.api_key = settings.stripe_secret_key

  try:
    stripe.PaymentMethod.detach(payment_method_id)
    logger.info('payment_method_detached', payment_method_id=payment_method_id)
    return DetachResponse(status='ok', message='Payment method removed')

  except stripe.error.StripeError as e:
    logger.error('stripe_detach_failed', error=str(e))
    raise HTTPException(
      status_code=status.HTTP_502_BAD_GATEWAY,
      detail=f'Stripe error: {str(e)}',
    )
