"""Generated PipelineStage model for TreasuryOS.

This module defines the PipelineStage model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class PipelineStage(BaseModel):
    """CRM pipeline stage for investor shortlisting"""

    _name = "vs_pipeline_stage"
    _schema = "venturestrat"
    _table = "vs_pipeline_stage"
    _description = "CRM pipeline stage for investor shortlisting"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    name: str = fields.String(size=100, required=True, help="Stage display name")
    code: str = fields.String(
        size=50, required=True, unique=True, help="Stage code for programmatic use"
    )
    sequence: str = fields.Integer(required=True, help="Display ordering")
    color: str = fields.String(size=20, required=False, help="Hex color for Kanban column")
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
