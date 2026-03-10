"""Generated Plan model for TreasuryOS.

This module defines the Plan model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Plan(BaseModel):
    """Subscription plan tier definition"""

    _name = "vs_plan"
    _schema = "venturestrat"
    _table = "vs_plan"
    _description = "Subscription plan tier definition"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    name: str = fields.String(size=50, required=True, unique=True)
    code: str = fields.String(size=20, required=True, unique=True)
    price_monthly: str = fields.Decimal(required=True, default="0.00")
    price_quarterly: str = fields.Decimal(required=False)
    price_annually: str = fields.Decimal(required=False)
    limits: str = fields.JSON(
        required=True,
        help="Usage limits: {ai_drafts_per_day, emails_per_day, emails_per_month, investors_per_day, investors_per_month, follow_ups_per_month}",
    )
    features: str = fields.JSON(
        required=True,
        help="Feature flags: {show_full_contact_info, advanced_filters, priority_support, custom_integrations, can_download_csv}",
    )
    usage_basis: str = fields.String(
        size=10, required=True, help="Whether limits are enforced daily (free) or monthly (paid)"
    )
    is_active: str = fields.Boolean(required=True, default=True)
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
