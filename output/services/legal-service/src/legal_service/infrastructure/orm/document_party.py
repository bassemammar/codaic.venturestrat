"""Generated DocumentParty model.

This module defines the DocumentParty model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class DocumentParty(BaseModel):
    """Links a legal document to its parties (entity + signatory) with role designation"""

    _name = "vs_document_party"
    _schema = "venturestrat"
    _table = "vs_document_party"
    _description = (
        "Links a legal document to its parties (entity + signatory) with role designation"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    legal_document_id: str = fields.Many2one(
        "venturestrat.vs_legal_document", required=True, ondelete="RESTRICT"
    )
    legal_entity_id: str = fields.Many2one(
        "venturestrat.vs_legal_entity",
        required=True,
        ondelete="RESTRICT",
        help="Company acting as party to the document",
    )
    signatory_id: str = fields.Many2one(
        "venturestrat.vs_contact_person",
        required=False,
        ondelete="RESTRICT",
        help="Person signing on behalf of the entity",
    )
    party_role: str = fields.String(size=20, required=True, help="Role in the document context")
    party_label: str = fields.String(
        size=50, required=False, help="Custom label, e.g. 'The Disclosing Party'"
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
