"""VentureStrat Forge — requirements endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.main import get_db
from src.requirement_service import RequirementService
from src.schemas import (
  ApproveRequirement,
  RejectRequirement,
  RequirementCreate,
  RequirementListResponse,
  RequirementResponse,
  RequirementUpdate,
  SubmitForReview,
)

router = APIRouter()
service = RequirementService()


@router.post('/', response_model=RequirementResponse, status_code=201)
def create_requirement(
  data: RequirementCreate,
  db: Session = Depends(get_db),
):
  """Create a new requirement."""
  requirement = service.create_requirement(db, data.model_dump())
  return requirement


@router.get('/', response_model=RequirementListResponse)
def list_requirements(
  page: int = 1,
  page_size: int = 50,
  status: Optional[str] = None,
  type: Optional[str] = None,
  db: Session = Depends(get_db),
):
  """List requirements with optional filters."""
  skip = (page - 1) * page_size
  items, total = service.list_requirements(
    db, skip=skip, limit=page_size, status=status, requirement_type=type,
  )
  return RequirementListResponse(
    items=items,
    total=total,
    page=page,
    page_size=page_size,
  )


@router.get('/{requirement_id}', response_model=RequirementResponse)
def get_requirement(
  requirement_id: str,
  db: Session = Depends(get_db),
):
  """Get a single requirement by ID."""
  return service.get_requirement(db, requirement_id)


@router.patch('/{requirement_id}', response_model=RequirementResponse)
def update_requirement(
  requirement_id: str,
  data: RequirementUpdate,
  db: Session = Depends(get_db),
):
  """Update a requirement."""
  update_data = data.model_dump(exclude_unset=True)
  return service.update_requirement(db, requirement_id, update_data)


@router.delete('/{requirement_id}', status_code=204)
def delete_requirement(
  requirement_id: str,
  db: Session = Depends(get_db),
):
  """Delete a requirement."""
  from src.repository import RequirementRepository
  repo = RequirementRepository()
  requirement = service.get_requirement(db, requirement_id)
  deleted = repo.delete(db, requirement.id)
  if not deleted:
    raise HTTPException(status_code=404, detail='Requirement not found')


@router.post('/{requirement_id}/submit', response_model=RequirementResponse)
def submit_for_review(
  requirement_id: str,
  data: SubmitForReview,
  db: Session = Depends(get_db),
):
  """Submit a requirement for review."""
  return service.submit_for_review(db, requirement_id, data.submitter_id)


@router.post('/{requirement_id}/approve', response_model=RequirementResponse)
def approve_requirement(
  requirement_id: str,
  data: ApproveRequirement,
  db: Session = Depends(get_db),
):
  """Approve a requirement."""
  return service.approve(db, requirement_id, data.reviewer_id, data.review_comments)


@router.post('/{requirement_id}/reject', response_model=RequirementResponse)
def reject_requirement(
  requirement_id: str,
  data: RejectRequirement,
  db: Session = Depends(get_db),
):
  """Reject a requirement."""
  return service.reject(db, requirement_id, data.reviewer_id, data.review_comments)
