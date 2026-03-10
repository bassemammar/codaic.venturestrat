"""Generated Investor model for TreasuryOS.

This module defines the Investor model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Investor(BaseModel):
    """VC investor profile with contact info, location, stages, types, and social links"""

    _name = "vs_investor"
    _schema = "venturestrat"
    _table = "vs_investor"
    _description = (
        "VC investor profile with contact info, location, stages, types, and social links"
    )

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    name: str = fields.String(size=300, required=True, help="Full name of the investor")
    avatar: str = fields.String(size=500, required=False, help="S3 signed URL for profile image")
    website: str = fields.String(size=500, required=False)
    phone: str = fields.String(size=50, required=False)
    title: str = fields.String(size=200, required=False, help="Job title, e.g. Managing Partner")
    external_id: str = fields.String(
        size=100, required=True, help="Original source ID from data import"
    )
    city: str = fields.String(size=100, required=False)
    state: str = fields.String(size=100, required=False)
    country: str = fields.String(size=100, required=False)
    company_name: str = fields.String(size=300, required=False, help="Fund or firm name")
    stages: str = fields.JSON(
        required=True, default="[]", help="Investment stages, e.g. ['Seed', 'Series A']"
    )
    investor_types: str = fields.JSON(
        required=True, default="[]", help="Investor types, e.g. ['Angel', 'VC']"
    )
    social_links: str = fields.JSON(
        required=False, help="Social media links: {linkedin, twitter, crunchbase}"
    )
    pipelines: str = fields.JSON(required=False, help="Deal pipeline data from source")
    founded_companies: str = fields.JSON(required=False)
    country_priority: str = fields.Integer(
        required=True, default=2, help="Sorting weight for country-based ordering"
    )
    source_data: str = fields.JSON(required=False, help="Raw import data from original source")
    # Audit Timestamps (auto-populated)
    created_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )
    updated_at: datetime = fields.DateTime(
        required=False, readonly=True, default_factory=get_current_timestamp
    )

    # Auto-injected by BaseModel:
    # - tenant_id: UUID (unless _no_tenant = True)
