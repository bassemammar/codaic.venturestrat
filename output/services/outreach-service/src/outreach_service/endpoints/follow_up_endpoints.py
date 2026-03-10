"""
Follow-up sequence endpoints.

Routes:
  POST   /api/v1/messages/{message_id}/follow-ups  — schedule a follow-up sequence
  GET    /api/v1/messages/{message_id}/follow-ups  — list follow-ups for a message
  DELETE /api/v1/follow-ups/{follow_up_id}          — cancel a scheduled follow-up
  PUT    /api/v1/follow-ups/{follow_up_id}          — update a follow-up
"""

from typing import List
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from outreach_service.application.services.follow_up_service import FollowUpService
from outreach_service.core.database import get_session
from outreach_service.schemas.follow_up import (
  FollowUpResponse,
  ScheduleFollowUpsRequest,
  UpdateFollowUpRequest,
)

logger = structlog.get_logger(__name__)

# Two routers because they have different prefixes (messages vs follow-ups)
messages_router = APIRouter(tags=['Follow-ups'])
follow_ups_router = APIRouter(tags=['Follow-ups'])


# ---------------------------------------------------------------------------
# POST /messages/{message_id}/follow-ups
# ---------------------------------------------------------------------------

@messages_router.post(
  '/{message_id}/follow-ups',
  response_model=List[FollowUpResponse],
  status_code=status.HTTP_201_CREATED,
  summary='Schedule a follow-up sequence',
  description=(
    'Creates a series of follow-up emails scheduled to be sent N days after the '
    'original message was (or will be) sent. Maximum 5 follow-ups per sequence. '
    'Actual sending is handled by a background worker; this endpoint only creates '
    'the schedule records.'
  ),
  responses={
    201: {'description': 'Follow-up sequence created'},
    404: {'description': 'Original message not found'},
    422: {'description': 'Validation error'},
  },
)
async def schedule_follow_ups(
  message_id: UUID,
  body: ScheduleFollowUpsRequest,
  session=Depends(get_session),
) -> List[FollowUpResponse]:
  """Schedule a sequence of follow-up emails after the given message."""
  service = FollowUpService(session)
  try:
    return await service.schedule_follow_ups(message_id, body)
  except ValueError as exc:
    raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /messages/{message_id}/follow-ups
# ---------------------------------------------------------------------------

@messages_router.get(
  '/{message_id}/follow-ups',
  response_model=List[FollowUpResponse],
  summary='List follow-ups for a message',
  description='Returns all follow-ups for the given message, ordered by sequence number.',
  responses={
    200: {'description': 'Follow-up list'},
    404: {'description': 'Message not found'},
  },
)
async def list_follow_ups(
  message_id: UUID,
  session=Depends(get_session),
) -> List[FollowUpResponse]:
  """List all follow-ups scheduled for a message."""
  service = FollowUpService(session)
  return await service.list_follow_ups(message_id)


# ---------------------------------------------------------------------------
# DELETE /follow-ups/{follow_up_id}
# ---------------------------------------------------------------------------

@follow_ups_router.delete(
  '/{follow_up_id}',
  response_model=FollowUpResponse,
  summary='Cancel a follow-up',
  description='Sets the follow-up status to "canceled". The record is kept for audit purposes.',
  responses={
    200: {'description': 'Follow-up canceled'},
    404: {'description': 'Follow-up not found'},
  },
)
async def cancel_follow_up(
  follow_up_id: UUID,
  session=Depends(get_session),
) -> FollowUpResponse:
  """Cancel a scheduled follow-up (soft delete via status change)."""
  service = FollowUpService(session)
  result = await service.cancel_follow_up(follow_up_id)
  if not result:
    raise HTTPException(status_code=404, detail='Follow-up not found')
  return result


# ---------------------------------------------------------------------------
# PUT /follow-ups/{follow_up_id}
# ---------------------------------------------------------------------------

@follow_ups_router.put(
  '/{follow_up_id}',
  response_model=FollowUpResponse,
  summary='Update a follow-up',
  description=(
    'Partially update a follow-up. Updateable fields: delay_days, subject, body, status. '
    'Changing delay_days on a sent message automatically recalculates scheduled_at.'
  ),
  responses={
    200: {'description': 'Follow-up updated'},
    404: {'description': 'Follow-up not found'},
  },
)
async def update_follow_up(
  follow_up_id: UUID,
  body: UpdateFollowUpRequest,
  session=Depends(get_session),
) -> FollowUpResponse:
  """Update a scheduled follow-up's delay, content, or status."""
  service = FollowUpService(session)
  result = await service.update_follow_up(follow_up_id, body)
  if not result:
    raise HTTPException(status_code=404, detail='Follow-up not found')
  return result
