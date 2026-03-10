"""Pydantic schemas for FollowUp resources."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ScheduleFollowUpsRequest(BaseModel):
  """Body for POST /messages/{id}/follow-ups — create a follow-up sequence."""

  delays: List[int] = Field(
    default=[3, 5, 7],
    description="Days after the original send for each follow-up (e.g. [3, 5, 7])",
    min_length=1,
    max_length=5,
  )
  subject_prefix: Optional[str] = Field(
    default='Re: ',
    max_length=50,
    description="Prefix prepended to the original message subject",
  )
  body_template: Optional[str] = Field(
    default='Hi {name},\n\nJust following up on my previous email. I wanted to make sure it didn\'t get lost in your inbox.\n\nWould love to connect and learn more about your perspective on this opportunity.\n\nBest,',
    description="Body template supporting {name} and {company} placeholders",
  )

  model_config = ConfigDict(
    json_schema_extra={
      'example': {
        'delays': [3, 5, 7],
        'subject_prefix': 'Re: ',
        'body_template': 'Hi {name}, just following up on my previous email...',
      }
    }
  )


class UpdateFollowUpRequest(BaseModel):
  """Body for PUT /follow-ups/{id} — update a single follow-up."""

  delay_days: Optional[int] = Field(
    default=None,
    ge=1,
    le=365,
    description="New delay in days (recalculates scheduled_at when message is sent)",
  )
  subject: Optional[str] = Field(default=None, max_length=500)
  body: Optional[str] = Field(default=None)
  status: Optional[Literal['scheduled', 'sent', 'canceled']] = Field(default=None)

  model_config = ConfigDict(
    json_schema_extra={
      'example': {
        'delay_days': 4,
        'body': 'Hi {name}, I wanted to reach out once more...',
      }
    }
  )


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class FollowUpResponse(BaseModel):
  """Serialized FollowUp returned by the API."""

  id: str
  message_id: str
  sequence_number: int
  delay_days: int
  scheduled_at: Optional[datetime] = None
  status: str
  subject: str
  body: str
  created_at: Optional[datetime] = None
  updated_at: Optional[datetime] = None

  model_config = ConfigDict(
    from_attributes=True,
    json_schema_extra={
      'example': {
        'id': '550e8400-e29b-41d4-a716-446655440001',
        'message_id': '550e8400-e29b-41d4-a716-446655440000',
        'sequence_number': 1,
        'delay_days': 3,
        'scheduled_at': '2024-01-04T12:00:00Z',
        'status': 'scheduled',
        'subject': 'Re: Investment Opportunity — VentureStrat',
        'body': 'Hi John, just following up...',
        'created_at': '2024-01-01T12:00:00Z',
        'updated_at': '2024-01-01T12:00:00Z',
      }
    },
  )
