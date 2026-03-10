"""Custom schemas for document generation endpoints.

These are NOT codegen-generated — they define request/response models for
the custom /preview, /generate, /download, and /validate endpoints.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime


class PartyReference(BaseModel):
  """Reference to a company + signatory for document generation."""
  company_id: str = Field(..., description='UUID of LegalEntity')
  signatory_person_id: Optional[str] = Field(
    default=None, description='UUID of ContactPerson signing'
  )


class DocumentData(BaseModel):
  """Party and configuration data for document generation."""
  party_a: PartyReference
  party_b: PartyReference
  configuration: dict[str, Any] = Field(default_factory=dict)


class DocumentPreviewRequest(BaseModel):
  """Request body for POST /documents/preview."""
  document_type: str = Field(..., max_length=50)
  title: str = Field(..., max_length=255)
  document_data: DocumentData
  format: str = Field(default='markdown')


class DocumentPreviewResponse(BaseModel):
  """Response for POST /documents/preview."""
  title: str
  content_preview: str
  estimated_pages: int
  word_count: int


class DocumentGenerateRequest(BaseModel):
  """Request body for POST /documents/generate."""
  document_type: str = Field(..., max_length=50)
  title: str = Field(..., max_length=255)
  document_data: DocumentData
  format: str = Field(default='markdown')


class DocumentMetadata(BaseModel):
  """Metadata about the generated document."""
  word_count: int
  clause_count: int
  page_count: int


class DocumentGenerateResponse(BaseModel):
  """Response for POST /documents/generate."""
  document: dict[str, Any]
  download_url: str
  preview_url: str
  metadata: DocumentMetadata


class DocumentValidateRequest(BaseModel):
  """Request body for POST /documents/validate."""
  legal_entity_id: str
  validation_type: str = Field(
    ..., description='One of: equity, person, company, all'
  )


class ValidationErrorResponse(BaseModel):
  """Single validation error in response."""
  rule_id: str
  severity: str
  message: str
  field: str
  blocking: bool


class DocumentValidateResponse(BaseModel):
  """Response for POST /documents/validate."""
  valid: bool
  errors: list[ValidationErrorResponse] = Field(default_factory=list)
  warnings: list[ValidationErrorResponse] = Field(default_factory=list)
