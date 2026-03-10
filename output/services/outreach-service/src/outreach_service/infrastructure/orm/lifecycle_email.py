"""Generated LifecycleEmail model for TreasuryOS.

This module defines the LifecycleEmail model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class LifecycleEmail(BaseModel):
    """Tracks drip campaign email execution per user"""

    _name = "vs_lifecycle_email"
    _schema = "venturestrat"
    _table = "vs_lifecycle_email"
    _description = "Tracks drip campaign email execution per user"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=100, required=True)
    template_code: str = fields.String(
        size=50,
        required=True,
        help="Lifecycle template identifier: welcome, onboarding_reminder, gmail_reminder, etc.",
    )
    status: str = fields.String(size=20, required=True, default="pending")
    scheduled_for: str = fields.DateTime(
        required=True, help="When this lifecycle email should be sent"
    )
    sent_at: str = fields.DateTime(required=False)
    skip_reason: str = fields.String(size=200, required=False, help="Why this email was skipped")
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
