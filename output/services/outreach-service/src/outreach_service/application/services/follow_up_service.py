"""FollowUpService — business logic for follow-up email sequences."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

import structlog

from outreach_service.infrastructure.repositories.follow_up_repository import FollowUpRepository
from outreach_service.infrastructure.repositories.message_repository import MessageRepository
from outreach_service.schemas.follow_up import (
  FollowUpResponse,
  ScheduleFollowUpsRequest,
  UpdateFollowUpRequest,
)

logger = structlog.get_logger(__name__)


def _to_response(obj) -> FollowUpResponse:
  """Convert a BaseModel ORM instance to a FollowUpResponse."""
  d = obj.to_dict()
  return FollowUpResponse(**d)


class FollowUpService:
  """Manages follow-up sequences attached to outreach messages."""

  def __init__(self, session=None):
    self.repo = FollowUpRepository(session)
    self.message_repo = MessageRepository(session)

  # ---------------------------------------------------------------------------
  # Create sequence
  # ---------------------------------------------------------------------------

  async def schedule_follow_ups(
    self,
    message_id: UUID,
    data: ScheduleFollowUpsRequest,
  ) -> List[FollowUpResponse]:
    """
    Create a follow-up sequence for *message_id*.

    - Resolves the original message to get its subject and sent_at.
    - If the message is already sent, calculates absolute scheduled_at times.
    - If not yet sent, stores delay_days only; scheduled_at is calculated later.
    - Existing follow-ups for the message are NOT removed — call the DELETE
      endpoint first if you want to replace the sequence.
    """
    message = await self.message_repo.get_by_id(message_id)
    if not message:
      raise ValueError(f'Message {message_id} not found')

    original_subject = getattr(message, 'subject', '') or ''
    subject_prefix = data.subject_prefix if data.subject_prefix is not None else 'Re: '

    # Build the base follow-up subject
    follow_up_subject = (
      original_subject
      if original_subject.startswith(subject_prefix)
      else f'{subject_prefix}{original_subject}'
    )

    # Determine base time for scheduling (sent_at if available, else None)
    sent_at_raw = getattr(message, 'updated_at', None)  # approximation when message is sent
    if getattr(message, 'status', '') == 'sent' and sent_at_raw:
      if isinstance(sent_at_raw, str):
        try:
          base_time: Optional[datetime] = datetime.fromisoformat(sent_at_raw.replace('Z', '+00:00'))
        except ValueError:
          base_time = None
      elif isinstance(sent_at_raw, datetime):
        base_time = sent_at_raw
      else:
        base_time = None
    else:
      base_time = None

    body_template = data.body_template or ''

    created: List[FollowUpResponse] = []
    for seq_num, delay_days in enumerate(data.delays, start=1):
      scheduled_at = (
        (base_time + timedelta(days=delay_days)).isoformat()
        if base_time
        else None
      )

      record = await self.repo.create(
        message_id=str(message_id),
        sequence_number=seq_num,
        delay_days=delay_days,
        scheduled_at=scheduled_at,
        status='scheduled',
        subject=follow_up_subject,
        body=body_template,
      )
      created.append(_to_response(record))
      logger.info(
        'follow_up_scheduled',
        message_id=str(message_id),
        sequence_number=seq_num,
        delay_days=delay_days,
        scheduled_at=scheduled_at,
      )

    return created

  # ---------------------------------------------------------------------------
  # List
  # ---------------------------------------------------------------------------

  async def list_follow_ups(self, message_id: UUID) -> List[FollowUpResponse]:
    """Return all follow-ups for a message, ordered by sequence_number."""
    records = await self.repo.find_by_message_id(str(message_id))
    return [_to_response(r) for r in records]

  # ---------------------------------------------------------------------------
  # Cancel (soft-delete via status change)
  # ---------------------------------------------------------------------------

  async def cancel_follow_up(self, follow_up_id: UUID) -> Optional[FollowUpResponse]:
    """
    Mark a single follow-up as *canceled*.
    Returns the updated record, or None if not found.
    """
    obj = await self.repo.get_by_id(follow_up_id)
    if not obj:
      return None

    obj.status = 'canceled'
    updated = await self.repo.update(obj)
    logger.info('follow_up_canceled', follow_up_id=str(follow_up_id))
    return _to_response(updated)

  # ---------------------------------------------------------------------------
  # Update
  # ---------------------------------------------------------------------------

  async def update_follow_up(
    self,
    follow_up_id: UUID,
    data: UpdateFollowUpRequest,
  ) -> Optional[FollowUpResponse]:
    """
    Partially update a follow-up (delay, subject, body, or status).

    When delay_days is changed and the original message is already sent,
    scheduled_at is recalculated automatically.
    """
    obj = await self.repo.get_by_id(follow_up_id)
    if not obj:
      return None

    patch = data.model_dump(exclude_unset=True)

    # If delay_days changes, try to recalculate scheduled_at
    if 'delay_days' in patch:
      new_delay = patch['delay_days']
      # Resolve original message to find its sent_at
      msg_id = getattr(obj, 'message_id', None)
      if msg_id:
        try:
          message = await self.message_repo.get_by_id(UUID(str(msg_id)))
          if message and getattr(message, 'status', '') == 'sent':
            raw = getattr(message, 'updated_at', None)
            if raw:
              base_time: Optional[datetime]
              if isinstance(raw, str):
                base_time = datetime.fromisoformat(raw.replace('Z', '+00:00'))
              elif isinstance(raw, datetime):
                base_time = raw
              else:
                base_time = None
              if base_time:
                patch['scheduled_at'] = (base_time + timedelta(days=new_delay)).isoformat()
        except Exception:
          pass  # Non-fatal — keep existing scheduled_at

    for key, value in patch.items():
      setattr(obj, key, value)

    updated = await self.repo.update(obj)
    logger.info('follow_up_updated', follow_up_id=str(follow_up_id))
    return _to_response(updated)
