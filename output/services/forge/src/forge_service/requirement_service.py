"""VentureStrat Forge — requirement business logic."""

import logging
from datetime import datetime, date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import Requirement
from src.repository import RequirementRepository

logger = logging.getLogger(__name__)

repo = RequirementRepository()


class RequirementService:
  """Business logic for requirement lifecycle."""

  def _generate_id(self, db: Session) -> str:
    """Generate a requirement ID in format REQ-YYYY-MM-DD-XXX."""
    today = date.today()
    prefix = f'REQ-{today.isoformat()}-'

    # Count existing requirements for today
    stmt = select(func.count()).select_from(Requirement).where(
      Requirement.requirement_id.like(f'{prefix}%')
    )
    count = db.execute(stmt).scalar() or 0
    seq = count + 1

    return f'{prefix}{seq:03d}'

  def create_requirement(self, db: Session, data: dict) -> Requirement:
    """Create a new requirement with generated ID and audit log."""
    requirement_id = self._generate_id(db)
    data['requirement_id'] = requirement_id
    data['status'] = 'draft'

    requirement = repo.create(db, data)
    repo.create_audit(
      db,
      requirement_id=requirement.id,
      action='created',
      details={'requirement_id': requirement_id},
    )
    logger.info(f'Created requirement {requirement_id}')
    return requirement

  def get_requirement(self, db: Session, requirement_id: str) -> Requirement:
    """Get a requirement by its human-readable ID."""
    requirement = repo.get_by_requirement_id(db, requirement_id)
    if not requirement:
      raise HTTPException(status_code=404, detail=f'Requirement {requirement_id} not found')
    return requirement

  def list_requirements(
    self,
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    requirement_type: Optional[str] = None,
  ) -> tuple[list[Requirement], int]:
    """List requirements with filters."""
    return repo.list(db, skip=skip, limit=limit, status=status, requirement_type=requirement_type)

  def update_requirement(
    self,
    db: Session,
    requirement_id: str,
    data: dict,
    actor_id: Optional[int] = None,
  ) -> Requirement:
    """Update a requirement and log the change."""
    requirement = self.get_requirement(db, requirement_id)

    # Only allow updates in draft or rejected status
    if requirement.status not in ('draft', 'rejected'):
      raise HTTPException(
        status_code=400,
        detail=f'Cannot update requirement in {requirement.status} status',
      )

    updated = repo.update(db, requirement.id, data)
    repo.create_audit(
      db,
      requirement_id=requirement.id,
      action='updated',
      actor_id=actor_id,
      details={'fields': list(data.keys())},
    )
    return updated

  def submit_for_review(
    self,
    db: Session,
    requirement_id: str,
    submitter_id: int,
  ) -> Requirement:
    """Submit a requirement for review. Must be in draft status."""
    requirement = self.get_requirement(db, requirement_id)

    if requirement.status != 'draft':
      raise HTTPException(
        status_code=400,
        detail=f'Can only submit draft requirements, current status: {requirement.status}',
      )

    updated = repo.update(db, requirement.id, {
      'status': 'submitted',
      'submitter_id': submitter_id,
      'submitted_at': datetime.utcnow(),
    })
    repo.create_audit(
      db,
      requirement_id=requirement.id,
      action='submitted',
      actor_id=submitter_id,
    )
    logger.info(f'Requirement {requirement_id} submitted for review')
    return updated

  def approve(
    self,
    db: Session,
    requirement_id: str,
    reviewer_id: int,
    comments: Optional[str] = None,
  ) -> Requirement:
    """Approve a requirement. Must be in submitted or under_review status."""
    requirement = self.get_requirement(db, requirement_id)

    if requirement.status not in ('submitted', 'under_review'):
      raise HTTPException(
        status_code=400,
        detail=f'Can only approve submitted/under_review requirements, current: {requirement.status}',
      )

    updated = repo.update(db, requirement.id, {
      'status': 'approved',
      'reviewer_id': reviewer_id,
      'review_comments': comments,
      'reviewed_at': datetime.utcnow(),
    })
    repo.create_audit(
      db,
      requirement_id=requirement.id,
      action='approved',
      actor_id=reviewer_id,
      details={'comments': comments},
    )
    logger.info(f'Requirement {requirement_id} approved by reviewer {reviewer_id}')
    return updated

  def reject(
    self,
    db: Session,
    requirement_id: str,
    reviewer_id: int,
    comments: Optional[str] = None,
  ) -> Requirement:
    """Reject a requirement. Must be in submitted or under_review status."""
    requirement = self.get_requirement(db, requirement_id)

    if requirement.status not in ('submitted', 'under_review'):
      raise HTTPException(
        status_code=400,
        detail=f'Can only reject submitted/under_review requirements, current: {requirement.status}',
      )

    updated = repo.update(db, requirement.id, {
      'status': 'rejected',
      'reviewer_id': reviewer_id,
      'review_comments': comments,
      'reviewed_at': datetime.utcnow(),
    })
    repo.create_audit(
      db,
      requirement_id=requirement.id,
      action='rejected',
      actor_id=reviewer_id,
      details={'comments': comments},
    )
    logger.info(f'Requirement {requirement_id} rejected by reviewer {reviewer_id}')
    return updated
