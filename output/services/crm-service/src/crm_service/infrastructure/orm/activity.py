"""Generated Activity model for TreasuryOS.

This module defines the Activity model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Activity(BaseModel):
    """Outreach activity touchpoint on a shortlisted investor"""

    _name = "vs_activity"
    _schema = "venturestrat"
    _table = "vs_activity"
    _description = "Outreach activity touchpoint on a shortlisted investor"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    shortlist_id: str = fields.Many2one(
        "venturestrat.vs_shortlist",
        required=True,
        ondelete="RESTRICT",
        help="Parent shortlist record",
    )
    activity_type: str = fields.String(size=30, required=True)
    summary: str = fields.String(size=500, required=False)
    details: str = fields.Text(required=False)
    date: str = fields.DateTime(required=True, help="When the activity occurred")
    user_id: str = fields.String(
        size=100, required=True, help="Auth user who performed the activity"
    )
    reference_id: str = fields.String(
        size=100, required=False, help="External reference, e.g. message ID"
    )
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
