"""VentureStrat Forge — admin endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.main import get_db
from src.models import Requirement

router = APIRouter()


@router.get('/executions')
def list_executions(
  status: Optional[str] = None,
  phase: Optional[str] = None,
  page: int = 1,
  page_size: int = 50,
  db: Session = Depends(get_db),
):
  """List all executions with optional filters."""
  stmt = select(Requirement).where(Requirement.adw_execution_id.isnot(None))
  count_stmt = select(func.count()).select_from(Requirement).where(
    Requirement.adw_execution_id.isnot(None)
  )

  if status:
    stmt = stmt.where(Requirement.execution_status == status)
    count_stmt = count_stmt.where(Requirement.execution_status == status)
  if phase:
    stmt = stmt.where(Requirement.current_phase == phase)
    count_stmt = count_stmt.where(Requirement.current_phase == phase)

  total = db.execute(count_stmt).scalar() or 0
  skip = (page - 1) * page_size
  items = db.execute(
    stmt.order_by(Requirement.execution_started_at.desc()).offset(skip).limit(page_size)
  ).scalars().all()

  return {
    'items': [
      {
        'requirement_id': r.requirement_id,
        'adw_execution_id': r.adw_execution_id,
        'execution_status': r.execution_status,
        'current_phase': r.current_phase,
        'plan_status': r.plan_status,
        'build_status': r.build_status,
        'ship_status': r.ship_status,
        'execution_started_at': r.execution_started_at.isoformat() if r.execution_started_at else None,
        'execution_completed_at': r.execution_completed_at.isoformat() if r.execution_completed_at else None,
        'execution_error': r.execution_error,
        'retry_count': r.retry_count,
      }
      for r in items
    ],
    'total': total,
    'page': page,
    'page_size': page_size,
  }


@router.get('/executions/{execution_id}')
def get_execution(
  execution_id: str,
  db: Session = Depends(get_db),
):
  """Get execution details by execution ID."""
  stmt = select(Requirement).where(Requirement.adw_execution_id == execution_id)
  requirement = db.execute(stmt).scalar_one_or_none()

  if not requirement:
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f'Execution {execution_id} not found')

  return {
    'requirement_id': requirement.requirement_id,
    'title': requirement.title,
    'adw_execution_id': requirement.adw_execution_id,
    'execution_status': requirement.execution_status,
    'current_phase': requirement.current_phase,
    'plan_status': requirement.plan_status,
    'plan_started_at': requirement.plan_started_at.isoformat() if requirement.plan_started_at else None,
    'plan_completed_at': requirement.plan_completed_at.isoformat() if requirement.plan_completed_at else None,
    'build_status': requirement.build_status,
    'build_started_at': requirement.build_started_at.isoformat() if requirement.build_started_at else None,
    'build_completed_at': requirement.build_completed_at.isoformat() if requirement.build_completed_at else None,
    'ship_status': requirement.ship_status,
    'ship_started_at': requirement.ship_started_at.isoformat() if requirement.ship_started_at else None,
    'ship_completed_at': requirement.ship_completed_at.isoformat() if requirement.ship_completed_at else None,
    'phase_error_message': requirement.phase_error_message,
    'execution_started_at': requirement.execution_started_at.isoformat() if requirement.execution_started_at else None,
    'execution_completed_at': requirement.execution_completed_at.isoformat() if requirement.execution_completed_at else None,
    'execution_error': requirement.execution_error,
    'retry_count': requirement.retry_count,
    'intervention_log': requirement.intervention_log,
  }


@router.post('/executions/{execution_id}/retry')
def retry_execution(
  execution_id: str,
  db: Session = Depends(get_db),
):
  """Retry a failed execution."""
  stmt = select(Requirement).where(Requirement.adw_execution_id == execution_id)
  requirement = db.execute(stmt).scalar_one_or_none()

  if not requirement:
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f'Execution {execution_id} not found')

  if requirement.execution_status != 'failed':
    from fastapi import HTTPException
    raise HTTPException(
      status_code=400,
      detail=f'Can only retry failed executions, current: {requirement.execution_status}',
    )

  from src.repository import RequirementRepository
  repo = RequirementRepository()
  repo.update(db, requirement.id, {
    'execution_status': 'pending_retry',
    'retry_count': requirement.retry_count + 1,
  })
  repo.create_audit(
    db,
    requirement_id=requirement.id,
    action='execution_retry',
    details={'execution_id': execution_id, 'retry_count': requirement.retry_count + 1},
  )

  return {'status': 'retry_queued', 'retry_count': requirement.retry_count + 1}


@router.post('/executions/{execution_id}/cancel')
def cancel_execution(
  execution_id: str,
  db: Session = Depends(get_db),
):
  """Cancel a running execution."""
  stmt = select(Requirement).where(Requirement.adw_execution_id == execution_id)
  requirement = db.execute(stmt).scalar_one_or_none()

  if not requirement:
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f'Execution {execution_id} not found')

  if requirement.execution_status != 'running':
    from fastapi import HTTPException
    raise HTTPException(
      status_code=400,
      detail=f'Can only cancel running executions, current: {requirement.execution_status}',
    )

  from src.repository import RequirementRepository
  repo = RequirementRepository()
  repo.update(db, requirement.id, {
    'execution_status': 'cancelled',
  })
  repo.create_audit(
    db,
    requirement_id=requirement.id,
    action='execution_cancelled',
    details={'execution_id': execution_id},
  )

  return {'status': 'cancelled'}


@router.get('/stats')
def get_stats(db: Session = Depends(get_db)):
  """Basic stats — total requirements, by status, by type."""
  total = db.execute(select(func.count()).select_from(Requirement)).scalar() or 0

  # By status
  status_stmt = (
    select(Requirement.status, func.count())
    .group_by(Requirement.status)
  )
  by_status = {row[0]: row[1] for row in db.execute(status_stmt).all()}

  # By type
  type_stmt = (
    select(Requirement.requirement_type, func.count())
    .group_by(Requirement.requirement_type)
  )
  by_type = {row[0]: row[1] for row in db.execute(type_stmt).all()}

  # Execution stats
  exec_stmt = (
    select(Requirement.execution_status, func.count())
    .where(Requirement.adw_execution_id.isnot(None))
    .group_by(Requirement.execution_status)
  )
  by_execution = {row[0]: row[1] for row in db.execute(exec_stmt).all()}

  return {
    'total_requirements': total,
    'by_status': by_status,
    'by_type': by_type,
    'by_execution_status': by_execution,
  }
