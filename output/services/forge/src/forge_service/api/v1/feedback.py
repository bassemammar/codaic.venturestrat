"""VentureStrat Forge — feedback widget endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.main import get_db
from src.requirement_service import RequirementService
from src.schemas import FeedbackCreate, RequirementResponse

router = APIRouter()
service = RequirementService()


@router.post('/', response_model=RequirementResponse, status_code=201)
def create_feedback(
  data: FeedbackCreate,
  db: Session = Depends(get_db),
):
  """Create a requirement from the PSC feedback widget.

  Simpler than full requirement creation — maps widget fields
  to a requirement with page_context and captured_context stored
  in spec_metadata.
  """
  requirement_data = {
    'title': data.title,
    'description': data.description,
    'requirement_type': data.requirement_type,
    'priority': data.priority,
    'spec_metadata': {
      'source': 'psc_widget',
      'page_context': data.page_context,
      'captured_context': data.captured_context,
    },
  }

  return service.create_requirement(db, requirement_data)
