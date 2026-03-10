"""Generated DocumentTemplate model.

This module defines the DocumentTemplate model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class DocumentTemplate(BaseModel):
    """Legal document template definition — NDA, founders agreement, SAFE, employment, etc."""

    _name = "vs_document_template"
    _schema = "venturestrat"
    _table = "vs_document_template"
    _description = (
        "Legal document template definition — NDA, founders agreement, SAFE, employment, etc."
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    name: str = fields.String(
        size=100, required=True, help="Template display name, e.g. Mutual NDA (England & Wales)"
    )
    document_type: str = fields.String(size=50, required=True)
    jurisdiction: str = fields.String(
        size=30, required=True, help="Which legal jurisdiction this template covers"
    )
    description: str = fields.Text(required=False)
    template_content: str = fields.Text(
        required=True, help="Jinja2 template content for document generation"
    )
    configuration_schema: str = fields.JSON(
        required=False, help="JSON schema defining required configuration fields for this template"
    )
    is_active: str = fields.Boolean(required=True, default=True)
    clause_ids: str = fields.JSON(
        required=False,
        default="[]",
        help="Ordered list of TemplateClause IDs used in this template",
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
