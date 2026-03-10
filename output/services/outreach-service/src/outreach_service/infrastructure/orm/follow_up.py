"""FollowUp ORM model — scheduled follow-up emails linked to a sent message."""

from datetime import datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
  return datetime.utcnow()


class FollowUp(BaseModel):
  """A scheduled follow-up email that is part of a post-send sequence."""

  _name = "vs_follow_up"
  _schema = "venturestrat"
  _table = "vs_follow_up"
  _description = "Scheduled follow-up email linked to an original sent message"

  # Primary key
  id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

  # Relationship to original message
  message_id: str = fields.Many2one(
    "venturestrat.vs_message",
    required=True,
    ondelete="CASCADE",
    help="Original message that triggered this follow-up sequence",
  )

  # Sequence position (1, 2, 3 …)
  sequence_number: int = fields.Integer(required=True, help="Position in the follow-up sequence")

  # How many days after the original send
  delay_days: int = fields.Integer(required=True, help="Days after original send to deliver this follow-up")

  # Calculated send time (set when original message is sent)
  scheduled_at: str = fields.DateTime(required=False, help="Absolute datetime to send (original.sent_at + delay_days)")

  # Lifecycle status
  status: str = fields.String(size=20, required=True, default="scheduled", help="scheduled | sent | canceled")

  # Email content
  subject: str = fields.String(size=500, required=True, help="Subject line (may include prefix like 'Re: ')")
  body: str = fields.Text(required=True, help="HTML body template — supports {name}, {company} placeholders")

  # Audit
  created_at: datetime = fields.DateTime(required=False, readonly=True, default_factory=get_current_timestamp)
  updated_at: datetime = fields.DateTime(required=False, readonly=True, default_factory=get_current_timestamp)
