"""Generated TemplateClause model.

This module defines the TemplateClause model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class TemplateClause(BaseModel):
    """Clause library entry with conditional variants (A/B/C/D) for legal document generation"""

    _name = "vs_template_clause"
    _schema = "venturestrat"
    _table = "vs_template_clause"
    _description = (
        "Clause library entry with conditional variants (A/B/C/D) for legal document generation"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    name: str = fields.String(
        size=100, required=True, help="Clause name, e.g. Purpose, Duration, Data Protection"
    )
    category: str = fields.String(
        size=50, required=True, help="Clause category for grouping and selection"
    )
    description: str = fields.Text(required=False)
    variants: str = fields.JSON(
        required=True, help="Clause variants as {A: {label, content}, B: {label, content}, ...}"
    )
    default_variant: str = fields.String(
        size=10, required=True, default="A", help="Default variant key"
    )
    applicable_document_types: str = fields.JSON(
        required=True,
        default="[]",
        help="Document types this clause applies to, e.g. ['mutual_nda', 'one_way_nda']",
    )
    sort_order: str = fields.Integer(
        required=True, default=0, help="Display ordering within category"
    )
    is_required: str = fields.Boolean(required=True, default=True)
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
