"""Generated VestingSchedule model.

This module defines the VestingSchedule model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class VestingSchedule(BaseModel):
    """Vesting schedule for equity grants — cliff period, total period, and acceleration triggers"""

    _name = "vs_vesting_schedule"
    _schema = "venturestrat"
    _table = "vs_vesting_schedule"
    _description = (
        "Vesting schedule for equity grants — cliff period, total period, and acceleration triggers"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    equity_grant_id: str = fields.Many2one(
        "venturestrat.vs_equity_grant", required=True, ondelete="RESTRICT"
    )
    total_period_months: str = fields.Integer(
        required=True, help="Total vesting period in months (12-60, typically 48 for 4-year vest)"
    )
    cliff_months: str = fields.Integer(
        required=True, help="Cliff period in months (0-24, typically 12 for 1-year cliff)"
    )
    start_date: str = fields.Date(required=True)
    acceleration_trigger: str = fields.String(
        size=20, required=True, default="none", help="Acceleration event type on change of control"
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
