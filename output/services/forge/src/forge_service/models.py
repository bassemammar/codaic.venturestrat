"""VentureStrat Forge — SQLAlchemy models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
  DateTime,
  ForeignKey,
  Integer,
  String,
  Text,
  func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
  """Declarative base for forge models."""
  pass


class Requirement(Base):
  """Core requirement record."""

  __tablename__ = 'requirement'
  __table_args__ = {'schema': 'forge'}

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  requirement_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
  title: Mapped[str] = mapped_column(String(500), nullable=False)
  description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  requirement_type: Mapped[str] = mapped_column(
    String(50), nullable=False, default='new_feature',
  )
  priority: Mapped[str] = mapped_column(String(20), nullable=False, default='medium')
  status: Mapped[str] = mapped_column(String(30), nullable=False, default='draft')

  # Spec content
  spec_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  spec_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

  # ADW execution
  adw_execution_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  execution_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
  execution_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  execution_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  execution_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

  # Phase tracking
  current_phase: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
  plan_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
  plan_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  plan_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  build_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
  build_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  build_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  ship_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
  ship_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  ship_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  phase_error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

  # Review
  submitter_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  reviewer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  review_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

  # Retry / intervention
  retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  intervention_log: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

  # Timestamps
  created_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, server_default=func.now(),
  )
  updated_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, server_default=func.now(), onupdate=func.now(),
  )
  submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
  reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

  # Relationships
  versions: Mapped[list['RequirementVersion']] = relationship(
    back_populates='requirement', cascade='all, delete-orphan',
  )
  audits: Mapped[list['RequirementAudit']] = relationship(
    back_populates='requirement', cascade='all, delete-orphan',
  )


class RequirementVersion(Base):
  """Versioned snapshot of a requirement's spec content."""

  __tablename__ = 'requirement_version'
  __table_args__ = {'schema': 'forge'}

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  requirement_id: Mapped[int] = mapped_column(
    Integer, ForeignKey('forge.requirement.id', ondelete='CASCADE'), nullable=False,
  )
  version_number: Mapped[int] = mapped_column(Integer, nullable=False)
  spec_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  spec_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
  created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  created_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, server_default=func.now(),
  )

  requirement: Mapped['Requirement'] = relationship(back_populates='versions')


class RequirementAudit(Base):
  """Audit trail for requirement lifecycle events."""

  __tablename__ = 'requirement_audit'
  __table_args__ = {'schema': 'forge'}

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  requirement_id: Mapped[int] = mapped_column(
    Integer, ForeignKey('forge.requirement.id', ondelete='CASCADE'), nullable=False,
  )
  action: Mapped[str] = mapped_column(String(50), nullable=False)
  actor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
  created_at: Mapped[datetime] = mapped_column(
    DateTime, nullable=False, server_default=func.now(),
  )

  requirement: Mapped['Requirement'] = relationship(back_populates='audits')
