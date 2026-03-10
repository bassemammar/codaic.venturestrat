"""VentureStrat Forge — repository layer."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models import Requirement, RequirementAudit, RequirementVersion


class RequirementRepository:
  """Data access layer for requirements."""

  def create(self, db: Session, data: dict) -> Requirement:
    """Create a new requirement."""
    requirement = Requirement(**data)
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement

  def get_by_id(self, db: Session, id: int) -> Optional[Requirement]:
    """Get requirement by primary key."""
    return db.get(Requirement, id)

  def get_by_requirement_id(self, db: Session, requirement_id: str) -> Optional[Requirement]:
    """Get requirement by its human-readable ID (REQ-YYYY-MM-DD-XXX)."""
    stmt = select(Requirement).where(Requirement.requirement_id == requirement_id)
    return db.execute(stmt).scalar_one_or_none()

  def list(
    self,
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    requirement_type: Optional[str] = None,
  ) -> tuple[list[Requirement], int]:
    """List requirements with optional filters. Returns (items, total)."""
    stmt = select(Requirement)
    count_stmt = select(func.count()).select_from(Requirement)

    if status:
      stmt = stmt.where(Requirement.status == status)
      count_stmt = count_stmt.where(Requirement.status == status)
    if requirement_type:
      stmt = stmt.where(Requirement.requirement_type == requirement_type)
      count_stmt = count_stmt.where(Requirement.requirement_type == requirement_type)

    total = db.execute(count_stmt).scalar() or 0
    items = db.execute(
      stmt.order_by(Requirement.created_at.desc()).offset(skip).limit(limit)
    ).scalars().all()

    return list(items), total

  def update(self, db: Session, id: int, data: dict) -> Optional[Requirement]:
    """Update a requirement by primary key."""
    requirement = db.get(Requirement, id)
    if not requirement:
      return None
    for key, value in data.items():
      setattr(requirement, key, value)
    db.commit()
    db.refresh(requirement)
    return requirement

  def delete(self, db: Session, id: int) -> bool:
    """Delete a requirement by primary key."""
    requirement = db.get(Requirement, id)
    if not requirement:
      return False
    db.delete(requirement)
    db.commit()
    return True

  def create_version(
    self,
    db: Session,
    requirement_id: int,
    version_data: dict,
  ) -> RequirementVersion:
    """Create a versioned snapshot of a requirement."""
    version = RequirementVersion(requirement_id=requirement_id, **version_data)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version

  def create_audit(
    self,
    db: Session,
    requirement_id: int,
    action: str,
    actor_id: Optional[int] = None,
    details: Optional[dict] = None,
  ) -> RequirementAudit:
    """Create an audit trail entry."""
    audit = RequirementAudit(
      requirement_id=requirement_id,
      action=action,
      actor_id=actor_id,
      details=details,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
