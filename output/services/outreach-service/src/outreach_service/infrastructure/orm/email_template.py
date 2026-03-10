"""Generated EmailTemplate model for TreasuryOS.

This module defines the EmailTemplate model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class EmailTemplate(BaseModel):
    """Reusable email template for outreach and lifecycle emails"""

    _name = "vs_email_template"
    _schema = "venturestrat"
    _table = "vs_email_template"
    _description = "Reusable email template for outreach and lifecycle emails"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(
        size=100, required=False, help="Owner user ID, null for system templates"
    )
    name: str = fields.String(size=200, required=True)
    subject: str = fields.String(size=500, required=True)
    body: str = fields.Text(required=True, help="HTML template body")
    category: str = fields.String(size=50, required=True)
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
