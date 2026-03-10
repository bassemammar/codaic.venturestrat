"""Generated InvestmentTerm model.

This module defines the InvestmentTerm model using BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class InvestmentTerm(BaseModel):
    """SAFE or priced round investment terms linked to a legal entity and investor person"""

    _name = "vs_investment_term"
    _schema = "venturestrat"
    _table = "vs_investment_term"
    _description = (
        "SAFE or priced round investment terms linked to a legal entity and investor person"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    legal_entity_id: str = fields.Many2one(
        "venturestrat.vs_legal_entity",
        required=True,
        ondelete="RESTRICT",
        help="Company receiving the investment",
    )
    investor_person_id: str = fields.Many2one(
        "venturestrat.vs_contact_person",
        required=True,
        ondelete="RESTRICT",
        help="Person making the investment",
    )
    investor_id: str = fields.String(
        size=255, required=False, help="Cross-service reference to investor-service Investor"
    )
    investment_amount: str = fields.Decimal(required=True, help="Investment amount (must be > 0)")
    currency: str = fields.String(size=3, required=True, default="USD")
    valuation_cap: str = fields.Decimal(
        required=False, help="SAFE valuation cap (null for uncapped)"
    )
    discount_percentage: str = fields.Decimal(
        required=False, help="Discount percentage 0-30 (null if no discount)"
    )
    investment_date: str = fields.Date(required=True)
    pro_rata_rights: str = fields.Boolean(required=True, default=False)
    source_document_id: str = fields.String(
        size=255, required=False, help="Reference to LegalDocument that defines these terms"
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
