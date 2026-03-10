"""Generated EquityGrant model.

This module defines the EquityGrant model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class EquityGrant(BaseModel):
    """Cap table entry — equity holding in a legal entity with share class and valuation"""

    _name = "vs_equity_grant"
    _schema = "venturestrat"
    _table = "vs_equity_grant"
    _description = (
        "Cap table entry — equity holding in a legal entity with share class and valuation"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    legal_entity_id: str = fields.Many2one(
        "venturestrat.vs_legal_entity",
        required=True,
        ondelete="RESTRICT",
        help="Company whose shares are held",
    )
    holder_person_id: str = fields.Many2one(
        "venturestrat.vs_contact_person",
        required=False,
        ondelete="RESTRICT",
        help="Person holding equity (null if entity holder)",
    )
    holder_entity_id: str = fields.Many2one(
        "venturestrat.vs_legal_entity",
        required=False,
        ondelete="RESTRICT",
        help="Entity holding equity (null if person holder)",
    )
    holder_type: str = fields.String(
        size=10, required=True, help="Polymorphic holder discriminator"
    )
    share_class: str = fields.String(size=30, required=True)
    number_of_shares: str = fields.Integer(
        required=True, help="Number of shares held (must be > 0)"
    )
    percentage: str = fields.Decimal(required=True, help="Ownership percentage (0.01 to 100.00)")
    valuation: str = fields.Decimal(required=False, help="Valuation at time of issue")
    issue_date: str = fields.Date(required=True)
    source_document_id: str = fields.String(
        size=255, required=False, help="Reference to LegalDocument that created this grant"
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
