"""Generated Subscription model for TreasuryOS.

This module defines the Subscription model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Subscription(BaseModel):
    """User subscription linked to Stripe"""

    _name = "vs_subscription"
    _schema = "venturestrat"
    _table = "vs_subscription"
    _description = "User subscription linked to Stripe"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(
        size=100, required=True, unique=True, help="Auth user reference — one subscription per user"
    )
    plan_id: str = fields.Many2one("venturestrat.vs_plan", required=True, ondelete="RESTRICT")
    status: str = fields.String(size=30, required=True, default="trialing")
    stripe_customer_id: str = fields.String(size=100, required=False, unique=True)
    stripe_subscription_id: str = fields.String(size=100, required=False, unique=True)
    stripe_payment_method_id: str = fields.String(size=100, required=False)
    billing_period: str = fields.String(size=20, required=False)
    current_period_end: str = fields.DateTime(required=False)
    cancel_at_period_end: str = fields.Boolean(required=True, default=False)
    trial_ends_at: str = fields.DateTime(required=False)
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
