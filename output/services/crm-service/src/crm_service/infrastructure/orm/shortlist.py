"""Generated Shortlist model for TreasuryOS.

This module defines the Shortlist model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Shortlist(BaseModel):
    """User's investor pipeline — tracks shortlisted investors with CRM status"""

    _name = "vs_shortlist"
    _schema = "venturestrat"
    _table = "vs_shortlist"
    _description = "User's investor pipeline — tracks shortlisted investors with CRM status"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=100, required=True, help="Auth user reference")
    investor_id: str = fields.String(
        size=255, required=True, help="Cross-service reference to investor-service Investor"
    )
    stage_id: str = fields.Many2one(
        "venturestrat.vs_pipeline_stage",
        required=False,
        ondelete="RESTRICT",
        help="Pipeline stage reference",
    )
    status: str = fields.String(
        size=30, required=True, default="target", help="Current pipeline status"
    )
    notes: str = fields.Text(required=False)
    added_at: str = fields.DateTime(required=True, help="When investor was shortlisted")
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
