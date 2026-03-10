"""Polling consumer for lifecycle (drip campaign) emails.

This is NOT a Kafka consumer. It runs as a background asyncio task that
polls the vs_lifecycle_email table for pending records whose
scheduled_for <= now, then evaluates skip conditions and sends via
SendGrid.

Runs on a configurable interval (default 60 seconds).
"""

import asyncio
from datetime import datetime
from typing import Optional

import structlog

from outreach_service.application.services.lifecycle_email_service import LifecycleEmailService
from outreach_service.application.services.message_service import MessageService
from outreach_service.config import settings
from outreach_service.providers import sendgrid as sendgrid_provider
from outreach_service.schemas.lifecycle_email import LifecycleEmailUpdate

logger = structlog.get_logger(__name__)

# Template code to subject/body mapping for lifecycle emails.
# In production this would come from the vs_email_template table.
LIFECYCLE_TEMPLATES = {
  'welcome': {
    'subject': 'Welcome to VentureStrat',
    'body': '<p>Welcome! We are glad to have you on board.</p>',
  },
  'onboarding_reminder': {
    'subject': 'Complete your VentureStrat setup',
    'body': '<p>You have not finished setting up your account. Let us help.</p>',
  },
  'gmail_reminder': {
    'subject': 'Connect your Gmail account',
    'body': '<p>Connect your Gmail for seamless investor outreach.</p>',
  },
}

DEFAULT_FROM_ADDRESS = 'noreply@venturestrat.com'


class LifecycleEmailConsumer:
  """Background polling task for pending lifecycle emails.

  On each tick:
  1. Query lifecycle emails where status='pending' and scheduled_for <= now.
  2. For each record evaluate skip conditions.
  3. If skip: set status='skipped' with reason.
  4. If send: dispatch via SendGrid, set status='sent' and sent_at.
  5. On failure: set status='failed'.
  """

  def __init__(self, poll_interval: int = 60) -> None:
    self._poll_interval = poll_interval
    self._running = False
    self._task: Optional[asyncio.Task] = None

  async def start(self) -> None:
    """Start the polling loop in a background task."""
    if self._running:
      return
    self._running = True
    self._task = asyncio.create_task(self._run())
    logger.info(
      'lifecycle_email_consumer_started',
      poll_interval=self._poll_interval,
    )

  async def stop(self) -> None:
    """Stop the polling loop."""
    self._running = False
    if self._task:
      self._task.cancel()
      try:
        await self._task
      except asyncio.CancelledError:
        pass
    logger.info('lifecycle_email_consumer_stopped')

  async def _run(self) -> None:
    """Main polling loop."""
    while self._running:
      try:
        await self._poll_and_process()
      except asyncio.CancelledError:
        break
      except Exception as e:
        logger.error('lifecycle_email_poll_error', error=str(e))

      if self._running:
        await asyncio.sleep(self._poll_interval)

  async def _poll_and_process(self) -> None:
    """Find pending lifecycle emails and process them."""
    svc = LifecycleEmailService()
    now = datetime.utcnow()

    # Search for pending records whose scheduled_for has passed
    pending = await svc.search_lifecycle_emails(
      domain=[
        ('status', '=', 'pending'),
        ('scheduled_for', '<=', now.isoformat()),
      ],
      limit=50,
    )

    if not pending:
      return

    logger.info('lifecycle_email_poll_found', count=len(pending))

    for record in pending:
      try:
        await self._process_record(record, svc)
      except Exception as e:
        logger.error(
          'lifecycle_email_process_error',
          lifecycle_email_id=record.id,
          error=str(e),
        )

  async def _process_record(self, record, svc: LifecycleEmailService) -> None:
    """Evaluate skip conditions and send or skip a single lifecycle email."""
    from uuid import UUID

    # Evaluate skip conditions
    skip_reason = await self._evaluate_skip_conditions(record)
    if skip_reason:
      await svc.update_lifecycle_email(
        UUID(record.id),
        LifecycleEmailUpdate(status='skipped', skip_reason=skip_reason),
      )
      logger.info(
        'lifecycle_email_skipped',
        lifecycle_email_id=record.id,
        reason=skip_reason,
      )
      return

    # Resolve template
    template = LIFECYCLE_TEMPLATES.get(record.template_code)
    if not template:
      await svc.update_lifecycle_email(
        UUID(record.id),
        LifecycleEmailUpdate(
          status='failed',
          skip_reason=f'Unknown template_code: {record.template_code}',
        ),
      )
      logger.warning(
        'lifecycle_email_unknown_template',
        lifecycle_email_id=record.id,
        template_code=record.template_code,
      )
      return

    # Attempt send via SendGrid
    try:
      await sendgrid_provider.send_email(
        access_token='',
        from_address=DEFAULT_FROM_ADDRESS,
        to_addresses=[record.user_id],
        cc_addresses=[],
        subject=template['subject'],
        body_html=template['body'],
        api_key=settings.sendgrid_api_key,
      )

      sent_at = datetime.utcnow()
      await svc.update_lifecycle_email(
        UUID(record.id),
        LifecycleEmailUpdate(status='sent', sent_at=sent_at),
      )
      logger.info(
        'lifecycle_email_sent',
        lifecycle_email_id=record.id,
        template_code=record.template_code,
      )

    except Exception as e:
      await svc.update_lifecycle_email(
        UUID(record.id),
        LifecycleEmailUpdate(status='failed'),
      )
      logger.error(
        'lifecycle_email_send_failed',
        lifecycle_email_id=record.id,
        error=str(e),
      )

  async def _evaluate_skip_conditions(self, record) -> Optional[str]:
    """Check whether a lifecycle email should be skipped.

    Skip conditions:
    - User already replied to a previous outreach message
    - The record has already been processed (non-pending status)

    Returns:
        A reason string if the email should be skipped, None otherwise.
    """
    msg_service = MessageService()

    # Skip if user has received a reply (indicates active engagement)
    try:
      replied_messages = await msg_service.search_messages(
        domain=[
          ('user_id', '=', record.user_id),
          ('status', '=', 'replied'),
        ],
        limit=1,
      )
      if replied_messages:
        return 'user_already_replied'
    except Exception:
      # If we cannot check, proceed with sending
      pass

    return None


# Global singleton — start/stop from main.py lifespan
lifecycle_email_consumer = LifecycleEmailConsumer(
  poll_interval=getattr(settings, 'lifecycle_poll_interval', 60),
)
