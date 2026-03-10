"""Activity consumer — creates Activity records from outreach events.

Subscribes to outreach.message.sent and creates an Activity record
on the matching Shortlist entry in the user's investor pipeline.
"""

from datetime import datetime
from typing import Any, Dict

import structlog

from crm_service.consumers.base import BaseConsumer
from crm_service.infrastructure.repositories.shortlist_repository import ShortlistRepository
from crm_service.infrastructure.repositories.activity_repository import ActivityRepository
from crm_service.integrations.events import event_publisher
from crm_service.integrations.metrics import entity_operations_total

logger = structlog.get_logger(__name__)

TOPIC = 'outreach.message.sent'
GROUP_ID = 'crm-activity-consumer'


class ActivityConsumer(BaseConsumer):
  """Consumes outreach.message.sent events and creates Activity records.

  When the outreach-service sends an email to an investor, this consumer
  looks up the Shortlist entry for that user+investor and logs an
  'email_sent' Activity against it.
  """

  def __init__(self):
    super().__init__(group_id=GROUP_ID, topics=[TOPIC])
    self.shortlist_repo = ShortlistRepository()
    self.activity_repo = ActivityRepository()

  async def handle_event(self, topic: str, event: Dict[str, Any]) -> None:
    """Handle outreach.message.sent event by creating an Activity."""
    data = event.get('data', {})
    investor_id = data.get('investor_id')
    user_id = data.get('user_id')
    subject = data.get('subject', '')
    message_id = data.get('message_id') or data.get('id') or event.get('event_id')
    tenant_id = event.get('tenant_id')

    if not investor_id or not user_id:
      logger.warning(
        'message_sent_missing_fields',
        event_id=event.get('event_id'),
        has_investor_id=bool(investor_id),
        has_user_id=bool(user_id),
      )
      return

    logger.info(
      'processing_message_sent',
      event_id=event.get('event_id'),
      investor_id=investor_id,
      user_id=user_id,
    )

    # Find the shortlist entry for this user + investor
    shortlists = await self.shortlist_repo.search(
      [('user_id', '=', user_id), ('investor_id', '=', investor_id)],
      skip=0,
      limit=1,
    )

    if not shortlists:
      logger.warning(
        'no_shortlist_for_message_sent',
        investor_id=investor_id,
        user_id=user_id,
        event_id=event.get('event_id'),
      )
      return

    shortlist = shortlists[0]

    # Create the activity record
    activity_data = {
      'shortlist_id': shortlist.id,
      'activity_type': 'email_sent',
      'summary': f'Email sent: {subject}' if subject else 'Email sent',
      'details': data.get('body_preview', ''),
      'date': datetime.utcnow().isoformat(),
      'user_id': user_id,
      'reference_id': str(message_id) if message_id else None,
    }
    if tenant_id:
      activity_data['tenant_id'] = tenant_id

    activity = await self.activity_repo.create(**activity_data)

    # Publish downstream event
    await event_publisher.publish(
      entity_name='activity',
      action='created',
      data=activity.to_dict(),
      tenant_id=tenant_id,
    )

    entity_operations_total.labels(
      entity='activity', operation='create', status='success'
    ).inc()

    logger.info(
      'activity_created_from_message_sent',
      activity_id=activity.id,
      shortlist_id=shortlist.id,
      event_id=event.get('event_id'),
    )
