"""VentureStrat Forge — ADW execution engine."""

import asyncio
import logging
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import Requirement
from src.repository import RequirementRepository
from src.sse_manager import sse_manager

logger = logging.getLogger(__name__)

repo = RequirementRepository()


class ADWExecutor:
  """Triggers and monitors ADW spec execution."""

  def trigger_execution(
    self,
    db: Session,
    requirement_id: str,
    spec_name: str,
  ) -> str:
    """Launch ADW execution for a spec. Returns execution ID."""
    from src.requirement_service import RequirementService
    svc = RequirementService()
    requirement = svc.get_requirement(db, requirement_id)

    execution_id = secrets.token_hex(4)

    repo.update(db, requirement.id, {
      'adw_execution_id': execution_id,
      'execution_status': 'running',
      'execution_started_at': datetime.utcnow(),
      'current_phase': 'plan',
      'plan_status': 'pending',
      'build_status': 'pending',
      'ship_status': 'pending',
    })
    repo.create_audit(
      db,
      requirement_id=requirement.id,
      action='execution_started',
      details={'execution_id': execution_id, 'spec_name': spec_name},
    )

    # Launch background monitoring
    asyncio.create_task(
      self._run_and_monitor(requirement_id, execution_id, spec_name)
    )

    logger.info(f'Triggered ADW execution {execution_id} for {requirement_id}')
    return execution_id

  async def _run_and_monitor(
    self,
    requirement_id: str,
    execution_id: str,
    spec_name: str,
  ):
    """Run ADW subprocess and monitor output."""
    try:
      process = await asyncio.create_subprocess_exec(
        'adw', 'execute', spec_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
      )

      sse_manager.publish(requirement_id, {
        'event_type': 'execution_started',
        'data': {'execution_id': execution_id, 'spec_name': spec_name},
        'timestamp': datetime.utcnow().isoformat(),
      })

      async for line in process.stdout:
        decoded = line.decode().strip()
        if not decoded:
          continue

        logger.debug(f'[{execution_id}] {decoded}')

        # Parse phase updates
        phase_event = self._parse_phase(decoded)
        if phase_event:
          sse_manager.publish(requirement_id, {
            'event_type': 'phase_update',
            'data': phase_event,
            'timestamp': datetime.utcnow().isoformat(),
          })

        # Stream raw output
        sse_manager.publish(requirement_id, {
          'event_type': 'output',
          'data': {'line': decoded},
          'timestamp': datetime.utcnow().isoformat(),
        })

      await process.wait()

      final_status = 'completed' if process.returncode == 0 else 'failed'
      error_msg = None if process.returncode == 0 else f'Process exited with code {process.returncode}'

      sse_manager.publish(requirement_id, {
        'event_type': 'execution_finished',
        'data': {
          'execution_id': execution_id,
          'status': final_status,
          'return_code': process.returncode,
        },
        'timestamp': datetime.utcnow().isoformat(),
      })

      logger.info(f'Execution {execution_id} finished: {final_status}')

    except Exception as e:
      logger.error(f'Execution {execution_id} error: {e}')
      sse_manager.publish(requirement_id, {
        'event_type': 'execution_error',
        'data': {'execution_id': execution_id, 'error': str(e)},
        'timestamp': datetime.utcnow().isoformat(),
      })

  def _parse_phase(self, line: str) -> dict | None:
    """Parse a log line for phase transition markers."""
    line_lower = line.lower()

    for phase in ('plan', 'build', 'ship'):
      if f'[{phase}]' in line_lower or f'phase: {phase}' in line_lower:
        if 'started' in line_lower or 'starting' in line_lower:
          return {'phase': phase, 'status': 'running'}
        elif 'completed' in line_lower or 'finished' in line_lower:
          return {'phase': phase, 'status': 'completed'}
        elif 'failed' in line_lower or 'error' in line_lower:
          return {'phase': phase, 'status': 'failed', 'message': line}

    return None
