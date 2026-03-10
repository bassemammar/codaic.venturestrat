"""Generated Message model for TreasuryOS.

This module defines the Message model using TreasuryOS BaseModel patterns.
"""

from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID, uuid4

from venturestrat.models import BaseModel, fields


def get_current_timestamp():
    """Helper to get current UTC timestamp."""
    return datetime.utcnow()


class Message(BaseModel):
    """Email message — draft, scheduled, sent, or received reply"""

    _name = "vs_message"
    _schema = "venturestrat"
    _table = "vs_message"
    _description = "Email message — draft, scheduled, sent, or received reply"

    # Primary Key (auto-generated UUID)
    id: str = fields.String(required=False, primary_key=True, default_factory=lambda: str(uuid4()))

    # User-defined Fields
    user_id: str = fields.String(size=100, required=True)
    investor_id: str = fields.String(
        size=255, required=False, help="Cross-service reference to investor-service Investor"
    )
    email_account_id: str = fields.Many2one(
        "venturestrat.vs_email_account", required=False, ondelete="RESTRICT"
    )
    status: str = fields.String(size=20, required=True, default="draft")
    to_addresses: str = fields.JSON(required=True, help="Recipient email addresses array")
    cc_addresses: str = fields.JSON(required=True, default="[]")
    subject: str = fields.String(size=500, required=True)
    from_address: str = fields.String(size=255, required=True)
    body: str = fields.Text(required=True, help="HTML email body")
    attachments: str = fields.JSON(
        required=True, default="[]", help="Array of {key, name, size, type} for S3 attachments"
    )
    thread_id: str = fields.String(
        size=200, required=False, help="Gmail thread ID for conversation threading"
    )
    provider_message_id: str = fields.String(
        size=500, required=False, help="Message-ID header from email provider"
    )
    provider_references: str = fields.Text(
        required=False, help="References header for email threading"
    )
    previous_message_id: str = fields.Many2one(
        "venturestrat.vs_message",
        required=False,
        ondelete="RESTRICT",
        help="Self-referential FK for reply threading",
    )
    scheduled_for: str = fields.DateTime(required=False, help="When to send if scheduled")
    job_id: str = fields.String(
        size=100, required=False, help="Kafka event reference for scheduled sends"
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
