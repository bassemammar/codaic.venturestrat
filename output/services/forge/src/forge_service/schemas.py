"""VentureStrat Forge — Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# --- Create / Update ---

class RequirementCreate(BaseModel):
  """Schema for creating a new requirement."""
  title: str
  description: str
  requirement_type: str = 'new_feature'
  priority: str = 'medium'
  spec_content: Optional[str] = None
  spec_metadata: Optional[dict] = None


class RequirementUpdate(BaseModel):
  """Schema for updating an existing requirement."""
  title: Optional[str] = None
  description: Optional[str] = None
  priority: Optional[str] = None
  spec_content: Optional[str] = None
  spec_metadata: Optional[dict] = None


# --- Response ---

class RequirementResponse(BaseModel):
  """Full requirement response."""
  model_config = ConfigDict(from_attributes=True)

  id: int
  requirement_id: str
  title: str
  description: Optional[str] = None
  requirement_type: str
  priority: str
  status: str
  spec_content: Optional[str] = None
  spec_metadata: Optional[dict] = None
  adw_execution_id: Optional[str] = None
  execution_status: Optional[str] = None
  execution_started_at: Optional[datetime] = None
  execution_completed_at: Optional[datetime] = None
  execution_error: Optional[str] = None
  current_phase: Optional[str] = None
  plan_status: Optional[str] = None
  plan_started_at: Optional[datetime] = None
  plan_completed_at: Optional[datetime] = None
  build_status: Optional[str] = None
  build_started_at: Optional[datetime] = None
  build_completed_at: Optional[datetime] = None
  ship_status: Optional[str] = None
  ship_started_at: Optional[datetime] = None
  ship_completed_at: Optional[datetime] = None
  phase_error_message: Optional[str] = None
  submitter_id: Optional[int] = None
  reviewer_id: Optional[int] = None
  review_comments: Optional[str] = None
  retry_count: int = 0
  intervention_log: Optional[dict] = None
  created_at: datetime
  updated_at: datetime
  submitted_at: Optional[datetime] = None
  reviewed_at: Optional[datetime] = None


class RequirementListResponse(BaseModel):
  """Paginated list of requirements."""
  items: list[RequirementResponse]
  total: int
  page: int
  page_size: int


# --- Actions ---

class SubmitForReview(BaseModel):
  """Submit a requirement for review."""
  submitter_id: int


class ApproveRequirement(BaseModel):
  """Approve a requirement."""
  reviewer_id: int
  review_comments: Optional[str] = None


class RejectRequirement(BaseModel):
  """Reject a requirement."""
  reviewer_id: int
  review_comments: Optional[str] = None


class TriggerExecution(BaseModel):
  """Trigger ADW execution for an approved requirement."""
  pass


class ExecutionResponse(BaseModel):
  """Response after triggering execution."""
  adw_execution_id: str
  sse_stream_url: str


# --- Feedback Widget ---

class FeedbackCreate(BaseModel):
  """Schema for the PSC feedback widget."""
  title: str
  description: str
  requirement_type: str = 'bug_fix'
  priority: str = 'medium'
  page_context: Optional[dict] = None
  captured_context: Optional[dict] = None


# --- SSE ---

class StreamEvent(BaseModel):
  """Server-sent event payload."""
  event_type: str
  data: dict
  timestamp: str
