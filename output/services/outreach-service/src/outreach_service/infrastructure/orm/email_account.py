"""Generated EmailAccount model for TreasuryOS.

This module defines the EmailAccount model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class EmailAccount(BaseModel):
    """OAuth email account for sending via Gmail, Microsoft, or SendGrid"""

    _name = "vs_email_account"
    _schema = "venturestrat"
    _table = "vs_email_account"
    _description = "OAuth email account for sending via Gmail, Microsoft, or SendGrid"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=100, required=True, help="Auth user reference")
    provider: str = fields.String(size=30, required=True)
    email_address: str = fields.String(size=255, required=True)
    access_token: str = fields.Text(required=False, help="Encrypted OAuth access token")
    refresh_token: str = fields.Text(required=False, help="Encrypted OAuth refresh token")
    token_expires_at: str = fields.DateTime(required=False)
    watch_history_id: str = fields.String(
        size=100, required=False, help="Gmail push notification history ID"
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
