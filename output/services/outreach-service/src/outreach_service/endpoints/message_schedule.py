"""POST /messages/{id}/schedule and /messages/{id}/cancel-schedule."""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from outreach_service.application.services.message_service import MessageService
from outreach_service.core.database import get_session
from outreach_service.schemas.message import MessageUpdate

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['Messages'])


class ScheduleRequest(BaseModel):
  """Request body for scheduling a message."""
  scheduled_for: datetime = Field(
    description='ISO datetime when the message should be sent'
  )


class ScheduleResult(BaseModel):
  """Response after scheduling or cancelling a schedule."""
  message_id: str = Field(description='Internal message ID')
  status: str = Field(description='New message status')
  scheduled_for: datetime | None = Field(
    default=None, description='Scheduled send time (null if cancelled)'
  )


@router.post(
  '/{id}/schedule',
  response_model=ScheduleResult,
  summary='Schedule a message for future sending',
  description=(
    'Sets the message status to "scheduled" and stores the scheduled_for timestamp. '
    'In production, a Kafka consumer polls for due messages.'
  ),
  responses={
    200: {'description': 'Message scheduled successfully'},
    400: {
      'description': 'Message not in schedulable state',
      'content': {'application/json': {'example': {'detail': 'Message is not in draft status'}}},
    },
    404: {
      'description': 'Message not found',
      'content': {'application/json': {'example': {'detail': 'Message not found'}}},
    },
  },
)
async def schedule_message(
  id: UUID,
  body: ScheduleRequest,
  session=Depends(get_session),
) -> ScheduleResult:
  """Schedule a draft message for future sending."""
  service = MessageService(session)

  message = await service.get_message(id)
  if not message:
    raise HTTPException(status_code=404, detail='Message not found')

  if message.status != 'draft':
    raise HTTPException(
      status_code=400,
      detail=f'Message is not in draft status (current: {message.status})',
    )

  if body.scheduled_for <= datetime.utcnow():
    raise HTTPException(
      status_code=400,
      detail='scheduled_for must be in the future',
    )

  update_data = MessageUpdate(
    status='scheduled',
    scheduled_for=body.scheduled_for,
  )
  await service.update_message(id, update_data)

  logger.info('message_scheduled', message_id=str(id), scheduled_for=body.scheduled_for.isoformat())

  return ScheduleResult(
    message_id=str(id),
    status='scheduled',
    scheduled_for=body.scheduled_for,
  )


@router.post(
  '/{id}/cancel-schedule',
  response_model=ScheduleResult,
  summary='Cancel a scheduled message',
  description='Reverts a scheduled message back to draft status and clears the scheduled_for timestamp.',
  responses={
    200: {'description': 'Schedule cancelled successfully'},
    400: {
      'description': 'Message is not scheduled',
      'content': {'application/json': {'example': {'detail': 'Message is not in scheduled status'}}},
    },
    404: {
      'description': 'Message not found',
      'content': {'application/json': {'example': {'detail': 'Message not found'}}},
    },
  },
)
async def cancel_schedule(
  id: UUID,
  session=Depends(get_session),
) -> ScheduleResult:
  """Cancel a scheduled message, reverting it to draft."""
  service = MessageService(session)

  message = await service.get_message(id)
  if not message:
    raise HTTPException(status_code=404, detail='Message not found')

  if message.status != 'scheduled':
    raise HTTPException(
      status_code=400,
      detail=f'Message is not in scheduled status (current: {message.status})',
    )

  update_data = MessageUpdate(
    status='draft',
    scheduled_for=None,
    job_id=None,
  )
  await service.update_message(id, update_data)

  logger.info('message_schedule_cancelled', message_id=str(id))

  return ScheduleResult(
    message_id=str(id),
    status='draft',
    scheduled_for=None,
  )
