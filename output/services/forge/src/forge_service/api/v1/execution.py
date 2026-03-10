"""VentureStrat Forge — execution endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from src.main import get_db
from src.adw_executor import ADWExecutor
from src.config import get_settings
from src.requirement_service import RequirementService
from src.schemas import ExecutionResponse, TriggerExecution
from src.spec_generator import SpecGenerator
from src.sse_manager import sse_manager

router = APIRouter()
service = RequirementService()
executor = ADWExecutor()
spec_gen = SpecGenerator()
settings = get_settings()


@router.post('/{requirement_id}', response_model=ExecutionResponse)
def trigger_execution(
  requirement_id: str,
  body: TriggerExecution = TriggerExecution(),
  db: Session = Depends(get_db),
):
  """Trigger ADW execution for an approved requirement."""
  requirement = service.get_requirement(db, requirement_id)

  if requirement.status != 'approved':
    raise HTTPException(
      status_code=400,
      detail=f'Requirement must be approved to execute, current status: {requirement.status}',
    )

  # Generate spec files
  spec_name = spec_gen.generate_spec(requirement, settings.PLATFORM_ROOT)

  # Trigger ADW execution
  execution_id = executor.trigger_execution(db, requirement_id, spec_name)

  return ExecutionResponse(
    adw_execution_id=execution_id,
    sse_stream_url=f'/api/v1/forge/execution/{requirement_id}/stream',
  )


@router.get('/{requirement_id}/stream')
async def stream_execution(requirement_id: str):
  """SSE endpoint streaming execution progress."""
  return EventSourceResponse(sse_manager.subscribe(requirement_id))
