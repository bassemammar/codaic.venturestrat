"""Shortlist status consumer — updates pipeline stage on reply events.

Subscribes to outreach.message.replied and promotes the matching
Shortlist entry to the 'interested' pipeline stage, plus logs a
'reply_received' Activity.
"""

from datetime import datetime
from typing import Any, Dict

import structlog

from crm_service.consumers.base import BaseConsumer
from crm_service.infrastructure.repositories.shortlist_repository import ShortlistRepository
from crm_service.infrastructure.repositories.activity_repository import ActivityRepository
from crm_service.infrastructure.repositories.pipeline_stage_repository import PipelineStageRepository
from crm_service.integrations.events import event_publisher
from crm_service.integrations.metrics import entity_operations_total

logger = structlog.get_logger(__name__)

TOPIC = 'outreach.message.replied'
GROUP_ID = 'crm-shortlist-status-consumer'

# Pipeline stage codes that are considered "before" the interested stage.
# If the shortlist is already at or past interested, we skip the update.
PRE_INTERESTED_STAGES = {'target', 'researching', 'contacted', 'outreach'}


class ShortlistStatusConsumer(BaseConsumer):
  """Consumes outreach.message.replied events and updates shortlist stage.

  When the outreach-service detects a reply from an investor, this
  consumer finds the Shortlist entry for that user+investor, checks
  whether the current pipeline stage is before 'interested', and if so
  promotes the shortlist to the 'interested' stage. It also creates a
  'reply_received' Activity.
  """

  def __init__(self):
    super().__init__(group_id=GROUP_ID, topics=[TOPIC])
    self.shortlist_repo = ShortlistRepository()
    self.activity_repo = ActivityRepository()
    self.pipeline_stage_repo = PipelineStageRepository()

  async def handle_event(self, topic: str, event: Dict[str, Any]) -> None:
    """Handle outreach.message.replied event."""
    data = event.get('data', {})
    investor_id = data.get('investor_id')
    user_id = data.get('user_id')
    investor_name = data.get('investor_name', 'investor')
    message_id = data.get('message_id') or data.get('id') or event.get('event_id')
    tenant_id = event.get('tenant_id')

    if not investor_id or not user_id:
      logger.warning(
        'message_replied_missing_fields',
        event_id=event.get('event_id'),
        has_investor_id=bool(investor_id),
        has_user_id=bool(user_id),
      )
      return

    logger.info(
      'processing_message_replied',
      event_id=event.get('event_id'),
      investor_id=investor_id,
      user_id=user_id,
    )

    # Find the shortlist entry
    shortlists = await self.shortlist_repo.search(
      [('user_id', '=', user_id), ('investor_id', '=', investor_id)],
      skip=0,
      limit=1,
    )

    if not shortlists:
      logger.warning(
        'no_shortlist_for_message_replied',
        investor_id=investor_id,
        user_id=user_id,
        event_id=event.get('event_id'),
      )
      return

    shortlist = shortlists[0]

    # Determine current stage code
    current_stage_code = await self._get_stage_code(shortlist.stage_id)

    # Only promote if current stage is before 'interested'
    if current_stage_code and current_stage_code not in PRE_INTERESTED_STAGES:
      logger.info(
        'shortlist_already_past_interested',
        shortlist_id=shortlist.id,
        current_stage=current_stage_code,
        event_id=event.get('event_id'),
      )
    else:
      # Look up the 'interested' stage
      interested_stage = await self._find_stage_by_code('interested')
      if interested_stage:
        old_stage = current_stage_code or 'unknown'
        shortlist.stage_id = interested_stage.id
        shortlist.status = 'interested'
        await self.shortlist_repo.update(shortlist)

        # Publish status_changed event
        await event_publisher.publish(
          entity_name='shortlist',
          action='status_changed',
          data={
            'shortlist_id': shortlist.id,
            'user_id': user_id,
            'investor_id': investor_id,
            'old_stage': old_stage,
            'new_stage': 'interested',
          },
          tenant_id=tenant_id,
        )

        entity_operations_total.labels(
          entity='shortlist', operation='update', status='success'
        ).inc()

        logger.info(
          'shortlist_promoted_to_interested',
          shortlist_id=shortlist.id,
          old_stage=old_stage,
          event_id=event.get('event_id'),
        )
      else:
        logger.error(
          'interested_stage_not_found',
          event_id=event.get('event_id'),
        )

    # Always create a reply_received activity
    activity_data = {
      'shortlist_id': shortlist.id,
      'activity_type': 'reply_received',
      'summary': f'Reply received from {investor_name}',
      'date': datetime.utcnow().isoformat(),
      'user_id': user_id,
      'reference_id': str(message_id) if message_id else None,
    }
    if tenant_id:
      activity_data['tenant_id'] = tenant_id

    activity = await self.activity_repo.create(**activity_data)

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
      'reply_activity_created',
      activity_id=activity.id,
      shortlist_id=shortlist.id,
      event_id=event.get('event_id'),
    )

  async def _get_stage_code(self, stage_id: str | None) -> str | None:
    """Resolve a stage_id to its code string."""
    if not stage_id:
      return None
    stage = await self.pipeline_stage_repo.get_by_id(stage_id)
    return stage.code if stage else None

  async def _find_stage_by_code(self, code: str):
    """Find a PipelineStage by its unique code."""
    stages = await self.pipeline_stage_repo.search(
      [('code', '=', code)],
      skip=0,
      limit=1,
    )
    return stages[0] if stages else None
