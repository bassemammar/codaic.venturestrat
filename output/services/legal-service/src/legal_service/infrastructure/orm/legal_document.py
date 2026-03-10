"""Generated LegalDocument model.

This module defines the LegalDocument model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class LegalDocument(BaseModel):
    """Generated legal document with full lifecycle tracking, template reference, and party links"""

    _name = "vs_legal_document"
    _schema = "venturestrat"
    _table = "vs_legal_document"
    _description = (
        "Generated legal document with full lifecycle tracking, template reference, and party links"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(
        size=100, required=True, help="Auth user who created this document"
    )
    template_id: str = fields.Many2one(
        "venturestrat.vs_document_template",
        required=False,
        ondelete="RESTRICT",
        help="Template used to generate this document",
    )
    investor_id: str = fields.String(
        size=255, required=False, help="Cross-service reference to investor-service Investor"
    )
    document_type: str = fields.String(size=50, required=True)
    title: str = fields.String(size=255, required=True)
    status: str = fields.String(size=20, required=True, default="draft")
    configuration: str = fields.JSON(
        required=True,
        default="{}",
        help="JSONB storing all form answers and clause variant selections",
    )
    content_markdown: str = fields.Text(required=False, help="Generated markdown content")
    content_html: str = fields.Text(required=False, help="Rendered HTML for preview")
    file_path_docx: str = fields.String(size=500, required=False)
    file_path_pdf: str = fields.String(size=500, required=False)
    generated_at: str = fields.DateTime(required=False)
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
