"""Integration tests for the Stripe webhook + subscription lifecycle in billing-service.

Covers the full subscription lifecycle via Stripe webhooks:
  1. Create a Plan in the mock DB
  2. checkout.session.completed -> create/activate Subscription
  3. customer.subscription.updated -> status change
  4. invoice.payment_succeeded -> period updated
  5. invoice.payment_failed -> past_due status
  6. customer.subscription.deleted -> cancelled

Also tests validate-usage and track-usage endpoints end-to-end.

All Stripe signature verification and Kafka event publishing are mocked.
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------

def _mock_plan(
  id='plan-001',
  name='Pro',
  code='pro',
  price_monthly='29.00',
  price_quarterly='79.00',
  price_annually='290.00',
  limits=None,
  features=None,
  usage_basis='daily',
  is_active=True,
):
  plan = MagicMock()
  plan.id = id
  plan.name = name
  plan.code = code
  plan.price_monthly = price_monthly
  plan.price_quarterly = price_quarterly
  plan.price_annually = price_annually
  plan.limits = limits or {
    'ai_drafts_per_day': 10,
    'emails_per_day': 50,
    'emails_per_month': 1000,
    'investors_per_day': 20,
    'investors_per_month': 500,
    'follow_ups_per_month': 200,
  }
  plan.features = features or {}
  plan.usage_basis = usage_basis
  plan.is_active = is_active
  return plan


def _mock_subscription(
  id=None,
  user_id='user-123',
  plan_id='plan-001',
  status='active',
  stripe_customer_id='cus_abc',
  stripe_subscription_id='sub_stripe_001',
  cancel_at_period_end=False,
  billing_period='monthly',
  current_period_end=None,
):
  sub = MagicMock()
  sub.id = id or str(uuid4())
  sub.user_id = user_id
  sub.plan_id = plan_id
  sub.status = status
  sub.stripe_customer_id = stripe_customer_id
  sub.stripe_subscription_id = stripe_subscription_id
  sub.stripe_payment_method_id = None
  sub.billing_period = billing_period
  sub.current_period_end = current_period_end
  sub.cancel_at_period_end = cancel_at_period_end
  sub.trial_ends_at = None
  return sub


def _mock_usage_record(
  id=None,
  user_id='user-123',
  ai_drafts_used=0,
  emails_sent=0,
  investors_added=0,
  monthly_emails_sent=0,
  monthly_investors_added=0,
  monthly_follow_ups_sent=0,
):
  rec = MagicMock()
  rec.id = id or str(uuid4())
  rec.user_id = user_id
  rec.date = date.today()
  rec.month = date.today().month
  rec.year = date.today().year
  rec.ai_drafts_used = ai_drafts_used
  rec.emails_sent = emails_sent
  rec.investors_added = investors_added
  rec.monthly_emails_sent = monthly_emails_sent
  rec.monthly_investors_added = monthly_investors_added
  rec.monthly_follow_ups_sent = monthly_follow_ups_sent
  return rec


def _build_stripe_event(event_type, event_data, event_id=None):
  """Build a dict that looks like stripe.Webhook.construct_event output."""
  return {
    'id': event_id or f'evt_{uuid4().hex[:12]}',
    'type': event_type,
    'data': {'object': event_data},
  }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
  import os
  os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
  os.environ.setdefault('PLATFORM_MODE', 'standalone')
  os.environ.setdefault('LOG_LEVEL', 'WARNING')
  from billing_service.main import app
  return TestClient(app)


# ---------------------------------------------------------------------------
# Integration Test: Full subscription lifecycle via Stripe webhooks
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestStripeSubscriptionLifecycle:
  """Tests the complete subscription lifecycle through Stripe webhooks."""

  def _post_webhook(self, client, event_type, event_data, mock_construct, mock_settings, service_instance):
    """Helper to post a webhook event."""
    mock_settings.stripe_webhook_secret = 'whsec_test'
    mock_construct.return_value = _build_stripe_event(event_type, event_data)

    return client.post(
      '/api/v1/stripe/webhook',
      content=b'raw_payload',
      headers={'stripe-signature': 'sig_test'},
    )

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_step1_checkout_session_completed_creates_subscription(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Step 1: checkout.session.completed creates a new subscription."""
    svc = MockSubService.return_value
    svc.search_subscriptions = AsyncMock(return_value=[])  # No existing
    created_sub = _mock_subscription(
      id='sub-new',
      user_id='user-456',
      stripe_subscription_id='sub_stripe_new',
    )
    svc.create_subscription = AsyncMock(return_value=created_sub)

    resp = self._post_webhook(client, 'checkout.session.completed', {
      'id': 'cs_123',
      'customer': 'cus_new',
      'subscription': 'sub_stripe_new',
      'metadata': {
        'user_id': 'user-456',
        'plan_id': 'plan-001',
        'billing_period': 'monthly',
      },
    }, mock_construct, mock_settings, svc)

    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'
    svc.create_subscription.assert_called_once()
    create_args = svc.create_subscription.call_args[0][0]
    assert create_args.user_id == 'user-456'
    assert create_args.plan_id == 'plan-001'
    assert create_args.status == 'active'
    assert create_args.stripe_subscription_id == 'sub_stripe_new'

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_step2_checkout_activates_existing_subscription(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Step 2: checkout.session.completed activates an existing subscription."""
    existing = _mock_subscription(id='sub-existing', stripe_subscription_id='sub_stripe_001')
    svc = MockSubService.return_value
    svc.search_subscriptions = AsyncMock(return_value=[existing])
    svc.update_subscription = AsyncMock(return_value=existing)

    resp = self._post_webhook(client, 'checkout.session.completed', {
      'id': 'cs_456',
      'customer': 'cus_abc',
      'subscription': 'sub_stripe_001',
      'metadata': {'user_id': 'user-123', 'plan_id': 'plan-001'},
    }, mock_construct, mock_settings, svc)

    assert resp.status_code == 200
    svc.update_subscription.assert_called_once()
    update_args = svc.update_subscription.call_args[0]
    assert update_args[0] == 'sub-existing'  # subscription id
    assert update_args[1].status == 'active'

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_step3_subscription_updated_changes_status(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Step 3: customer.subscription.updated maps Stripe status + period."""
    existing = _mock_subscription(id='sub-001', stripe_subscription_id='sub_stripe_001')
    svc = MockSubService.return_value
    svc.search_subscriptions = AsyncMock(return_value=[existing])
    svc.update_subscription = AsyncMock(return_value=existing)

    resp = self._post_webhook(client, 'customer.subscription.updated', {
      'id': 'sub_stripe_001',
      'status': 'past_due',
      'cancel_at_period_end': True,
      'current_period_end': 1735689600,  # 2025-01-01
    }, mock_construct, mock_settings, svc)

    assert resp.status_code == 200
    update_data = svc.update_subscription.call_args[0][1]
    assert update_data.status == 'past_due'
    assert update_data.cancel_at_period_end is True
    assert update_data.current_period_end is not None

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_step4_invoice_payment_succeeded_updates_period(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Step 4: invoice.payment_succeeded sets active + updates period."""
    existing = _mock_subscription(id='sub-001', stripe_subscription_id='sub_stripe_001')
    svc = MockSubService.return_value
    svc.search_subscriptions = AsyncMock(return_value=[existing])
    svc.update_subscription = AsyncMock(return_value=existing)

    resp = self._post_webhook(client, 'invoice.payment_succeeded', {
      'subscription': 'sub_stripe_001',
      'lines': {
        'data': [{
          'period': {'end': 1738368000},  # 2025-02-01
        }],
      },
    }, mock_construct, mock_settings, svc)

    assert resp.status_code == 200
    update_data = svc.update_subscription.call_args[0][1]
    assert update_data.status == 'active'
    assert update_data.current_period_end is not None
    assert update_data.current_period_end.year == 2025

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_step5_invoice_payment_failed_sets_past_due(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Step 5: invoice.payment_failed sets status to past_due."""
    existing = _mock_subscription(id='sub-001', stripe_subscription_id='sub_stripe_001')
    svc = MockSubService.return_value
    svc.search_subscriptions = AsyncMock(return_value=[existing])
    svc.update_subscription = AsyncMock(return_value=existing)

    resp = self._post_webhook(client, 'invoice.payment_failed', {
      'subscription': 'sub_stripe_001',
    }, mock_construct, mock_settings, svc)

    assert resp.status_code == 200
    update_data = svc.update_subscription.call_args[0][1]
    assert update_data.status == 'past_due'

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_step6_subscription_deleted_cancels(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Step 6: customer.subscription.deleted sets status to cancelled."""
    existing = _mock_subscription(id='sub-001', stripe_subscription_id='sub_stripe_001')
    svc = MockSubService.return_value
    svc.search_subscriptions = AsyncMock(return_value=[existing])
    svc.update_subscription = AsyncMock(return_value=existing)

    resp = self._post_webhook(client, 'customer.subscription.deleted', {
      'id': 'sub_stripe_001',
    }, mock_construct, mock_settings, svc)

    assert resp.status_code == 200
    update_data = svc.update_subscription.call_args[0][1]
    assert update_data.status == 'cancelled'

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_subscription_not_found_handled_gracefully(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Webhook for unknown subscription should not error (200 ok)."""
    svc = MockSubService.return_value
    svc.search_subscriptions = AsyncMock(return_value=[])  # Not found

    resp = self._post_webhook(client, 'customer.subscription.deleted', {
      'id': 'sub_stripe_unknown',
    }, mock_construct, mock_settings, svc)

    assert resp.status_code == 200
    svc.update_subscription.assert_not_called()

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  def test_missing_webhook_secret_returns_500(self, mock_settings, client):
    mock_settings.stripe_webhook_secret = ''
    resp = client.post(
      '/api/v1/stripe/webhook',
      content=b'body',
      headers={'stripe-signature': 'sig'},
    )
    assert resp.status_code == 500

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  def test_invalid_signature_returns_400(self, mock_settings, client):
    mock_settings.stripe_webhook_secret = 'whsec_test'
    # Without mocking construct_event, the real Stripe lib will reject
    resp = client.post(
      '/api/v1/stripe/webhook',
      content=b'invalid_body',
      headers={'stripe-signature': 'bad_sig'},
    )
    assert resp.status_code == 400

  @patch('billing_service.api.endpoints.stripe_webhook.settings')
  @patch('billing_service.api.endpoints.stripe_webhook.stripe.Webhook.construct_event')
  @patch('billing_service.api.endpoints.stripe_webhook.SubscriptionService')
  def test_unhandled_event_type_returns_ok(
    self, MockSubService, mock_construct, mock_settings, client
  ):
    """Unhandled event types should return 200 without processing."""
    mock_settings.stripe_webhook_secret = 'whsec_test'
    mock_construct.return_value = _build_stripe_event('customer.source.created', {})

    resp = client.post(
      '/api/v1/stripe/webhook',
      content=b'raw_body',
      headers={'stripe-signature': 'sig_test'},
    )
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'


# ---------------------------------------------------------------------------
# Integration Test: Validate usage
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestValidateUsageIntegration:
  """Validate-usage integration tests with active subscription."""

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  @patch('billing_service.api.endpoints.subscription_manage.PlanService')
  @patch('billing_service.api.endpoints.subscription_manage.SubscriptionService')
  def test_validate_usage_allowed(self, MockSubSvc, MockPlanSvc, MockUsageSvc, client):
    """Usage under limit should be allowed."""
    sub = _mock_subscription()
    MockSubSvc.return_value.search_subscriptions = AsyncMock(return_value=[sub])

    plan = _mock_plan()
    MockPlanSvc.return_value.get_plan = AsyncMock(return_value=plan)

    usage = _mock_usage_record(ai_drafts_used=3)  # limit is 10
    MockUsageSvc.return_value.search_usage_records = AsyncMock(return_value=[usage])

    resp = client.post('/api/v1/subscriptions/validate-usage', json={
      'user_id': 'user-123',
      'usage_type': 'ai_drafts',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['allowed'] is True
    assert data['current'] == 3
    assert data['limit'] == 10
    assert data['plan'] == 'Pro'

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  @patch('billing_service.api.endpoints.subscription_manage.PlanService')
  @patch('billing_service.api.endpoints.subscription_manage.SubscriptionService')
  def test_validate_usage_denied_at_limit(self, MockSubSvc, MockPlanSvc, MockUsageSvc, client):
    """Usage at limit should be denied."""
    sub = _mock_subscription()
    MockSubSvc.return_value.search_subscriptions = AsyncMock(return_value=[sub])

    plan = _mock_plan()
    MockPlanSvc.return_value.get_plan = AsyncMock(return_value=plan)

    usage = _mock_usage_record(ai_drafts_used=10)  # exactly at limit
    MockUsageSvc.return_value.search_usage_records = AsyncMock(return_value=[usage])

    resp = client.post('/api/v1/subscriptions/validate-usage', json={
      'user_id': 'user-123',
      'usage_type': 'ai_drafts',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['allowed'] is False
    assert data['current'] == 10
    assert data['limit'] == 10

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  @patch('billing_service.api.endpoints.subscription_manage.PlanService')
  @patch('billing_service.api.endpoints.subscription_manage.SubscriptionService')
  def test_validate_usage_denied_over_limit(self, MockSubSvc, MockPlanSvc, MockUsageSvc, client):
    """Usage over limit should be denied."""
    sub = _mock_subscription()
    MockSubSvc.return_value.search_subscriptions = AsyncMock(return_value=[sub])

    plan = _mock_plan()
    MockPlanSvc.return_value.get_plan = AsyncMock(return_value=plan)

    usage = _mock_usage_record(ai_drafts_used=15)  # over limit of 10
    MockUsageSvc.return_value.search_usage_records = AsyncMock(return_value=[usage])

    resp = client.post('/api/v1/subscriptions/validate-usage', json={
      'user_id': 'user-123',
      'usage_type': 'ai_drafts',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['allowed'] is False

  @patch('billing_service.api.endpoints.subscription_manage.SubscriptionService')
  def test_validate_usage_no_subscription(self, MockSubSvc, client):
    """No subscription should return allowed=False."""
    MockSubSvc.return_value.search_subscriptions = AsyncMock(return_value=[])

    resp = client.post('/api/v1/subscriptions/validate-usage', json={
      'user_id': 'user-unknown',
      'usage_type': 'ai_drafts',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['allowed'] is False
    assert data['plan'] == 'none'

  def test_validate_usage_invalid_type(self, client):
    resp = client.post('/api/v1/subscriptions/validate-usage', json={
      'user_id': 'user-123',
      'usage_type': 'invalid_type',
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Integration Test: Track usage
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestTrackUsageIntegration:
  """Track-usage integration tests with increment validation."""

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  def test_track_usage_increments_correctly(self, MockUsageSvc, client):
    """Single increment should update the counter."""
    usage = _mock_usage_record(ai_drafts_used=5)
    svc = MockUsageSvc.return_value
    svc.search_usage_records = AsyncMock(return_value=[usage])
    svc.update_usage_record = AsyncMock(return_value=usage)

    resp = client.post('/api/v1/subscriptions/track-usage', json={
      'user_id': 'user-123',
      'usage_type': 'ai_drafts',
      'increment': 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['current'] == 6  # 5 + 1
    assert data['user_id'] == 'user-123'
    assert data['usage_type'] == 'ai_drafts'
    assert data['date'] == str(date.today())

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  def test_track_usage_multiple_increments(self, MockUsageSvc, client):
    """Multiple calls should accumulate (simulated via sequential calls)."""
    # First call: start at 0, increment by 3
    usage_initial = _mock_usage_record(ai_drafts_used=0)
    svc = MockUsageSvc.return_value
    svc.search_usage_records = AsyncMock(return_value=[usage_initial])
    svc.update_usage_record = AsyncMock(return_value=usage_initial)

    resp1 = client.post('/api/v1/subscriptions/track-usage', json={
      'user_id': 'user-123',
      'usage_type': 'ai_drafts',
      'increment': 3,
    })
    assert resp1.status_code == 200
    assert resp1.json()['current'] == 3

    # Second call: start at 3, increment by 2
    usage_updated = _mock_usage_record(ai_drafts_used=3)
    svc.search_usage_records = AsyncMock(return_value=[usage_updated])

    resp2 = client.post('/api/v1/subscriptions/track-usage', json={
      'user_id': 'user-123',
      'usage_type': 'ai_drafts',
      'increment': 2,
    })
    assert resp2.status_code == 200
    assert resp2.json()['current'] == 5

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  def test_track_usage_creates_record_if_missing(self, MockUsageSvc, client):
    """First tracking call for a new day creates a usage record."""
    new_usage = _mock_usage_record(ai_drafts_used=0)
    svc = MockUsageSvc.return_value
    svc.search_usage_records = AsyncMock(return_value=[])  # No existing record
    svc.create_usage_record = AsyncMock(return_value=new_usage)
    svc.update_usage_record = AsyncMock(return_value=new_usage)

    resp = client.post('/api/v1/subscriptions/track-usage', json={
      'user_id': 'user-new',
      'usage_type': 'ai_drafts',
      'increment': 1,
    })
    assert resp.status_code == 200
    assert resp.json()['current'] == 1
    svc.create_usage_record.assert_called_once()

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  def test_track_emails_updates_daily_and_monthly(self, MockUsageSvc, client):
    """Tracking emails should increment both daily and monthly counters."""
    usage = _mock_usage_record(emails_sent=10, monthly_emails_sent=200)
    svc = MockUsageSvc.return_value
    svc.search_usage_records = AsyncMock(return_value=[usage])
    svc.update_usage_record = AsyncMock(return_value=usage)

    resp = client.post('/api/v1/subscriptions/track-usage', json={
      'user_id': 'user-123',
      'usage_type': 'emails',
      'increment': 5,
    })
    assert resp.status_code == 200
    assert resp.json()['current'] == 15  # 10 + 5 daily

    # Verify the update included both counters
    update_data = svc.update_usage_record.call_args[0][1]
    assert update_data.emails_sent == 15
    assert update_data.monthly_emails_sent == 205

  @patch('billing_service.api.endpoints.subscription_manage.UsageRecordService')
  def test_track_follow_ups_monthly_only(self, MockUsageSvc, client):
    """Follow-ups have no daily counter, only monthly."""
    usage = _mock_usage_record(monthly_follow_ups_sent=50)
    svc = MockUsageSvc.return_value
    svc.search_usage_records = AsyncMock(return_value=[usage])
    svc.update_usage_record = AsyncMock(return_value=usage)

    resp = client.post('/api/v1/subscriptions/track-usage', json={
      'user_id': 'user-123',
      'usage_type': 'follow_ups',
      'increment': 10,
    })
    assert resp.status_code == 200
    assert resp.json()['current'] == 60  # 50 + 10

  def test_track_usage_invalid_type(self, client):
    resp = client.post('/api/v1/subscriptions/track-usage', json={
      'user_id': 'user-123',
      'usage_type': 'nonexistent',
      'increment': 1,
    })
    assert resp.status_code == 400
