"""Custom document generation endpoints.

POST /preview — render preview without saving
POST /generate — full generation flow with DOCX + storage
GET /{id}/download — download generated document
POST /validate — run cross-document validation rules
"""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, Response

from legal_service.schemas.document_generation import (
  DocumentPreviewRequest,
  DocumentPreviewResponse,
  DocumentGenerateRequest,
  DocumentGenerateResponse,
  DocumentValidateRequest,
  DocumentValidateResponse,
)
from legal_service.application.services.document_generation_service import (
  DocumentGenerationService,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=['document-generation'])

# Service singleton — lazy-initialized
_service_instance: DocumentGenerationService | None = None


def _get_document_service() -> DocumentGenerationService:
  """Get or create the document generation service singleton."""
  global _service_instance
  if _service_instance is None:
    _service_instance = DocumentGenerationService()
  return _service_instance


@router.post('/preview', response_model=DocumentPreviewResponse)
async def preview_document(body: DocumentPreviewRequest) -> dict[str, Any]:
  """Generate document preview without saving to database."""
  svc = _get_document_service()
  return await svc.preview_document(
    document_type=body.document_type,
    title=body.title,
    document_data=body.document_data.model_dump(),
    format=body.format,
  )


@router.post('/generate', response_model=DocumentGenerateResponse, status_code=201)
async def generate_document(
  body: DocumentGenerateRequest,
  request: Request,
) -> dict[str, Any]:
  """Generate document, save to database, create DOCX, return download URL."""
  user_id = getattr(request.state, 'user_id', 'anonymous') if hasattr(request, 'state') else 'anonymous'
  tenant_id = getattr(request.state, 'tenant_id', None) if hasattr(request, 'state') else None

  svc = _get_document_service()
  return await svc.generate_document(
    document_type=body.document_type,
    title=body.title,
    document_data=body.document_data.model_dump(),
    user_id=user_id,
    tenant_id=tenant_id,
  )


@router.get('/{document_id}/download')
async def download_document(
  document_id: str,
  format: str = Query('docx', description='Download format: docx or md'),
  request: Request = None,
) -> Response:
  """Download generated document as DOCX or markdown."""
  user_id = None
  if request and hasattr(request, 'state'):
    user_id = getattr(request.state, 'user_id', None)

  svc = _get_document_service()
  result = await svc.download_document(
    document_id=document_id,
    format=format,
    user_id=user_id,
  )

  return Response(
    content=result['content'],
    media_type=result['media_type'],
    headers={
      'Content-Disposition': f'attachment; filename="{result["filename"]}"',
    },
  )


@router.post('/validate', response_model=DocumentValidateResponse)
async def validate_document(body: DocumentValidateRequest) -> dict[str, Any]:
  """Run cross-document validation rules."""
  svc = _get_document_service()
  return await svc.validate_entity(
    legal_entity_id=body.legal_entity_id,
    validation_type=body.validation_type,
  )
