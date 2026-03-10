"""Generated Tag model for TreasuryOS.

This module defines the Tag model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Tag(BaseModel):
    """Tag for categorizing shortlisted investors"""

    _name = "vs_tag"
    _schema = "venturestrat"
    _table = "vs_tag"
    _description = "Tag for categorizing shortlisted investors"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    name: str = fields.String(size=100, required=True, unique=True)
    color: str = fields.String(size=20, required=False, help="Hex color code")
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
