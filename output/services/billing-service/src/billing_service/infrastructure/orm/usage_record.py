"""Generated UsageRecord model for TreasuryOS.

This module defines the UsageRecord model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class UsageRecord(BaseModel):
    """Daily usage tracking for subscription limit enforcement"""

    _name = "vs_usage_record"
    _schema = "venturestrat"
    _table = "vs_usage_record"
    _description = "Daily usage tracking for subscription limit enforcement"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=100, required=True)
    date: str = fields.Date(required=True, help="Tracking date")
    month: str = fields.Integer(required=True, help="Month number (1-12)")
    year: str = fields.Integer(required=True)
    ai_drafts_used: str = fields.Integer(required=True, default=0)
    emails_sent: str = fields.Integer(required=True, default=0)
    investors_added: str = fields.Integer(required=True, default=0)
    monthly_emails_sent: str = fields.Integer(required=True, default=0)
    monthly_investors_added: str = fields.Integer(required=True, default=0)
    monthly_follow_ups_sent: str = fields.Integer(required=True, default=0)
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
